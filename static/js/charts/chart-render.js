/**
 * The only module that touches Chart.js (global `Chart` from the vendored UMD build).
 * Instances live outside Alpine state so they are never wrapped in reactive proxies.
 * Design ref: MOD-40.
 */

const instances = new Map();

export function destroyChart(id) {
  instances.get(id)?.destroy();
  instances.delete(id);
}

/** Recreate the chart (used on data load and on language change). */
export function renderChart(id, canvas, config) {
  destroyChart(id);
  if (!canvas || typeof window.Chart !== 'function') return;
  // Follow Pico's light/dark text color so labels stay readable in both themes.
  const styles = getComputedStyle(document.documentElement);
  window.Chart.defaults.color = styles.getPropertyValue('--pico-muted-color').trim() || '#666';
  window.Chart.defaults.borderColor = styles.getPropertyValue('--pico-muted-border-color').trim() || '#ddd';
  instances.set(id, new window.Chart(canvas, config));
}
