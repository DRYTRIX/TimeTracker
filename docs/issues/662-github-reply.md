# Draft GitHub reply for issue #662

Use this as a reply to [issue #662](https://github.com/DRYTRIX/TimeTracker/issues/662#issuecomment-4768346669).

---

Hi @fufiderheld — thanks for the follow-up video.

The original expense-linking bug was fixed in **TimeTracker 5.8.2**. Please upgrade your Docker deployment to **5.8.4** (or at least **5.8.2**).

## Time entries vs. expenses

TimeTracker keeps two separate sections on an invoice:

| Goal | Button to use | Where it appears |
|------|---------------|------------------|
| Add **logged work hours** | **Generate from Time/Costs** (or **Add Time Entries** on the edit page) | **Invoice Items** |
| Add **travel, meals, materials** (Expense module records) | **Add Expense** | **Expenses** |

Time entries are **not** expense records. They always become invoice line items (hourly work), not rows in the Expenses section.

## If billable time entries do not show up

On **Generate from Time/Costs**, entries must match all of the following:

1. **Same project** as the invoice (the invoice is tied to one project).
2. Marked **billable**.
3. Timer **stopped** (running timers have no end time yet).
4. **Not already on another invoice** for this client.

If you clicked **Add Expense**, expand **Show time entries and project costs** at the top — time entries are listed there, not under billable expenses.

## Preserving individual descriptions

On **Generate from Time/Costs**, enable **Create one invoice line per time entry** to avoid grouping multiple entries on the same task into a single line (which merges descriptions).

## Please confirm

After upgrading, can you check:

- The invoice project matches where you logged the time?
- The entries are billable and stopped?
- You use **Generate from Time/Costs** / **Add Time Entries** for hours?

If it still fails, please share the invoice project name and whether the time entries appear on the project dashboard as billable and unbilled.
