"""Spedizioni - vessels tracking."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date
import pandas as pd
import streamlit as st

from lib.data import read_sheet, add_row, update_row, delete_row, next_id
from lib.theme import apply_theme, kpi_card

st.set_page_config(page_title="Spedizioni - Protein Trading", page_icon="🚢", layout="wide")
apply_theme()

st.markdown(
    """
    <div class="page-title">Spedizioni & Vessel Tracking</div>
    <div class="page-sub">Gestisci tutte le spedizioni con vessel, container, ETA e stato in tempo reale.</div>
    """,
    unsafe_allow_html=True,
)

SHEET = "SHIPMENTS"
df = read_sheet(SHEET)
STATUS_OPTIONS = ["BOOKED", "LOADING", "IN_TRANSIT", "ARRIVED", "DELIVERED", "DELAYED", "CANCELLED"]

# -------------------------------------------------------------------
# KPI
# -------------------------------------------------------------------
today = date.today()
in_transit = df[df.get("Status", pd.Series()).astype(str).str.upper() == "IN_TRANSIT"] if not df.empty else df
delayed = df[df.get("Status", pd.Series()).astype(str).str.upper() == "DELAYED"] if not df.empty else df

# ETA prossime
eta_soon = pd.DataFrame()
if not df.empty and "ETA" in df.columns:
    tmp = df.copy()
    tmp["ETA_d"] = pd.to_datetime(tmp["ETA"], errors="coerce").dt.date
    tmp["giorni"] = tmp["ETA_d"].apply(lambda d: (d - today).days if d else None)
    eta_soon = tmp[(tmp["giorni"].notna()) & (tmp["giorni"] >= 0) & (tmp["giorni"] <= 7) &
                       (tmp.get("Status", "").astype(str).str.upper().isin(["IN_TRANSIT", "LOADING", "BOOKED"]))]

fmt = lambda n: f"{int(n):,}".replace(",", "'")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(kpi_card("In transito", fmt(len(in_transit)), "spedizioni attive"), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card("ETA ≤ 7 giorni", fmt(len(eta_soon)), "arrivo imminente"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("In ritardo", fmt(len(delayed)), "status DELAYED"), unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card("Totale", fmt(len(df)), "tutte le spedizioni"), unsafe_allow_html=True)

st.markdown("")

# -------------------------------------------------------------------
# Toolbar
# -------------------------------------------------------------------
left, mid, right = st.columns([3, 2, 1])
with left:
    q = st.text_input("Cerca", placeholder="Cerca per cliente, prodotto, vessel, container...",
                      label_visibility="collapsed")
with mid:
    st_sel = st.selectbox("Status", ["Tutti"] + STATUS_OPTIONS, label_visibility="collapsed")
with right:
    if st.button("➕ Nuova spedizione", use_container_width=True, type="primary"):
        st.session_state["shp_mode"] = "add"
        st.session_state["shp_edit_id"] = None

view = df.copy()
if q:
    qq = q.lower()
    view = view[view.apply(lambda r: qq in " ".join(str(v) for v in r.values).lower(), axis=1)]
if st_sel != "Tutti" and "Status" in view.columns:
    view = view[view["Status"].astype(str).str.upper() == st_sel.upper()]

st.caption(f"**{len(view):,}** spedizioni".replace(",", "'") +
            (f" (filtrate su {len(df):,})".replace(",", "'") if len(view) != len(df) else ""))

# Tabella
display_cols = ["Shipment ID", "Client", "Product", "Quantity", "Unit",
                "Carrier/Vessel", "Container #", "Origin Port", "Destination Port",
                "ETD", "ETA", "Status"]
display_cols = [c for c in display_cols if c in view.columns]
st.dataframe(view[display_cols], use_container_width=True, hide_index=True, height=420,
               column_config={
                   "Shipment ID": st.column_config.TextColumn("ID", width="small"),
                   "Quantity": st.column_config.NumberColumn("Quantità", format="%.0f"),
                   "ETD": st.column_config.DateColumn("ETD"),
                   "ETA": st.column_config.DateColumn("ETA"),
               })

# Azioni
st.markdown("##### Azioni su una spedizione esistente")
col_id, col_b1, col_b2 = st.columns([3, 1, 1])
with col_id:
    sel_id = st.selectbox("ID spedizione",
        options=[""] + view["Shipment ID"].astype(str).tolist() if not view.empty else [""],
        label_visibility="collapsed", placeholder="Seleziona una spedizione...")
with col_b1:
    if st.button("✏️ Modifica", use_container_width=True, disabled=not sel_id):
        st.session_state["shp_mode"] = "edit"; st.session_state["shp_edit_id"] = sel_id
with col_b2:
    if st.button("🗑️ Cancella", use_container_width=True, disabled=not sel_id):
        st.session_state["shp_mode"] = "delete"; st.session_state["shp_edit_id"] = sel_id


mode = st.session_state.get("shp_mode")
edit_id = st.session_state.get("shp_edit_id")

if mode in ("add", "edit"):
    title = "Nuova spedizione" if mode == "add" else f"Modifica {edit_id}"
    new_id = next_id(SHEET) if mode == "add" else edit_id
    existing = {}
    if mode == "edit" and edit_id:
        row = df[df["Shipment ID"].astype(str) == str(edit_id)]
        if not row.empty:
            existing = row.iloc[0].to_dict()

    with st.expander(f"📝 {title}", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Shipment ID", value=new_id, disabled=True)
            invoice_id = st.text_input("Invoice ID", value=str(existing.get("Invoice ID", "") or ""))
            bid_id_v = st.text_input("Bid ID", value=str(existing.get("Bid ID", "") or ""))
            client = st.text_input("Client *", value=str(existing.get("Client", "") or ""))
            product = st.text_input("Product *", value=str(existing.get("Product", "") or ""))
            try:
                qty = st.number_input("Quantity", value=float(existing.get("Quantity") or 0),
                                         step=100.0, format="%.0f")
            except Exception:
                qty = st.number_input("Quantity", value=0.0, step=100.0, format="%.0f")
            unit = st.selectbox("Unit", ["KG", "LB", "MT"],
                                  index=["KG", "LB", "MT"].index(str(existing.get("Unit", "KG") or "KG"))
                                  if str(existing.get("Unit", "KG") or "KG") in ["KG", "LB", "MT"] else 0)
            origin = st.text_input("Origin Port", value=str(existing.get("Origin Port", "") or ""))
            dest = st.text_input("Destination Port", value=str(existing.get("Destination Port", "") or ""))
        with c2:
            vessel = st.text_input("Carrier/Vessel", value=str(existing.get("Carrier/Vessel", "") or ""))
            container = st.text_input("Container #", value=str(existing.get("Container #", "") or ""))
            container_type = st.text_input("Container Type", value=str(existing.get("Container Type", "") or ""))
            incoterm = st.text_input("Incoterm", value=str(existing.get("Incoterm", "") or ""))
            tracking = st.text_input("Tracking #", value=str(existing.get("Tracking #", "") or ""))
            cur_status = str(existing.get("Status", "") or "BOOKED")
            status = st.selectbox("Status", STATUS_OPTIONS,
                                    index=STATUS_OPTIONS.index(cur_status)
                                    if cur_status in STATUS_OPTIONS else 0)
            notes = st.text_area("Notes", value=str(existing.get("Notes", "") or ""), height=70)

        cd1, cd2 = st.columns(2)
        with cd1:
            etd_def = existing.get("ETD") if mode == "edit" else None
            try:
                etd = st.date_input("ETD", value=pd.to_datetime(etd_def).date()
                                       if etd_def and pd.notna(etd_def) else None)
            except Exception:
                etd = st.date_input("ETD", value=None)
        with cd2:
            eta_def = existing.get("ETA") if mode == "edit" else None
            try:
                eta = st.date_input("ETA", value=pd.to_datetime(eta_def).date()
                                       if eta_def and pd.notna(eta_def) else None)
            except Exception:
                eta = st.date_input("ETA", value=None)

        cb1, cb2, _ = st.columns([1, 1, 4])
        with cb1: save_clicked = st.button("💾 Salva", type="primary", use_container_width=True)
        with cb2: cancel_clicked = st.button("✖ Annulla", use_container_width=True)

        if save_clicked:
            if not client.strip() or not product.strip():
                st.error("Client e Product sono obbligatori.")
            else:
                values = {
                    "Invoice ID": invoice_id.strip() or None,
                    "Bid ID": bid_id_v.strip() or None,
                    "Client": client.strip(),
                    "Product": product.strip(),
                    "Quantity": float(qty) if qty else None,
                    "Unit": unit,
                    "Origin Port": origin.strip() or None,
                    "Destination Port": dest.strip() or None,
                    "Carrier/Vessel": vessel.strip() or None,
                    "Container #": container.strip() or None,
                    "Container Type": container_type.strip() or None,
                    "Incoterm": incoterm.strip() or None,
                    "ETD": etd if etd else None,
                    "ETA": eta if eta else None,
                    "Days in Transit": (eta - etd).days if (etd and eta) else None,
                    "Status": status,
                    "Tracking #": tracking.strip() or None,
                    "Notes": notes.strip() or None,
                }
                try:
                    if mode == "add":
                        nid = add_row(SHEET, values)
                        st.success(f"Spedizione aggiunta: {nid}")
                    else:
                        update_row(SHEET, edit_id, values)
                        st.success(f"Spedizione {edit_id} aggiornata.")
                    st.session_state["shp_mode"] = None
                    st.session_state["shp_edit_id"] = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")
        if cancel_clicked:
            st.session_state["shp_mode"] = None
            st.session_state["shp_edit_id"] = None
            st.rerun()

if mode == "delete" and edit_id:
    st.warning(f"Cancellare la spedizione **{edit_id}**?")
    cc1, cc2, _ = st.columns([1, 1, 4])
    with cc1:
        if st.button("🗑️ Sì, cancella", type="primary", use_container_width=True):
            delete_row(SHEET, edit_id)
            st.success(f"{edit_id} cancellata.")
            st.session_state["shp_mode"] = None
            st.session_state["shp_edit_id"] = None
            st.rerun()
    with cc2:
        if st.button("Annulla", use_container_width=True):
            st.session_state["shp_mode"] = None
            st.session_state["shp_edit_id"] = None
            st.rerun()
