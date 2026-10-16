// The API evaluates expiry using UTC calendar days, not elapsed 24-hour periods.
export function expiryState(item, today = new Date().toISOString().slice(0, 10)) {
  if (!item.expires_on || Number(item.quantity) <= 0) return "none";
  const days = (Date.parse(item.expires_on) - Date.parse(today)) / 86400000;
  return days < 0 ? "expired" : days <= 7 ? "soon" : "ok";
}
