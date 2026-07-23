# End-to-end and accessibility tests

Playwright drives a real browser against a running TimeTracker instance. This is the
only layer that can catch the failure modes the Python suite structurally cannot:

- **Runtime CSP violations.** The strict, nonce-based policy currently ships as
  `Content-Security-Policy-Report-Only`. It can only become the enforced policy once a
  real browser confirms zero `script-src` violations across the app. `csp.spec.js`
  asserts exactly that.
- **Broken JS bundles.** `base.html` used to load ~32 separate scripts; they are now
  concatenated into ordered bundles (`scripts/build-js.mjs`). Several of those files
  declare globals that other files consume, so a bad grouping breaks silently at
  runtime with a green Python suite.
- **Offline capability.** `offline.spec.js` blocks all external hosts and asserts the
  app still renders — the guarantee that makes air-gapped installs viable.
- **Accessibility.** axe-core runs over the highest-traffic screens.

## Running locally

```bash
npm install
npx playwright install --with-deps chromium
# start the app on :8080 however you normally do, then:
E2E_BASE_URL=http://localhost:8080 npx playwright test
```

Set `E2E_USERNAME` / `E2E_PASSWORD` for an account that can reach the authenticated
screens; the specs skip those checks when credentials are absent.
