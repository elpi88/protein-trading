"""Home page - KPI, alert e benvenuto."""
import streamlit as st
from lib import auth
from lib.theme import kpi_card
import pandas as pd

auth.require_login()

u = auth.get_current_user()

# -----------------------------------------------------------------------
# PANNELLO ALERT
# -----------------------------------------------------------------------
try:
    from lib.db import get_alerts
    alerts = get_alerts()
except Exception:
    alerts = []

if alerts:
    n_errors   = sum(1 for a in alerts if a["level"] == "error")
    n_warnings = sum(1 for a in alerts if a["level"] == "warning")

    badge_parts = []
    if n_errors:
        badge_parts.append(f"🔴 {n_errors} critical")
    if n_warnings:
        badge_parts.append(f"🟡 {n_warnings} warning")

    with st.expander(f"⚠️ Alerts — {' · '.join(badge_parts)}", expanded=True):
        for a in alerts:
            color = "#ff4b4b" if a["level"] == "error" else "#ffa500"
            st.markdown(
                f"<div style='border-left:3px solid {color}; padding:6px 10px; "
                f"margin-bottom:6px; background:#1a1a2e; border-radius:4px;'>"
                f"<span style='font-weight:600; color:{color}'>{a['icon']} {a['title']}</span>"
                f"<br><span style='font-size:0.8rem; color:#aaa'>{a['detail']}</span></div>",
                unsafe_allow_html=True,
            )

st.markdown("---")

# -----------------------------------------------------------------------
# NAVIGAZIONE RAPIDA
# -----------------------------------------------------------------------
st.markdown("#### 📱 Navigazione rapida")
cols = st.columns(4)
nav_items = [
    ("pages/1_Dashboard.py",        "📊 Dashboard"),
    ("pages/2_Fornitori.py",        "🏭 Fornitori"),
    ("pages/3_Clienti.py",          "👥 Clienti"),
    ("pages/4_Offerte.py",          "📋 Offerte"),
    ("pages/5_Bid.py",              "🎯 Bid"),
    ("pages/7_Matching.py",         "🔗 Matching"),
    ("pages/8_Margini.py",          "💰 Margini"),
    ("pages/11_Spedizioni.py",      "🚢 Spedizioni"),
    ("pages/12_Ordini.py",          "📦 Ordini"),
    ("pages/13_Storico.py",         "📜 Storico"),
    ("pages/14_Ordini_Fresco.py",   "🥩 Ordini Fresco"),
    ("pages/15_Carico_Camion.py",   "🚛 Carico Camion"),
    ("pages/16_Trasportatori.py",   "🚚 Trasportatori"),
    ("pages/17_Agenda.py",          "📅 Agenda"),
    ("pages/18_Prezzi.py",          "📈 Storico Prezzi"),
    ("pages/6_Impostazioni.py",     "⚙️ Impostazioni"),
]
for i, (page, label) in enumerate(nav_items):
    with cols[i % 4]:
        st.page_link(page, label=label, use_container_width=True)

st.markdown("---")

st.markdown(
    f'<div class="page-title">Benvenuto, {u["username"].capitalize()}</div>'
    '<div class="page-sub">Piattaforma di trading proteine — fornitori, clienti, '
    'offerte e bid in un unico posto.</div>',
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------
# KPI
# -----------------------------------------------------------------------
try:
    from lib.data import get_kpis
    kpis = get_kpis()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card("Fornitori",
                              f"{kpis['n_suppliers']:,}".replace(",", "'"),
                              "in anagrafica"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Clienti",
                              f"{kpis['n_clients']:,}".replace(",", "'"),
                              "in anagrafica"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("Offerte",
                              f"{kpis['n_offers']:,}".replace(",", "'"),
                              "ricevute"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Bid aperti",
                              f"{kpis['n_bids_open']:,}".replace(",", "'"),
                              f"su {kpis['n_bids']} totali"),
                     unsafe_allow_html=True)
except Exception as e:
    st.warning(f"Non riesco a leggere i dati: {e}")

st.markdown(
    "<div style='text-align:center; color:#94a3b8; font-size:0.8rem; "
    "margin-top:60px;'>v2.1 - Build per Nicolas Colombo - Maggio 2026</div>",
    unsafe_allow_html=True,
)
