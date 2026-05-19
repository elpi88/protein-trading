"""Gestione Bid (richieste clienti)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date
import pandas as pd
import streamlit as st

from lib.data import (
    read_sheet, add_row, update_row, delete_row, next_id,
    get_currencies, get_units, get_countries,
    list_attachments, save_attachment, delete_attachment,
)
from lib.theme import apply_theme

st.set_page_config(page_title="Bid - Protein Trading", page_icon="🎯", layout="wide")
apply_theme()

st.markdown(
    """
    <div class="page-title">Bid (richieste dei clienti)</div>
    <div class="page-sub">Target USD/kg calcolato automaticamente in Excel.</div>
    """,
    unsafe_allow_html=True,
)

SHEET = "BIDS"
df = read_sheet(SHEET)
STATUS_OPTIONS = ["OPEN", "IN_DISCUSSION", "WON", "LOST", "CLOSED", "CANCELLED"]

left, mid, right = st.columns([3, 2, 1])
with left:
    q = st.text_input("Cerca", placeholder="Cerca cliente, prodotto, paese...",
                      label_visibility="collapsed")
with mid:
    st_opts = ["Tutti"] + STATUS_OPTIONS
    st_sel = st.selectbox("Status", st_opts, label_visibility="collapsed")
with right:
    if st.button("➕ Nuovo bid", use_container_width=True, type="primary"):
        st.session_state["bid_mode"] = "add"
        st.session_state["bid_edit_id"] = None

view = df.copy()
if q:
    qq = q.lower()
    view = view[view.apply(lambda r: qq in " ".join(str(v) for v in r.values).lower(), axis=1)]
if st_sel != "Tutti" and "Status" in view.columns:
    view = view[view["Status"].astype(str).str.upper() == st_sel.upper()]

st.caption(f"**{len(view):,}** bid".replace(",", "'") +
            (f" (filtrati su {len(df):,})".replace(",", "'") if len(view) != len(df) else ""))

display_cols = ["Bid ID", "Client", "Product", "Subproduct", "Target Price",
                "Currency", "Unit", "Target USD/kg", "Volume (kg)", "Status",
                "Need By Date"]
display_cols = [c for c in display_cols if c in view.columns]
st.dataframe(
    view[display_cols],
    use_container_width=True, hide_index=True, height=420,
    column_config={
        "Bid ID": st.column_config.TextColumn("ID", width="small"),
        "Target Price": st.column_config.NumberColumn("Target", format="%.4f"),
        "Target USD/kg": st.column_config.NumberColumn("USD/kg", format="%.4f"),
        "Volume (kg)": st.column_config.NumberColumn("Volume kg", format="%.0f"),
    },
)

st.markdown("##### Azioni su un bid esistente")
col_id, col_b1, col_b2 = st.columns([3, 1, 1])
with col_id:
    sel_id = st.selectbox("ID bid",
        options=[""] + view["Bid ID"].astype(str).tolist() if not view.empty else [""],
        label_visibility="collapsed", placeholder="Seleziona un bid...")
with col_b1:
    if st.button("✏️ Modifica", use_container_width=True, disabled=not sel_id):
        st.session_state["bid_mode"] = "edit"; st.session_state["bid_edit_id"] = sel_id
with col_b2:
    if st.button("🗑️ Cancella", use_container_width=True, disabled=not sel_id):
        st.session_state["bid_mode"] = "delete"; st.session_state["bid_edit_id"] = sel_id


mode = st.session_state.get("bid_mode")
edit_id = st.session_state.get("bid_edit_id")

if mode in ("add", "edit"):
    title = "Nuovo bid" if mode == "add" else f"Modifica {edit_id}"
    new_id = next_id(SHEET) if mode == "add" else edit_id
    existing = {}
    if mode == "edit" and edit_id:
        row = df[df["Bid ID"].astype(str) == str(edit_id)]
        if not row.empty:
            existing = row.iloc[0].to_dict()

    with st.expander(f"📝 {title}", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Bid ID", value=new_id, disabled=True)
            client = st.text_input("Client *", value=str(existing.get("Client", "") or ""))
            product = st.text_input("Product *", value=str(existing.get("Product", "") or ""))
            subproduct = st.text_input("Subproduct", value=str(existing.get("Subproduct", "") or ""))
            specifics = st.text_input("Specifics", value=str(existing.get("Specifics", "") or ""))
            packaging = st.text_input("Packaging", value=str(existing.get("Packaging", "") or ""))
            try:
                price = st.number_input("Target Price *",
                                          value=float(existing.get("Target Price") or 0),
                                          step=0.01, format="%.4f")
            except Exception:
                price = st.number_input("Target Price *", value=0.0, step=0.01, format="%.4f")
            try:
                volume = st.number_input("Volume (kg)",
                                          value=float(existing.get("Volume (kg)") or 0),
                                          step=1000.0, format="%.0f")
            except Exception:
                volume = st.number_input("Volume (kg)", value=0.0, step=1000.0, format="%.0f")

        with c2:
            currencies = get_currencies()
            cur_cur = str(existing.get("Currency", "") or "USD")
            if cur_cur and cur_cur not in currencies: currencies = [cur_cur] + currencies
            currency = st.selectbox("Currency *", currencies,
                                    index=currencies.index(cur_cur) if cur_cur in currencies else 0)
            units = get_units()
            cur_u = str(existing.get("Unit", "") or "KG")
            if cur_u and cur_u not in units: units = [cur_u] + units
            unit = st.selectbox("Unit *", units,
                                index=units.index(cur_u) if cur_u in units else 0)
            incoterm = st.text_input("Incoterm", value=str(existing.get("Incoterm", "") or ""))
            countries = get_countries()
            cur_o = str(existing.get("Origin Country", "") or "")
            if cur_o and cur_o not in countries:
                countries = [cur_o] + countries
            origin = st.selectbox("Origin Country", [""] + countries,
                index=([""] + countries).index(cur_o) if cur_o in ([""] + countries) else 0)
            cur_status = str(existing.get("Status", "") or "OPEN")
            if cur_status and cur_status not in STATUS_OPTIONS:
                STATUS_OPTIONS_LOCAL = [cur_status] + STATUS_OPTIONS
            else:
                STATUS_OPTIONS_LOCAL = STATUS_OPTIONS
            status = st.selectbox("Status", STATUS_OPTIONS_LOCAL,
                                    index=STATUS_OPTIONS_LOCAL.index(cur_status) if cur_status in STATUS_OPTIONS_LOCAL else 0)
            notes = st.text_area("Notes", value=str(existing.get("Notes", "") or ""), height=70)

        c3, c4 = st.columns(2)
        with c3:
            nbd_default = existing.get("Need By Date") if mode == "edit" else None
            try:
                nbd = st.date_input("Need By Date", value=pd.to_datetime(nbd_default).date()
                                     if nbd_default and pd.notna(nbd_default) else None)
            except Exception:
                nbd = st.date_input("Need By Date", value=None)
        with c4:
            bd_default = existing.get("Bid Date") if mode == "edit" else date.today()
            try:
                bd = st.date_input("Bid Date", value=pd.to_datetime(bd_default).date()
                                     if bd_default and pd.notna(bd_default) else date.today())
            except Exception:
                bd = st.date_input("Bid Date", value=date.today())

        # --- Allegati (solo in modalita' MODIFICA) ---
        if mode == "edit":
            st.markdown("---")
            st.markdown("##### 📎 Allegati")
            existing_files = list_attachments("BIDS", edit_id)
            if existing_files:
                for f in existing_files:
                    fc1, fc2, fc3 = st.columns([5, 1, 1])
                    with fc1:
                        st.markdown(f"📄 **{f.name}**  *({f.stat().st_size/1024:.0f} KB)*")
                    with fc2:
                        with open(f, "rb") as fh:
                            st.download_button("⬇", fh.read(), file_name=f.name,
                                                 key=f"bid_dl_{f.name}",
                                                 use_container_width=True)
                    with fc3:
                        if st.button("🗑", key=f"bid_del_{f.name}", use_container_width=True):
                            delete_attachment("BIDS", edit_id, f.name)
                            st.rerun()
            else:
                st.caption("Nessun allegato.")
            new_files = st.file_uploader("Aggiungi file (PDF, immagini, Excel, ...)",
                                            accept_multiple_files=True,
                                            key=f"bid_upload_{edit_id}")
            if new_files:
                for f in new_files:
                    save_attachment("BIDS", edit_id, f.name, f.getvalue())
                st.success(f"{len(new_files)} file caricati.")
                st.rerun()
            st.markdown("---")

        cb1, cb2, _ = st.columns([1, 1, 4])
        with cb1: save_clicked = st.button("💾 Salva", type="primary", use_container_width=True)
        with cb2: cancel_clicked = st.button("✖ Annulla", use_container_width=True)

        if save_clicked:
            if not client.strip() or not product.strip():
                st.error("Client e Product sono obbligatori.")
            else:
                values = {
                    "Client": client.strip(),
                    "Product": product.strip(),
                    "Subproduct": subproduct.strip() or None,
                    "Specifics": specifics.strip() or None,
                    "Packaging": packaging.strip() or None,
                    "Target Price": float(price),
                    "Currency": currency,
                    "Unit": unit,
                    "Volume (kg)": float(volume) if volume else None,
                    "Incoterm": incoterm.strip() or None,
                    "Origin Country": origin or None,
                    "Need By Date": nbd if nbd else None,
                    "Bid Date": bd if bd else None,
                    "Status": status,
                    "Notes": notes.strip() or None,
                }
                try:
                    if mode == "add":
                        nid = add_row(SHEET, values)
                        st.success(f"Bid aggiunto: {nid}")
                    else:
                        update_row(SHEET, edit_id, values)
                        st.success(f"Bid {edit_id} aggiornato.")
                    st.session_state["bid_mode"] = None
                    st.session_state["bid_edit_id"] = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")
        if cancel_clicked:
            st.session_state["bid_mode"] = None
            st.session_state["bid_edit_id"] = None
            st.rerun()

if mode == "delete" and edit_id:
    st.warning(f"Cancellare il bid **{edit_id}**?")
    cc1, cc2, _ = st.columns([1, 1, 4])
    with cc1:
        if st.button("🗑️ Sì, cancella", type="primary", use_container_width=True):
            delete_row(SHEET, edit_id)
            st.success(f"{edit_id} cancellato.")
            st.session_state["bid_mode"] = None
            st.session_state["bid_edit_id"] = None
            st.rerun()
    with cc2:
        if st.button("Annulla", use_container_width=True):
            st.session_state["bid_mode"] = None
            st.session_state["bid_edit_id"] = None
            st.rerun()
