/**
 * Tiny chrome/browser API shim for Chromium + Firefox.
 * Prefer `browser` (Promise-based) when available; fall back to `chrome`.
 */

export const ext =
  typeof globalThis.browser !== 'undefined' ? globalThis.browser : globalThis.chrome;
