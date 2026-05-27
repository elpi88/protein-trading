"""
Storico Prezzi — andamento prezzi USD/kg per prodotto e fornitore.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

from lib.auth import require_login
from lib.data import read_sheet
from lib.theme import apply_theme

require_login()
apply_theme()

st.markdown(
    '<div class="page-title">📈 Storico Prezzi</div>'
    '<div class="page-sub">Andamento prezzi USD/kg per prodotto, fornitore e categoria</div>',
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------
# Carica dati
# -----------------------------------------------------------------------
offers = read_sheet("OFFERS")
bids   = read_sheet("BIDS")

if offers.empty:
    st.info("Nessuna offerta presente. Aggiungi offerte per vedere i trend di prezzo.")
    st.stop()

# Normalizza colonne
offers = offers.copy()
offers["Price USD/kg"] = pd.to_numeric(offers.get("Price USD/kg", pd.Series()), errors="coerce")
offers["Offer Date"]   = pd.to_datetime(offers.get("Offer Date", pd.Series()), errors="coerce")
offers = offers.dropna(subset=["Price USD/kg", "Offer Date"])
offers = offers[offers["Price USD/kg"] > 0]

if not bids.empty:
    bids = bids.copy()
    bids["Target USD/kg"] = pd.to_numeric(bids.get("Target USD/kg", pd.Series()), errors="coerce")
    bids["Bid Date"]      = pd.to_datetime(bids.get("Bid Date", pd.Series()), errors="coerce")
    bids = bids.dropna(subset=["Target USD/kg", "Bid Date"])
    bids = bids[bids["Target USD/kg"] > 0]

# -----------------------------------------------------------------------
# Filtri
# -----------------------------------------------------------------------
st.markdown("### Filtri")
f1, f2, f3, f4 = st.columns(4)

with f1:
    all_products = sorted(offers["Product"].dropna().astype(str).unique().tolist())
    sel_product  = st.multiselect("Prodotto", all_products,
                                   default=all_products[:3] if len(all_products) >= 3 else all_products)

with f2:
    all_suppliers = sorted(offers["Supplier"].dropna().astype(str).unique().tolist())
    sel_supplier  = st.multiselect("Fornitore", ["Tutti"] + all_suppliers, default=["Tutti"])

with f3:
    period = st.selectbox("Periodo", ["Ultimi 6 mesi", "Ultimo anno", "Ultimi 2 anni", "Tutto"])

with f4:
    view_mode = st.radio("Vista", ["Per prodotto", "Per fornitore"], horizontal=True)

# Applica filtri temporali
today = date.today()
period_map = {
    "Ultimi 6 mesi":  today - timedelta(days=180),
    "Ultimo anno":    today - timedelta(days=365),
    "Ultimi 2 anni":  today - timedelta(days=730),
    "Tutto":          date(2000, 1, 1),
}
date_from = pd.Timestamp(period_map[period])

df_filtered = offers[offers["Offer Date"] >= date_from].copy()

if sel_product:
    df_filtered = df_filtered[df_filtered["Product"].isin(sel_product)]

if "Tutti" not in sel_supplier and sel_supplier:
    df_filtered = df_filtered[df_filtered["Supplier"].isin(sel_supplier)]

if df_filtered.empty:
    st.warning("Nessun dato per i filtri selezionati.")
    st.stop()

st.markdown("---")

# -----------------------------------------------------------------------
# Grafico principale: trend prezzi
# -----------------------------------------------------------------------
st.markdown("### Andamento prezzi offerte (USD/kg)")

if view_mode == "Per prodotto":
    color_col = "Product"
else:
    color_col = "Supplier"

fig = px.scatter(
    df_filtered.sort_values("Offer Date"),
    x="Offer Date",
    y="Price USD/kg",
    color=color_col,
    hover_data=["Offer ID", "Supplier", "Product", "Subproduct", "Incoterm", "Currency"],
    title=None,
    template="plotly_dark",
    size_max=10,
)

# Aggiungi linee di tendenza per ogni gruppo
for group_val, group_df in df_filtered.groupby(color_col):
    if len(group_df) >= 2:
        gdf = group_df.sort_values("Offer Date")
        fig.add_trace(go.Scatter(
            x=gdf["Offer Date"], y=gdf["Price USD/kg"],
            mode="lines",
            line=dict(width=1, dash="dot"),
            name=f"{group_val} (trend)",
            showlegend=False,
            opacity=0.4,
        ))

fig.update_layout(
    height=420,
    plot_bgcolor="#0e1117",
    paper_bgcolor="#0e1117",
    font_color="#ccc",
    xaxis_title="Data offerta",
    yaxis_title="Prezzo USD/kg",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=40, r=20, t=20, b=40),
)
st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------
# Box plot: distribuzione prezzi per prodotto
# -----------------------------------------------------------------------
if len(sel_product) > 1 or (not sel_product and len(all_products) > 1):
    st.markdown("### Distribuzione prezzi per prodotto")
    fig2 = px.box(
        df_filtered,
        x="Product", y="Price USD/kg",
        color="Product",
        template="plotly_dark",
        points="all",
        hover_data=["Supplier", "Offer Date"],
    )
    fig2.update_layout(
        height=350,
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#ccc",
        showlegend=False,
        xaxis_title="",
        yaxis_title="Prezzo USD/kg",
        margin=dict(l=40, r=20, t=10, b=80),
    )
    st.plotly_chart(fig2, use_container_width=True)

# -----------------------------------------------------------------------
# Confronto Offerte vs Bid (se dati bid disponibili)
# -----------------------------------------------------------------------
if not bids.empty and sel_product:
    bids_filtered = bids[
        bids["Product"].isin(sel_product) &
        (bids["Bid Date"] >= date_from)
    ].copy()

    if not bids_filtered.empty:
        st.markdown("### Confronto Offerte vs Bid (target cliente)")
        fig3 = go.Figure()

        for prod in sel_product:
            off_prod = df_filtered[df_filtered["Product"] == prod].sort_values("Offer Date")
            bid_prod = bids_filtered[bids_filtered["Product"] == prod].sort_values("Bid Date")

            if not off_prod.empty:
                fig3.add_trace(go.Scatter(
                    x=off_prod["Offer Date"], y=off_prod["Price USD/kg"],
                    mode="markers+lines", name=f"{prod} — Offer",
                    line=dict(width=2), marker=dict(size=7),
                ))
            if not bid_prod.empty:
                fig3.add_trace(go.Scatter(
                    x=bid_prod["Bid Date"], y=bid_prod["Target USD/kg"],
                    mode="markers+lines", name=f"{prod} — Bid target",
                    line=dict(width=2, dash="dash"), marker=dict(symbol="diamond", size=8),
                ))

        fig3.update_layout(
            height=380,
            template="plotly_dark",
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font_color="#ccc",
            xaxis_title="Data",
            yaxis_title="USD/kg",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=20, t=20, b=40),
        )
        st.plotly_chart(fig3, use_container_width=True)

# -----------------------------------------------------------------------
# Tabella riepilogo: prezzo medio / min / max per prodotto
# -----------------------------------------------------------------------
st.markdown("### Riepilogo statistico")
summary = (
    df_filtered.groupby("Product")["Price USD/kg"]
    .agg(["count", "mean", "min", "max", "std"])
    .reset_index()
)
summary.columns = ["Product", "# Offers", "Avg USD/kg", "Min USD/kg", "Max USD/kg", "Std Dev"]
for col in ["Avg USD/kg", "Min USD/kg", "Max USD/kg", "Std Dev"]:
    summary[col] = summary[col].round(3)
summary = summary.sort_values("Avg USD/kg", ascending=False)
st.dataframe(summary, use_container_width=True, hide_index=True)
