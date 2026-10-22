/**
 * Language-specific display formatting. Formatting only, no business calculation (NFR-007).
 * Design refs: REQ-021, 02 screen design ch.4 table.
 */

const LOCALES = { en: 'en-US', ja: 'ja-JP' };
const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;
const ISO_MONTH = /^(\d{4})-(\d{2})$/;

function locale(lang) {
  return LOCALES[lang] ?? LOCALES.en;
}

export function formatNumber(value, lang) {
  return new Intl.NumberFormat(locale(lang)).format(value);
}

/** en: ¥1,200 / -¥1,200, ja: 1,200円 / -1,200円 */
export function formatMoney(amount, lang) {
  if (amount === null || amount === undefined) return '—';
  const sign = amount < 0 ? '-' : '';
  const digits = formatNumber(Math.abs(amount), lang);
  return lang === 'ja' ? `${sign}${digits}円` : `${sign}¥${digits}`;
}

/** Month-over-month difference: +¥1,200 / -¥1,200 / ¥0 */
export function formatSignedMoney(amount, lang) {
  if (amount === null || amount === undefined) return '—';
  return amount > 0 ? `+${formatMoney(amount, lang)}` : formatMoney(amount, lang);
}

/** en: Oct 23, 2026, ja: 2026年10月23日. Built in UTC so the browser timezone cannot shift the day. */
export function formatDate(iso, lang) {
  const match = ISO_DATE.exec(iso ?? '');
  if (!match) return iso ?? '';
  const [year, month, day] = [Number(match[1]), Number(match[2]), Number(match[3])];
  if (lang === 'ja') return `${year}年${month}月${day}日`;
  return new Intl.DateTimeFormat(locale(lang), {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(Date.UTC(year, month - 1, day)));
}

/** en: Oct 2026, ja: 2026年10月 */
export function formatMonth(ym, lang) {
  const match = ISO_MONTH.exec(ym ?? '');
  if (!match) return ym ?? '';
  const [year, month] = [Number(match[1]), Number(match[2])];
  if (lang === 'ja') return `${year}年${month}月`;
  return new Intl.DateTimeFormat(locale(lang), { year: 'numeric', month: 'short', timeZone: 'UTC' }).format(
    new Date(Date.UTC(year, month - 1, 1)),
  );
}

/** Rate strings come from the API (BR-06): "12.5" -> +12.5%, "-6.3" -> -6.3%, null -> — */
export function formatRate(rate) {
  if (rate === null || rate === undefined) return '—';
  const text = String(rate);
  if (text.startsWith('-') || /^0(\.0+)?$/.test(text)) return `${text}%`;
  return `+${text}%`;
}

/** Budget usage (integer from the API). */
export function formatPercent(value) {
  if (value === null || value === undefined) return '—';
  return `${value}%`;
}
