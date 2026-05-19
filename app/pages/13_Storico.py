"""Storico modifiche - audit log."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from lib.data import read_audit_log, AUDIT_LOG
from lib.theme import apply_theme, kpi_card

st.set_page_config(page_title="Storico - Protein Trading", page_icon="📜", layout="wide")
apply_theme()

st.markdown(
    """
    <div class="page-title">Storico modifiche</div>
    <div class="page-sub">Log di tutte le aggiunte, modifiche, cancellazioni e merge fatti dall'app.</div>
    """,
    unsafe_allow_html=True,
)

df = read_audit_log(limit=2000)

# -------------------------------------------------------------------
# KPI
# -------------------------------------------------------------------
fmt = lambda n: f"{int(n):,}".replace(",", "'")
n_total = len(df)
n_add = int((df["action"].str.upper() == "ADD").sum()) if not df.empty else 0
n_upd = int((df["action"].str.upper() == "UPDATE").sum()) if not df.empty else 0
n_del = int((df["action"].str.upper() == "DELETE").sum()) if not df.empty else 0

c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(kpi_card("Eventi totali", fmt(n_total), "registrati"), unsafe_allow_html=True)
with c2: st.markdown(kpi_card("Aggiunte", fmt(n_add), "ADD"), unsafe_allow_html=True)
with c3: st.markdown(kpi_card("Modifiche", fmt(n_upd), "UPDATE"), unsafe_allow_html=True)
with c4: st.markdown(kpi_card("Cancellazioni", fmt(n_del), "DELETE"), unsafe_allow_html=True)

st.markdown("")

# -------------------------------------------------------------------
# Filtri
# -------------------------------------------------------------------
if df.empty:
    st.info("Nessun evento ancora registrato. Le modifiche fatte dall'app verranno loggate qui.")
    st.stop()

c1, c2, c3 = st.columns(3)
with c1:
    q = st.text_input("Cerca", placeholder="Cerca ID, dettagli, ...")
with c2:
    sheets = ["Tutti"] + sorted(df["sheet"].dropna().unique().tolist())
    sheet_sel = st.selectbox("Foglio", sheets)
with c3:
    actions = ["Tutte"] + sorted(df["action"].dropna().unique().tolist())
    act_sel = st.selectbox("Azione", actions)

view = df.copy()
if q:
    qq = q.lower()
    view = view[view.apply(lambda r: qq in " ".join(str(v) for v in r.values).lower(), axis=1)]
if sheet_sel != "Tutti":
    view = view[view["sheet"] == sheet_sel]
if act_sel != "Tutte":
    view = view[view["action"] == act_sel]

st.caption(f"**{len(view):,}** eventi mostrati".replace(",", "'") +
            (f" (filtrati su {len(df):,})".replace(",", "'") if len(view) != len(df) else ""))

# -------------------------------------------------------------------
# Tabella
# -------------------------------------------------------------------
st.dataframe(
    view, use_container_width=True, hide_index=True, height=520,
    column_config={
        "timestamp": st.column_config.TextColumn("Quando", width="medium"),
        "user": st.column_config.TextColumn("Utente", width="small"),
        "action": st.column_config.TextColumn("Azione", width="small"),
        "sheet": st.column_config.TextColumn("Foglio", width="small"),
        "row_id": st.column_config.TextColumn("ID record", width="small"),
        "details": st.column_config.TextColumn("Dettagli"),
    },
)

# Download
with open(AUDIT_LOG, "rb") as f:
    st.download_button(
        "⬇ Scarica tutto il log CSV",
        f.read(),
        file_name=AUDIT_LOG.name,
        mime="text/csv",
    )
