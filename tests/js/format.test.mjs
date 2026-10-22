// UT-JFMT: display formatting (REQ-021). Run: node --test "tests/js/*.test.mjs"
import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  formatDate,
  formatMoney,
  formatMonth,
  formatNumber,
  formatPercent,
  formatRate,
  formatSignedMoney,
} from '../../static/js/i18n/format.js';

test('UT-JFMT-01 formatMoney', () => {
  assert.equal(formatMoney(1200, 'en'), '¥1,200');
  assert.equal(formatMoney(1200, 'ja'), '1,200円');
  assert.equal(formatMoney(-1200, 'en'), '-¥1,200');
  assert.equal(formatMoney(-1200, 'ja'), '-1,200円');
  assert.equal(formatMoney(0, 'en'), '¥0');
  assert.equal(formatMoney(null, 'en'), '—');
  assert.equal(formatMoney(undefined, 'ja'), '—');
});

test('UT-JFMT-02 formatSignedMoney', () => {
  assert.equal(formatSignedMoney(1200, 'en'), '+¥1,200');
  assert.equal(formatSignedMoney(1200, 'ja'), '+1,200円');
  assert.equal(formatSignedMoney(0, 'en'), '¥0');
  assert.equal(formatSignedMoney(-1200, 'en'), '-¥1,200');
  assert.equal(formatSignedMoney(null, 'en'), '—');
});

test('UT-JFMT-03 formatDate', () => {
  assert.equal(formatDate('2026-10-23', 'en'), 'Oct 23, 2026');
  assert.equal(formatDate('2026-10-23', 'ja'), '2026年10月23日');
  assert.equal(formatDate('2026-01-05', 'ja'), '2026年1月5日');
  assert.equal(formatDate('2026-01-05', 'en'), 'Jan 5, 2026');
  assert.equal(formatDate('not a date', 'en'), 'not a date');
  assert.equal(formatDate(null, 'en'), '');
});

test('UT-JFMT-04 formatDate does not shift by timezone', () => {
  const original = process.env.TZ;
  try {
    for (const tz of ['Pacific/Honolulu', 'Asia/Tokyo', 'UTC']) {
      process.env.TZ = tz;
      assert.equal(formatDate('2026-10-01', 'en'), 'Oct 1, 2026', tz);
      assert.equal(formatMonth('2026-10', 'en'), 'Oct 2026', tz);
    }
  } finally {
    process.env.TZ = original;
  }
});

test('UT-JFMT-05 formatMonth', () => {
  assert.equal(formatMonth('2026-10', 'en'), 'Oct 2026');
  assert.equal(formatMonth('2026-01', 'ja'), '2026年1月');
  assert.equal(formatMonth('bad', 'ja'), 'bad');
});

test('UT-JFMT-06 formatRate', () => {
  assert.equal(formatRate('12.5'), '+12.5%');
  assert.equal(formatRate('-6.3'), '-6.3%');
  assert.equal(formatRate('0.0'), '0.0%');
  assert.equal(formatRate(null), '—');
});

test('UT-JFMT-07 formatPercent and formatNumber', () => {
  assert.equal(formatPercent(93), '93%');
  assert.equal(formatPercent(null), '—');
  assert.equal(formatNumber(9999999, 'ja'), '9,999,999');
  assert.equal(formatNumber(1234, 'xx'), '1,234'); // unknown language falls back to en
});
