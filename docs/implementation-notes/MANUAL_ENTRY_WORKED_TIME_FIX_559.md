# Manual Entry Worked Time Recalculation (Issue #559)

**Issue:** [#559](https://github.com/DRYTRIX/TimeTracker/issues/559) — "Worked Time" on manual entry only recalculated after reselecting end date.

## Problem

When creating a manual time entry with start/end dates that are **not** today:

1. User selects start and end date (e.g. yesterday).
2. User then selects start and end time.
3. **Bug:** Worked time was calculated from start date/time to **today's date** (with the selected end time), instead of the selected end date.
4. Worked time only became correct after the user reselected the end date.

## Root cause

Recalculation ran synchronously in `change` handlers for the date/time inputs. In some browsers or interaction orders, the `change` event can fire before the input’s `.value` is updated in the DOM (e.g. date picker commits the value after the event). So `getStartEnd()` sometimes read the previous end date (today) when recalculating.

## Solution

- **Deferred recalculation:** When any of the four fields (start_date, start_time, end_date, end_time) changes, the update is scheduled with `queueMicrotask(...)` so it runs in the next task. By then the browser has committed the new value, and `getStartEnd()` reads the correct DOM state.
- **Recalculate on every selection:** Both `change` and `input` events are listened to on all four fields, so worked time is recalculated on every date/time change (picker or keyboard).
- **Single run per tick:** A small scheduler with `pendingStart` / `pendingEnd` and one microtask prevents duplicate work when multiple events fire in the same turn.

## File changed

- **`app/templates/timer/manual_entry.html`** — Added `scheduleWorkedTimeUpdate(isStart)` and wired `change` + `input` on start_date, start_time, end_date, end_time to use it. Initial `updateWorkedFromStartEnd()` on load is unchanged.

## User-visible behavior

- Worked time now updates correctly as soon as the user selects dates and times, including when the end date is in the past, without needing to reselect the end date.
- Recalculation runs after every relevant selection (date or time), as requested in the issue.
