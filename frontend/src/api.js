async function request(path, options = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  if (res.status === 204) return null;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail ? JSON.stringify(body.detail) : `${res.status} ${res.statusText}`);
  return body;
}

export const api = {
  ready: () => request("/ready"),
  list: (params = {}) => request("/api/items?" + new URLSearchParams(params)),
  stats: () => request("/api/items/stats"),
  add: (item) => request("/api/items", { method: "POST", body: JSON.stringify(item) }),
  update: (id, patch) => request(`/api/items/${id}`, { method: "PUT", body: JSON.stringify(patch) }),
  consume: (id, amount) => request(`/api/items/${id}/consume`, { method: "POST", body: JSON.stringify({ amount }) }),
  remove: (id) => request(`/api/items/${id}`, { method: "DELETE" }),
};
