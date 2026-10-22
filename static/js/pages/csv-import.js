/**
 * [SCR-05] CSV import. API: 24. The report is displayed as returned (CSV-07).
 */

import { api } from '../api/client.js';
import { errorView } from './shared.js';

export function csvImportPage() {
  return {
    file: null,
    uploading: false,
    report: null,
    error: null,

    pick(event) {
      this.file = event.target.files?.[0] ?? null;
      this.report = null;
      this.error = null;
    },

    async upload() {
      if (!this.file || this.uploading) return;
      this.uploading = true;
      this.report = null;
      this.error = null;
      try {
        this.report = await api.postCsv('/api/imports/expenses', this.file);
        if (this.report.imported_count > 0) {
          this.$store.app.notify('success', 'toast.imported', { count: this.report.imported_count });
        }
      } catch (error) {
        this.error = errorView(error);
      } finally {
        this.uploading = false;
      }
    },
  };
}
