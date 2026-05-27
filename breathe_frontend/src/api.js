const BASE = '/api';

async function req(url, m = 'GET', body = null) {
  const opt = {
    method: m,
    headers: {
      'Content-Type': 'application/json',
    },
  };
  if (body) opt.body = JSON.stringify(body);
  try {
    const res = await fetch(`${BASE}${url}`, opt);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP error! status: ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error(err);
    throw err;
  }
}

export const api = {
  getRows: () => req('/rows/normalized/'),
  approve: (id) => req(`/rows/normalized/${id}/approve/`, 'POST'),
  flag: (id, code, msg) => req(`/rows/normalized/${id}/flag/`, 'POST', { code, msg }),
  lock: (id) => req(`/rows/normalized/${id}/lock/`, 'POST'),
  edit: (id, raw_val, raw_unit) => req(`/rows/normalized/${id}/`, 'PATCH', { raw_val, raw_unit }),
  ingest: (type, payload) => req(`/ingest/${type}/`, 'POST', payload),
  checkHealth: () => req('/health/'),
};
