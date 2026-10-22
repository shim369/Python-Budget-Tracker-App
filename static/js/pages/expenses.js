/**
 * [SCR-02] Expense list and form. APIs: 05, 02, 06, 08, 09.
 */

import { api } from '../api/client.js';
import { categoryLabel, errorView, fieldErrorsFrom, toNumberOrNull } from './shared.js';

const ROUTE = 'expenses';

export function expensesPage() {
  return {
    month: null,
    list: null,
    categories: [],
    form: { date: '', amount: '', category_id: '', memo: '' },
    editingId: null,
    fieldErrors: {},
    dialogOpen: false,
    deleteTarget: null,
    saving: false,
    loading: false,
    error: null,

    init() {
      this.$watch('$store.app.route', (route) => route === ROUTE && this.load());
      if (this.$store.app.route === ROUTE) this.load();
    },

    async load() {
      await this.$store.app.ready();
      this.month = this.month || this.$store.app.status?.current_month || '';
      const query = this.month ? `?month=${encodeURIComponent(this.month)}` : '';
      this.loading = true;
      this.error = null;
      try {
        const [list, categories] = await Promise.all([api.get(`/api/expenses${query}`), api.get('/api/categories')]);
        this.list = list;
        this.month = list.month;
        this.categories = categories.items;
      } catch (error) {
        this.error = errorView(error);
      } finally {
        this.loading = false;
      }
    },

    categoryName(categoryId) {
      const category = this.categories.find((c) => c.id === categoryId);
      return category ? categoryLabel(category, (key) => this.$store.i18n.t(key)) : categoryId;
    },

    openCreate() {
      this.editingId = null;
      this.form = {
        date: this.$store.app.status?.today ?? '',
        amount: '',
        category_id: this.categories[0]?.id ?? '',
        memo: '',
      };
      this.fieldErrors = {};
      this.dialogOpen = true;
    },

    openEdit(item) {
      this.editingId = item.id;
      this.form = { date: item.date, amount: item.amount, category_id: item.category_id, memo: item.memo };
      this.fieldErrors = {};
      this.dialogOpen = true;
    },

    async save() {
      this.saving = true;
      const payload = {
        date: this.form.date,
        amount: toNumberOrNull(this.form.amount),
        category_id: this.form.category_id,
        memo: this.form.memo ?? '',
      };
      try {
        if (this.editingId) await api.put(`/api/expenses/${this.editingId}`, payload);
        else await api.post('/api/expenses', payload);
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

    async confirmDelete() {
      const target = this.deleteTarget;
      this.deleteTarget = null;
      try {
        await api.del(`/api/expenses/${target.id}`);
        this.$store.app.notify('success', 'toast.deleted');
      } catch (error) {
        this.$store.app.notifyError(error);
      }
      await this.load();
    },
  };
}
