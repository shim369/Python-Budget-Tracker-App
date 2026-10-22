/**
 * Dictionary lookup, interpolation and language persistence.
 * Design refs: REQ-020, 02 screen design ch.4. Pure module (storage/fetch are injected).
 */

export const SUPPORTED_LANGS = ['en', 'ja'];
export const DEFAULT_LANG = 'en';
export const STORAGE_KEY = 'budgetTracker.lang';

/** Resolve a dotted key ("nav.dashboard") in a nested dictionary. */
export function resolveKey(dict, key) {
  return key.split('.').reduce((node, part) => (node && typeof node === 'object' ? node[part] : undefined), dict);
}

/** Replace {name} placeholders; unknown placeholders are left as they are. */
export function interpolate(template, params = {}) {
  return template.replace(/\{(\w+)\}/g, (match, name) =>
    params[name] !== undefined && params[name] !== null ? String(params[name]) : match,
  );
}

export function hasKey(dicts, lang, key) {
  return typeof resolveKey(dicts[lang], key) === 'string' || typeof resolveKey(dicts[DEFAULT_LANG], key) === 'string';
}

/** Current language first, then English, then the key itself (so gaps are visible). */
export function translate(dicts, lang, key, params) {
  let value = resolveKey(dicts[lang], key);
  if (typeof value !== 'string') value = resolveKey(dicts[DEFAULT_LANG], key);
  if (typeof value !== 'string') return key;
  return interpolate(value, params);
}

/** Saved language if valid, otherwise English. Storage errors are ignored. */
export function readStoredLang(storage) {
  try {
    const value = storage?.getItem(STORAGE_KEY);
    return SUPPORTED_LANGS.includes(value) ? value : DEFAULT_LANG;
  } catch {
    return DEFAULT_LANG;
  }
}

export function saveLang(storage, lang) {
  try {
    storage?.setItem(STORAGE_KEY, lang);
  } catch {
    // Private mode etc.: keep working without persistence.
  }
}

export async function loadDictionary(lang, fetchFn = (...args) => globalThis.fetch(...args)) {
  const response = await fetchFn(`/static/i18n/${lang}.json`);
  if (!response.ok) throw new Error(`Failed to load dictionary: ${lang}`);
  return response.json();
}

/** All leaf keys as dotted paths (used by the key consistency test, REQ-023). */
export function collectKeys(dict, prefix = '') {
  return Object.entries(dict).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return value && typeof value === 'object' ? collectKeys(value, path) : [path];
  });
}
