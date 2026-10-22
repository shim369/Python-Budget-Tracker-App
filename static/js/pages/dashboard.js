/**
 * [SCR-01] Dashboard. Shows API results only; no aggregation here (NFR-007).
 * State and APIs: 02 screen design ch.7 (API-21, 18, 22, 23).
 */

import { api } from '../api/client.js';
import { buildBreakdownConfig, buildTrendConfig, isAllZero } from '../charts/chart-config.js';
import { destroyChart, renderChart } from '../charts/chart-render.js';
import { formatMoney, formatMonth } from '../i18n/format.js';
import { categoryLabel, errorView } from './shared.js';

const ROUTE = 'dashboard';

export function dashboardPage() {
  return {
    month: null,
    summary: null,
    upcoming: null,
    breakdown: null,
    trend: null,
    loading: false,
    error: null,

    init() {
      this.$watch('$store.app.route', (route) => route === ROUTE && this.load());
      if (this.$store.app.route === ROUTE) this.load();
    },

    async load(month) {
      await this.$store.app.ready();
      const ym = month ?? this.month ?? this.$store.app.status?.current_month;
      const query = ym ? `?month=${encodeURIComponent(ym)}` : '';
      this.loading = true;
      this.error = null;
      try {
        const [summary, upcoming, breakdown, trend] = await Promise.all([
          api.get(`/api/summary${query}`),
          api.get('/api/subscriptions/upcoming'),
          api.get(`/api/charts/category-breakdown${query}`),
          api.get(`/api/charts/monthly-trend${query}`),
        ]);
        Object.assign(this, { month: summary.month, summary, upcoming, breakdown, trend });
        this.$nextTick(() => this.renderCharts());
      } catch (error) {
        this.error = errorView(error);
      } finally {
        this.loading = false;
      }
    },

    get isCurrentMonth() {
      return this.month === this.$store.app.status?.current_month;
    },

    get trendEmpty() {
      return isAllZero(this.trend?.items);
    },

    chartFormatters() {
      const i18n = this.$store.i18n;
      const lang = i18n.lang;
      return {
        t: (key) => i18n.t(key),
        money: (value) => formatMoney(value, lang),
        month: (ym) => formatMonth(ym, lang),
      };
    },

    /** Called after loading and on `i18n:changed` (labels follow the language). */
    renderCharts() {
      if (!this.breakdown || !this.trend) return;
      const raw = window.Alpine.raw;
      const formatters = this.chartFormatters();
      if (this.breakdown.items.length > 0) {
        renderChart('breakdown', this.$refs.breakdownCanvas, buildBreakdownConfig(raw(this.breakdown), formatters));
      } else {
        destroyChart('breakdown');
      }
      if (!this.trendEmpty) {
        renderChart('trend', this.$refs.trendCanvas, buildTrendConfig(raw(this.trend), formatters));
      } else {
        destroyChart('trend');
      }
    },

    label(item) {
      return categoryLabel(item, (key) => this.$store.i18n.t(key));
    },

    alertText(alert) {
      const t = (key, params) => this.$store.i18n.t(key, params);
      const name = alert.scope === 'overall' ? t('alert.overall') : this.label(alert);
      return t(`alert.${alert.status}`, { name, percent: alert.usage_percent });
    },

    upcomingText(item) {
      const t = (key, params) => this.$store.i18n.t(key, params);
      if (item.is_overdue) return t('upcoming.overdue', { days: Math.abs(item.days_until) });
      if (item.days_until === 0) return t('upcoming.today');
      return t('upcoming.in_days', { days: item.days_until });
    },
  };
}
