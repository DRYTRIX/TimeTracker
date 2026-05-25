# Client email reply — workday sessions & hour limits

Ready to send (adjust name and delivery timeline before sending).

---

**Subject:** Re: Time tracking for employee workday + project time

Hello!

Thank you for the detailed feedback — these are all valid points and we are happy to address them. Below is what is possible in TimeTracker today and what we have added to fully cover your use case.

**1. One-click "Start Work" / "End Work" for employees**

Previously, every timer in TimeTracker had to be linked to a project or to a client, so there was no truly project-less clock-in button.

We have added a dedicated **"Workday Session"** feature: employees see a clearly labelled **Start Workday** button on the dashboard and on the timer page. One click starts their workday, a second click ends it. No project, no client, no task required. The same is available via the REST API and kiosk mode.

**2. Avoiding double bookings between workday time and project time**

You correctly identified the core issue: if "starting the workday" and "tracking a project hour" lived in the same bucket, the same hour would be counted twice.

The **Workday Session** lives on a separate axis from project time entries:

- The Workday Session answers "how long was the employee at work today/this week".
- Project time entries continue to answer "how much time was spent on Client X / Project Y".

The dashboard and reports show these as two parallel totals; they are never added together. So an 8-hour workday that includes one hour for Client X stays 8 hours total — never 9.

**3. Soft daily and weekly limits with notifications and justification**

This is available as a configurable feature (Admin → Settings → Working time limits), with optional per-user overrides in user settings.

- Admins set a daily cap (default 10h) and weekly cap (default 48h).
- When an employee exceeds the cap, the system sends an email and asks them to submit a short written reason.
- The employee submits the justification inside TimeTracker; admins review submissions under **Admin → Working time limit reviews**.
- Enforcement is **soft**: timers keep running; every exceedance is recorded.

We can add hard-blocking (timer cannot continue without a justification) in a later iteration if you prefer.

Before we finalize rollout, please let us know:

1. Should the workday button be available in kiosk / shared-device mode as well, or only on individual accounts? (Both are supported today.)
2. For hour caps, should the email go only to the employee, or should the admin/manager be CC'ed by default?
3. Should weekly caps trigger as soon as the total exceeds the limit, or only at end of week?

Mit freundlichen Grüßen,  
[Your name]
