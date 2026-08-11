# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 5.11.x  | :white_check_mark: |
| < 5.11  | :x:                |

Security fixes are released on the latest stable line. Older major/minor versions are not backported unless a fix is specifically announced.

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

### Preferred: GitHub private reporting

1. Go to the repository **Security** tab → **Advisories** → **Report a vulnerability**, or use [GitHub’s private vulnerability reporting](https://github.com/drytrix/TimeTracker/security/advisories/new).
2. Include:
   - A clear description of the issue and impact
   - Affected versions / commit if known
   - Steps to reproduce (PoC welcome)
   - Suggested fix if you have one
3. We will acknowledge the report, coordinate a fix, and credit you in the advisory if you wish.

### Coordinated disclosure

- We aim to acknowledge reports within **7 days**.
- We aim to release a fix (or mitigation guidance) within a reasonable window after confirmation, typically **30–90 days** depending on severity and complexity.
- Please keep details confidential until a fix is released and an advisory is published.
- After a fix ships, we may request a CVE via a GitHub Security Advisory and list the reporter as credit when appropriate.

### Out of scope (examples)

- Denial-of-service via resource exhaustion without a clear security boundary bypass
- Issues that require physical access or already-compromised admin credentials (unless privilege escalation beyond that is demonstrated)
- Reports against third-party dependencies without a clear exploitable path in TimeTracker (please report those upstream when possible)

Thank you for helping keep TimeTracker and its users safe.
