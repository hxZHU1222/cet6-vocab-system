async function readApiResponse(res) {
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return await res.json();
  }
  const text = await res.text();
  return { ok: false, error: text || `HTTP ${res.status}`, status_code: res.status };
}

function asErrorMessage(payload, fallback) {
  if (!payload) return fallback;
  if (typeof payload === 'string') return payload;
  return payload.error || payload.message || payload.detail || fallback;
}

async function apiGet(url) {
  const res = await fetch(url, { credentials: 'same-origin' });
  const payload = await readApiResponse(res);
  if (!res.ok) throw new Error(asErrorMessage(payload, `请求失败：${res.status}`));
  return payload;
}
async function apiPost(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data || {})
  });
  const payload = await readApiResponse(res);
  if (!res.ok) throw new Error(asErrorMessage(payload, `请求失败：${res.status}`));
  return payload;
}
async function apiUpload(url, file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(url, { method: 'POST', credentials: 'same-origin', body: form });
  const payload = await readApiResponse(res);
  if (!res.ok) throw new Error(asErrorMessage(payload, `请求失败：${res.status}`));
  return payload;
}
