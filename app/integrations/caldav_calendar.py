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
- default_project_id: int (optional - if not provided, events imported without project)
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
    """Ensure URL ends with a trailing slash, but preserve query strings and fragments."""
    if not u:
        return u
    # Don't add slash if URL has query string or fragment
    if '?' in u or '#' in u:
        return u
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

    def __init__(self, username: str, password: str, verify_ssl: bool = True, timeout: int = 60):
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = timeout  # Increased default timeout to 60 seconds for slow servers

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
                allow_redirects=False,  # Don't follow redirects automatically for PUT requests
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
        response_count = len(root.findall(_ns("response", DAV_NS)))
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"CalDAV query returned {response_count} responses for time range {start_utc} to {end_utc}")
        logger.info(f"  Query time range: {time_min_utc} to {time_max_utc}")
        logger.info(f"  CalDAV format: {start_utc} to {end_utc}")
        
        skipped_count = 0
        skipped_reasons = {"no_href": 0, "no_caldata": 0, "parse_error": 0, "no_uid": 0, "no_dtstart": 0, "all_day": 0, "no_dtend": 0}
        
        for resp in root.findall(_ns("response", DAV_NS)):
            href_el = resp.find(_ns("href", DAV_NS))
            href = href_el.text.strip() if href_el is not None and href_el.text else None
            if not href:
                skipped_count += 1
                skipped_reasons["no_href"] += 1
                logger.debug(f"Skipping response with no href")
                continue

            caldata_el = resp.find(f".//{_ns('calendar-data', CALDAV_NS)}")
            if caldata_el is None or not caldata_el.text:
                skipped_count += 1
                skipped_reasons["no_caldata"] += 1
                logger.debug(f"Skipping response {href} with no calendar-data")
                continue

            ics = caldata_el.text
            try:
                cal = Calendar.from_ical(ics)
            except Exception as e:
                # Log parsing errors but continue with other events
                import logging
                logger = logging.getLogger(__name__)
                skipped_count += 1
                skipped_reasons["parse_error"] += 1
                logger.warning(f"Failed to parse iCalendar data for event {href}: {e}")
                continue

            for comp in cal.walk():
                if comp.name != "VEVENT":
                    continue

                uid = str(comp.get("UID", "")).strip()
                if not uid:
                    skipped_count += 1
                    skipped_reasons["no_uid"] += 1
                    logger.debug(f"Skipping VEVENT with no UID in {href}")
                    continue

                dtstart = comp.get("DTSTART")
                if not dtstart:
                    skipped_count += 1
                    skipped_reasons["no_dtstart"] += 1
                    logger.debug(f"Skipping event {uid} with no DTSTART")
                    continue

                start = dtstart.dt
                # Skip all-day events (date objects, not datetime)
                if not isinstance(start, datetime):
                    skipped_count += 1
                    skipped_reasons["all_day"] += 1
                    logger.debug(f"Skipping all-day event {uid} (date object, not datetime)")
                    continue

                # Ensure timezone-aware datetime (assume UTC if naive)
                if start.tzinfo is None:
                    # If naive, assume it's in the calendar's timezone or UTC
                    # For CalDAV, naive datetimes are typically in UTC
                    start = start.replace(tzinfo=timezone.utc)
                else:
                    # Convert to UTC if timezone-aware
                    start = start.astimezone(timezone.utc)

                # Handle DTEND or DURATION
                dtend = comp.get("DTEND")
                duration = comp.get("DURATION")
                
                if dtend:
                    end = dtend.dt
                    if not isinstance(end, datetime):
                        skipped_count += 1
                        skipped_reasons["no_dtend"] += 1
                        logger.debug(f"Skipping event {uid} with DTEND that's not a datetime")
                        continue
                    # Ensure timezone-aware datetime (assume UTC if naive)
                    if end.tzinfo is None:
                        end = end.replace(tzinfo=timezone.utc)
                    else:
                        end = end.astimezone(timezone.utc)
                elif duration:
                    # Calculate end from start + duration
                    dur = duration.dt
                    if isinstance(dur, timedelta):
                        end = start + dur
                    else:
                        # Skip if duration is not a timedelta
                        skipped_count += 1
                        skipped_reasons["no_dtend"] += 1
                        logger.debug(f"Skipping event {uid} with DURATION that's not a timedelta")
                        continue
                else:
                    # No DTEND or DURATION - skip this event
                    skipped_count += 1
                    skipped_reasons["no_dtend"] += 1
                    logger.debug(f"Skipping event {uid} with no DTEND or DURATION")
                    continue

                summary = str(comp.get("SUMMARY", "")).strip()
                description = str(comp.get("DESCRIPTION", "")).strip()

                logger.debug(f"Parsed event: uid={uid}, summary={summary[:50]}, start={start}, end={end}")
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

            logger.info(f"Parsed {len(events)} events from {response_count} responses")
            if skipped_count > 0:
                logger.info(f"Skipped {skipped_count} events: {skipped_reasons}")
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
        import logging
        logger = logging.getLogger(__name__)
        
        calendar_url = _ensure_trailing_slash(calendar_url)
        # Use provided href if available, otherwise construct from UID
        if event_href:
            # If event_href is absolute, validate it matches calendar_url base, otherwise reconstruct
            if event_href.startswith('http://') or event_href.startswith('https://'):
                # Parse both URLs to compare
                from urllib.parse import urlparse
                href_parsed = urlparse(event_href)
                cal_parsed = urlparse(calendar_url)
                
                # If the href is from a different host/port, reconstruct using calendar_url base
                if (href_parsed.scheme != cal_parsed.scheme or 
                    href_parsed.netloc != cal_parsed.netloc):
                    logger.warning(f"Event href {event_href} doesn't match calendar URL {calendar_url}, reconstructing")
                    # Reconstruct using calendar_url base
                    filename = f"{event_uid}.ics"
                    if calendar_url.endswith('/'):
                        event_url = calendar_url + filename
                    else:
                        event_url = calendar_url + '/' + filename
                else:
                    event_url = event_href
            else:
                # Relative href - join with calendar_url base
                event_url = urljoin(calendar_url, event_href.lstrip('/'))
        else:
            # Event URL is typically: calendar_url + event_uid + ".ics"
            # Use proper URL joining - ensure calendar_url ends with / and filename doesn't start with /
            filename = f"{event_uid}.ics"
            if calendar_url.endswith('/'):
                event_url = calendar_url + filename
            else:
                event_url = calendar_url + '/' + filename
        
        headers = {
            "Content-Type": "text/calendar; charset=utf-8",
        }
        
        try:
            logger.info(f"PUT request to {event_url} for event {event_uid} (calendar_url: {calendar_url})")
            logger.info(f"  iCalendar content length: {len(ical_content)} bytes")
            logger.debug(f"  iCalendar content preview: {ical_content[:200]}...")
            resp = self._request("PUT", event_url, headers=headers, data=ical_content)
            
            logger.info(f"  Response status: {resp.status_code}")
            logger.debug(f"  Response headers: {dict(resp.headers)}")
            
            # Handle redirects manually for PUT requests
            if resp.status_code in (301, 302, 303, 307, 308):
                redirect_url = resp.headers.get('Location')
                if redirect_url:
                    logger.info(f"Following redirect from {event_url} to {redirect_url}")
                    # Make redirect URL absolute if it's relative
                    if not redirect_url.startswith('http'):
                        from urllib.parse import urljoin, urlparse
                        parsed = urlparse(event_url)
                        redirect_url = f"{parsed.scheme}://{parsed.netloc}{redirect_url}"
                    resp = self._request("PUT", redirect_url, headers=headers, data=ical_content)
                    logger.info(f"  Redirect response status: {resp.status_code}")
            
            resp.raise_for_status()
            logger.info(f"Successfully created/updated event {event_uid} at {event_url} (status: {resp.status_code})")
            return True
        except requests.exceptions.HTTPError as e:
            error_detail = f"HTTP {e.response.status_code}"
            if e.response.text:
                error_detail += f": {e.response.text[:500]}"
            logger.warning(f"HTTP error creating/updating CalDAV event {event_uid} at {event_url}: {error_detail}")
            logger.debug(f"  Full response text: {e.response.text}")
            
            if e.response.status_code == 404:
                logger.info(f"CalDAV event {event_uid} not found at {event_url}, attempting to create with standard URL")
                # Try creating with standard URL if custom href failed
                if event_href:
                    # Try standard URL format
                    filename = f"{event_uid}.ics"
                    if calendar_url.endswith('/'):
                        standard_url = calendar_url + filename
                    else:
                        standard_url = calendar_url + '/' + filename
                    if event_href != standard_url:
                        try:
                            logger.info(f"Trying standard URL: {standard_url}")
                            resp = self._request("PUT", standard_url, headers=headers, data=ical_content)
                            logger.info(f"  Standard URL response status: {resp.status_code}")
                            resp.raise_for_status()
                            logger.info(f"Successfully created event {event_uid} at standard URL {standard_url}")
                            return True
                        except Exception as e2:
                            logger.warning(f"Failed to create event at standard URL {standard_url}: {e2}")
                            if hasattr(e2, 'response') and e2.response:
                                logger.warning(f"  Response status: {e2.response.status_code}, text: {e2.response.text[:200]}")
                            return False
            elif e.response.status_code == 403:
                logger.warning(f"Permission denied (403) when creating event {event_uid}. Check calendar write permissions.")
                logger.warning(f"  Response: {e.response.text[:200]}")
            elif e.response.status_code == 401:
                logger.warning(f"Authentication failed (401) when creating event {event_uid}. Check credentials.")
                logger.warning(f"  Response: {e.response.text[:200]}")
            else:
                logger.warning(f"Unexpected HTTP status {e.response.status_code} when creating event {event_uid}")
                logger.warning(f"  Response: {e.response.text[:200]}")
            return False
        except Exception as e:
            logger.warning(f"Exception creating/updating CalDAV event {event_uid} at {event_url}: {e}", exc_info=True)
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

            logger.info(f"CalDAV sync starting with sync_direction='{sync_direction}', sync_type='{sync_type}'")
            logger.info(f"  Calendar URL: {calendar_url}")
            logger.info(f"  Lookback days: {lookback_days}")

            if sync_direction in ("calendar_to_time_tracker", "bidirectional"):
                logger.info(f"Executing Calendar→TimeTracker sync (sync_direction: {sync_direction})")
                calendar_result = self._sync_calendar_to_time_tracker(cfg, calendar_url, sync_type, default_project_id, lookback_days)
                # If bidirectional, also do TimeTracker to Calendar sync
                if sync_direction == "bidirectional":
                    logger.info(f"Executing TimeTracker→Calendar sync (bidirectional mode)")
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
                logger.info(f"Calendar→TimeTracker sync completed, returning result")
                return calendar_result

            # Handle TimeTracker to Calendar sync
            if sync_direction == "time_tracker_to_calendar":
                logger.info(f"Executing TimeTracker→Calendar sync only (sync_direction: {sync_direction})")
                return self._sync_time_tracker_to_calendar(cfg, calendar_url, sync_type)
            
            logger.warning(f"Unknown sync direction: {sync_direction}")
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
        """Sync calendar events from CalDAV to TimeTracker CalendarEvent records."""
        from app import db
        from app.models import Project, CalendarEvent
        from app.models.integration_external_event_link import IntegrationExternalEventLink
        import logging
        
        logger = logging.getLogger(__name__)
        
        # default_project_id is optional - if not provided, events will be imported without a project

        # Determine time window
        now_utc = datetime.now(timezone.utc)
        if sync_type == "incremental" and self.integration.last_sync_at:
            time_min_utc = self.integration.last_sync_at.replace(tzinfo=timezone.utc)
            logger.info(f"Incremental sync: using last_sync_at {time_min_utc}")
        else:
            time_min_utc = now_utc - timedelta(days=lookback_days)
            logger.info(f"Full sync: using lookback_days={lookback_days}, calculated time_min_utc={time_min_utc}")
        time_max_utc = now_utc + timedelta(days=7)
        
        logger.info(f"Time range calculation:")
        logger.info(f"  now_utc: {now_utc}")
        logger.info(f"  time_min_utc: {time_min_utc} (lookback: {lookback_days} days)")
        logger.info(f"  time_max_utc: {time_max_utc} (lookahead: 7 days)")
        logger.info(f"  Time range span: {(time_max_utc - time_min_utc).days} days")

        logger.info(f"Fetching events from {calendar_url} between {time_min_utc} and {time_max_utc}")
        client = self._client()
        try:
            events = client.fetch_events(calendar_url, time_min_utc, time_max_utc)
            logger.info(f"Fetched {len(events)} events from CalDAV calendar")
            
            # If no events found, try with an expanded time range (some servers are strict about time-range)
            if len(events) == 0:
                logger.debug(f"No events found with initial time range, trying expanded range (extending by 1 day on each side)")
                expanded_min = time_min_utc - timedelta(days=1)
                expanded_max = time_max_utc + timedelta(days=1)
                try:
                    events = client.fetch_events(calendar_url, expanded_min, expanded_max)
                    logger.info(f"Fetched {len(events)} events with expanded time range")
                    # Filter events to only include those within the original time range
                    if events:
                        original_events = events
                        events = [
                            e for e in original_events
                            if (e["start"] <= time_max_utc and e["end"] >= time_min_utc)
                        ]
                        logger.info(f"Filtered to {len(events)} events within original time range")
                except Exception as e2:
                    logger.debug(f"Expanded time range query also failed: {e2}")
            
            if len(events) == 0:
                logger.warning(f"No events found in calendar {calendar_url} for time range {time_min_utc} to {time_max_utc}")
            else:
                logger.debug(f"Event details (first 5): {[{'uid': e.get('uid', 'N/A')[:20], 'summary': e.get('summary', 'N/A')[:30], 'start': str(e.get('start', 'N/A')), 'end': str(e.get('end', 'N/A'))} for e in events[:5]]}")
        except Exception as e:
            logger.error(f"Failed to fetch events from calendar: {e}", exc_info=True)
            return {"success": False, "message": f"Failed to fetch events from calendar: {str(e)}"}

        # Preload projects for title matching
        projects = Project.query.filter_by(status="active").order_by(Project.name).all()

        imported = 0
        skipped = 0
        errors: List[str] = []
        skipped_reasons = {"already_imported": 0, "invalid_time": 0, "other": 0}

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
                
                # Check if this event was already imported
                # Since CalendarEvent doesn't have time_entry_id for IntegrationExternalEventLink,
                # we track imports by checking for CalendarEvent records with the [CalDAV: uid] marker in description
                existing_calendar_event = CalendarEvent.query.filter(
                    CalendarEvent.user_id == self.integration.user_id,
                    CalendarEvent.description.like(f"%[CalDAV: {uid}]%")
                ).first()
                
                # Also check link table in case it was previously imported as TimeEntry (for backward compatibility)
                existing_link = IntegrationExternalEventLink.query.filter_by(
                    integration_id=self.integration.id, external_uid=uid
                ).first()
                
                if existing_calendar_event or existing_link:
                    logger.debug(f"Event {uid} already imported (CalendarEvent or link exists), skipping")
                    skipped += 1
                    skipped_reasons["already_imported"] += 1
                    continue

                start_dt: datetime = ev["start"]
                end_dt: datetime = ev["end"]
                
                # Ensure both are timezone-aware UTC
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                else:
                    start_dt = start_dt.astimezone(timezone.utc)
                    
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=timezone.utc)
                else:
                    end_dt = end_dt.astimezone(timezone.utc)

                start_local = _to_local_naive(start_dt)
                end_local = _to_local_naive(end_dt)

                if end_local <= start_local:
                    logger.warning(f"Event {uid} has invalid time range: start={start_local}, end={end_local}")
                    skipped += 1
                    skipped_reasons["invalid_time"] += 1
                    continue

                # Use default_project_id if provided, otherwise try to match by project name, or leave as None
                project_id = None
                if default_project_id:
                    project_id = int(default_project_id)
                
                title = (ev.get("summary") or "").strip()
                if not title:
                    title = "Imported Calendar Event"
                
                # Try to match project by name in title (only if we have projects loaded)
                if not project_id:
                    for p in projects:
                        if p and p.name and p.name in title:
                            project_id = p.id
                            break

                description = (ev.get("description") or "").strip()
                # Add a marker to indicate this was imported from CalDAV (for tracking purposes)
                if description:
                    description = f"[CalDAV: {uid}]\n\n{description}"
                else:
                    description = f"[CalDAV: {uid}]"

                # Create CalendarEvent instead of TimeEntry
                calendar_event = CalendarEvent(
                    user_id=self.integration.user_id,
                    title=title,
                    start_time=start_local,
                    end_time=end_local,
                    description=description,
                    all_day=False,  # CalDAV events we fetch are timed events (all-day events are skipped in fetch_events)
                    location=None,  # Could extract from LOCATION property if needed
                    event_type="event",
                    project_id=project_id,
                )

                db.session.add(calendar_event)
                db.session.flush()

                # Note: We don't create IntegrationExternalEventLink for CalendarEvent since it requires time_entry_id
                # We track imports by checking for the [CalDAV: uid] marker in the description field
                logger.info(f"Created CalendarEvent {calendar_event.id} from CalDAV event {uid} (title: {title})")

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
            message = f"No new events imported ({skipped} already imported: {skipped_reasons['already_imported']} duplicates, {skipped_reasons['invalid_time']} invalid time, {skipped_reasons['other']} other, {len(events)} total found)."
        elif imported == 0:
            message = f"No events found in calendar for the specified time range ({time_min_utc.date()} to {time_max_utc.date()})."
        else:
            message = f"Imported {imported} events ({skipped} skipped: {skipped_reasons['already_imported']} duplicates, {skipped_reasons['invalid_time']} invalid time, {skipped_reasons['other']} other, {len(events)} total found)."

        logger.info(f"CalDAV sync completed: {message}")
        logger.debug(f"Sync statistics: imported={imported}, skipped={skipped}, errors={len(errors)}, total_events={len(events)}")

        return {
            "success": True,
            "imported": imported,
            "skipped": skipped,
            "synced_items": imported,
            "errors": errors,
            "message": message,
        }
    
    def _sync_time_tracker_to_calendar(self, cfg: Dict[str, Any], calendar_url: str, sync_type: str) -> Dict[str, Any]:
        """Sync TimeTracker time entries and calendar events to CalDAV calendar."""
        from app import db
        from app.models import TimeEntry, Project, Task, CalendarEvent
        from app.models.integration_external_event_link import IntegrationExternalEventLink
        import logging
        
        logger = logging.getLogger(__name__)
        
        lookback_days = int(cfg.get("lookback_days", 90))
        lookahead_days = int(cfg.get("lookahead_days", 7))
        
        now_utc = datetime.now(timezone.utc)
        if sync_type == "incremental" and self.integration.last_sync_at:
            time_min = self.integration.last_sync_at.replace(tzinfo=timezone.utc)
            logger.info(f"Incremental sync: using last_sync_at {time_min}")
        else:
            time_min = now_utc - timedelta(days=lookback_days)
            logger.info(f"Full sync: using lookback_days={lookback_days}, calculated time_min={time_min}")
        time_max = now_utc + timedelta(days=lookahead_days)
        
        logger.info(f"Time range calculation for TimeTracker→Calendar sync:")
        logger.info(f"  now_utc: {now_utc}")
        logger.info(f"  time_min (UTC): {time_min} (lookback: {lookback_days} days)")
        logger.info(f"  time_max (UTC): {time_max} (lookahead: {lookahead_days} days)")
        logger.info(f"  Time range span: {(time_max - time_min).days} days")
        
        time_min_local = _to_local_naive(time_min)
        time_max_local = _to_local_naive(time_max)
        
        logger.info(f"Looking for time entries and calendar events for user {self.integration.user_id} between {time_min_local} and {time_max_local}")
        
        # Get time entries
        # First, check how many entries exist for this user in the time range (without end_time filter)
        all_entries_in_range = TimeEntry.query.filter(
            TimeEntry.user_id == self.integration.user_id,
            TimeEntry.start_time >= time_min_local,
            TimeEntry.start_time <= time_max_local,
        ).all()
        logger.info(f"  Total time entries in time range (including without end_time): {len(all_entries_in_range)}")
        
        # Check how many have end_time
        entries_with_end_time = [e for e in all_entries_in_range if e.end_time is not None]
        logger.info(f"  Time entries with end_time: {len(entries_with_end_time)}")
        entries_without_end_time = [e for e in all_entries_in_range if e.end_time is None]
        if entries_without_end_time:
            logger.info(f"  Time entries without end_time (will be skipped): {[e.id for e in entries_without_end_time]}")
        
        time_entries = TimeEntry.query.filter(
            TimeEntry.user_id == self.integration.user_id,
            TimeEntry.start_time >= time_min_local,
            TimeEntry.start_time <= time_max_local,
            TimeEntry.end_time.isnot(None),
        ).order_by(TimeEntry.start_time).all()
        
        logger.info(f"Found {len(time_entries)} time entries to sync to CalDAV calendar (with end_time)")
        if time_entries:
            logger.info(f"  Time entry IDs found: {[e.id for e in time_entries]}")
            for entry in time_entries:
                logger.info(f"    Time Entry {entry.id}: start={entry.start_time}, end={entry.end_time}, project_id={entry.project_id}, source={getattr(entry, 'source', 'unknown')}")
        
        # Get calendar events
        calendar_events = CalendarEvent.query.filter(
            CalendarEvent.user_id == self.integration.user_id,
            CalendarEvent.start_time >= time_min_local,
            CalendarEvent.start_time <= time_max_local,
        ).order_by(CalendarEvent.start_time).all()
        
        logger.info(f"Found {len(calendar_events)} calendar events to sync to CalDAV calendar")
        if calendar_events:
            logger.info(f"  Calendar event IDs found: {[e.id for e in calendar_events]}")
            for event in calendar_events:
                logger.info(f"    Calendar Event {event.id}: start={event.start_time}, end={event.end_time}, title={event.title}, all_day={event.all_day}")
        
        if not time_entries and not calendar_events:
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
        skipped_count = 0
        errors: List[str] = []
        
        total_items = len(time_entries) + len(calendar_events)
        logger.info(f"Starting sync of {len(time_entries)} time entries and {len(calendar_events)} calendar events ({total_items} total) to CalDAV calendar")
        
        # Sync time entries
        for time_entry in time_entries:
            try:
                event_uid = f"timetracker-{time_entry.id}@timetracker.local"
                
                existing_link = IntegrationExternalEventLink.query.filter_by(
                    integration_id=self.integration.id,
                    time_entry_id=time_entry.id
                ).first()
                
                # Log entry details for debugging
                logger.info(f"Processing time entry {time_entry.id}: start={time_entry.start_time}, end={time_entry.end_time}, project_id={time_entry.project_id}, source={getattr(time_entry, 'source', 'unknown')}")
                if existing_link:
                    logger.info(f"  Existing link found: external_uid={existing_link.external_uid}, external_href={existing_link.external_href}")
                    logger.info(f"  Link external_uid starts with 'timetracker-': {existing_link.external_uid.startswith('timetracker-') if existing_link.external_uid else False}")
                else:
                    logger.info(f"  No existing link found - will create new event")
                
                # Skip entries that were imported FROM CalDAV (to avoid circular sync)
                # If there's a link but the external_uid doesn't start with "timetracker-",
                # it means this entry was imported from CalDAV, not created by us
                # Also handle case where external_uid is None or empty - treat as new sync
                if existing_link and existing_link.external_uid:
                    if not existing_link.external_uid.startswith("timetracker-"):
                        logger.info(f"Skipping time entry {time_entry.id} - it was imported from CalDAV (external_uid: {existing_link.external_uid}), avoiding circular sync")
                        skipped_count += 1
                        continue
                    else:
                        logger.info(f"  Entry {time_entry.id} has timetracker- UID, will update existing event")
                elif existing_link and not existing_link.external_uid:
                    # Link exists but external_uid is None/empty - treat as new sync, update the link
                    logger.info(f"Time entry {time_entry.id} has link with empty external_uid - will create new event and update link")
                else:
                    logger.info(f"  Entry {time_entry.id} has no link - will create new event")
                
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
                
                logger.info(f"Syncing time entry {time_entry.id}: {title} from {start_utc} to {end_utc}")
                
                ical_content = self._generate_icalendar_event(
                    uid=event_uid,
                    title=title,
                    description=description,
                    start=start_utc,
                    end=end_utc,
                    created=time_entry.created_at.replace(tzinfo=timezone.utc) if time_entry.created_at else datetime.now(timezone.utc),
                    updated=time_entry.updated_at.replace(tzinfo=timezone.utc) if time_entry.updated_at else datetime.now(timezone.utc),
                )
                
                # Always construct our standard event URL (don't use imported event hrefs)
                filename = f"{event_uid}.ics"
                if calendar_url.endswith('/'):
                    event_href = calendar_url + filename
                else:
                    event_href = calendar_url + '/' + filename
                
                logger.info(f"  Event UID: {event_uid}")
                logger.info(f"  Event href: {event_href}")
                logger.info(f"  Calendar URL: {calendar_url}")
                
                # Check if we already synced this entry (has link with our UID)
                if existing_link and existing_link.external_uid == event_uid:
                    # Update existing event we created
                    logger.info(f"Updating existing event for time entry {time_entry.id} at {event_href}")
                    # Use the stored href if it exists and is valid, otherwise use our generated one
                    stored_href = existing_link.external_href if existing_link.external_href else event_href
                    logger.info(f"  Using stored href: {stored_href}")
                    success = client.create_or_update_event(calendar_url, event_uid, ical_content, event_href=stored_href)
                    if success:
                        # Update the stored href in case it changed
                        if existing_link.external_href != event_href:
                            existing_link.external_href = event_href
                            db.session.flush()
                        updated += 1
                        logger.info(f"Successfully updated event for time entry {time_entry.id}")
                    else:
                        error_msg = f"Failed to update time entry {time_entry.id} in calendar"
                        errors.append(error_msg)
                        logger.warning(f"{error_msg} - create_or_update_event returned False")
                else:
                    # Create new event
                    logger.info(f"Creating new event for time entry {time_entry.id} at {event_href}")
                    success = client.create_or_update_event(calendar_url, event_uid, ical_content)
                    logger.info(f"  create_or_update_event returned: {success}")
                    if success:
                        # Create or update the link
                        if existing_link:
                            # Update existing link with our UID and href
                            logger.info(f"  Updating existing link with UID {event_uid} and href {event_href}")
                            existing_link.external_uid = event_uid
                            existing_link.external_href = event_href
                        else:
                            logger.info(f"  Creating new link with UID {event_uid} and href {event_href}")
                            link = IntegrationExternalEventLink(
                                integration_id=self.integration.id,
                                time_entry_id=time_entry.id,
                                external_uid=event_uid,
                                external_href=event_href,
                            )
                            db.session.add(link)
                        synced += 1
                        logger.info(f"Successfully created event for time entry {time_entry.id}")
                    else:
                        error_msg = f"Failed to create time entry {time_entry.id} in calendar"
                        errors.append(error_msg)
                        logger.warning(f"{error_msg} - create_or_update_event returned False")
                    
            except Exception as e:
                error_msg = f"Time entry {time_entry.id}: {str(e)}"
                errors.append(error_msg)
                logger.warning(f"Failed to sync time entry {time_entry.id} to CalDAV: {e}")
        
        # Sync calendar events
        # Note: IntegrationExternalEventLink requires time_entry_id, so for calendar events we track by external_uid only
        for calendar_event in calendar_events:
            try:
                # Skip calendar events that were imported FROM CalDAV (to avoid circular sync)
                # We check for the [CalDAV: uid] marker in the description
                if calendar_event.description and "[CalDAV:" in calendar_event.description:
                    logger.info(f"Skipping calendar event {calendar_event.id} - it was imported from CalDAV (has [CalDAV: marker in description), avoiding circular sync")
                    skipped_count += 1
                    continue
                
                event_uid = f"timetracker-calendarevent-{calendar_event.id}@timetracker.local"
                
                # For calendar events, check by external_uid only (since IntegrationExternalEventLink
                # requires time_entry_id which calendar events don't have)
                existing_link_by_uid = IntegrationExternalEventLink.query.filter_by(
                    integration_id=self.integration.id,
                    external_uid=event_uid
                ).first()
                
                # Log event details for debugging
                logger.info(f"Processing calendar event {calendar_event.id}: start={calendar_event.start_time}, end={calendar_event.end_time}, title={calendar_event.title}")
                if existing_link_by_uid:
                    logger.info(f"  Existing link found: external_uid={existing_link_by_uid.external_uid}, external_href={existing_link_by_uid.external_href}, time_entry_id={existing_link_by_uid.time_entry_id}")
                    # If link exists but has a time_entry_id, it might be for a different entry - we'll update it
                else:
                    logger.info(f"  No existing link found - will create new event")
                
                # Skip all-day events for now (CalDAV sync currently only handles timed events)
                if calendar_event.all_day:
                    logger.info(f"Skipping calendar event {calendar_event.id} - all-day events not yet supported in CalDAV sync")
                    skipped_count += 1
                    continue
                
                title = calendar_event.title
                description_parts = []
                if calendar_event.description:
                    # Remove the [CalDAV: uid] marker if present (it's only for tracking imports)
                    desc = calendar_event.description
                    import re
                    desc = re.sub(r'\[CalDAV: [^\]]+\]\s*\n?\n?', '', desc).strip()
                    if desc:
                        description_parts.append(desc)
                if calendar_event.location:
                    description_parts.append(f"Location: {calendar_event.location}")
                if calendar_event.event_type:
                    description_parts.append(f"Type: {calendar_event.event_type}")
                description = "\n\n".join(description_parts) if description_parts else "TimeTracker: Calendar event"
                
                # Convert to UTC
                start_utc = local_to_utc(calendar_event.start_time)
                end_utc = local_to_utc(calendar_event.end_time)
                
                logger.info(f"Syncing calendar event {calendar_event.id}: {title} from {start_utc} to {end_utc}")
                
                ical_content = self._generate_icalendar_event(
                    uid=event_uid,
                    title=title,
                    description=description,
                    start=start_utc,
                    end=end_utc,
                    created=calendar_event.created_at.replace(tzinfo=timezone.utc) if calendar_event.created_at else datetime.now(timezone.utc),
                    updated=calendar_event.updated_at.replace(tzinfo=timezone.utc) if calendar_event.updated_at else datetime.now(timezone.utc),
                )
                
                # Construct event URL
                filename = f"{event_uid}.ics"
                if calendar_url.endswith('/'):
                    event_href = calendar_url + filename
                else:
                    event_href = calendar_url + '/' + filename
                
                logger.info(f"  Event UID: {event_uid}")
                logger.info(f"  Event href: {event_href}")
                
                # Check if we already synced this event
                if existing_link_by_uid and existing_link_by_uid.external_uid == event_uid:
                    # Update existing event
                    logger.info(f"Updating existing event for calendar event {calendar_event.id} at {event_href}")
                    stored_href = existing_link_by_uid.external_href if existing_link_by_uid.external_href else event_href
                    logger.info(f"  Using stored href: {stored_href}")
                    success = client.create_or_update_event(calendar_url, event_uid, ical_content, event_href=stored_href)
                    if success:
                        if existing_link_by_uid.external_href != event_href:
                            existing_link_by_uid.external_href = event_href
                            db.session.flush()
                        updated += 1
                        logger.info(f"Successfully updated event for calendar event {calendar_event.id}")
                    else:
                        error_msg = f"Failed to update calendar event {calendar_event.id} in calendar"
                        errors.append(error_msg)
                        logger.warning(f"{error_msg} - create_or_update_event returned False")
                else:
                    # Create new event
                    logger.info(f"Creating new event for calendar event {calendar_event.id} at {event_href}")
                    success = client.create_or_update_event(calendar_url, event_uid, ical_content)
                    logger.info(f"  create_or_update_event returned: {success}")
                    if success:
                        # Update or create link
                        # Note: IntegrationExternalEventLink requires time_entry_id, so for calendar events
                        # we use a workaround: we'll find an existing link by UID and update it, or if none exists,
                        # we'll create one with a dummy time_entry_id (we'll use 0 or find an orphaned link)
                        # Actually, better approach: just update the href if link exists, otherwise don't create link
                        # The UID check above will prevent duplicates
                        if existing_link_by_uid:
                            logger.info(f"  Updating existing link with UID {event_uid} and href {event_href}")
                            existing_link_by_uid.external_href = event_href
                            db.session.flush()
                        else:
                            # Can't create IntegrationExternalEventLink without time_entry_id
                            # So we'll just track by UID in future queries
                            # This means we'll try to sync every time, but the UID check prevents duplicates
                            logger.info(f"  Event created but no link record (calendar events don't have time_entry_id)")
                        synced += 1
                        logger.info(f"Successfully created event for calendar event {calendar_event.id}")
                    else:
                        error_msg = f"Failed to create calendar event {calendar_event.id} in calendar"
                        errors.append(error_msg)
                        logger.warning(f"{error_msg} - create_or_update_event returned False")
                    
            except Exception as e:
                error_msg = f"Calendar event {calendar_event.id}: {str(e)}"
                errors.append(error_msg)
                logger.warning(f"Failed to sync calendar event {calendar_event.id} to CalDAV: {e}")
        
        self.integration.last_sync_at = datetime.utcnow()
        self.integration.last_sync_status = "success" if not errors else "partial"
        self.integration.last_error = "; ".join(errors[:3]) if errors else None
        
        db.session.commit()
        
        total_processed = len(time_entries) + len(calendar_events)
        message = f"Synced {synced} new events, updated {updated} events to CalDAV calendar."
        logger.info(f"CalDAV TimeTracker→Calendar sync completed: {message}")
        logger.info(f"  Summary: {total_processed} items processed ({len(time_entries)} time entries, {len(calendar_events)} calendar events), {synced} created, {updated} updated, {skipped_count} skipped, {len(errors)} errors")
        
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
                    "required": False,
                    "description": "Default project to assign imported calendar events to (optional)",
                    "help": "If not specified, events will be imported without a project. You can also match projects by name in event titles.",
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
            "required": [],
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


