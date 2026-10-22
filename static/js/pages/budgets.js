/**
 * [SCR-04] Budgets and categories. APIs: 02, 19, 20, 03, 04.
 * Delete buttons only reflect is_fixed / in_use from the API; the API still decides (409).
 */

import { api } from '../api/client.js';
import { categoryLabel, errorView, fieldErrorsFrom, toNumberOrNull } from './shared.js';

const ROUTE = 'budgets';

export function budgetsPage() {
  return {
    categories: [],
    budgetForm: { overall: '', byCategory: {} },
    newCategoryName: '',
    fieldErrors: {},
    categoryErrors: {},
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
      this.loading = true;
      this.error = null;
      try {
        const [categories, budgets] = await Promise.all([api.get('/api/categories'), api.get('/api/budgets')]);
        this.categories = categories.items;
        const byId = Object.fromEntries(budgets.categories.map((b) => [b.category_id, b.amount]));
        this.budgetForm = {
          overall: budgets.overall ?? '',
          byCategory: Object.fromEntries(this.categories.map((c) => [c.id, byId[c.id] ?? ''])),
        };
      } catch (error) {
        this.error = errorView(error);
      } finally {
        this.loading = false;
      }
    },

    label(category) {
      return categoryLabel(category, (key) => this.$store.i18n.t(key));
    },

    /** Field errors use the payload index: categories.<i>.amount (same order as this.categories). */
    rowError(index) {
      return this.fieldErrors[`categories.${index}.amount`] ?? this.fieldErrors[`categories.${index}.category_id`];
    },

    async saveBudgets() {
      this.saving = true;
      this.fieldErrors = {};
      const payload = {
        overall: toNumberOrNull(this.budgetForm.overall),
        categories: this.categories.map((c) => ({
          category_id: c.id,
          amount: toNumberOrNull(this.budgetForm.byCategory[c.id]),
        })),
      };
      try {
        await api.put('/api/budgets', payload);
        this.$store.app.notify('success', 'toast.saved');
        await this.load();
      } catch (error) {
        this.fieldErrors = fieldErrorsFrom(error);
        if (Object.keys(this.fieldErrors).length === 0) this.$store.app.notifyError(error);
      } finally {
        this.saving = false;
      }
    },

    async addCategory() {
      this.categoryErrors = {};
      try {
        await api.post('/api/categories', { name: this.newCategoryName });
        this.newCategoryName = '';
        this.$store.app.notify('success', 'toast.saved');
        await this.load();
      } catch (error) {
        this.categoryErrors = fieldErrorsFrom(error);
        if (Object.keys(this.categoryErrors).length === 0) this.$store.app.notifyError(error);
      }
    },

    async confirmDelete() {
      const target = this.deleteTarget;
      this.deleteTarget = null;
      try {
        await api.del(`/api/categories/${target.id}`);
        this.$store.app.notify('success', 'toast.deleted');
      } catch (error) {
        this.$store.app.notifyError(error);
      }
      await this.load();
    },
  };
}
