"""Home page - KPI, alert, navigazione rapida ottimizzata mobile."""
import streamlit as st
import pandas as pd
from lib import auth
from lib.theme import kpi_card, apply_theme

auth.require_login()
apply_theme()

u = auth.get_current_user()

# ── CSS extra per mobile ─────────────────────────────────────────────────
st.markdown("""
<style>
/* Bottoni navigazione rapida più grandi su mobile */
@media (max-width: 768px) {
    .nav-btn-wrap .stLinkButton a {
        font-size: 1rem !important;
        padding: 14px 8px !important;
        min-height: 56px !important;
    }
    .kpi-card { font-size: 1.1rem !important; }
    .kpi-value { font-size: 2rem !important; }
    .page-title { font-size: 1.4rem !important; }
}
.nav-section-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #64748b;
    margin: 14px 0 4px 0;
}
</style>
""", unsafe_allow_html=True)

# ── PANNELLO ALERT ───────────────────────────────────────────────────────
try:
    from lib.db import get_alerts
    alerts = get_alerts()
except Exception:
    alerts = []

if alerts:
    n_err  = sum(1 for a in alerts if a["level"] == "error")
    n_warn = sum(1 for a in alerts if a["level"] == "warning")
    parts  = []
    if n_err:  parts.append(f"🔴 {n_err} critical")
    if n_warn: parts.append(f"🟡 {n_warn} warning")
    with st.expander(f"⚠️ Alerts — {' · '.join(parts)}", expanded=True):
        for a in alerts:
            color = "#ff4b4b" if a["level"] == "error" else "#ffa500"
            st.markdown(
                f"<div style='border-left:3px solid {color}; padding:6px 10px; "
                f"margin-bottom:6px; background:#1a1a2e; border-radius:4px;'>"
                f"<b style='color:{color}'>{a['icon']} {a['title']}</b>"
                f"<br><span style='font-size:0.8rem;color:#aaa'>{a['detail']}</span></div>",
                unsafe_allow_html=True,
            )

# ── BENVENUTO ────────────────────────────────────────────────────────────
from datetime import date
today = date.today()
iso_week = today.isocalendar()[1]

st.markdown(
    f'<div class="page-title">👋 {u["username"].capitalize()}</div>'
    f'<div class="page-sub">{today.strftime("%A, %d %B %Y")} · Week {iso_week}</div>',
    unsafe_allow_html=True,
)

# ── KPI ──────────────────────────────────────────────────────────────────
try:
    from lib.data import get_kpis
    kpis = get_kpis()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card("Suppliers",
            f"{kpis['n_suppliers']:,}".replace(",", "'"), "in database"),
            unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Clients",
            f"{kpis['n_clients']:,}".replace(",", "'"), "in database"),
            unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("Offers",
            f"{kpis['n_offers']:,}".replace(",", "'"), "received"),
            unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Open Bids",
            f"{kpis['n_bids_open']:,}".replace(",", "'"),
            f"of {kpis['n_bids']} total"),
            unsafe_allow_html=True)
except Exception:
    pass

st.markdown("---")

# ── NAVIGAZIONE RAPIDA ───────────────────────────────────────────────────
st.markdown('<div class="nav-section-label">Trading</div>', unsafe_allow_html=True)
with st.container():
    c = st.columns(4)
    items_trade = [
        ("pages/4_Offerte.py",   "📋 Offerte"),
        ("pages/5_Bid.py",       "🎯 Bid"),
        ("pages/7_Matching.py",  "🔗 Matching"),
        ("pages/8_Margini.py",   "💰 Margini"),
    ]
    for i, (pg, lbl) in enumerate(items_trade):
        with c[i]: st.page_link(pg, label=lbl, use_container_width=True)

st.markdown('<div class="nav-section-label">Anagrafiche</div>', unsafe_allow_html=True)
with st.container():
    c = st.columns(4)
    items_ana = [
        ("pages/2_Fornitori.py",  "🏭 Fornitori"),
        ("pages/3_Clienti.py",    "👥 Clienti"),
        ("pages/16_Trasportatori.py", "🚚 Trasportatori"),
        ("pages/19_Cerca.py",     "🔍 Cerca"),
    ]
    for i, (pg, lbl) in enumerate(items_ana):
        with c[i]: st.page_link(pg, label=lbl, use_container_width=True)

st.markdown('<div class="nav-section-label">Logistica & Finanza</div>', unsafe_allow_html=True)
with st.container():
    c = st.columns(4)
    items_log = [
        ("pages/11_Spedizioni.py",    "🚢 Spedizioni"),
        ("pages/12_Ordini.py",        "📦 Ordini"),
        ("pages/14_Ordini_Fresco.py", "🥩 Fresco"),
        ("pages/15_Carico_Camion.py", "🚛 Carico"),
    ]
    for i, (pg, lbl) in enumerate(items_log):
        with c[i]: st.page_link(pg, label=lbl, use_container_width=True)

st.markdown('<div class="nav-section-label">Analisi & Tools</div>', unsafe_allow_html=True)
with st.container():
    c = st.columns(4)
    items_tools = [
        ("pages/1_Dashboard.py",  "📊 Dashboard"),
        ("pages/18_Prezzi.py",    "📈 Prezzi"),
        ("pages/17_Agenda.py",    "📅 Agenda"),
        ("pages/13_Storico.py",   "📜 Storico"),
    ]
    for i, (pg, lbl) in enumerate(items_tools):
        with c[i]: st.page_link(pg, label=lbl, use_container_width=True)

st.markdown("---")

# ── PROSSIMI APPUNTAMENTI ────────────────────────────────────────────────
try:
    from lib.db import get_agenda_events
    agenda_df = get_agenda_events(date_from=str(today))
    if not agenda_df.empty:
        st.markdown('<div class="nav-section-label">Prossimi appuntamenti</div>',
                    unsafe_allow_html=True)
        agenda_df["event_date"] = pd.to_datetime(agenda_df["event_date"])
        agenda_df = agenda_df.sort_values("event_date").head(5)
        for _, row in agenda_df.iterrows():
            d   = row["event_date"].strftime("%a %d %b")
            t   = row.get("time_start", "") or ""
            loc = row.get("location", "") or ""
            loc_str = f" · 📍 {loc}" if loc else ""
            st.markdown(
                f"<div style='padding:6px 10px; background:#1a1a2e; border-radius:6px; "
                f"border-left:3px solid #e84e0f; margin-bottom:5px; font-size:0.85rem'>"
                f"<b style='color:#eee'>{row['title']}</b> "
                f"<span style='color:#aaa; font-size:0.78rem'>{d} {t}{loc_str}</span></div>",
                unsafe_allow_html=True,
            )
        st.page_link("pages/17_Agenda.py", label="→ Apri Agenda completa")
except Exception:
    pass

st.markdown(
    "<div style='text-align:center;color:#94a3b8;font-size:0.75rem;margin-top:40px'>"
    "v2.1 · Protein Trading Platform · Nicolas Colombo</div>",
    unsafe_allow_html=True,
)
