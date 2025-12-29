"""
CalDAV Calendar integration connector.

Supports CalDAV servers such as Zimbra by using WebDAV PROPFIND/REPORT requests
and parsing iCalendar (VEVENT) payloads.

This connector is **not OAuth-based**. Credentials are stored as:
- IntegrationCredential.access_token: password (or app password)
- IntegrationCredential.extra_data.username: username

Integration.config fields used:
- calendar_url: full CalDAV calendar collection URL (ends with '/')
- calendar_name: optional display name
- server_url: optional base server URL for discovery
- verify_ssl: bool (default True)
- sync_direction: 'calendar_to_time_tracker' | 'time_tracker_to_calendar' | 'bidirectional'
- default_project_id: int (required for importing as TimeEntry)
- lookback_days: int (default 90)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import requests
from icalendar import Calendar

from app.integrations.base import BaseConnector
from app.utils.timezone import get_timezone_obj, local_to_utc, utc_to_local, now_in_app_timezone


DAV_NS = "DAV:"
CALDAV_NS = "urn:ietf:params:xml:ns:caldav"


def _ns(tag: str, ns: str) -> str:
    return f"{{{ns}}}{tag}"


def _ensure_trailing_slash(u: str) -> str:
    return u if u.endswith("/") else (u + "/")


def _to_local_naive(dt: datetime) -> datetime:
    """
    Convert a datetime to app-local timezone and drop tzinfo (DB stores local naive).
    """
    tz = get_timezone_obj()
    if dt.tzinfo is None:
        # Treat as local app time already
        return dt
    return dt.astimezone(tz).replace(tzinfo=None)


def _to_utc_aware(dt_local_naive: datetime) -> datetime:
    """
    Convert app-local naive datetime to UTC aware.
    """
    return local_to_utc(dt_local_naive)


def _datetime_to_caldav_utc(dt_utc: datetime) -> str:
    """
    CalDAV time-range uses UTC timestamps in basic format: YYYYMMDDTHHMMSSZ
    """
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    dt_utc = dt_utc.astimezone(timezone.utc)
    return dt_utc.strftime("%Y%m%dT%H%M%SZ")


@dataclass(frozen=True)
class CalDAVCalendar:
    href: str
    name: str


class CalDAVClient:
    """
    Minimal CalDAV client using requests.
    """

    def __init__(self, username: str, password: str, verify_ssl: bool = True, timeout: int = 20):
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = timeout

    def _request(self, method: str, url: str, *, headers: Optional[Dict[str, str]] = None, data: Optional[str] = None):
        h = {
            "User-Agent": "TimeTracker-CalDAV/1.0",
        }
        if headers:
            h.update(headers)
        try:
            resp = requests.request(
                method,
                url,
                headers=h,
                data=data.encode("utf-8") if isinstance(data, str) else data,
                auth=(self.username, self.password),
                verify=self.verify_ssl,
                timeout=self.timeout,
            )
            return resp
        except requests.exceptions.SSLError as e:
            raise ValueError(f"SSL certificate verification failed. If using a self-signed certificate, disable SSL verification in settings. Error: {str(e)}") from e
        except requests.exceptions.Timeout as e:
            raise ValueError(f"Request timeout after {self.timeout} seconds. The server may be slow or unreachable.") from e
        except requests.exceptions.ConnectionError as e:
            raise ValueError(f"Connection error: {str(e)}. Please check the server URL and network connectivity.") from e

    def _propfind(self, url: str, xml_body: str, depth: str = "0") -> ET.Element:
        resp = self._request(
            "PROPFIND",
            url,
            headers={"Depth": depth, "Content-Type": "application/xml; charset=utf-8"},
            data=xml_body,
        )
        resp.raise_for_status()
        if not resp.text or not resp.text.strip():
            raise ValueError(f"Empty response from PROPFIND request to {url}")
        try:
            return ET.fromstring(resp.text)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML response from server: {str(e)}") from e

    def _report(self, url: str, xml_body: str, depth: str = "1") -> ET.Element:
        resp = self._request(
            "REPORT",
            url,
            headers={"Depth": depth, "Content-Type": "application/xml; charset=utf-8"},
            data=xml_body,
        )
        resp.raise_for_status()
        if not resp.text or not resp.text.strip():
            # Empty response might mean no events found, return empty multistatus
            return ET.Element(_ns("multistatus", DAV_NS))
        try:
            return ET.fromstring(resp.text)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML response from server: {str(e)}") from e

    def discover_calendars(self, server_url: str) -> List[CalDAVCalendar]:
        """
        Best-effort CalDAV discovery:
        - PROPFIND server_url depth 0 for current-user-principal
        - PROPFIND principal for calendar-home-set
        - PROPFIND home-set depth 1 for calendars
        """
        server_url = _ensure_trailing_slash(server_url)

        # 1) Find current-user-principal
        try:
            body = (
                '<?xml version="1.0" encoding="utf-8" ?>'
                f'<d:propfind xmlns:d="{DAV_NS}">'
                "<d:prop><d:current-user-principal/></d:prop>"
                "</d:propfind>"
            )
            root = self._propfind(server_url, body, depth="0")
            principal_href = self._find_href(root, [(_ns("current-user-principal", DAV_NS),)])
            if not principal_href:
                # Some servers support well-known principal path fallback
                principal_href = "/.well-known/caldav"
        except Exception as e:
            raise ValueError(f"Failed to discover current-user-principal from {server_url}: {str(e)}") from e

        principal_url = urljoin(server_url, principal_href)

        # 2) Find calendar-home-set on principal
        try:
            body = (
                '<?xml version="1.0" encoding="utf-8" ?>'
                f'<d:propfind xmlns:d="{DAV_NS}" xmlns:cs="{CALDAV_NS}">'
                "<d:prop><cs:calendar-home-set/></d:prop>"
                "</d:propfind>"
            )
            root = self._propfind(principal_url, body, depth="0")
            home_href = self._find_href(root, [(_ns("calendar-home-set", CALDAV_NS),)])
            if not home_href:
                raise ValueError("Could not discover calendar-home-set from CalDAV server. The server may not support CalDAV or the credentials may be incorrect.")
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to discover calendar-home-set from {principal_url}: {str(e)}") from e

        home_url = urljoin(server_url, home_href)

        # 3) List calendars (Depth: 1)
        body = (
            '<?xml version="1.0" encoding="utf-8" ?>'
            f'<d:propfind xmlns:d="{DAV_NS}" xmlns:cs="{CALDAV_NS}">'
            "<d:prop>"
            "<d:displayname/>"
            "<d:resourcetype/>"
            "</d:prop>"
            "</d:propfind>"
        )
        root = self._propfind(home_url, body, depth="1")

        calendars: List[CalDAVCalendar] = []
        for resp in root.findall(_ns("response", DAV_NS)):
            href_el = resp.find(_ns("href", DAV_NS))
            href = href_el.text.strip() if href_el is not None and href_el.text else None
            if not href:
                continue

            prop = resp.find(f".//{_ns('prop', DAV_NS)}")
            if prop is None:
                continue

            res_type = prop.find(_ns("resourcetype", DAV_NS))
            if res_type is None:
                continue

            is_calendar = res_type.find(_ns("calendar", CALDAV_NS)) is not None
            if not is_calendar:
                continue

            dn_el = prop.find(_ns("displayname", DAV_NS))
            displayname = dn_el.text.strip() if dn_el is not None and dn_el.text else href

            calendars.append(CalDAVCalendar(href=urljoin(server_url, href), name=displayname))

        return calendars

    def fetch_events(self, calendar_url: str, time_min_utc: datetime, time_max_utc: datetime) -> List[Dict[str, Any]]:
        """
        Fetch VEVENTs within a time range using a calendar-query REPORT.
        Returns a list of dicts with uid, summary, description, start, end, href.
        
        Note: Recurring events (RRULE) are not expanded - only instances that fall
        within the time range are returned if the server supports it.
        """
        calendar_url = _ensure_trailing_slash(calendar_url)
        
        # Validate time range
        if time_max_utc <= time_min_utc:
            raise ValueError("time_max_utc must be after time_min_utc")

        start_utc = _datetime_to_caldav_utc(time_min_utc)
        end_utc = _datetime_to_caldav_utc(time_max_utc)

        body = (
            '<?xml version="1.0" encoding="utf-8" ?>'
            f'<c:calendar-query xmlns:d="{DAV_NS}" xmlns:c="{CALDAV_NS}">'
            "<d:prop>"
            "<d:getetag/>"
            "<c:calendar-data/>"
            "</d:prop>"
            "<c:filter>"
            "<c:comp-filter name=\"VCALENDAR\">"
            "<c:comp-filter name=\"VEVENT\">"
            f'<c:time-range start="{start_utc}" end="{end_utc}"/>'
            "</c:comp-filter>"
            "</c:comp-filter>"
            "</c:filter>"
            "</c:calendar-query>"
        )

        root = self._report(calendar_url, body, depth="1")

        events: List[Dict[str, Any]] = []
        for resp in root.findall(_ns("response", DAV_NS)):
            href_el = resp.find(_ns("href", DAV_NS))
            href = href_el.text.strip() if href_el is not None and href_el.text else None
            if not href:
                continue

            caldata_el = resp.find(f".//{_ns('calendar-data', CALDAV_NS)}")
            if caldata_el is None or not caldata_el.text:
                continue

            ics = caldata_el.text
            try:
                cal = Calendar.from_ical(ics)
            except Exception as e:
                # Log parsing errors but continue with other events
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Failed to parse iCalendar data for event {href}: {e}")
                continue

            for comp in cal.walk():
                if comp.name != "VEVENT":
                    continue

                uid = str(comp.get("UID", "")).strip()
                if not uid:
                    continue

                dtstart = comp.get("DTSTART")
                if not dtstart:
                    continue

                start = dtstart.dt
                # Skip all-day events (date objects, not datetime)
                if not isinstance(start, datetime):
                    continue

                # Handle DTEND or DURATION
                dtend = comp.get("DTEND")
                duration = comp.get("DURATION")
                
                if dtend:
                    end = dtend.dt
                    if not isinstance(end, datetime):
                        continue
                elif duration:
                    # Calculate end from start + duration
                    dur = duration.dt
                    if isinstance(dur, timedelta):
                        end = start + dur
                    else:
                        # Skip if duration is not a timedelta
                        continue
                else:
                    # No DTEND or DURATION - skip this event
                    continue

                summary = str(comp.get("SUMMARY", "")).strip()
                description = str(comp.get("DESCRIPTION", "")).strip()

                events.append(
                    {
                        "uid": uid,
                        "summary": summary,
                        "description": description,
                        "start": start,
                        "end": end,
                        "href": urljoin(calendar_url, href),
                    }
                )

        return events

    def create_or_update_event(self, calendar_url: str, event_uid: str, ical_content: str, event_href: Optional[str] = None) -> bool:
        """
        Create or update a calendar event using PUT request.
        
        Args:
            calendar_url: Calendar collection URL
            event_uid: Unique identifier for the event
            ical_content: iCalendar content (VCALENDAR with VEVENT)
            event_href: Optional existing event href for updates
        
        Returns:
            True if successful, False otherwise
        """
        calendar_url = _ensure_trailing_slash(calendar_url)
        # Use provided href if available, otherwise construct from UID
        if event_href:
            event_url = event_href
        else:
            # Event URL is typically: calendar_url + event_uid + ".ics"
            event_url = urljoin(calendar_url, f"{event_uid}.ics")
        
        headers = {
            "Content-Type": "text/calendar; charset=utf-8",
        }
        
        try:
            resp = self._request("PUT", event_url, headers=headers, data=ical_content)
            resp.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            import logging
            logger = logging.getLogger(__name__)
            if e.response.status_code == 404:
                logger.warning(f"CalDAV event {event_uid} not found at {event_url}, attempting to create")
                # Try creating with standard URL if custom href failed
                if event_href and event_href != urljoin(calendar_url, f"{event_uid}.ics"):
                    standard_url = urljoin(calendar_url, f"{event_uid}.ics")
                    try:
                        resp = self._request("PUT", standard_url, headers=headers, data=ical_content)
                        resp.raise_for_status()
                        return True
                    except Exception:
                        pass
            logger.error(f"Failed to create/update CalDAV event {event_uid}: {e}")
            return False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create/update CalDAV event {event_uid}: {e}", exc_info=True)
            return False

    def _find_href(self, root: ET.Element, prop_paths: List[Tuple[str, ...]]) -> Optional[str]:
        """
        Find a DAV:href under a given prop path.
        Currently supports one-level CalDAV props.
        """
        # Typical shape:
        # multistatus/response/propstat/prop/<propname>/href
        for response in root.findall(_ns("response", DAV_NS)):
            prop = response.find(f".//{_ns('prop', DAV_NS)}")
            if prop is None:
                continue
            # Search for either DAV or CalDAV prop
            for prop_tag_tuple in prop_paths:
                prop_tag = prop_tag_tuple[0]
                el = prop.find(prop_tag)
                if el is None:
                    continue
                href_el = el.find(_ns("href", DAV_NS))
                if href_el is not None and href_el.text:
                    return href_el.text.strip()
        return None


class CalDAVCalendarConnector(BaseConnector):
    """CalDAV integration connector."""

    display_name = "CalDAV Calendar"
    description = "Import/sync with a CalDAV calendar (e.g., Zimbra)"
    icon = "calendar"

    @property
    def provider_name(self) -> str:
        return "caldav_calendar"

    # --- OAuth methods (not used) ---
    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:  # noqa: ARG002
        raise NotImplementedError("CalDAV does not use OAuth in this integration. Use the CalDAV setup form.")

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:  # noqa: ARG002
        raise NotImplementedError("CalDAV does not use OAuth in this integration.")

    def refresh_access_token(self) -> Dict[str, Any]:
        raise NotImplementedError("CalDAV does not use OAuth token refresh in this integration.")

    # --- Helpers ---
    def _get_basic_creds(self) -> Tuple[str, str]:
        if not self.credentials:
            raise ValueError("Missing CalDAV credentials.")
        username = (self.credentials.extra_data or {}).get("username")
        password = self.credentials.access_token
        if not username or not password:
            raise ValueError("Missing CalDAV username/password.")
        return username, password

    def _client(self) -> CalDAVClient:
        username, password = self._get_basic_creds()
        verify_ssl = bool(self.integration.config.get("verify_ssl", True)) if self.integration else True
        return CalDAVClient(username=username, password=password, verify_ssl=verify_ssl)

    # --- Public API ---
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connectivity and (optionally) discover calendars.
        """
        try:
            # Check if credentials exist
            if not self.credentials:
                return {"success": False, "message": "No credentials configured. Please set up username and password."}
            
            # Check if we have username and password
            try:
                username, password = self._get_basic_creds()
            except ValueError as e:
                return {"success": False, "message": f"Missing credentials: {str(e)}. Please configure username and password."}
            
            cfg = self.integration.config or {}
            server_url = cfg.get("server_url")
            calendar_url = cfg.get("calendar_url")

            # Need at least one URL
            if not server_url and not calendar_url:
                return {"success": False, "message": "Either server URL or calendar URL must be configured."}

            client = self._client()

            calendars: List[CalDAVCalendar] = []
            if server_url:
                try:
                    calendars = client.discover_calendars(server_url)
                except Exception as e:
                    # If discovery fails but we have calendar_url, continue with calendar_url test
                    if not calendar_url:
                        return {"success": False, "message": f"Failed to discover calendars from server: {str(e)}"}

            # If a calendar URL is provided, validate we can run a REPORT against it (lightweight window)
            if calendar_url:
                try:
                    now_utc = datetime.now(timezone.utc)
                    _ = client.fetch_events(calendar_url, now_utc - timedelta(days=1), now_utc + timedelta(days=1))
                except Exception as e:
                    return {"success": False, "message": f"Failed to access calendar at {calendar_url}: {str(e)}"}

            return {
                "success": True,
                "message": f"Connected to CalDAV. Found {len(calendars)} calendars." if server_url else "Connected to CalDAV calendar.",
                "calendars": [{"url": c.href, "name": c.name} for c in calendars],
            }
        except Exception as e:
            return {"success": False, "message": f"Connection test failed: {str(e)}"}

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """
        Sync data between CalDAV and TimeTracker.
        MVP: calendar_to_time_tracker imports VEVENTs as TimeEntry records.
        """
        from app import db
        from app.models import TimeEntry, Project, IntegrationExternalEventLink
        import logging

        logger = logging.getLogger(__name__)

        try:
            if not self.integration or not self.integration.user_id:
                return {"success": False, "message": "CalDAV integration must be a per-user integration."}

            # Check credentials
            if not self.credentials:
                return {"success": False, "message": "No credentials configured. Please set up username and password."}
            
            try:
                username, password = self._get_basic_creds()
            except ValueError as e:
                return {"success": False, "message": f"Missing credentials: {str(e)}. Please configure username and password."}

            cfg = self.integration.config or {}
            calendar_url = cfg.get("calendar_url")
            server_url = cfg.get("server_url")
            
            if not calendar_url:
                if server_url:
                    # Try to discover and use first calendar
                    try:
                        client = self._client()
                        logger.info(f"Discovering calendars from server: {server_url}")
                        calendars = client.discover_calendars(server_url)
                        if calendars:
                            calendar_url = calendars[0].href
                            logger.info(f"Discovered calendar: {calendar_url} ({calendars[0].name})")
                            # Update config with discovered calendar
                            if not self.integration.config:
                                self.integration.config = {}
                            self.integration.config["calendar_url"] = calendar_url
                            if not self.integration.config.get("calendar_name"):
                                self.integration.config["calendar_name"] = calendars[0].name
                            # Save the discovered calendar URL
                            db.session.commit()
                        else:
                            return {"success": False, "message": "No calendars found on server. Please configure calendar URL manually."}
                    except Exception as e:
                        logger.error(f"Could not discover calendars: {e}", exc_info=True)
                        return {"success": False, "message": f"Could not discover calendars: {str(e)}. Please configure calendar URL manually."}
                else:
                    return {"success": False, "message": "No calendar selected. Please configure calendar URL or server URL first."}

            sync_direction = cfg.get("sync_direction", "calendar_to_time_tracker")
            default_project_id = cfg.get("default_project_id")
            lookback_days = int(cfg.get("lookback_days", 90))

            if sync_direction in ("calendar_to_time_tracker", "bidirectional"):
                calendar_result = self._sync_calendar_to_time_tracker(cfg, calendar_url, sync_type, default_project_id, lookback_days)
                # If bidirectional, also do TimeTracker to Calendar sync
                if sync_direction == "bidirectional":
                    tracker_result = self._sync_time_tracker_to_calendar(cfg, calendar_url, sync_type)
                    # Merge results
                    if calendar_result.get("success") and tracker_result.get("success"):
                        return {
                            "success": True,
                            "synced_items": calendar_result.get("synced_items", 0) + tracker_result.get("synced_items", 0),
                            "imported": calendar_result.get("imported", 0),
                            "skipped": calendar_result.get("skipped", 0),
                            "errors": calendar_result.get("errors", []) + tracker_result.get("errors", []),
                            "message": f"Bidirectional sync: Calendar→TimeTracker: {calendar_result.get('message', '')} | TimeTracker→Calendar: {tracker_result.get('message', '')}",
                        }
                    elif calendar_result.get("success"):
                        return calendar_result
                    elif tracker_result.get("success"):
                        return tracker_result
                    else:
                        return {"success": False, "message": f"Both sync directions failed. Calendar→TimeTracker: {calendar_result.get('message')}, TimeTracker→Calendar: {tracker_result.get('message')}"}
                return calendar_result

            # Handle TimeTracker to Calendar sync
            if sync_direction == "time_tracker_to_calendar":
                return self._sync_time_tracker_to_calendar(cfg, calendar_url, sync_type)
            
            return {"success": False, "message": f"Unknown sync direction: {sync_direction}"}
        except Exception as e:
            try:
                from app import db

                db.session.rollback()
            except Exception:
                pass
            if self.integration:
                self.integration.last_sync_status = "error"
                self.integration.last_error = str(e)
                try:
                    from app import db

                    db.session.commit()
                except Exception:
                    pass
            return {"success": False, "message": f"Sync failed: {str(e)}"}
    
    def _sync_calendar_to_time_tracker(self, cfg: Dict[str, Any], calendar_url: str, sync_type: str, default_project_id: Optional[int], lookback_days: int) -> Dict[str, Any]:
        """Sync calendar events to TimeTracker time entries."""
        from app.models import Project, TimeEntry
        from app.models.integration_external_event_link import IntegrationExternalEventLink
        
        if not default_project_id:
            return {"success": False, "message": "default_project_id is required to import calendar events as time entries."}

        # Determine time window
        if sync_type == "incremental" and self.integration.last_sync_at:
            time_min_utc = self.integration.last_sync_at.replace(tzinfo=timezone.utc)
        else:
            time_min_utc = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        time_max_utc = datetime.now(timezone.utc) + timedelta(days=7)

        logger.info(f"Fetching events from {calendar_url} between {time_min_utc} and {time_max_utc}")
        client = self._client()
        try:
            events = client.fetch_events(calendar_url, time_min_utc, time_max_utc)
            logger.info(f"Fetched {len(events)} events from CalDAV calendar")
            if len(events) == 0:
                logger.warning(f"No events found in calendar {calendar_url} for time range {time_min_utc} to {time_max_utc}")
        except Exception as e:
            logger.error(f"Failed to fetch events from calendar: {e}", exc_info=True)
            return {"success": False, "message": f"Failed to fetch events from calendar: {str(e)}"}

        # Preload projects for title matching
        projects = Project.query.filter_by(status="active").order_by(Project.name).all()

        imported = 0
        skipped = 0
        errors: List[str] = []

        if len(events) == 0:
            self.integration.last_sync_at = datetime.utcnow()
            self.integration.last_sync_status = "success"
            self.integration.last_error = None
            db.session.commit()
            return {
                "success": True,
                "imported": 0,
                "skipped": 0,
                "synced_items": 0,
                "errors": [],
                "message": f"No events found in calendar for the specified time range ({time_min_utc.date()} to {time_max_utc.date()}).",
            }

        for ev in events:
            try:
                uid = ev["uid"]
                existing_link = IntegrationExternalEventLink.query.filter_by(
                    integration_id=self.integration.id, external_uid=uid
                ).first()
                if existing_link:
                    skipped += 1
                    continue

                start_dt: datetime = ev["start"]
                end_dt: datetime = ev["end"]

                start_local = _to_local_naive(start_dt)
                end_local = _to_local_naive(end_dt)

                if end_local <= start_local:
                    skipped += 1
                    continue

                project_id = int(default_project_id)
                title = (ev.get("summary") or "").strip()
                for p in projects:
                    if p and p.name and p.name in title:
                        project_id = p.id
                        break

                notes_parts = []
                if title:
                    notes_parts.append(title)
                desc = (ev.get("description") or "").strip()
                if desc:
                    notes_parts.append(desc)
                notes = "\n\n".join(notes_parts) if notes_parts else None

                time_entry = TimeEntry(
                    user_id=self.integration.user_id,
                    project_id=project_id,
                    start_time=start_local,
                    end_time=end_local,
                    notes=notes,
                    source="auto",
                    billable=True,
                )

                db.session.add(time_entry)
                db.session.flush()

                link = IntegrationExternalEventLink(
                    integration_id=self.integration.id,
                    time_entry_id=time_entry.id,
                    external_uid=uid,
                    external_href=ev.get("href"),
                )
                db.session.add(link)
                db.session.flush()

                imported += 1
            except Exception as e:
                error_str = str(e).lower()
                if "unique" in error_str or "duplicate" in error_str or "uq_integration_external_uid" in error_str:
                    skipped += 1
                    logger.debug(f"Event {ev.get('uid', 'unknown')} already imported (duplicate UID - race condition)")
                else:
                    error_msg = f"Event {ev.get('uid', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning(f"Failed to import event {ev.get('uid', 'unknown')}: {e}")

        self.integration.last_sync_at = datetime.utcnow()
        self.integration.last_sync_status = "success" if not errors else "partial"
        self.integration.last_error = "; ".join(errors[:3]) if errors else None

        db.session.commit()

        if imported == 0 and skipped > 0:
            message = f"No new events imported ({skipped} already imported, {len(events)} total found)."
        elif imported == 0:
            message = f"No events found in calendar for the specified time range ({time_min_utc.date()} to {time_max_utc.date()})."
        else:
            message = f"Imported {imported} events ({skipped} skipped, {len(events)} total found)."

        logger.info(f"CalDAV sync completed: {message}")

        return {
            "success": True,
            "imported": imported,
            "skipped": skipped,
            "synced_items": imported,
            "errors": errors,
            "message": message,
        }
    
    def _sync_time_tracker_to_calendar(self, cfg: Dict[str, Any], calendar_url: str, sync_type: str) -> Dict[str, Any]:
        """Sync TimeTracker time entries to CalDAV calendar."""
        from app.models import TimeEntry, Project, Task
        from app.models.integration_external_event_link import IntegrationExternalEventLink
        
        lookback_days = int(cfg.get("lookback_days", 90))
        lookahead_days = int(cfg.get("lookahead_days", 7))
        
        if sync_type == "incremental" and self.integration.last_sync_at:
            time_min = self.integration.last_sync_at.replace(tzinfo=timezone.utc)
        else:
            time_min = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        time_max = datetime.now(timezone.utc) + timedelta(days=lookahead_days)
        
        time_min_local = _to_local_naive(time_min)
        time_max_local = _to_local_naive(time_max)
        
        time_entries = TimeEntry.query.filter(
            TimeEntry.user_id == self.integration.user_id,
            TimeEntry.start_time >= time_min_local,
            TimeEntry.start_time <= time_max_local,
            TimeEntry.end_time.isnot(None),
        ).order_by(TimeEntry.start_time).all()
        
        if not time_entries:
            self.integration.last_sync_at = datetime.utcnow()
            self.integration.last_sync_status = "success"
            self.integration.last_error = None
            db.session.commit()
            return {
                "success": True,
                "synced_items": 0,
                "errors": [],
                "message": f"No time entries found in the specified time range ({time_min_local.date()} to {time_max_local.date()}).",
            }
        
        client = self._client()
        synced = 0
        updated = 0
        errors: List[str] = []
        
        for time_entry in time_entries:
            try:
                event_uid = f"timetracker-{time_entry.id}@timetracker.local"
                
                existing_link = IntegrationExternalEventLink.query.filter_by(
                    integration_id=self.integration.id,
                    time_entry_id=time_entry.id
                ).first()
                
                project = Project.query.get(time_entry.project_id) if time_entry.project_id else None
                task = Task.query.get(time_entry.task_id) if time_entry.task_id else None
                
                title_parts = []
                if project:
                    title_parts.append(project.name)
                if task:
                    title_parts.append(task.name)
                if not title_parts:
                    title_parts.append("Time Entry")
                title = " - ".join(title_parts)
                
                description_parts = []
                if time_entry.notes:
                    description_parts.append(time_entry.notes)
                if time_entry.tags:
                    description_parts.append(f"Tags: {time_entry.tags}")
                description = "\n\n".join(description_parts) if description_parts else "TimeTracker: Created from time entry"
                
                start_utc = local_to_utc(time_entry.start_time)
                end_utc = local_to_utc(time_entry.end_time) if time_entry.end_time else start_utc + timedelta(hours=1)
                
                ical_content = self._generate_icalendar_event(
                    uid=event_uid,
                    title=title,
                    description=description,
                    start=start_utc,
                    end=end_utc,
                    created=time_entry.created_at.replace(tzinfo=timezone.utc) if time_entry.created_at else datetime.now(timezone.utc),
                    updated=time_entry.updated_at.replace(tzinfo=timezone.utc) if time_entry.updated_at else datetime.now(timezone.utc),
                )
                
                # Use existing href if available, otherwise generate new one
                event_href = existing_link.external_href if existing_link else urljoin(calendar_url, f"{event_uid}.ics")
                
                # For updates, we need to use the existing href
                if existing_link:
                    # Update existing event using its href
                    success = client.create_or_update_event(calendar_url, event_uid, ical_content, event_href=existing_link.external_href)
                    if success:
                        updated += 1
                    else:
                        errors.append(f"Failed to update time entry {time_entry.id} in calendar")
                else:
                    # Create new event
                    success = client.create_or_update_event(calendar_url, event_uid, ical_content)
                    if success:
                        link = IntegrationExternalEventLink(
                            integration_id=self.integration.id,
                            time_entry_id=time_entry.id,
                            external_uid=event_uid,
                            external_href=event_href,
                        )
                        db.session.add(link)
                        synced += 1
                    else:
                        errors.append(f"Failed to create time entry {time_entry.id} in calendar")
                    
            except Exception as e:
                error_msg = f"Time entry {time_entry.id}: {str(e)}"
                errors.append(error_msg)
                logger.warning(f"Failed to sync time entry {time_entry.id} to CalDAV: {e}")
        
        self.integration.last_sync_at = datetime.utcnow()
        self.integration.last_sync_status = "success" if not errors else "partial"
        self.integration.last_error = "; ".join(errors[:3]) if errors else None
        
        db.session.commit()
        
        message = f"Synced {synced} new events, updated {updated} events to CalDAV calendar."
        logger.info(f"CalDAV TimeTracker→Calendar sync completed: {message}")
        
        return {
            "success": True,
            "synced_items": synced + updated,
            "errors": errors,
            "message": message,
        }
    
    def _generate_icalendar_event(self, uid: str, title: str, description: str, start: datetime, end: datetime, created: datetime, updated: datetime) -> str:
        """Generate iCalendar content for an event."""
        from icalendar import Event
        
        event = Event()
        event.add('uid', uid)
        event.add('summary', title)
        event.add('description', description)
        event.add('dtstart', start)
        event.add('dtend', end)
        event.add('dtstamp', datetime.now(timezone.utc))
        event.add('created', created)
        event.add('last-modified', updated)
        event.add('status', 'CONFIRMED')
        event.add('transp', 'OPAQUE')
        
        cal = Calendar()
        cal.add('prodid', '-//TimeTracker//CalDAV Integration//EN')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')
        cal.add_component(event)
        
        return cal.to_ical().decode('utf-8')
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema."""
        return {
            "fields": [
                {
                    "name": "server_url",
                    "type": "url",
                    "label": "Server URL",
                    "required": False,
                    "placeholder": "https://mail.example.com/dav",
                    "description": "CalDAV server base URL (optional if calendar_url is provided)",
                    "help": "Base URL of your CalDAV server (e.g., https://mail.example.com/dav)",
                },
                {
                    "name": "calendar_url",
                    "type": "url",
                    "label": "Calendar URL",
                    "required": False,
                    "placeholder": "https://mail.example.com/dav/user/calendar/",
                    "description": "Full URL to the calendar collection (ends with /)",
                    "help": "Direct URL to your calendar. Must end with a forward slash (/).",
                },
                {
                    "name": "calendar_name",
                    "type": "string",
                    "label": "Calendar Name",
                    "required": False,
                    "placeholder": "My Calendar",
                    "description": "Display name for the calendar (optional)",
                },
                {
                    "name": "sync_direction",
                    "type": "select",
                    "label": "Sync Direction",
                    "options": [
                        {"value": "calendar_to_time_tracker", "label": "Calendar → TimeTracker (Import only)"},
                        {"value": "time_tracker_to_calendar", "label": "TimeTracker → Calendar (Export only)"},
                        {"value": "bidirectional", "label": "Bidirectional (Two-way sync)"},
                    ],
                    "default": "calendar_to_time_tracker",
                    "description": "Choose how data flows between CalDAV calendar and TimeTracker",
                },
                {
                    "name": "sync_items",
                    "type": "array",
                    "label": "Items to Sync",
                    "options": [
                        {"value": "time_entries", "label": "Time Entries"},
                        {"value": "events", "label": "Calendar Events"},
                    ],
                    "default": ["events"],
                    "description": "Select which items to synchronize",
                },
                {
                    "name": "default_project_id",
                    "type": "number",
                    "label": "Default Project",
                    "required": True,
                    "description": "Default project to assign imported calendar events to",
                    "help": "Required for importing calendar events as time entries",
                },
                {
                    "name": "lookback_days",
                    "type": "number",
                    "label": "Lookback Days",
                    "default": 90,
                    "validation": {"min": 1, "max": 365},
                    "description": "Number of days in the past to sync (1-365)",
                    "help": "How far back to sync calendar events",
                },
                {
                    "name": "lookahead_days",
                    "type": "number",
                    "label": "Lookahead Days",
                    "default": 7,
                    "validation": {"min": 1, "max": 365},
                    "description": "Number of days in the future to sync (1-365)",
                    "help": "How far ahead to sync calendar events",
                },
                {
                    "name": "verify_ssl",
                    "type": "boolean",
                    "label": "Verify SSL Certificate",
                    "default": True,
                    "description": "Verify SSL certificate when connecting to CalDAV server",
                    "help": "Disable only if using a self-signed certificate",
                },
                {
                    "name": "auto_sync",
                    "type": "boolean",
                    "label": "Auto Sync",
                    "default": False,
                    "description": "Automatically sync on a schedule",
                },
                {
                    "name": "sync_interval",
                    "type": "select",
                    "label": "Sync Schedule",
                    "options": [
                        {"value": "manual", "label": "Manual only"},
                        {"value": "hourly", "label": "Every hour"},
                        {"value": "daily", "label": "Daily"},
                    ],
                    "default": "manual",
                    "description": "How often to automatically sync data",
                },
            ],
            "required": ["default_project_id"],
            "sections": [
                {
                    "title": "Connection Settings",
                    "description": "Configure your CalDAV server connection",
                    "fields": ["server_url", "calendar_url", "calendar_name", "verify_ssl"],
                },
                {
                    "title": "Sync Settings",
                    "description": "Configure what and how to sync",
                    "fields": ["sync_direction", "sync_items", "default_project_id", "lookback_days", "lookahead_days", "auto_sync", "sync_interval"],
                },
            ],
            "sync_settings": {
                "enabled": True,
                "auto_sync": False,
                "sync_interval": "manual",
                "sync_direction": "calendar_to_time_tracker",
                "sync_items": ["events"],
            },
        }


