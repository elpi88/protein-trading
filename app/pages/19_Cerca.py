"""
Ricerca globale — cerca su fornitori, clienti, offerte, bid, spedizioni.
"""
import streamlit as st
import pandas as pd
from lib.auth import require_login
from lib.data import read_sheet
from lib.theme import apply_theme

require_login()
apply_theme()

st.markdown(
    '<div class="page-title">🔍 Ricerca globale</div>'
    '<div class="page-sub">Cerca contemporaneamente su tutte le sezioni</div>',
    unsafe_allow_html=True,
)

# Preleva query da sidebar o da input locale
q_init = st.session_state.pop("global_search_query", "")

q = st.text_input(
    "Cerca ovunque",
    value=q_init,
    placeholder="Es: Smithfield, pork loin, BID-00012, Spain...",
    label_visibility="collapsed",
)

if not q or len(q.strip()) < 2:
    st.info("Digita almeno 2 caratteri per cercare.")
    st.stop()

term = q.strip().lower()

# -----------------------------------------------------------------------
# Configurazione fonti di ricerca
# -----------------------------------------------------------------------
SOURCES = [
    {
        "sheet":   "SUPPLIERS_CLEAN",
        "label":   "Fornitori",
        "icon":    "🏭",
        "page":    "pages/2_Fornitori.py",
        "id_col":  "Supplier ID",
        "name_col":"Company Name",
        "cols":    ["Supplier ID", "Company Name", "Country", "Protein Category", "Products"],
    },
    {
        "sheet":   "CLIENTS",
        "label":   "Clienti",
        "icon":    "👥",
        "page":    "pages/3_Clienti.py",
        "id_col":  "Client ID",
        "name_col":"Company Name",
        "cols":    ["Client ID", "Company Name", "COUNTRY", "PROTEIN CATEGORY", "ITEMS"],
    },
    {
        "sheet":   "OFFERS",
        "label":   "Offerte",
        "icon":    "📋",
        "page":    "pages/4_Offerte.py",
        "id_col":  "Offer ID",
        "name_col":"Supplier",
        "cols":    ["Offer ID", "Supplier", "Product", "Subproduct", "Price USD/kg",
                    "Incoterm", "Country Destination", "Load Ready Date"],
    },
    {
        "sheet":   "BIDS",
        "label":   "Bid",
        "icon":    "🎯",
        "page":    "pages/5_Bid.py",
        "id_col":  "Bid ID",
        "name_col":"Client",
        "cols":    ["Bid ID", "Client", "Product", "Subproduct", "Target USD/kg",
                    "Volume (kg)", "Need By Date", "Status"],
    },
    {
        "sheet":   "SHIPMENTS",
        "label":   "Spedizioni",
        "icon":    "🚢",
        "page":    "pages/11_Spedizioni.py",
        "id_col":  "Shipment ID",
        "name_col":"Client",
        "cols":    ["Shipment ID", "Client", "Product", "ETA", "Status",
                    "Origin Port", "Destination Port"],
    },
    {
        "sheet":   "INVOICES",
        "label":   "Fatture",
        "icon":    "💰",
        "page":    "pages/12_Ordini.py",
        "id_col":  "Invoice ID",
        "name_col":"Client",
        "cols":    ["Invoice ID", "Client", "Product", "Total USD",
                    "Payment Status", "Due Date"],
    },
]

# -----------------------------------------------------------------------
# Esegui ricerca
# -----------------------------------------------------------------------
total_hits = 0
results = []

for src in SOURCES:
    try:
        df = read_sheet(src["sheet"])
        if df.empty:
            continue
        # Cerca in tutte le colonne come stringa
        available_cols = [c for c in src["cols"] if c in df.columns]
        mask = df[available_cols].astype(str).apply(
            lambda col: col.str.lower().str.contains(term, na=False)
        ).any(axis=1)
        hits = df[mask][available_cols].copy()
        if not hits.empty:
            results.append({**src, "hits": hits})
            total_hits += len(hits)
    except Exception:
        pass

# -----------------------------------------------------------------------
# Mostra risultati
# -----------------------------------------------------------------------
if total_hits == 0:
    st.warning(f"Nessun risultato per **\"{q}\"**.")
    st.stop()

st.markdown(
    f"<div style='font-size:0.9rem; color:#aaa; margin-bottom:16px'>"
    f"Trovati <b style='color:#eee'>{total_hits}</b> risultati per "
    f"<b style='color:#e84e0f'>"{q}"</b></div>",
    unsafe_allow_html=True,
)

for src in results:
    hits = src["hits"]
    n = len(hits)
    with st.expander(f"{src['icon']} {src['label']} — {n} risultat{'o' if n == 1 else 'i'}", expanded=True):
        st.dataframe(hits, use_container_width=True, hide_index=True, height=min(200, 40 + n * 35))
        st.page_link(src["page"], label=f"→ Vai a {src['label']}", use_container_width=False)
