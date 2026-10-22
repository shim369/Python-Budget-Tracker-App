// UT-JCHT: chart configuration builders (CH-01, CH-02).
import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  OTHER_COLOR,
  PALETTE,
  buildBreakdownConfig,
  buildTrendConfig,
  isAllZero,
} from '../../static/js/charts/chart-config.js';
import { formatMoney, formatMonth } from '../../static/js/i18n/format.js';

const labels = { 'category.food': '食費', 'category.others': 'その他(合算)', 'chart.total': '合計' };
const fmt = {
  t: (key) => labels[key] ?? key,
  money: (v) => formatMoney(v, 'ja'),
  month: (ym) => formatMonth(ym, 'ja'),
};

test('UT-JCHT-01 isAllZero', () => {
  assert.equal(isAllZero([{ total: 0 }, { total: 0 }]), true);
  assert.equal(isAllZero([{ total: 0 }, { total: 1 }]), false);
  assert.equal(isAllZero([]), true);
  assert.equal(isAllZero(undefined), true);
});

const breakdown = {
  items: [
    { kind: 'category', key: 'category.food', name: null, amount: 42000, ratio_percent: '37.3' },
    { kind: 'category', key: null, name: 'Pets', amount: 5400, ratio_percent: '4.8' },
    { kind: 'other', key: 'category.others', name: null, amount: 3000, ratio_percent: '2.7' },
  ],
};

test('UT-JCHT-02 pie labels follow key / name', () => {
  const config = buildBreakdownConfig(breakdown, fmt);
  assert.equal(config.type, 'pie');
  assert.deepEqual(config.data.labels, ['食費', 'Pets', 'その他(合算)']);
  assert.deepEqual(config.data.datasets[0].data, [42000, 5400, 3000]);
});

test('UT-JCHT-03 pie colors', () => {
  const colors = buildBreakdownConfig(breakdown, fmt).data.datasets[0].backgroundColor;
  assert.deepEqual(colors, [PALETTE[0], PALETTE[1], OTHER_COLOR]);
  const many = { items: Array.from({ length: 9 }, (_, i) => ({ kind: 'category', name: `c${i}`, amount: 1 })) };
  assert.equal(buildBreakdownConfig(many, fmt).data.datasets[0].backgroundColor[8], PALETTE[0]);
});

test('UT-JCHT-04 pie tooltip', () => {
  const config = buildBreakdownConfig(breakdown, fmt);
  assert.equal(config.options.plugins.tooltip.callbacks.label({ dataIndex: 0 }), '食費: 42,000円 (37.3%)');
});

test('UT-JCHT-05 bar config uses the formatters', () => {
  const trend = { items: [{ month: '2026-09', total: 100000 }, { month: '2026-10', total: 112500 }] };
  const config = buildTrendConfig(trend, fmt);
  assert.equal(config.type, 'bar');
  assert.deepEqual(config.data.labels, ['2026年9月', '2026年10月']);
  assert.equal(config.data.datasets[0].label, '合計');
  assert.equal(config.options.scales.y.beginAtZero, true);
  assert.equal(config.options.scales.y.ticks.callback(50000), '50,000円');
  assert.equal(config.options.plugins.tooltip.callbacks.label({ dataIndex: 1 }), '2026年10月: 112,500円');
  assert.equal(config.options.plugins.legend.display, false);
});
