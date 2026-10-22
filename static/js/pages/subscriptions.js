/**
 * [SCR-03] Subscription list and actions. APIs: 10, 18, 11, 13, 14, 15, 16, 17.
 * The renew button is never disabled here: the API decides (BR-03 stays in the backend).
 */

import { api } from '../api/client.js';
import { errorView, fieldErrorsFrom, toNumberOrNull } from './shared.js';

const ROUTE = 'subscriptions';

export function subscriptionsPage() {
  return {
    items: [],
    upcomingById: {},
    form: { name: '', amount: '', cycle: 'monthly', next_renewal_date: '' },
    editingId: null,
    fieldErrors: {},
    dialogOpen: false,
    confirmTarget: null, // { kind: 'renew' | 'delete', item }
    saving: false,
    loading: false,
    error: null,

    init() {
      this.$watch('$store.app.route', (route) => route === ROUTE && this.load());
      if (this.$store.app.route === ROUTE) this.load();
    },

    async load() {
      await this.$store.app.ready();
      this.loading = true;
      this.error = null;
      try {
        const [list, upcoming] = await Promise.all([
          api.get('/api/subscriptions'),
          api.get('/api/subscriptions/upcoming'),
        ]);
        this.items = list.items;
        this.upcomingById = Object.fromEntries(upcoming.items.map((item) => [item.id, item]));
      } catch (error) {
        this.error = errorView(error);
      } finally {
        this.loading = false;
      }
    },

    badgeText(id) {
      const item = this.upcomingById[id];
      if (!item) return '';
      const t = (key, params) => this.$store.i18n.t(key, params);
      if (item.is_overdue) return t('upcoming.overdue', { days: Math.abs(item.days_until) });
      if (item.days_until === 0) return t('upcoming.today');
      return t('upcoming.in_days', { days: item.days_until });
    },

    openCreate() {
      this.editingId = null;
      this.form = { name: '', amount: '', cycle: 'monthly', next_renewal_date: this.$store.app.status?.today ?? '' };
      this.fieldErrors = {};
      this.dialogOpen = true;
    },

    openEdit(item) {
      this.editingId = item.id;
      this.form = {
        name: item.name,
        amount: item.amount,
        cycle: item.cycle,
        next_renewal_date: item.next_renewal_date,
      };
      this.fieldErrors = {};
      this.dialogOpen = true;
    },

    async save() {
      this.saving = true;
      const payload = { ...this.form, amount: toNumberOrNull(this.form.amount) };
      try {
        if (this.editingId) await api.put(`/api/subscriptions/${this.editingId}`, payload);
        else await api.post('/api/subscriptions', payload);
        this.dialogOpen = false;
        this.$store.app.notify('success', 'toast.saved');
        await this.load();
      } catch (error) {
        this.fieldErrors = fieldErrorsFrom(error);
        if (Object.keys(this.fieldErrors).length === 0) this.$store.app.notifyError(error);
      } finally {
        this.saving = false;
      }
    },

    async setActive(item, active) {
      try {
        await api.post(`/api/subscriptions/${item.id}/${active ? 'resume' : 'pause'}`);
        this.$store.app.notify('success', active ? 'toast.resumed' : 'toast.paused');
      } catch (error) {
        this.$store.app.notifyError(error);
      }
      await this.load();
    },

    async confirmAction() {
      const { kind, item } = this.confirmTarget;
      this.confirmTarget = null;
      try {
        if (kind === 'renew') {
          const updated = await api.post(`/api/subscriptions/${item.id}/renew`);
          this.$store.app.notify('success', 'toast.renewed', { date: updated.next_renewal_date });
        } else {
          await api.del(`/api/subscriptions/${item.id}`);
          this.$store.app.notify('success', 'toast.deleted');
        }
      } catch (error) {
        this.$store.app.notifyError(error);
      }
      await this.load();
    },
  };
}
