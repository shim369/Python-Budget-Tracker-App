/**
 * Hash routing (#/dashboard, #/expenses, ...). Design ref: SCR-00, 02 screen list.
 * Pure functions; startRouter() receives the window object explicitly.
 */

export const ROUTES = ['dashboard', 'expenses', 'subscriptions', 'budgets', 'import'];
export const DEFAULT_ROUTE = 'dashboard';

/** Unknown or empty hashes fall back to the dashboard. */
export function parseHash(hash) {
  const match = /^#\/([a-z-]+)\/?$/.exec(hash ?? '');
  return match && ROUTES.includes(match[1]) ? match[1] : DEFAULT_ROUTE;
}

export function hashFor(route) {
  return `#/${route}`;
}

/** Normalize the current hash and call onChange(route) now and on every change. */
export function startRouter(win, onChange) {
  const sync = () => {
    const route = parseHash(win.location.hash);
    if (win.location.hash !== hashFor(route)) {
      win.history.replaceState(null, '', hashFor(route));
    }
    onChange(route);
  };
  win.addEventListener('hashchange', sync);
  sync();
}
