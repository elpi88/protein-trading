"""Home page - KPI e benvenuto."""
import streamlit as st
from lib import auth
from lib.theme import kpi_card
import pandas as pd

auth.require_login()

u = auth.get_current_user()

# --- Navigazione rapida (utile su mobile) ---
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
    ("pages/6_Impostazioni.py",     "⚙️ Impostazioni"),
]
for i, (page, label) in enumerate(nav_items):
    with cols[i % 4]:
        st.page_link(page, label=label, use_container_width=True)

st.markdown("---")

st.markdown(
    f'<div class="page-title">Benvenuto, {u["username"].capitalize()}</div>'
    '<div class="page-sub">Piattaforma di trading proteine - fornitori, clienti, '
    'offerte e bid in un unico posto.</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown("### Come iniziare")
    st.markdown(
        """
        Usa il **menu a sinistra** per navigare tra le sezioni:

        - **Dashboard** — numeri chiave e grafici in tempo reale
        - **Fornitori** — anagrafica completa, ricerca e modifica
        - **Clienti** — anagrafica clienti
        - **Offerte** — offerte ricevute dai fornitori
        - **Bid** — richieste dei clienti
        - **Impostazioni** — backup, gestione utenti (solo admin), refresh dati
        """
    )

with col2:
    st.info(
        "**Suggerimento**\n\n"
        "Puoi esportare i dati in Excel quando vuoi dalla pagina "
        "Impostazioni: utile per inviare report via email."
    )

st.markdown("---")

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
    "margin-top:60px;'>v2.0 - Build per Nicolas Colombo - Maggio 2026</div>",
    unsafe_allow_html=True,
)
