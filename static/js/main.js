/**
 * Entry point: registers Alpine stores, magics and page components on `alpine:init`.
 * Loaded as a module before the deferred Alpine script (AD-02), so the listener is ready in time.
 * Design refs: MOD-40, SCR-00, 02 screen design ch.4 and ch.7.
 */

import { api } from './api/client.js';
import * as fmt from './i18n/format.js';
import {
  DEFAULT_LANG,
  SUPPORTED_LANGS,
  hasKey,
  loadDictionary,
  readStoredLang,
  saveLang,
  translate,
} from './i18n/i18n.js';
import { budgetsPage } from './pages/budgets.js';
import { csvImportPage } from './pages/csv-import.js';
import { dashboardPage } from './pages/dashboard.js';
import { expensesPage } from './pages/expenses.js';
import { errorKey, errorParams, errorView, fieldMessage } from './pages/shared.js';
import { subscriptionsPage } from './pages/subscriptions.js';
import { startRouter } from './router.js';

const TOAST_MS = 4000;

function safeStorage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

document.addEventListener('alpine:init', () => {
  const Alpine = window.Alpine;
  let resolveReady;
  const readyPromise = new Promise((resolve) => {
    resolveReady = resolve;
  });
  let toastTimer = null;

  Alpine.store('i18n', {
    lang: DEFAULT_LANG,
    dicts: {},
    ready: false,
    t(key, params) {
      return translate(this.dicts, this.lang, key, params);
    },
    has(key) {
      return hasKey(this.dicts, this.lang, key);
    },
    async ensure(lang) {
      if (!this.dicts[lang]) this.dicts = { ...this.dicts, [lang]: await loadDictionary(lang) };
    },
    /** [REQ-020] Load dictionary, switch, persist, and let charts re-render. */
    async setLang(lang) {
      if (!SUPPORTED_LANGS.includes(lang)) return;
      await this.ensure(lang);
      this.lang = lang;
      document.documentElement.lang = lang;
      document.title = this.t('app.title');
      saveLang(safeStorage(), lang);
      window.dispatchEvent(new CustomEvent('i18n:changed', { detail: { lang } }));
    },
  });

  Alpine.store('app', {
    route: 'dashboard',
    status: null,
    statusError: null,
    bannerDismissed: false,
    toast: null,
    ready() {
      return readyPromise;
    },
    notify(kind, key, params = {}) {
      this.toast = { kind, key, params };
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => {
        this.toast = null;
      }, TOAST_MS);
    },
    notifyError(error) {
      const view = errorView(error);
      this.notify('error', errorKey(view.code, (key) => Alpine.store('i18n').has(key)), view.params);
    },
    toastText() {
      if (!this.toast) return '';
      const i18n = Alpine.store('i18n');
      const params = errorParams({ params: this.toast.params }, i18n.lang);
      return i18n.t(this.toast.key, params);
    },
  });

  // $t('key', params) and $fmt.money(...) follow the current language reactively.
  Alpine.magic('t', () => (key, params) => Alpine.store('i18n').t(key, params));
  Alpine.magic('fmt', () => {
    const lang = Alpine.store('i18n').lang;
    return {
      money: (value) => fmt.formatMoney(value, lang),
      signedMoney: (value) => fmt.formatSignedMoney(value, lang),
      date: (value) => fmt.formatDate(value, lang),
      month: (value) => fmt.formatMonth(value, lang),
      rate: (value) => fmt.formatRate(value),
      percent: (value) => fmt.formatPercent(value),
      number: (value) => fmt.formatNumber(value, lang),
    };
  });
  Alpine.magic('fieldMsg', () => (fieldError) => {
    const i18n = Alpine.store('i18n');
    return fieldMessage(fieldError, { t: (k, p) => i18n.t(k, p), has: (k) => i18n.has(k), lang: i18n.lang });
  });
  Alpine.magic('errMsg', () => (view) => {
    const i18n = Alpine.store('i18n');
    if (!view) return '';
    return i18n.t(errorKey(view.code, (k) => i18n.has(k)), errorParams(view, i18n.lang));
  });

  Alpine.data('dashboardPage', dashboardPage);
  Alpine.data('expensesPage', expensesPage);
  Alpine.data('subscriptionsPage', subscriptionsPage);
  Alpine.data('budgetsPage', budgetsPage);
  Alpine.data('csvImportPage', csvImportPage);

  startRouter(window, (route) => {
    Alpine.store('app').route = route;
  });

  (async () => {
    const i18n = Alpine.store('i18n');
    const app = Alpine.store('app');
    try {
      await i18n.ensure(DEFAULT_LANG);
      await i18n.setLang(readStoredLang(safeStorage()));
    } catch {
      // Dictionaries are local files; if they fail, keys are shown instead of text.
    }
    try {
      app.status = await api.get('/api/status');
    } catch (error) {
      app.statusError = errorView(error);
    }
    i18n.ready = true;
    resolveReady();
  })();
});
