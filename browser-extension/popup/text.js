/**
 * Text helpers for display. Server data occasionally contains pre-escaped
 * HTML entities (e.g. "&amp;" stored literally), so display strings are
 * decoded once before rendering; anything written via innerHTML is escaped
 * afterwards to stay XSS-safe.
 */

const decoder = typeof document !== 'undefined' ? document.createElement('textarea') : null;

/** Decode HTML entities in display strings ("&amp;" → "&"), once. */
export function decodeEntities(text) {
  const s = String(text ?? '');
  if (!s.includes('&') || !decoder) return s;
  decoder.innerHTML = s;
  return decoder.value;
}

/** Escape a string for safe insertion via innerHTML. */
export function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = String(text ?? '');
  return div.innerHTML;
}

/** decode → escape, for innerHTML targets. */
export function displayHtml(text) {
  return escapeHtml(decodeEntities(text));
}
