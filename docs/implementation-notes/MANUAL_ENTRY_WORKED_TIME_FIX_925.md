# Manual Entry Worked Time 24:00 for Past Dates (Issue #925)

**Issue:** [#925](https://github.com/DRYTRIX/TimeTracker/issues/925) — Worked Time shows `24:00` instead of the real span (e.g. `04:00`) when logging time for a past day. Re-selecting End Date fixed the display; saving before that persisted the wrong duration.

Related: [#559](./MANUAL_ENTRY_WORKED_TIME_FIX_559.md) deferred recalculation with `queueMicrotask`, but did not cover duration lock-in or Flatpickr `altInput` hooks.

## Problem

1. Form defaults both Start Date and End Date to **today**, and both times to the **same clock time**.
2. User moves Start Date to yesterday while End Date is still today → span is exactly **24:00**.
3. `onStartChange()` treated any parseable `#worked_time` (including that auto-filled `24:00`) as an explicit duration and called `updateEndFromStartWorked()`, locking the wrong value when the user later edited start time.
4. Flatpickr wraps date/time with `altInput`; native `change`/`input` listeners alone could miss commits (same family as #559).

## Solution

In `app/templates/timer/manual_entry.html`:

- **Explicit duration only:** `onStartChange()` preserves duration via `updateEndFromStartWorked()` only when the user edited worked time (`workedTimeUserEdited` or `worked_time_mode === 'explicit'`). Otherwise it always recomputes from start/end.
- **Same-day end sync:** When Start Date changes and End Date still equals the previous Start Date, End Date follows the new Start Date (Flatpickr `setDate` when present).
- **Flatpickr hooks:** Attach `onChange` and `altInput` listeners for all four fields, with a short poll until `date-picker-init` has created instances (mirrors `edit_timer.html`).
- **`setFlatpickrValue`:** Programmatic end updates keep the visible picker in sync.

## User-visible behavior

- Logging 10:00→14:00 on a past day shows Worked Time **04:00** without re-selecting End Date.
- Changing only Start Date to yesterday moves End Date with it when they still matched (no spurious **24:00**).
- Typing an explicit Worked Time still moves End when Start changes.
