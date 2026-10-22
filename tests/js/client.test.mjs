// UT-JCLI: API client error normalization (ERR-20).
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { ApiError, createClient, toApiError } from '../../static/js/api/client.js';

function response(status, text) {
  return { status, ok: status >= 200 && status < 300, text: async () => text };
}

function recordingFetch(result) {
  const calls = [];
  const fetchFn = async (path, init) => {
    calls.push({ path, init });
    if (result instanceof Error) throw result;
    return result;
  };
  return { calls, fetchFn };
}

test('UT-JCLI-01 toApiError', () => {
  const unified = toApiError(409, { error: { code: 'CATEGORY_IN_USE', details: [{ params: { count: 2 } }] } });
  assert.ok(unified instanceof ApiError);
  assert.equal(unified.status, 409);
  assert.equal(unified.code, 'CATEGORY_IN_USE');
  assert.deepEqual(unified.details, [{ params: { count: 2 } }]);
  assert.deepEqual(toApiError(400, { error: { code: 'X' } }).details, []);
  assert.equal(toApiError(422, { detail: [] }).code, 'UNKNOWN');
  assert.equal(toApiError(500, null).code, 'UNKNOWN');
});

test('UT-JCLI-02 success responses', async () => {
  const ok = createClient(recordingFetch(response(200, '{"a":1}')).fetchFn);
  assert.deepEqual(await ok.get('/api/x'), { a: 1 });
  const noContent = createClient(recordingFetch(response(204, '')).fetchFn);
  assert.equal(await noContent.del('/api/x/1'), null);
});

test('UT-JCLI-03 error responses', async () => {
  const unified = createClient(
    recordingFetch(response(400, '{"error":{"code":"VALIDATION_ERROR","message":"m","details":[]}}')).fetchFn,
  );
  await assert.rejects(unified.post('/api/x', {}), (err) => err.code === 'VALIDATION_ERROR' && err.status === 400);
  const html = createClient(recordingFetch(response(502, '<html>Bad gateway</html>')).fetchFn);
  await assert.rejects(html.get('/api/x'), (err) => err.code === 'UNKNOWN' && err.status === 502);
});

test('UT-JCLI-04 network failure', async () => {
  const offline = createClient(recordingFetch(new TypeError('Failed to fetch')).fetchFn);
  await assert.rejects(offline.get('/api/x'), (err) => err.code === 'NETWORK_ERROR' && err.status === 0);
});

test('UT-JCLI-05 success with a non-JSON body', async () => {
  const client = createClient(recordingFetch(response(200, 'not json')).fetchFn);
  await assert.rejects(client.get('/api/x'), (err) => err.code === 'UNKNOWN' && err.status === 200);
});

test('UT-JCLI-06 request headers and body', async () => {
  const { calls, fetchFn } = recordingFetch(response(200, '{}'));
  const client = createClient(fetchFn);
  await client.put('/api/budgets', { overall: 1 });
  await client.postCsv('/api/imports/expenses', 'csv-bytes');
  await client.post('/api/subscriptions/sub-000001/renew');

  assert.equal(calls[0].init.method, 'PUT');
  assert.equal(calls[0].init.headers['Content-Type'], 'application/json');
  assert.equal(calls[0].init.body, '{"overall":1}');
  assert.equal(calls[1].init.headers['Content-Type'], 'text/csv');
  assert.equal(calls[1].init.body, 'csv-bytes');
  assert.equal(calls[2].init.body, undefined);
  assert.equal(calls[2].init.headers['Content-Type'], undefined);
});
