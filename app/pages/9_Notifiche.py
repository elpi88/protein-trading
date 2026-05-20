"""Notifiche e scadenze - alert su bid in scadenza, offerte vecchie, bid senza match."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

from lib.data import read_sheet, get_matches, normalize_product
from lib.theme import apply_theme, kpi_card

from lib.auth import require_login
require_login()


st.set_page_config(page_title="Notifiche - Protein Trading", page_icon="🔔", layout="wide")
apply_theme()

st.markdown(
    """
    <div class="page-title">Notifiche & Scadenze</div>
    <div class="page-sub">Cosa richiede la tua attenzione oggi.</div>
    """,
    unsafe_allow_html=True,
)

ca, cb = st.columns([4, 1])
with cb:
    if st.button("🔄 Ricarica", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

today = datetime.now().date()

# -------------------------------------------------------------------
# Calcolo alert
# -------------------------------------------------------------------
bids = read_sheet("BIDS")
offers = read_sheet("OFFERS")
matches = get_matches(open_bids_only=True)

# Bid OPEN in scadenza (< 14 giorni)
bids_scad = pd.DataFrame()
bids_overdue = pd.DataFrame()
if not bids.empty and "Status" in bids.columns and "Need By Date" in bids.columns:
    open_bids = bids[bids["Status"].astype(str).str.upper() == "OPEN"].copy()
    open_bids["Need By Date"] = pd.to_datetime(open_bids["Need By Date"], errors="coerce")
    open_bids["Giorni rimasti"] = (open_bids["Need By Date"].dt.date - today).apply(
        lambda d: d.days if pd.notna(d) else None
    )
    valid = open_bids[open_bids["Need By Date"].notna()].copy()
    bids_scad = valid[(valid["Giorni rimasti"] >= 0) & (valid["Giorni rimasti"] <= 14)].copy()
    bids_scad = bids_scad.sort_values("Giorni rimasti")
    bids_overdue = valid[valid["Giorni rimasti"] < 0].copy()
    bids_overdue["Giorni di ritardo"] = -bids_overdue["Giorni rimasti"]
    bids_overdue = bids_overdue.sort_values("Giorni di ritardo", ascending=False)

# Offerte vecchie (> 30 giorni)
offers_old = pd.DataFrame()
if not offers.empty and "Offer Date" in offers.columns:
    o = offers.copy()
    o["Offer Date"] = pd.to_datetime(o["Offer Date"], errors="coerce")
    valid_o = o[o["Offer Date"].notna()].copy()
    valid_o["Età (giorni)"] = (today - valid_o["Offer Date"].dt.date).apply(
        lambda d: d.days if pd.notna(d) else None
    )
    offers_old = valid_o[valid_o["Età (giorni)"] > 30].sort_values("Età (giorni)", ascending=False)

# Bid OPEN senza match
bids_no_match = pd.DataFrame()
if not bids.empty and "Status" in bids.columns:
    open_bids = bids[bids["Status"].astype(str).str.upper() == "OPEN"].copy()
    matched_bid_ids = set(matches["Bid ID"].astype(str)) if not matches.empty else set()
    bids_no_match = open_bids[~open_bids["Bid ID"].astype(str).isin(matched_bid_ids)].copy()

# -------------------------------------------------------------------
# KPI cards
# -------------------------------------------------------------------
fmt = lambda n: f"{int(n):,}".replace(",", "'")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(kpi_card("Bid in scadenza", fmt(len(bids_scad)), "≤ 14 giorni"),
                  unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card("Bid scaduti", fmt(len(bids_overdue)), "Need By Date superata"),
                  unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("Offerte vecchie", fmt(len(offers_old)), "> 30 giorni"),
                  unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card("Bid senza match", fmt(len(bids_no_match)), "nessuna offerta"),
                  unsafe_allow_html=True)

st.markdown("")
st.markdown("---")

# -------------------------------------------------------------------
# Sezione: bid scaduti
# -------------------------------------------------------------------
if not bids_overdue.empty:
    st.markdown(f"### 🚨 {len(bids_overdue)} bid scaduti")
    st.error("Need By Date già passata. Decidere se chiudere come LOST o aggiornare.")
    show_cols = ["Bid ID", "Client", "Product", "Volume (kg)", "Need By Date",
                 "Giorni di ritardo", "Status"]
    show_cols = [c for c in show_cols if c in bids_overdue.columns]
    st.dataframe(bids_overdue[show_cols], use_container_width=True, hide_index=True,
                   column_config={
                       "Bid ID": st.column_config.TextColumn("ID", width="small"),
                       "Need By Date": st.column_config.DateColumn("Data limite"),
                       "Giorni di ritardo": st.column_config.NumberColumn("Ritardo", format="%d gg"),
                       "Volume (kg)": st.column_config.NumberColumn("Volume kg", format="%.0f"),
                   })
    st.markdown("")

# -------------------------------------------------------------------
# Sezione: bid in scadenza
# -------------------------------------------------------------------
if not bids_scad.empty:
    st.markdown(f"### ⏰ {len(bids_scad)} bid in scadenza")
    st.warning("Bid OPEN con Need By Date entro 14 giorni.")
    show_cols = ["Bid ID", "Client", "Product", "Volume (kg)", "Target USD/kg",
                 "Need By Date", "Giorni rimasti"]
    show_cols = [c for c in show_cols if c in bids_scad.columns]
    st.dataframe(bids_scad[show_cols], use_container_width=True, hide_index=True,
                   column_config={
                       "Bid ID": st.column_config.TextColumn("ID", width="small"),
                       "Need By Date": st.column_config.DateColumn("Data limite"),
                       "Giorni rimasti": st.column_config.NumberColumn("Mancano", format="%d gg"),
                       "Volume (kg)": st.column_config.NumberColumn("Volume kg", format="%.0f"),
                       "Target USD/kg": st.column_config.NumberColumn("Target $/kg", format="%.4f"),
                   })
    st.markdown("")

# -------------------------------------------------------------------
# Sezione: bid senza match
# -------------------------------------------------------------------
if not bids_no_match.empty:
    st.markdown(f"### 🔍 {len(bids_no_match)} bid senza match")
    st.info("Bid OPEN per cui non c'è ancora un'offerta sullo stesso prodotto. "
            "Considera di cercare attivamente fornitori.")
    show_cols = ["Bid ID", "Client", "Product", "Volume (kg)", "Target USD/kg",
                 "Need By Date", "Status"]
    show_cols = [c for c in show_cols if c in bids_no_match.columns]
    st.dataframe(bids_no_match[show_cols], use_container_width=True, hide_index=True,
                   column_config={
                       "Bid ID": st.column_config.TextColumn("ID", width="small"),
                       "Volume (kg)": st.column_config.NumberColumn("Volume kg", format="%.0f"),
                       "Target USD/kg": st.column_config.NumberColumn("Target $/kg", format="%.4f"),
                   })
    st.markdown("")

# -------------------------------------------------------------------
# Sezione: offerte vecchie
# -------------------------------------------------------------------
if not offers_old.empty:
    st.markdown(f"### 📅 {len(offers_old)} offerte vecchie")
    st.info("Offerte con Offer Date più vecchia di 30 giorni. "
            "Potrebbero non essere più valide - chiedere conferma al fornitore.")
    show_cols = ["Offer ID", "Supplier", "Product", "Price", "Currency",
                 "Offer Date", "Età (giorni)"]
    show_cols = [c for c in show_cols if c in offers_old.columns]
    st.dataframe(offers_old[show_cols], use_container_width=True, hide_index=True,
                   column_config={
                       "Offer ID": st.column_config.TextColumn("ID", width="small"),
                       "Offer Date": st.column_config.DateColumn("Data offerta"),
                       "Età (giorni)": st.column_config.NumberColumn("Età", format="%d gg"),
                   })
    st.markdown("")

# Nessuna notifica
if (bids_overdue.empty and bids_scad.empty and bids_no_match.empty and offers_old.empty):
    st.success("Tutto sotto controllo: nessuna scadenza, nessun bid senza match, nessuna offerta vecchia.")
