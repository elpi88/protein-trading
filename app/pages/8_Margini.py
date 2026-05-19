"""Margini & P&L - vista analitica delle opportunità."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from lib.data import get_matches, read_sheet
from lib.theme import apply_theme, kpi_card, PROTEIN_COLORS
try:
    from lib.pdf_export import margins_report
    PDF_OK = True
except Exception:
    PDF_OK = False
    margins_report = None

st.set_page_config(page_title="Margini - Protein Trading", page_icon="💰", layout="wide")
apply_theme()

st.markdown(
    """
    <div class="page-title">Margini & P&L</div>
    <div class="page-sub">Top opportunità per margine, ripartizione per categoria, analisi di redditività.</div>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------
# Calcolo
# -------------------------------------------------------------------
df = get_matches(open_bids_only=True)

if df.empty:
    st.info("Nessun match disponibile. Aggiungi prima qualche offerta o bid.")
    st.stop()

# Tieni solo positivi per le analisi P&L
pos = df[df["Margin USD/kg"] > 0].copy()
neg = df[df["Margin USD/kg"] <= 0].copy()

# -------------------------------------------------------------------
# KPI principali
# -------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
total_pl = float(pos["Margin USD"].sum())
avg_pl_kg = float(pos["Margin USD/kg"].mean()) if not pos.empty else 0
median_pct = (
    float(((pos["Margin USD/kg"] / pos["Target USD/kg"]) * 100).median())
    if not pos.empty else 0
)

with c1:
    st.markdown(kpi_card("P&L potenziale",
                           f"USD {total_pl/1000:,.0f}k".replace(",", "'"),
                           "somma margini positivi"),
                  unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card("Margine medio",
                           f"USD {avg_pl_kg:.3f}/kg",
                           "media match positivi"),
                  unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("Margine % mediano",
                           f"{median_pct:.1f}%",
                           "mediana match positivi"),
                  unsafe_allow_html=True)
with c4:
    pct_win = 100 * len(pos) / len(df) if len(df) else 0
    st.markdown(kpi_card("Win rate match",
                           f"{pct_win:.0f}%",
                           f"{len(pos)} su {len(df)}"),
                  unsafe_allow_html=True)

st.markdown("")

# Pulsante export PDF
if PDF_OK:
    try:
        pdf_bytes = margins_report(pos.head(25) if not pos.empty else df.head(25),
                                      title="Report Margini & P&L")
        st.download_button("📄 Esporta report PDF", pdf_bytes,
                              file_name="Report_Margini.pdf",
                              mime="application/pdf",
                              type="primary")
    except Exception as e:
        st.caption(f"Export PDF non disponibile: {e}")
else:
    st.caption("📄 Export PDF non disponibile - libreria reportlab mancante. "
                "Doppio click su Installa_PDF.bat per attivarlo.")

st.markdown("")

# -------------------------------------------------------------------
# Top 10 opportunità per valore totale
# -------------------------------------------------------------------
st.markdown("### Top 10 opportunità per valore totale")
top = pos.head(10).copy() if not pos.empty else pd.DataFrame()
if not top.empty:
    top_display = top[[
        "Bid ID", "Client", "Offer ID", "Supplier",
        "Product (bid)", "Margin USD/kg", "Volume (kg)", "Margin USD",
    ]].copy()
    top_display["Margin %"] = (top["Margin USD/kg"] / top["Target USD/kg"] * 100).round(1)
    st.dataframe(
        top_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Bid ID": st.column_config.TextColumn("Bid", width="small"),
            "Offer ID": st.column_config.TextColumn("Offer", width="small"),
            "Product (bid)": st.column_config.TextColumn("Prodotto"),
            "Margin USD/kg": st.column_config.NumberColumn("Margin $/kg", format="%.4f"),
            "Volume (kg)": st.column_config.NumberColumn("Volume kg", format="%.0f"),
            "Margin USD": st.column_config.NumberColumn("Margin USD", format="$%.0f"),
            "Margin %": st.column_config.NumberColumn("Margin %", format="%.1f%%"),
        },
    )

st.markdown("---")

# -------------------------------------------------------------------
# Grafici di analisi
# -------------------------------------------------------------------
ga, gb = st.columns(2)

with ga:
    st.markdown("##### Margine per prodotto")
    if not pos.empty:
        by_prod = (pos.groupby("Product (bid)")["Margin USD"]
                       .sum().sort_values(ascending=True).reset_index())
        by_prod.columns = ["Prodotto", "Margine USD"]
        fig = px.bar(by_prod.tail(15), x="Margine USD", y="Prodotto",
                     orientation="h", text="Margine USD",
                     color_discrete_sequence=["#059669"])
        fig.update_traces(texttemplate="$%{x:,.0f}", textposition="outside")
        fig.update_layout(height=420, margin=dict(l=0, r=20, t=10, b=0),
                          plot_bgcolor="white",
                          yaxis=dict(title=""),
                          xaxis=dict(gridcolor="#e2e8f0", title=""))
        st.plotly_chart(fig, use_container_width=True)

with gb:
    st.markdown("##### Distribuzione margine USD/kg")
    if not pos.empty:
        fig = px.histogram(pos, x="Margin USD/kg", nbins=20,
                           color_discrete_sequence=["#0b3d91"])
        fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0),
                          plot_bgcolor="white",
                          yaxis=dict(gridcolor="#e2e8f0", title="Numero match"),
                          xaxis=dict(gridcolor="#e2e8f0", title="USD/kg"))
        st.plotly_chart(fig, use_container_width=True)

st.markdown("")

# -------------------------------------------------------------------
# Scatter margine vs volume
# -------------------------------------------------------------------
st.markdown("##### Margine vs Volume (bolle = USD totale)")
if not pos.empty:
    pos_plot = pos.copy()
    pos_plot["abs_margin"] = pos_plot["Margin USD"].abs()
    fig = px.scatter(
        pos_plot, x="Volume (kg)", y="Margin USD/kg",
        size="abs_margin", hover_data=["Bid ID", "Offer ID", "Product (bid)",
                                          "Supplier", "Client", "Margin USD"],
        color="Product (bid)",
        color_discrete_sequence=px.colors.qualitative.Set2,
        size_max=50,
    )
    fig.update_layout(height=450, margin=dict(l=0, r=0, t=10, b=0),
                      plot_bgcolor="white",
                      yaxis=dict(gridcolor="#e2e8f0", zeroline=True, zerolinecolor="#94a3b8"),
                      xaxis=dict(gridcolor="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------------------------
# Match negativi (warning)
# -------------------------------------------------------------------
if not neg.empty:
    with st.expander(f"⚠️ {len(neg)} match con margine negativo - da rinegoziare", expanded=False):
        neg_display = neg[[
            "Bid ID", "Client", "Offer ID", "Supplier",
            "Product (bid)", "Target USD/kg", "Price USD/kg", "Margin USD/kg",
        ]].copy()
        st.dataframe(neg_display, use_container_width=True, hide_index=True,
                       column_config={
                           "Target USD/kg": st.column_config.NumberColumn("Target $/kg", format="%.4f"),
                           "Price USD/kg": st.column_config.NumberColumn("Offer $/kg", format="%.4f"),
                           "Margin USD/kg": st.column_config.NumberColumn("Margin $/kg", format="%.4f"),
                       })
