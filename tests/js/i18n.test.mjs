// UT-JI18N: dictionary lookup and language persistence (REQ-020).
import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  STORAGE_KEY,
  collectKeys,
  hasKey,
  interpolate,
  loadDictionary,
  readStoredLang,
  resolveKey,
  saveLang,
  translate,
} from '../../static/js/i18n/i18n.js';

const dicts = {
  en: { nav: { dashboard: 'Dashboard' }, only: { en: 'English only' }, greet: 'Hello {name}' },
  ja: { nav: { dashboard: 'ダッシュボード' }, greet: 'こんにちは {name}' },
};

function memoryStorage(initial = {}) {
  const data = { ...initial };
  return {
    data,
    getItem: (key) => (key in data ? data[key] : null),
    setItem: (key, value) => {
      data[key] = value;
    },
  };
}

test('UT-JI18N-01 resolveKey', () => {
  assert.equal(resolveKey(dicts.en, 'nav.dashboard'), 'Dashboard');
  assert.equal(resolveKey(dicts.en, 'nav.missing'), undefined);
  assert.equal(resolveKey(dicts.en, 'greet.deeper'), undefined);
  assert.equal(resolveKey(undefined, 'nav'), undefined);
});

test('UT-JI18N-02 interpolate', () => {
  assert.equal(interpolate('Hello {name}', { name: 'Ann' }), 'Hello Ann');
  assert.equal(interpolate('Hello {name}', {}), 'Hello {name}');
  assert.equal(interpolate('{count} items', { count: 0 }), '0 items');
  assert.equal(interpolate('no params'), 'no params');
});

test('UT-JI18N-03 translate falls back ja -> en -> key', () => {
  assert.equal(translate(dicts, 'ja', 'nav.dashboard'), 'ダッシュボード');
  assert.equal(translate(dicts, 'ja', 'only.en'), 'English only');
  assert.equal(translate(dicts, 'ja', 'no.such.key'), 'no.such.key');
  assert.equal(translate(dicts, 'ja', 'greet', { name: '太郎' }), 'こんにちは 太郎');
});

test('UT-JI18N-04 readStoredLang', () => {
  assert.equal(readStoredLang(memoryStorage({ [STORAGE_KEY]: 'ja' })), 'ja');
  assert.equal(readStoredLang(memoryStorage({ [STORAGE_KEY]: 'fr' })), 'en');
  assert.equal(readStoredLang(memoryStorage()), 'en');
  assert.equal(
    readStoredLang({
      getItem: () => {
        throw new Error('SecurityError');
      },
    }),
    'en',
  );
  assert.equal(readStoredLang(null), 'en');
});

test('UT-JI18N-05 saveLang', () => {
  const storage = memoryStorage();
  saveLang(storage, 'ja');
  assert.equal(storage.data[STORAGE_KEY], 'ja');
  assert.doesNotThrow(() =>
    saveLang(
      {
        setItem: () => {
          throw new Error('QuotaExceeded');
        },
      },
      'ja',
    ),
  );
});

test('UT-JI18N-06 loadDictionary', async () => {
  const calls = [];
  const okFetch = async (url) => {
    calls.push(url);
    return { ok: true, json: async () => ({ a: 'b' }) };
  };
  assert.deepEqual(await loadDictionary('ja', okFetch), { a: 'b' });
  assert.deepEqual(calls, ['/static/i18n/ja.json']);
  await assert.rejects(loadDictionary('ja', async () => ({ ok: false })));
});

test('UT-JI18N-07 collectKeys and hasKey', () => {
  assert.deepEqual(collectKeys(dicts.en), ['nav.dashboard', 'only.en', 'greet']);
  assert.equal(hasKey(dicts, 'ja', 'nav.dashboard'), true);
  assert.equal(hasKey(dicts, 'ja', 'only.en'), true);
  assert.equal(hasKey(dicts, 'ja', 'nav'), false);
});
