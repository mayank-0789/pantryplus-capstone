import React, { useEffect, useRef, useState } from "react";
import { pantryClient } from "./pantryClient.js";
import { expiryState } from "./stockDisplay.js";

const CATEGORIES = ["produce", "dairy", "grains", "protein", "spices", "frozen", "other"];
const UNITS = ["pcs", "g", "kg", "ml", "l", "pack"];
const empty = { name: "", category: "produce", quantity: 1, unit: "pcs", min_quantity: 0, expires_on: "", location: "", notes: "" };

export default function PantryDashboard() {
  const [items, setItems] = useState([]);
  const [events, setEvents] = useState([]);
  const [stats, setStats] = useState(null);
  const [backend, setBackend] = useState("checking");
  const [view, setView] = useState("all");
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [stockAction, setStockAction] = useState(null);
  const [amount, setAmount] = useState("1");
  const [note, setNote] = useState("");
  const requestSequence = useRef(0);
  const editHeading = useRef(null);

  async function refresh() {
    const sequence = ++requestSequence.current;
    const params = view === "low" ? { low_stock: true } : view === "expiring" ? { expiring: true } : view === "expired" ? { expired: true } : {};
    try {
      const [list, summary, health, history] = await Promise.all([
        pantryClient.list(params), pantryClient.stats(), pantryClient.ready(), pantryClient.activity(),
      ]);
      if (sequence !== requestSequence.current) return;
      setItems(list); setStats(summary); setBackend(health.status); setEvents(history);
    } catch (e) {
      if (sequence !== requestSequence.current) return;
      setBackend("unreachable"); setError(e.message);
    }
  }
  useEffect(() => { refresh(); return () => { requestSequence.current++; }; }, [view]);

  async function runMutation(action) {
    if (busy) return;
    setBusy(true); setError("");
    try { await action(); await refresh(); } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  function saveItem(e) {
    e.preventDefault();
    runMutation(async () => {
      const payload = { ...form, expires_on: form.expires_on || null };
      if (editing !== null) {
        delete payload.quantity; delete payload.unit;
        await pantryClient.update(editing, payload);
      } else { await pantryClient.add(payload); }
      setEditing(null); setForm(empty);
    });
  }

  function editItem(item) {
    const { id, created_at, updated_at, ...fields } = item;
    setEditing(id); setForm({ ...fields, expires_on: fields.expires_on || "" });
    editHeading.current?.focus();
  }

  function openStockAction(item, kind) {
    setStockAction({ item, kind }); setAmount("1"); setNote("");
  }

  function saveStock(e) {
    e.preventDefault();
    runMutation(async () => {
      await pantryClient.changeStock(stockAction.item.id, stockAction.kind, amount, note);
      setStockAction(null);
    });
  }

  const setField = (field) => (e) => setForm({ ...form, [field]: e.target.value });
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand-mark" aria-hidden="true">P+</div>
        <h1>Pantry Plus</h1>
        <p className="muted">Keep stock in sight.<br />Make every ingredient count.</p>
        <div className={`pill ${backend === "ready" ? "ok" : "bad"}`} role="status">API {backend}</div>
        <nav aria-label="Pantry views">
          {[["all", "My pantry"], ["expiring", "Use soon"], ["expired", "Expired"], ["low", "Running low"], ["activity", "Stock activity"]].map(([key, label]) => (
            <button key={key} disabled={busy} aria-current={view === key ? "page" : undefined} className={view === key ? "active" : ""} onClick={() => setView(key)}>{label}</button>
          ))}
        </nav>
        <p className="side-foot">MAYANK GUPTA<br />DevOps capstone · 10220</p>
      </aside>
      <main>
        <header className="page-heading"><div><p className="eyebrow">KITCHEN INVENTORY</p><h2>A little less waste.<br />A little more order.</h2></div><button disabled={busy} onClick={refresh}>Refresh</button></header>
        <section className="kpis" aria-label="Inventory summary">
          <InventoryStat label="Items tracked" value={stats?.total_items ?? "–"} />
          <InventoryStat label="Use within 7 days" value={stats?.expiring_soon ?? "–"} tone="warn" />
          <InventoryStat label="Expired in stock" value={stats?.expired ?? "–"} tone="bad" />
          <InventoryStat label="Running low" value={stats?.low_stock ?? "–"} tone="warn" />
        </section>
        {error && <p className="error" role="alert">{error}</p>}
        {view === "activity" ? <section><h3>Stock activity</h3><p className="muted">Latest 50 changes. History remains after an item is removed.</p><div className="table-scroll"><table>
          <thead><tr><th>When</th><th>Item</th><th>Action</th><th>Change</th><th>Balance</th><th>Note</th></tr></thead>
          <tbody>{events.map(event => <tr key={event.id}><td>{new Date(event.created_at).toLocaleString()}</td><td>{event.item_name}</td><td>{event.kind}</td><td>{Number(event.amount) > 0 ? "+" : ""}{Number(event.amount)} {event.unit}</td><td>{Number(event.balance)} {event.unit}</td><td>{event.note || "—"}</td></tr>)}{!events.length && <tr><td colSpan="6">No stock changes yet.</td></tr>}</tbody>
        </table></div></section> : <>
          <section className="editor"><h3 ref={editHeading} tabIndex={-1}>{editing !== null ? "Edit item details" : "Add to your pantry"}</h3>
            <form className="add" onSubmit={saveItem}>
              <label>Item name<input required maxLength={80} value={form.name} onChange={setField("name")} placeholder="e.g. Basmati rice" /></label>
              <label>Category<select value={form.category} onChange={setField("category")}>{CATEGORIES.map(c => <option key={c}>{c}</option>)}</select></label>
              <label>Quantity<input type="number" required min="0" max="99999999.99" step="0.01" disabled={editing !== null} value={form.quantity} onChange={setField("quantity")} /></label>
              <label>Unit<select disabled={editing !== null} value={form.unit} onChange={setField("unit")}>{UNITS.map(u => <option key={u}>{u}</option>)}</select></label>
              <label>Low stock at<input type="number" required min="0" max="99999999.99" step="0.01" value={form.min_quantity} onChange={setField("min_quantity")} /></label>
              <label>Best before<input type="date" value={form.expires_on} onChange={setField("expires_on")} /></label>
              <label>Location<input maxLength={40} value={form.location} onChange={setField("location")} placeholder="Kitchen shelf" /></label>
              <label>Notes<input maxLength={2000} value={form.notes} onChange={setField("notes")} /></label>
              <div className="form-actions"><button type="submit" disabled={busy}>{editing !== null ? "Save details" : "Add item"}</button>{editing !== null && <button type="button" onClick={() => { setEditing(null); setForm(empty); }}>Cancel edit</button>}</div>
            </form>
            {editing !== null && <p className="muted">Use the stock actions below to change quantity and keep an accurate history. Units stay fixed.</p>}
          </section>
          <div className="table-scroll"><table>
            <thead><tr><th>Item</th><th>Category</th><th>Stock</th><th>Best before (UTC)</th><th>Where</th><th>Actions</th></tr></thead>
            <tbody>{items.map(item => <tr key={item.id}>
              <td><strong>{item.name}</strong>{item.notes && <div className="muted">{item.notes}</div>}</td>
              <td><span className={`tag ${item.category}`}>{item.category}</span></td>
              <td className={Number(item.quantity) <= Number(item.min_quantity) ? "low" : ""}>{Number(item.quantity)} {item.unit}<div className="muted">Low at {Number(item.min_quantity)}</div></td>
              <td className={`exp ${expiryState(item)}`}>{item.expires_on || "—"}</td><td>{item.location || "—"}</td>
              <td className="actions"><button disabled={busy} onClick={() => editItem(item)}>Edit</button><button disabled={busy} onClick={() => openStockAction(item, "restock")}>Restock</button><button disabled={busy || Number(item.quantity) === 0} onClick={() => openStockAction(item, "consume")}>Use</button><button disabled={busy || Number(item.quantity) === 0} onClick={() => openStockAction(item, "waste")}>Waste</button><button disabled={busy} className="x" onClick={() => { if (window.confirm(`Remove ${item.name}? Stock history will be retained.`)) runMutation(() => pantryClient.remove(item.id)); }}>Remove</button></td>
            </tr>)}{!items.length && <tr><td colSpan="6" className="center muted">No items in this view. Add your first ingredient above.</td></tr>}</tbody>
          </table></div>
        </>}
        {stockAction && <div className="modal-backdrop"><section role="dialog" aria-modal="true" aria-labelledby="stock-title" className="stock-dialog"><h3 id="stock-title">{stockAction.kind === "consume" ? "Use" : stockAction.kind === "waste" ? "Record waste" : "Restock"}: {stockAction.item.name}</h3><p className="muted">Available: {Number(stockAction.item.quantity)} {stockAction.item.unit}</p><form onSubmit={saveStock}><label>Amount ({stockAction.item.unit})<input autoFocus required type="number" min="0.01" max={stockAction.kind === "restock" ? "99999999.99" : stockAction.item.quantity} step="0.01" value={amount} onChange={e => setAmount(e.target.value)} /></label><label>Reason or note<input maxLength={200} value={note} onChange={e => setNote(e.target.value)} /></label><div className="form-actions"><button disabled={busy} type="submit">Confirm change</button><button disabled={busy} type="button" onClick={() => setStockAction(null)}>Cancel</button></div>{error && <p role="alert" className="error">{error}</p>}</form></section></div>}
      </main>
    </div>
  );
}

function InventoryStat({ label, value, tone }) {
  return <div className={`kpi ${tone || ""}`}><div className="v">{value}</div><div className="l">{label}</div></div>;
}
