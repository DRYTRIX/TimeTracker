# Client email reply — workday sessions & hour limits

Ready to send: copy the message below. Replace `[Your name]` and adjust rollout details if needed.

---

**Subject:** Re: Time tracking for employee workday + project time

Hello,

Thank you for your message and for testing TimeTracker so thoroughly. Your questions match exactly what many teams need when they use the product both for **employee attendance** and for **project/client time**. We have implemented the following in **version 5.7.0** to cover your use case.

---

### 1. One-click “Start work” / “End work” (without a project)

Previously, starting a timer always required a **project** or a **client**, so there was no simple “I am at work now” button.

**What you have now:** a **Workday** control on the **Dashboard** and on the **Timer** page:

- **Start Workday** — one click when the employee begins their day (no project, client, or task).
- **End Workday** — one click when they leave.

The same actions are available on **shared kiosk devices** and via the **REST API** (for mobile or integrations).

---

### 2. Avoiding “duplicate” time when also tracking projects

You described the situation well: if workday time and project time were stored in the same total, one hour on a client project could be counted twice (once as “at work” and once as “on project”).

**How we solve this:** workday time and project time are **two separate tracks**:

| Track | Meaning |
|--------|---------|
| **Workday session** | How long the person was at work (clock-in to clock-out). |
| **Project time entries** | How long they spent on a specific project or client. |

On the dashboard you will see both **“At work today”** and **“On projects today”** side by side. **These numbers are never added together.** Example: an 8-hour workday with 1 hour on Client X is shown as **8 h at work** and **1 h on projects** — not 9 h total.

During the day, employees can run a **project timer** as before; that does not replace the workday session.

---

### 3. Daily and weekly hour limits, email, and justification

Yes — this is supported and configurable.

**For administrators** (Admin → Settings → Time entry requirements → **Working time limits**):

- Enable daily and weekly caps (defaults: **10 h/day**, **48 h/week**; adjustable).
- Optional **email** when a limit is exceeded.
- Per-user overrides are possible under each user’s settings.

**For employees (soft enforcement):**

- Work can continue; the system does **not** block urgent work by default.
- When a limit is exceeded, the employee receives an **email** and sees a notice on the dashboard.
- They submit a **short justification** in TimeTracker.
- Administrators review submissions under **Working time limit reviews** (`/admin/working-time`) and can acknowledge them.

If you prefer **hard blocking** (timer cannot continue until a reason is entered), we can discuss that as a follow-up — the current release uses the softer model you described.

---

### What we need from you before rollout

To configure this cleanly for your company, please let us know:

1. **Kiosk / shared devices:** Should all employees use **Start/End Workday** on kiosk terminals as well as on their own accounts? (Both are supported today.)
2. **Notifications:** When a limit is exceeded, should the email go **only to the employee**, or should a **manager/admin be copied** by default?
3. **Weekly limit:** Should the weekly cap trigger **as soon as the running total exceeds the limit**, or only with a **summary at end of week**?

---

### Technical note for your IT team

After upgrading to **5.7.0**, please run the database migration (`flask db upgrade` — revision **158**). A short admin/user guide is available in our documentation: *Workday sessions and working time limits*.

We are happy to walk you through the setup on a short call if that helps.

Mit freundlichen Grüßen,  
[Your name]
