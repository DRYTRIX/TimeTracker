# Workforce Tab: Delete Entries

This feature adds the ability to delete timesheet periods, time-off requests, leave types, and company holidays from the Workforce tab (web, desktop, and mobile). It addresses [Issue #562](https://github.com/DRYTRIX/TimeTracker/issues/562).

## What Can Be Deleted

| Entity | Who can delete | When |
|--------|----------------|------|
| **Timesheet period** | Owner or admin | Only when status is **draft** or **rejected** |
| **Time-off request** | Owner or approver/admin | Only when status is **draft**, **submitted**, or **cancelled** |
| **Leave type** | Admin only | Only if no time-off request uses this leave type |
| **Company holiday** | Admin only | Always (no dependencies) |

Submitted, approved, closed, or rejected records that affect audit or reporting cannot be deleted.

## Web (Workforce dashboard)

- **Timesheet periods:** Each draft or rejected period has a **Delete** button (owner or admin).
- **Time-off requests:** Each draft, submitted, or cancelled request has a **Delete** button (owner or approver).
- **Leave types:** In the admin section, each leave type is listed with a **Delete** button. Delete is blocked with an error if the leave type has any time-off requests.
- **Company holidays:** Each holiday in the list has a **Delete** button (admin only).

All delete actions use POST forms with CSRF protection and redirect back to the dashboard after success or error.

## API v1 (Desktop & mobile)

Delete is exposed as HTTP `DELETE`:

| Endpoint | Scope | Notes |
|----------|--------|--------|
| `DELETE /api/v1/timesheet-periods/{id}` | `write:time_entries` | Owner or admin; period must be draft or rejected |
| `DELETE /api/v1/time-off/requests/{id}` | `write:time_entries` | Owner or approver; request must be draft, submitted, or cancelled |
| `DELETE /api/v1/time-off/leave-types/{id}` | `write:reports` | Admin only; returns 400 if leave type has requests |
| `DELETE /api/v1/time-off/holidays/{id}` | `write:reports` | Admin only |

Success: `200` with JSON `{ "message": "..." }`.  
Failure: `400` with `{ "error": "..." }` or `403` for permission errors.

## Desktop app

- **Timesheet periods:** Delete button on each draft or rejected period; confirmation dialog then refresh.
- **Time-off requests:** Delete button on each draft, submitted, or cancelled request (own requests or when user can approve); confirmation then refresh.

See `desktop/src/renderer/js/api/client.js` (`deleteTimesheetPeriod`, `deleteTimeOffRequest`) and `desktop/src/renderer/js/app.js` (workforce render and handlers).

## Mobile app

- **Timesheet periods:** Popup menu on each period includes **Delete** when status is draft or rejected.
- **Time-off requests:** Popup menu includes **Delete** when status is draft, submitted, or cancelled and the user is owner or approver.

See `mobile/lib/data/api/api_client.dart` and `mobile/lib/presentation/screens/finance_workforce_screen.dart`.

## Backend

- **Service:** `app/services/workforce_governance_service.py`  
  - `delete_period(period_id, actor_id)`  
  - `delete_leave_request(request_id, actor_id, actor_can_approve=False)`  
  - `delete_leave_type(leave_type_id)`  
  - `delete_holiday(holiday_id)`
- **Web routes:** `app/routes/workforce.py` — POST routes for each delete, CSRF and permissions.
- **API routes:** `app/routes/api_v1.py` — DELETE endpoints with token scopes and admin checks where required.

## Risks and notes

- Deleting a leave type that has time-off requests is prevented; the API and web UI return a clear error.
- Only draft or rejected periods can be deleted to keep audit history for submitted/approved/closed periods.
- Only draft, submitted, or cancelled time-off requests can be deleted; approved or rejected ones are kept for reporting.
