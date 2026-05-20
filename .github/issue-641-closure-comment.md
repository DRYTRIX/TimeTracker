Thanks again for testing and for the clear follow-up — that helps a lot.

You're right: TimeTracker is built as **one company with many users**, not as multi-tenant software with separate company profiles, invoice letterheads, and email senders per tenant. Roles and permissions (including the own-scope work on `develop` for tasks, projects, and clients) can limit what users see **within a single organization**, but they cannot deliver the fully independent companies you described.

**Recommended approach for your setup:** run **one TimeTracker instance per company** (e.g. three Docker Compose stacks on different ports, each with its own database volume, `SECRET_KEY`, company settings, and SMTP). Each person can be admin of their own instance with complete isolation.

We documented this pattern here:

https://github.com/DRYTRIX/TimeTracker/blob/develop/docs/MULTI_INSTANCE_SETUP.md

The UI issues you noted on create-task / manual log (project dropdowns, grayed-out task field) are side effects of partial RBAC scoping in a single instance; they are not relevant if you use separate instances, and we are not pursuing further RBAC changes for the multi-company scenario in the short term.

Closing this as **won't fix (multi-company architecture)** with the separate-instance workaround documented. If multi-tenant support becomes a future epic, we can track it separately.

Best regards!
