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

    def _propfind(self, url: str, xml_body: str, depth: str = "0") -> ET.Element:
        resp = self._request(
            "PROPFIND",
            url,
            headers={"Depth": depth, "Content-Type": "application/xml; charset=utf-8"},
            data=xml_body,
        )
        resp.raise_for_status()
        return ET.fromstring(resp.text)

    def _report(self, url: str, xml_body: str, depth: str = "1") -> ET.Element:
        resp = self._request(
            "REPORT",
            url,
            headers={"Depth": depth, "Content-Type": "application/xml; charset=utf-8"},
            data=xml_body,
        )
        resp.raise_for_status()
        return ET.fromstring(resp.text)

    def discover_calendars(self, server_url: str) -> List[CalDAVCalendar]:
        """
        Best-effort CalDAV discovery:
        - PROPFIND server_url depth 0 for current-user-principal
        - PROPFIND principal for calendar-home-set
        - PROPFIND home-set depth 1 for calendars
        """
        server_url = _ensure_trailing_slash(server_url)

        # 1) Find current-user-principal
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

        principal_url = urljoin(server_url, principal_href)

        # 2) Find calendar-home-set on principal
        body = (
            '<?xml version="1.0" encoding="utf-8" ?>'
            f'<d:propfind xmlns:d="{DAV_NS}" xmlns:cs="{CALDAV_NS}">'
            "<d:prop><cs:calendar-home-set/></d:prop>"
            "</d:propfind>"
        )
        root = self._propfind(principal_url, body, depth="0")
        home_href = self._find_href(root, [(_ns("calendar-home-set", CALDAV_NS),)])
        if not home_href:
            raise ValueError("Could not discover calendar-home-set from CalDAV server.")

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
        """
        calendar_url = _ensure_trailing_slash(calendar_url)

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
            except Exception:
                continue

            for comp in cal.walk():
                if comp.name != "VEVENT":
                    continue

                uid = str(comp.get("UID", "")).strip()
                if not uid:
                    continue

                dtstart = comp.get("DTSTART")
                dtend = comp.get("DTEND")
                if not dtstart or not dtend:
                    continue

                start = dtstart.dt
                end = dtend.dt
                # Skip all-day events (date)
                if not isinstance(start, datetime) or not isinstance(end, datetime):
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
            cfg = self.integration.config or {}
            server_url = cfg.get("server_url")
            calendar_url = cfg.get("calendar_url")

            client = self._client()

            calendars: List[CalDAVCalendar] = []
            if server_url:
                calendars = client.discover_calendars(server_url)

            # If a calendar URL is provided, validate we can run a REPORT against it (lightweight window)
            if calendar_url:
                now_utc = datetime.now(timezone.utc)
                _ = client.fetch_events(calendar_url, now_utc - timedelta(days=1), now_utc + timedelta(days=1))

            return {
                "success": True,
                "message": f"Connected to CalDAV. Found {len(calendars)} calendars." if server_url else "Connected to CalDAV.",
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

        try:
            if not self.integration or not self.integration.user_id:
                return {"success": False, "message": "CalDAV integration must be a per-user integration."}

            cfg = self.integration.config or {}
            calendar_url = cfg.get("calendar_url")
            server_url = cfg.get("server_url")
            
            if not calendar_url:
                if server_url:
                    # Try to discover and use first calendar
                    try:
                        client = self._client()
                        calendars = client.discover_calendars(server_url)
                        if calendars:
                            calendar_url = calendars[0].href
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
                        return {"success": False, "message": f"Could not discover calendars: {str(e)}. Please configure calendar URL manually."}
                else:
                    return {"success": False, "message": "No calendar selected. Please configure calendar URL or server URL first."}

            sync_direction = cfg.get("sync_direction", "calendar_to_time_tracker")
            default_project_id = cfg.get("default_project_id")
            lookback_days = int(cfg.get("lookback_days", 90))

            if sync_direction in ("calendar_to_time_tracker", "bidirectional"):
                if not default_project_id:
                    return {"success": False, "message": "default_project_id is required to import calendar events as time entries."}

                # Determine time window
                if sync_type == "incremental" and self.integration.last_sync_at:
                    # last_sync_at stored as naive UTC in Integration; treat as UTC
                    time_min_utc = self.integration.last_sync_at.replace(tzinfo=timezone.utc)
                else:
                    time_min_utc = datetime.now(timezone.utc) - timedelta(days=lookback_days)
                time_max_utc = datetime.now(timezone.utc) + timedelta(days=7)

                client = self._client()
                events = client.fetch_events(calendar_url, time_min_utc, time_max_utc)

                # Preload projects for title matching
                projects = Project.query.filter_by(status="active").order_by(Project.name).all()

                imported = 0
                skipped = 0
                errors: List[str] = []

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

                        # Convert to local naive for DB storage
                        start_local = _to_local_naive(start_dt)
                        end_local = _to_local_naive(end_dt)

                        # Ensure valid duration
                        if end_local <= start_local:
                            skipped += 1
                            continue

                        # Try project match, else default
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
                        db.session.flush()  # get id

                        link = IntegrationExternalEventLink(
                            integration_id=self.integration.id,
                            time_entry_id=time_entry.id,
                            external_uid=uid,
                            external_href=ev.get("href"),
                        )
                        db.session.add(link)

                        imported += 1
                    except Exception as e:
                        errors.append(str(e))

                # Update integration status
                self.integration.last_sync_at = datetime.utcnow()
                self.integration.last_sync_status = "success" if not errors else "partial"
                self.integration.last_error = "; ".join(errors[:3]) if errors else None

                db.session.commit()

                return {
                    "success": True,
                    "imported": imported,
                    "skipped": skipped,
                    "errors": errors,
                    "message": f"Imported {imported} events ({skipped} skipped).",
                }

            return {"success": False, "message": "Sync direction not implemented for CalDAV yet."}
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


