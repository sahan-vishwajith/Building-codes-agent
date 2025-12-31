import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";

function toNumberOrNull(v) {
  const x = Number(v);
  return Number.isFinite(x) ? x : null;
}

function cleanContext(raw) {
  const ctx = {
    district: raw.district || null,
    building_type: raw.building_type || null,
    is_new_building: raw.is_new_building === "" ? null : raw.is_new_building === "true",
    floor_area_m2: raw.floor_area_m2 ? toNumberOrNull(raw.floor_area_m2) : null,
    electrical_demand_kva: raw.electrical_demand_kva ? toNumberOrNull(raw.electrical_demand_kva) : null,
    cooling_capacity_kwth: raw.cooling_capacity_kwth ? toNumberOrNull(raw.cooling_capacity_kwth) : null,
    heating_capacity_kwth: raw.heating_capacity_kwth ? toNumberOrNull(raw.heating_capacity_kwth) : null,
    wwr_percent: raw.wwr_percent ? toNumberOrNull(raw.wwr_percent) : null,
    skylight_percent: raw.skylight_percent ? toNumberOrNull(raw.skylight_percent) : null,
    glazing_vlt: raw.glazing_vlt ? toNumberOrNull(raw.glazing_vlt) : null,
    hvac_type: raw.hvac_type || null,
    operating_hours: raw.operating_hours || null,
  };

  Object.keys(ctx).forEach((k) => ctx[k] === null && delete ctx[k]);
  return Object.keys(ctx).length ? ctx : null;
}

function uid() {
  return Math.random().toString(16).slice(2) + Date.now().toString(16);
}

export default function App() {
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [toast, setToast] = useState(null);

  const [ctx, setCtx] = useState({
    district: "",
    building_type: "",
    is_new_building: "",
    floor_area_m2: "",
    electrical_demand_kva: "",
    cooling_capacity_kwth: "",
    heating_capacity_kwth: "",
    wwr_percent: "",
    skylight_percent: "",
    glazing_vlt: "",
    hvac_type: "",
    operating_hours: "",
  });

  const contextPayload = useMemo(() => cleanContext(ctx), [ctx]);

  const [messages, setMessages] = useState([
    {
      id: uid(),
      role: "assistant",
      content:
        "Hi 👋 I’m EEBC Advisor. Describe your building (type, area, glazing/WWR, HVAC) and I’ll suggest relevant EEBC guidance with sources.",
      meta: { applies: "unknown", reason: "Ask a question to begin." },
      sources: [],
      ts: Date.now(),
    },
  ]);

  const listRef = useRef(null);

  useEffect(() => {
    // auto-scroll to bottom
    const el = listRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, busy]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(t);
  }, [toast]);

  async function send() {
    const text = input.trim();
    if (!text) return;

    const userMsg = { id: uid(), role: "user", content: text, ts: Date.now() };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setBusy(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, context: contextPayload }),
      });

      if (!res.ok) {
        const raw = await res.text();
        throw new Error(`Backend error (${res.status}): ${raw}`);
      }

      const data = await res.json();
      const botMsg = {
        id: uid(),
        role: "assistant",
        content: data.answer ?? "",
        meta: { applies: data.applies ?? "unknown", reason: data.reason ?? "" },
        sources: data.sources ?? [],
        ts: Date.now(),
      };
      setMessages((m) => [...m, botMsg]);
    } catch (e) {
      setToast(e?.message || "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!busy) send();
    }
  }

  return (
    <div className="app">
      <div className="bgGlow" />

      <header className="topbar">
        <div className="brand">
          <div className="logo">E</div>
          <div>
            <div className="brandTitle">EEBC Advisor</div>
            <div className="brandSub">Energy-efficiency code guidance from your PDF</div>
          </div>
        </div>

        <div className="topActions">
          <button className="btn ghost" onClick={() => setDrawerOpen(true)}>
            Building details
          </button>
        </div>
      </header>

      <main className="shell">
        <section className="chatCard">
          <div className="chatHeader">
            <div className="chatTitle">Chat</div>
            <div className="chatHint">Press Enter to send • Shift+Enter new line</div>
          </div>

          <div className="chatList" ref={listRef}>
            {messages.map((m) => (
              <ChatBubble key={m.id} msg={m} />
            ))}

            {busy && (
              <div className="row left">
                <div className="bubble assistant typing">
                  <span className="dot" />
                  <span className="dot" />
                  <span className="dot" />
                </div>
              </div>
            )}
          </div>

          <div className="composer">
            <textarea
              className="input"
              rows={2}
              value={input}
              placeholder='Try: "New office in Colombo, 1200 m², central AC, WWR 55%. What should I follow?"'
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={busy}
            />

            <button className="btn primary" onClick={send} disabled={busy || !input.trim()}>
              {busy ? "Thinking…" : "Send"}
            </button>
          </div>
        </section>

        <aside className="sideCard">
          <div className="sideTitle">Quick tips</div>
          <ul className="sideList">
            <li>Give floor area (m²), glazing/WWR, and HVAC type for best results.</li>
            <li>Ask “explain like I’m new” to get simpler output.</li>
            <li>Sources appear under each assistant reply.</li>
          </ul>

          <div className="sideFooter">
            <span className="miniPill">RAG</span>
            <span className="miniPill">Citations</span>
            <span className="miniPill">Agents</span>
          </div>
        </aside>
      </main>

      {/* Drawer */}
      <div className={`drawerOverlay ${drawerOpen ? "open" : ""}`} onClick={() => setDrawerOpen(false)} />
      <div className={`drawer ${drawerOpen ? "open" : ""}`}>
        <div className="drawerHead">
          <div>
            <div className="drawerTitle">Building details</div>
            <div className="drawerSub">Optional – helps the advisor be more accurate</div>
          </div>
          <button className="iconBtn" onClick={() => setDrawerOpen(false)} aria-label="Close">
            ✕
          </button>
        </div>

        <div className="drawerBody">
          <div className="grid2">
            <Field label="District / City" value={ctx.district} onChange={(v) => setCtx({ ...ctx, district: v })} />
            <Field label="Building type" value={ctx.building_type} onChange={(v) => setCtx({ ...ctx, building_type: v })} />

            <SelectField
              label="New building?"
              value={ctx.is_new_building}
              onChange={(v) => setCtx({ ...ctx, is_new_building: v })}
              options={[
                { value: "", label: "Unknown" },
                { value: "true", label: "Yes" },
                { value: "false", label: "No" },
              ]}
            />

            <Field label="Floor area (m²)" value={ctx.floor_area_m2} onChange={(v) => setCtx({ ...ctx, floor_area_m2: v })} />
            <Field label="Electrical demand (kVA)" value={ctx.electrical_demand_kva} onChange={(v) => setCtx({ ...ctx, electrical_demand_kva: v })} />
            <Field label="Cooling capacity (kWth)" value={ctx.cooling_capacity_kwth} onChange={(v) => setCtx({ ...ctx, cooling_capacity_kwth: v })} />
            <Field label="Heating capacity (kWth)" value={ctx.heating_capacity_kwth} onChange={(v) => setCtx({ ...ctx, heating_capacity_kwth: v })} />

            <Field label="WWR (%)" value={ctx.wwr_percent} onChange={(v) => setCtx({ ...ctx, wwr_percent: v })} />
            <Field label="Skylight (%)" value={ctx.skylight_percent} onChange={(v) => setCtx({ ...ctx, skylight_percent: v })} />
            <Field label="Glazing VLT" value={ctx.glazing_vlt} onChange={(v) => setCtx({ ...ctx, glazing_vlt: v })} />

            <Field label="HVAC type" value={ctx.hvac_type} onChange={(v) => setCtx({ ...ctx, hvac_type: v })} />
            <Field label="Operating hours" value={ctx.operating_hours} onChange={(v) => setCtx({ ...ctx, operating_hours: v })} />
          </div>

          <div className="drawerNote">
            These values will be sent along with your message. Leave blank if unknown.
          </div>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className="toast">
          <div className="toastTitle">Error</div>
          <div className="toastText">{toast}</div>
        </div>
      )}
    </div>
  );
}

