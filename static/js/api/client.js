/**
 * Thin fetch wrapper. Every failure becomes an ApiError {status, code, details}.
 * Design refs: ERR-20, ERR-01. Pure module: safe to import from Node tests.
 */

export class ApiError extends Error {
  constructor(status, code, details = []) {
    super(code);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/** [ERR-20] Normalize an error response body into an ApiError. */
export function toApiError(status, body) {
  const error = body && typeof body === 'object' ? body.error : null;
  if (error && typeof error.code === 'string') {
    return new ApiError(status, error.code, Array.isArray(error.details) ? error.details : []);
  }
  return new ApiError(status, 'UNKNOWN', []);
}

/** Build a client around a fetch implementation (injected in tests). */
export function createClient(fetchFn) {
  const doFetch = fetchFn ?? ((...args) => globalThis.fetch(...args));

  async function request(method, path, { json, body, headers } = {}) {
    const init = { method, headers: { Accept: 'application/json', ...headers } };
    if (json !== undefined) {
      init.headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(json);
    } else if (body !== undefined) {
      init.body = body;
    }

    let response;
    try {
      response = await doFetch(path, init);
    } catch {
      throw new ApiError(0, 'NETWORK_ERROR');
    }
    if (response.status === 204) return null;

    let parsed = null;
    let parseOk = true;
    try {
      const text = await response.text();
      parsed = text ? JSON.parse(text) : null;
    } catch {
      parseOk = false;
    }
    if (!response.ok) throw toApiError(response.status, parseOk ? parsed : null);
    if (!parseOk) throw new ApiError(response.status, 'UNKNOWN');
    return parsed;
  }

  return {
    request,
    get: (path) => request('GET', path),
    post: (path, json) => request('POST', path, { json }),
    put: (path, json) => request('PUT', path, { json }),
    del: (path) => request('DELETE', path),
    /** [API-24] Send the file bytes as the request body. */
    postCsv: (path, file) => request('POST', path, { body: file, headers: { 'Content-Type': 'text/csv' } }),
  };
}

export const api = createClient();
