# Belgium 2027 Time Registration Compliance

This guide explains how TimeTracker supports Belgium's mandatory working-time registration from **1 January 2027**, based on EU case law (CJEU C-55/18, Loredas 2024) and the federal budget commitment of November 2025.

> **Legal caveat:** Final Belgian implementing legislation (bill + Royal Decree) was still pending as of early 2026. TimeTracker implements the known **objective, reliable, accessible** standard from EU case law. When the Royal Decree is published, review [app/compliance/belgium_config.py](../app/compliance/belgium_config.py) and Admin → Compliance settings for any JSON overrides.

## What the law requires

Employers must operate a system that:

1. **Objectively** records actual start/end times (not estimates)
2. **Reliably** prevents untraced changes (audit trail + corrections)
3. **Accessibly** lets employees view their records and inspectors export data
4. Covers **daily** work, **breaks**, and **absences** (vacation, sick leave, etc.)
5. Supports **remote/hybrid** workers (mobile app + API)

Belgium does **not** require a physical punch clock — software is sufficient.

## Enable Belgium preset

1. Go to **Admin → Settings → Time entry requirements**
2. Under **Belgium / EU attendance compliance (2027)**:
   - Enable **attendance compliance module**
   - Select jurisdiction preset **Belgium (2027)**
   - Save settings

The Belgium preset applies:

| Setting | Default |
|---------|---------|
| Standard daily hours | 8h |
| Standard weekly hours | 38h |
| Break required after | 6h worked |
| Minimum break | 15 minutes |
| Minimum daily rest | 11 hours between shifts |
| Record retention | 10 years |

## Employee workflow

1. **Start Workday** when arriving (Dashboard or Timer page)
2. **Start Break** / **End Break** during the day (compliance break tracking)
3. **End Workday** when leaving
4. View **My attendance** at `/workday/history` (work periods, breaks, absences, warnings)
5. Declare **multi-employer** status in **User settings** if applicable

Project timers remain separate for billing — they are not the legal attendance record.

## Corrections (reliable records)

Direct deletion of attendance records is blocked. To fix errors:

1. Employee submits a **correction request** with a mandatory reason
2. Admin reviews at **Admin → Attendance corrections**
3. Approved changes are applied and logged in the audit trail

Locked timesheet periods also lock attendance for those dates.

## Inspector export

Admins and approvers can export a Belgium-oriented CSV:

- **Web:** Workforce → Belgium attendance report  
  `GET /workforce/reports/belgium-attendance.csv?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- **API:** `GET /api/v1/reports/compliance/belgium-attendance`

Export columns include: employee, date, status, work/break times, net hours, daily rest gap, overtime, absence type, correction summary, lock status, multi-employer declaration.

## API endpoints (mobile / integrations)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/attendance/status` | Active work period, break, today's record |
| POST | `/api/v1/workday/start` | Clock in |
| POST | `/api/v1/workday/end` | Clock out |
| POST | `/api/v1/attendance/break/start` | Start break |
| POST | `/api/v1/attendance/break/end` | End break |
| GET | `/api/v1/attendance/history` | Personal history |
| POST | `/api/v1/attendance/corrections` | Request correction |

## Retention

Default retention is **10 years** (recommended for time registration disputes). Minimum configurable value is **5 years**. Do not purge attendance data below your configured retention without legal review.

## Adapting to the final Royal Decree

When the Royal Decree is published:

1. Review official modalities (export format, sector rules, retention)
2. Update `Settings.compliance_royal_decree_config` JSON in Admin (or `app/compliance/belgium_config.py`)
3. Re-run inspector export against a sample period to verify columns

## Verification checklist

- [ ] Belgium preset enabled
- [ ] Employees clock in/out daily (web or mobile)
- [ ] Breaks registered when work exceeds 6h
- [ ] Approved time-off appears as absence days
- [ ] Inspector CSV exports for a date range
- [ ] Corrections require reason and appear in audit log
- [ ] Multi-employer declarations captured on user profile
