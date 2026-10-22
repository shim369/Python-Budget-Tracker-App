// UT-JSHR: page helpers (ERR-20, screen design ch.4 "error display").
import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  categoryLabel,
  errorKey,
  errorParams,
  errorView,
  fieldErrorsFrom,
  fieldMessage,
  toNumberOrNull,
} from '../../static/js/pages/shared.js';

const messages = {
  'errors.field.OUT_OF_RANGE': '{min}〜{max}の範囲で入力してください。',
  'errors.field.DATE_OUT_OF_RANGE': '{min}〜{max}',
  'errors.field.INVALID_CHOICE': '{choices}',
  'errors.field.INVALID_VALUE': '値が正しくありません。',
};
const ctx = (lang) => ({
  t: (key, params = {}) => (messages[key] ?? key).replace(/\{(\w+)\}/g, (_, n) => params[n]),
  has: (key) => key in messages,
  lang,
});

test('UT-JSHR-01 fieldErrorsFrom', () => {
  const error = {
    code: 'VALIDATION_ERROR',
    details: [
      { field: 'amount', code: 'OUT_OF_RANGE', params: { min: 1, max: 9999999 } },
      { field: 'amount', code: 'INVALID_TYPE' },
      { field: null, code: 'X' },
      { field: 'date', code: 'INVALID_DATE' },
    ],
  };
  assert.deepEqual(fieldErrorsFrom(error), {
    amount: { code: 'OUT_OF_RANGE', params: { min: 1, max: 9999999 } },
    date: { code: 'INVALID_DATE', params: {} },
  });
  assert.deepEqual(fieldErrorsFrom({ code: 'CATEGORY_IN_USE', details: [] }), {});
  assert.deepEqual(fieldErrorsFrom(null), {});
});

test('UT-JSHR-02 errorView and errorKey', () => {
  assert.deepEqual(errorView({ code: 'CATEGORY_IN_USE', details: [{ params: { count: 2 } }] }), {
    code: 'CATEGORY_IN_USE',
    params: { count: 2 },
  });
  assert.deepEqual(errorView(undefined), { code: 'UNKNOWN', params: {} });
  const has = (key) => key === 'errors.CATEGORY_IN_USE';
  assert.equal(errorKey('CATEGORY_IN_USE', has), 'errors.CATEGORY_IN_USE');
  assert.equal(errorKey('SOMETHING_NEW', has), 'errors.UNKNOWN');
  assert.deepEqual(errorParams({ params: { max: 5000 } }, 'en'), { max: '5,000' });
});

test('UT-JSHR-03 fieldMessage formats params by language', () => {
  const range = { code: 'OUT_OF_RANGE', params: { min: 1, max: 9999999 } };
  assert.equal(fieldMessage(range, ctx('ja')), '1〜9,999,999の範囲で入力してください。');
  const dates = { code: 'DATE_OUT_OF_RANGE', params: { min: '2000-01-01', max: '2099-12-31' } };
  assert.equal(fieldMessage(dates, ctx('ja')), '2000年1月1日〜2099年12月31日');
  assert.equal(fieldMessage(dates, ctx('en')), 'Jan 1, 2000〜Dec 31, 2099');
  assert.equal(fieldMessage({ code: 'INVALID_CHOICE', params: { choices: ['monthly', 'yearly'] } }, ctx('en')), 'monthly, yearly');
  assert.equal(fieldMessage({ code: 'BRAND_NEW', params: {} }, ctx('ja')), '値が正しくありません。');
  assert.equal(fieldMessage(undefined, ctx('ja')), '');
});

test('UT-JSHR-04 toNumberOrNull', () => {
  assert.equal(toNumberOrNull(''), null);
  assert.equal(toNumberOrNull(null), null);
  assert.equal(toNumberOrNull(undefined), null);
  assert.equal(toNumberOrNull('12'), 12);
  assert.equal(toNumberOrNull(12), 12);
  assert.equal(toNumberOrNull('abc'), 'abc');
});

test('UT-JSHR-05 categoryLabel', () => {
  const t = (key) => `T(${key})`;
  assert.equal(categoryLabel({ key: 'category.food', name: null }, t), 'T(category.food)');
  assert.equal(categoryLabel({ key: null, name: 'Pets' }, t), 'Pets');
  assert.equal(categoryLabel({ key: null, name: null }, t), '');
  assert.equal(categoryLabel(null, t), '');
});
