import en from './en.json';

const catalogs = { en };
let locale = 'en';
const listeners = new Set();

function interpolate(template, vars = {}) {
  return String(template).replace(/\{\{(\w+)\}\}/g, (_, key) => {
    if (vars[key] == null) return '';
    return String(vars[key]);
  });
}

export function getLocale() {
  return locale;
}

export function listLocales() {
  return Object.keys(catalogs);
}

export function setLocale(next) {
  if (!catalogs[next]) return locale;
  if (locale === next) return locale;
  locale = next;
  listeners.forEach((fn) => {
    try {
      fn(locale);
    } catch {
      /* ignore listener errors */
    }
  });
  return locale;
}

export function onLocaleChange(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function t(key, fallbackOrVars, maybeVars) {
  const parts = String(key).split('.');
  let cur = catalogs[locale];
  for (const part of parts) {
    cur = cur?.[part];
  }

  let fallback = key;
  let vars = {};
  if (typeof fallbackOrVars === 'string') {
    fallback = fallbackOrVars;
    vars = maybeVars || {};
  } else if (fallbackOrVars && typeof fallbackOrVars === 'object') {
    vars = fallbackOrVars;
  }

  if (cur != null && typeof cur === 'string') return interpolate(cur, vars);
  return interpolate(fallback, vars);
}
