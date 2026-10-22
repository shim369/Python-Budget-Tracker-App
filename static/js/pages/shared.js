/**
 * Helpers shared by the page components. Pure functions (no DOM / Alpine).
 * Design refs: ERR-20, 02 screen design ch.4 "error display".
 */

import { formatDate, formatNumber } from '../i18n/format.js';

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

/** [AD-03] Fixed categories are translated by key, user categories show their name. */
export function categoryLabel(item, t) {
  if (!item) return '';
  return item.key ? t(item.key) : (item.name ?? '');
}

/** VALIDATION_ERROR details -> { "amount": {code, params}, ... } (first error per field). */
export function fieldErrorsFrom(error) {
  if (!error || error.code !== 'VALIDATION_ERROR' || !Array.isArray(error.details)) return {};
  const result = {};
  for (const detail of error.details) {
    if (detail.field && !(detail.field in result)) {
      result[detail.field] = { code: detail.code, params: detail.params ?? {} };
    }
  }
  return result;
}

/** Keep errors as code + params so the text follows language switches. */
export function errorView(error) {
  return {
    code: error?.code ?? 'UNKNOWN',
    params: error?.details?.[0]?.params ?? {},
  };
}

/** Translation key for a top-level error code, falling back to errors.UNKNOWN. */
export function errorKey(code, has) {
  const key = `errors.${code}`;
  return has(key) ? key : 'errors.UNKNOWN';
}

function formatParam(value, lang) {
  if (typeof value === 'number') return formatNumber(value, lang);
  if (typeof value === 'string' && ISO_DATE.test(value)) return formatDate(value, lang);
  if (Array.isArray(value)) return value.join(', ');
  return value;
}

/** Text for one field error, with numbers and dates formatted for the language. */
export function fieldMessage(fieldError, { t, has, lang }) {
  if (!fieldError) return '';
  const key = `errors.field.${fieldError.code}`;
  const params = Object.fromEntries(
    Object.entries(fieldError.params ?? {}).map(([name, value]) => [name, formatParam(value, lang)]),
  );
  return t(has(key) ? key : 'errors.field.INVALID_VALUE', params);
}

/** Message parameters for top-level errors (e.g. {count}, {max}). */
export function errorParams(view, lang) {
  return Object.fromEntries(Object.entries(view?.params ?? {}).map(([name, value]) => [name, formatParam(value, lang)]));
}

/** Form value -> number for the API. Empty -> null. Non-numeric text is sent as is (API rejects it). */
export function toNumberOrNull(value) {
  if (value === '' || value === null || value === undefined) return null;
  if (typeof value === 'number') return value;
  const number = Number(value);
  return Number.isNaN(number) ? value : number;
}
