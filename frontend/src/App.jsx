import React, { useEffect, useState } from "react";
import { api } from "./api.js";

const CATEGORIES = ["produce", "dairy", "grains", "protein", "spices", "frozen", "other"];
const UNITS = ["pcs", "g", "kg", "ml", "l", "pack"];
const DAY = 24 * 60 * 60 * 1000;

function expiryState(item) {
  if (!item.expires_on) return "none";
  const days = Math.ceil((new Date(item.expires_on) - new Date()) / DAY);
  if (days < 0) return "expired";
  if (days <= 7) return "soon";
  return "ok";
}

const empty = { name: "", category: "produce", quantity: 1, unit: "pcs", min_quantity: 0, expires_on: "", location: "" };

export default function App() {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [backend, setBackend] = useState("checking");
  const [view, setView] = useState("all");
  const [form, setForm] = useState(empty);
  const [error, setError] = useState("");

  async function refresh() {
    const params = view === "low" ? { low_stock: true } : view === "expiring" ? { expiring: true } : {};
    try {
      const [list, s, h] = await Promise.all([api.list(params), api.stats(), api.ready()]);
      setItems(list); setStats(s); setBackend(h.status); setError("");
    } catch (e) {
      setBackend("unreachable"); setError(e.message);
    }
  }
  useEffect(() => { refresh(); }, [view]);

  async function submit(e) {
    e.preventDefault();
    if (!form.name.trim()) return;
    const payload = { ...form, expires_on: form.expires_on || null };
    try { await api.add(payload); setForm(empty); refresh(); } catch (e) { setError(e.message); }
  }

  async function useOne(item) {
    const amount = item.unit === "pcs" || item.unit === "pack" ? 1 : item.unit === "kg" || item.unit === "l" ? 0.25 : 100;
    try { await api.consume(item.id, amount); refresh(); } catch (e) { setError(e.message); }
  }

  return (
    <div className="shell">
      <aside className="side">
        <h1>Pantry</h1>
        <p className="muted">what is in the kitchen, how much is left, and what to use first</p>
        <div className={`pill ${backend === "ready" ? "ok" : "bad"}`}>api {backend}</div>
        <nav>
          {[["all", "Everything"], ["expiring", "Use soon"], ["low", "Running low"]].map(([key, label]) => (
            <button key={key} className={view === key ? "active" : ""} onClick={() => setView(key)}>{label}</button>
          ))}
        </nav>
      </aside>
      <main>
        <section className="kpis">
          <Kpi label="Items" value={stats?.total_items ?? "–"} />
          <Kpi label="Use within 7 days" value={stats?.expiring_soon ?? "–"} tone="warn" />
          <Kpi label="Expired" value={stats?.expired ?? "–"} tone="bad" />
          <Kpi label="Running low" value={stats?.low_stock ?? "–"} tone="warn" />
        </section>

        <form className="add" onSubmit={submit}>
          <input placeholder="Item" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
            {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
          </select>
          <input type="number" min="0" step="0.25" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} />
          <select value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })}>
            {UNITS.map((u) => <option key={u}>{u}</option>)}
          </select>
          <input type="date" value={form.expires_on} onChange={(e) => setForm({ ...form, expires_on: e.target.value })} />
          <input placeholder="where" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
          <button type="submit">Add</button>
        </form>
        {error && <p className="error">{error}</p>}

        <table>
          <thead><tr><th>Item</th><th>Category</th><th>Stock</th><th>Best before</th><th>Where</th><th></th></tr></thead>
          <tbody>
            {items.map((i) => {
              const state = expiryState(i);
              const low = Number(i.quantity) <= Number(i.min_quantity);
              return (
                <tr key={i.id}>
                  <td>{i.name}</td>
                  <td><span className={`tag ${i.category}`}>{i.category}</span></td>
                  <td className={low ? "low" : ""}>{Number(i.quantity)} {i.unit}{low && <span className="hint"> low</span>}</td>
                  <td className={`exp ${state}`}>{i.expires_on || <span className="muted">–</span>}</td>
                  <td>{i.location || <span className="muted">–</span>}</td>
                  <td className="actions">
                    <button onClick={() => useOne(i)} disabled={Number(i.quantity) <= 0}>use</button>
                    <button className="x" onClick={() => api.remove(i.id).then(refresh)}>remove</button>
                  </td>
                </tr>
              );
            })}
            {items.length === 0 && <tr><td colSpan="6" className="muted center">Nothing here.</td></tr>}
          </tbody>
        </table>
      </main>
    </div>
  );
}

function Kpi({ label, value, tone }) {
  return <div className={`kpi ${tone || ""}`}><div className="v">{value}</div><div className="l">{label}</div></div>;
}
