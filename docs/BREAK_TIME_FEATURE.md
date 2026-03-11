# Break Time for Timers and Manual Time Entries

**Issue:** [#561](https://github.com/DRYTRIX/TimeTracker/issues/561)

This feature lets you account for break time when tracking work: either by pausing a running timer (so time while paused counts as break) or by entering break duration on manual time entries. Stored duration is always **worked time** (total span minus break).

---

## For Running Timers

### Pause and Resume

- **Pause** — Stops the clock. Time while paused is not counted as work. When you click **Resume**, the elapsed pause time is added to **break** for that entry.
- **Resume** — Continues the timer and records the time you were paused as break. You can pause and resume multiple times; all pause segments are summed as break.
- **Stop & save** — Saves the entry. Stored **duration** = (end time − start time) − break time, then rounded according to your rounding settings.

**Where it appears**

- **Dashboard** — When a timer is running: **Pause** and **Stop & save**. When paused: **Resume** and **Stop & save**, plus a “Break: HH:MM:SS” line and a “Paused” badge. Elapsed time does not increase while paused.
- **Timer page** — Same Pause / Resume / Stop controls and break display.
- **Floating timer bar** — Shows paused state (e.g. amber icon); click to Resume or Stop depending on state.

**API**

- `POST /timer/pause` (web) and `POST /api/v1/timer/pause` (API)
- `POST /timer/resume` (web) and `POST /api/v1/timer/resume` (API)
- Timer status (`GET /timer/status`, `GET /api/v1/timer/status`) includes `paused`, `paused_at`, `break_seconds`, `break_formatted`.

---

## For Manual Time Entries

### Break field

- On **Log Time** (manual entry) and **Edit time entry** you can enter **Break** in HH:MM (e.g. `0:30` for 30 minutes).
- **Effective duration** (what is stored and shown) = (end − start) − break. If you also use **Worked time**, that value is treated as net (after break); break can still be entered and is subtracted when both are present.
- Break is optional; leave it empty for no break.

### Suggest break (manual entry)

- A **Suggest** button next to the Break field uses optional default rules (e.g. Germany: >6 h → 30 min, >9 h → 45 min) to propose a break from the current start/end or worked time. You can change or clear the suggestion.

---

## Default Break Rules (optional)

Admins can configure default break rules in **Settings** (e.g. for labour-law style rules):

- **Break after hours 1** / **Break minutes 1** — e.g. 6 h → 30 min
- **Break after hours 2** / **Break minutes 2** — e.g. 9 h → 45 min

These are used only to **suggest** break in the manual entry form; the user can always override or leave break empty. They do not auto-apply.

---

## Data model

- **`time_entries.break_seconds`** — Total break in seconds for this entry (timer pauses or manual break).
- **`time_entries.paused_at`** — When set, the timer is paused; on resume, `(now − paused_at)` is added to `break_seconds` and `paused_at` is cleared.
- **`duration_seconds`** — Always **worked time**: (end − start) − break, then rounding. Reports and lists use this.

---

## API summary

| Action        | Web route           | API v1 route              |
|---------------|---------------------|---------------------------|
| Pause timer   | `POST /timer/pause` | `POST /api/v1/timer/pause` |
| Resume timer  | `POST /timer/resume`| `POST /api/v1/timer/resume`|
| Timer status  | `GET /timer/status` | `GET /api/v1/timer/status` |

Time entry create/update (manual and API) accept optional **`break_seconds`**; response includes `break_seconds` and (for active timers) `paused_at`, `break_formatted`.
