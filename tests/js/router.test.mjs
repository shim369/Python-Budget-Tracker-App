// UT-JRTE: hash routing (SCR-00).
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { hashFor, parseHash, startRouter } from '../../static/js/router.js';

test('UT-JRTE-01 parseHash', () => {
  assert.equal(parseHash('#/budgets'), 'budgets');
  assert.equal(parseHash('#/import/'), 'import');
  assert.equal(parseHash('#/unknown'), 'dashboard');
  assert.equal(parseHash(''), 'dashboard');
  assert.equal(parseHash(undefined), 'dashboard');
  assert.equal(hashFor('expenses'), '#/expenses');
});

test('UT-JRTE-02 startRouter normalizes and notifies', () => {
  const listeners = {};
  const replaced = [];
  const win = {
    location: { hash: '#/nope' },
    history: {
      replaceState: (_state, _title, url) => {
        replaced.push(url);
        win.location.hash = url;
      },
    },
    addEventListener: (type, fn) => {
      listeners[type] = fn;
    },
  };
  const routes = [];
  startRouter(win, (route) => routes.push(route));
  assert.deepEqual(replaced, ['#/dashboard']);
  win.location.hash = '#/expenses';
  listeners.hashchange();
  assert.deepEqual(routes, ['dashboard', 'expenses']);
  assert.equal(replaced.length, 1);
});