function ChatBubble({ msg }) {
  const isUser = msg.role === "user";
  const applies = msg?.meta?.applies || "unknown";

  return (
    <div className={`row ${isUser ? "right" : "left"}`}>
      <div className={`bubble ${isUser ? "user" : "assistant"}`}>
        {!isUser && msg.meta && (
          <div className="meta">
            <span className={`pill ${applies}`}>Applies: {String(applies).toUpperCase()}</span>
            {msg.meta.reason && <span className="reason">{msg.meta.reason}</span>}
          </div>
        )}

        <div className="text">{msg.content}</div>

        {!isUser && msg.sources?.length > 0 && (
          <details className="sources" open={false}>
            <summary>Sources ({msg.sources.length})</summary>
            <div className="sourcesGrid">
              {msg.sources.map((s, i) => (
                <div className="src" key={s.chunk_id || i}>
                  <div className="srcTop">
                    <span className="srcTag">p.{s.page}</span>
                    <span className="srcId">{s.chunk_id}</span>
                    {typeof s.score === "number" && <span className="srcScore">{s.score.toFixed(3)}</span>}
                  </div>
                  <div className="srcText">{s.excerpt}</div>
                </div>
              ))}
            </div>
          </details>
        )}

        <div className="time">{new Date(msg.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</div>
      </div>
    </div>
  );
}

function Field({ label, value, onChange }) {
  return (
    <label className="field">
      <div className="fieldLabel">{label}</div>
      <input className="fieldInput" value={value} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

function SelectField({ label, value, onChange, options }) {
  return (
    <label className="field">
      <div className="fieldLabel">{label}</div>
      <select className="fieldInput" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
