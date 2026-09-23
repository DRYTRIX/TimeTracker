import en from './en.json';

const catalogs = { en };
let locale = 'en';

export function setLocale(next) {
  if (catalogs[next]) locale = next;
}

export function t(key, fallback) {
  const parts = String(key).split('.');
  let cur = catalogs[locale];
  for (const part of parts) {
    cur = cur?.[part];
  }
  if (cur != null && typeof cur === 'string') return cur;
  return fallback ?? key;
}
