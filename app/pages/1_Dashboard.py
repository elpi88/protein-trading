"""Dashboard - vista d'insieme con KPI e grafici."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from lib.data import read_sheet, get_kpis
from lib.theme import apply_theme, kpi_card, PROTEIN_COLORS

st.set_page_config(page_title="Dashboard - Protein Trading", page_icon="📊", layout="wide")
apply_theme()

st.markdown(
    """
    <div class="page-title">Dashboard</div>
    <div class="page-sub">Panoramica in tempo reale dei dati nel file Excel.</div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------
# Bottoni utili in alto a destra
# -----------------------------------------------------------------
col_actions = st.columns([4, 1])[1]
with col_actions:
    if st.button("🔄 Ricarica dati", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# -----------------------------------------------------------------
# KPI cards
# -----------------------------------------------------------------
kpis = get_kpis()

c1, c2, c3, c4, c5 = st.columns(5)
fmt = lambda n: f"{int(n):,}".replace(",", "'")
with c1:
    st.markdown(kpi_card("Fornitori", fmt(kpis["n_suppliers"]), "in anagrafica"), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card("Clienti", fmt(kpis["n_clients"]), "in anagrafica"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("Offerte", fmt(kpis["n_offers"]), "ricevute totali"), unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card("Bid Aperti", fmt(kpis["n_bids_open"]),
                            f"su {kpis['n_bids']} totali"), unsafe_allow_html=True)
with c5:
    pl_str = f"USD {kpis['pipeline_usd']/1000:,.0f}k".replace(",", "'")
    st.markdown(kpi_card("Pipeline", pl_str, "valore bid aperti"), unsafe_allow_html=True)

st.markdown("")
st.markdown("")

# -----------------------------------------------------------------
# Grafici
# -----------------------------------------------------------------
suppliers = read_sheet("SUPPLIERS_CLEAN")
clients = read_sheet("CLIENTS")
offers = read_sheet("OFFERS")
bids = read_sheet("BIDS")

tab1, tab2, tab3 = st.tabs(["Fornitori", "Clienti", "Offerte / Bid"])

with tab1:
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("##### Fornitori per categoria proteina")
        if not suppliers.empty and "Protein Category" in suppliers.columns:
            agg = (suppliers["Protein Category"].fillna("UNCLASSIFIED")
                   .str.upper().value_counts().reset_index())
            agg.columns = ["Categoria", "N. fornitori"]
            color_map = {c: PROTEIN_COLORS.get(c, "#94A3B8") for c in agg["Categoria"]}
            fig = px.bar(agg, x="Categoria", y="N. fornitori",
                         color="Categoria", color_discrete_map=color_map,
                         text="N. fornitori")
            fig.update_traces(textposition="outside")
            fig.update_layout(showlegend=False, height=380,
                              margin=dict(l=0, r=0, t=10, b=0),
                              plot_bgcolor="white",
                              yaxis=dict(gridcolor="#e2e8f0"))
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("##### Top 10 paesi (fornitori)")
        if not suppliers.empty and "Country" in suppliers.columns:
            top = (suppliers["Country"].fillna("(Nessun paese)")
                   .value_counts().head(10).reset_index())
            top.columns = ["Paese", "N. fornitori"]
            fig = px.bar(top, x="N. fornitori", y="Paese", orientation="h",
                         text="N. fornitori",
                         color_discrete_sequence=["#0b3d91"])
            fig.update_traces(textposition="outside")
            fig.update_layout(height=380, margin=dict(l=0, r=20, t=10, b=0),
                              plot_bgcolor="white",
                              yaxis=dict(autorange="reversed", title=""),
                              xaxis=dict(gridcolor="#e2e8f0", title=""))
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("##### Clienti per categoria")
        if not clients.empty and "PROTEIN CATEGORY" in clients.columns:
            agg = (clients["PROTEIN CATEGORY"].fillna("UNCLASSIFIED")
                   .str.upper().value_counts().reset_index())
            agg.columns = ["Categoria", "N. clienti"]
            color_map = {c: PROTEIN_COLORS.get(c, "#94A3B8") for c in agg["Categoria"]}
            fig = px.pie(agg, names="Categoria", values="N. clienti",
                         color="Categoria", color_discrete_map=color_map, hole=0.55)
            fig.update_traces(textinfo="label+value")
            fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0),
                              showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("##### Clienti per paese")
        if not clients.empty and "COUNTRY" in clients.columns:
            top = (clients["COUNTRY"].fillna("(Nessun paese)")
                   .value_counts().head(10).reset_index())
            top.columns = ["Paese", "N. clienti"]
            fig = px.bar(top, x="N. clienti", y="Paese", orientation="h",
                         text="N. clienti",
                         color_discrete_sequence=["#1d4ed8"])
            fig.update_traces(textposition="outside")
            fig.update_layout(height=380, margin=dict(l=0, r=20, t=10, b=0),
                              plot_bgcolor="white",
                              yaxis=dict(autorange="reversed", title=""),
                              xaxis=dict(gridcolor="#e2e8f0", title=""))
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("##### Offerte per prodotto")
        if not offers.empty and "Product" in offers.columns:
            agg = (offers["Product"].fillna("?")
                   .value_counts().head(10).reset_index())
            agg.columns = ["Prodotto", "N. offerte"]
            fig = px.bar(agg, x="N. offerte", y="Prodotto", orientation="h",
                         text="N. offerte",
                         color_discrete_sequence=["#059669"])
            fig.update_traces(textposition="outside")
            fig.update_layout(height=380, margin=dict(l=0, r=20, t=10, b=0),
                              plot_bgcolor="white",
                              yaxis=dict(autorange="reversed", title=""),
                              xaxis=dict(gridcolor="#e2e8f0", title=""))
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("##### Bid per status")
        if not bids.empty and "Status" in bids.columns:
            agg = (bids["Status"].fillna("UNKNOWN").str.upper()
                   .value_counts().reset_index())
            agg.columns = ["Status", "N. bid"]
            status_colors = {"OPEN":"#059669", "WON":"#0b3d91",
                             "LOST":"#dc2626", "CLOSED":"#64748b",
                             "IN_DISCUSSION":"#d97706", "CANCELLED":"#94a3b8"}
            color_map = {k: status_colors.get(k, "#94a3b8") for k in agg["Status"]}
            fig = px.pie(agg, names="Status", values="N. bid",
                         color="Status", color_discrete_map=color_map, hole=0.55)
            fig.update_traces(textinfo="label+value")
            fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0),
                              showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
