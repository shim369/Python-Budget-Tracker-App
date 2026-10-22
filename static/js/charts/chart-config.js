/**
 * API response -> Chart.js configuration. Pure functions (no Chart.js import).
 * Design refs: 02 screen design ch.6 (CH-01, CH-02), REQ-015, REQ-021.
 */

import { categoryLabel } from '../pages/shared.js';

export const PALETTE = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc948', '#b07aa1', '#ff9da7'];
export const OTHER_COLOR = '#9aa0a6';
export const BAR_COLOR = '#4e79a7';

/** Show "no data" instead of the bar chart when all months are 0 yen. */
export function isAllZero(items) {
  return !Array.isArray(items) || items.every((item) => item.total === 0);
}

/**
 * [CH-01] Pie chart of the category breakdown (API-22).
 * @param {{items: Array}} breakdown
 * @param {{t: Function, money: Function}} fmt
 */
export function buildBreakdownConfig(breakdown, { t, money }) {
  const items = breakdown.items;
  const labels = items.map((item) => categoryLabel(item, t));
  return {
    type: 'pie',
    data: {
      labels,
      datasets: [
        {
          data: items.map((item) => item.amount),
          backgroundColor: items.map((item, index) =>
            item.kind === 'other' ? OTHER_COLOR : PALETTE[index % PALETTE.length],
          ),
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { position: 'bottom' },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const item = items[ctx.dataIndex];
              return `${labels[ctx.dataIndex]}: ${money(item.amount)} (${item.ratio_percent}%)`;
            },
          },
        },
      },
    },
  };
}

/**
 * [CH-02] Bar chart of the last six months (API-23).
 * @param {{items: Array}} trend
 * @param {{t: Function, money: Function, month: Function}} fmt
 */
export function buildTrendConfig(trend, { t, money, month }) {
  const items = trend.items;
  const labels = items.map((item) => month(item.month));
  return {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label: t('chart.total'), data: items.map((item) => item.total), backgroundColor: BAR_COLOR }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      scales: {
        y: { beginAtZero: true, ticks: { callback: (value) => money(value) } },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `${labels[ctx.dataIndex]}: ${money(items[ctx.dataIndex].total)}`,
          },
        },
      },
    },
  };
}
