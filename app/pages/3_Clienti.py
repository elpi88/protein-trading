"""Gestione Clienti."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from lib.data import (
    read_sheet, add_row, update_row, delete_row, next_id,
    get_protein_categories, get_countries,
)
from lib.theme import apply_theme

from lib.auth import require_login
require_login()

try:
    from lib.pdf_export import client_card
    PDF_OK = True
except Exception:
    PDF_OK = False
    client_card = None

st.set_page_config(page_title="Clienti - Protein Trading", page_icon="🛒", layout="wide")
apply_theme()

st.markdown(
    """
    <div class="page-title">Clienti</div>
    <div class="page-sub">Anagrafica clienti. Cerca, filtra, aggiungi e modifica.</div>
    """,
    unsafe_allow_html=True,
)

SHEET = "CLIENTS"
df = read_sheet(SHEET)

left, mid, right = st.columns([3, 2, 1])
with left:
    q = st.text_input("Cerca", placeholder="Cerca per nome, contatto, paese, email...",
                      label_visibility="collapsed")
with mid:
    cat_opts = ["Tutte"] + sorted(set(get_protein_categories() +
                df.get("PROTEIN CATEGORY", pd.Series()).dropna().astype(str).str.upper().unique().tolist()))
    cat_sel = st.selectbox("Categoria", cat_opts, label_visibility="collapsed")
with right:
    if st.button("➕ Nuovo cliente", use_container_width=True, type="primary"):
        st.session_state["cli_mode"] = "add"
        st.session_state["cli_edit_id"] = None

view = df.copy()
if q:
    qq = q.lower()
    view = view[view.apply(lambda r: qq in " ".join(str(v) for v in r.values).lower(), axis=1)]
if cat_sel != "Tutte" and "PROTEIN CATEGORY" in view.columns:
    view = view[view["PROTEIN CATEGORY"].astype(str).str.upper() == cat_sel.upper()]

st.caption(f"**{len(view):,}** clienti".replace(",", "'") +
            (f" (filtrati su {len(df):,})".replace(",", "'") if len(view) != len(df) else ""))

display_cols = ["Client ID", "Company Name", "PROTEIN CATEGORY", "COUNTRY",
                "CONTACT PERSON", "Email", "Phone", "Monthly Capacity"]
display_cols = [c for c in display_cols if c in view.columns]
st.dataframe(
    view[display_cols],
    use_container_width=True, hide_index=True, height=420,
    column_config={
        "Client ID": st.column_config.TextColumn("ID", width="small"),
        "Company Name": st.column_config.TextColumn("Nome azienda", width="large"),
        "PROTEIN CATEGORY": st.column_config.TextColumn("Categoria", width="small"),
        "COUNTRY": st.column_config.TextColumn("Paese", width="small"),
        "CONTACT PERSON": st.column_config.TextColumn("Contatto"),
        "Monthly Capacity": st.column_config.TextColumn("Capacità mensile"),
    },
)

st.markdown("##### Azioni su un cliente esistente")
col_id, col_b1, col_b2, col_b3 = st.columns([3, 1, 1, 1])
with col_id:
    sel_id = st.selectbox("ID cliente",
        options=[""] + view["Client ID"].astype(str).tolist() if not view.empty else [""],
        label_visibility="collapsed", placeholder="Seleziona un cliente...")
with col_b1:
    if st.button("✏️ Modifica", use_container_width=True, disabled=not sel_id):
        st.session_state["cli_mode"] = "edit"; st.session_state["cli_edit_id"] = sel_id
with col_b2:
    if st.button("🗑️ Cancella", use_container_width=True, disabled=not sel_id):
        st.session_state["cli_mode"] = "delete"; st.session_state["cli_edit_id"] = sel_id
with col_b3:
    if sel_id and PDF_OK:
        row_sel = df[df["Client ID"].astype(str) == str(sel_id)]
        if not row_sel.empty:
            try:
                pdf_bytes = client_card(row_sel.iloc[0].to_dict())
                st.download_button("📄 PDF", pdf_bytes,
                                     file_name=f"Cliente_{sel_id}.pdf",
                                     mime="application/pdf",
                                     use_container_width=True)
            except Exception as e:
                st.caption(f"PDF non disponibile: {e}")
    elif sel_id and not PDF_OK:
        st.caption("📄 PDF non disponibile (manca reportlab)")


mode = st.session_state.get("cli_mode")
edit_id = st.session_state.get("cli_edit_id")

if mode in ("add", "edit"):
    title = "Nuovo cliente" if mode == "add" else f"Modifica {edit_id}"
    new_id = next_id(SHEET) if mode == "add" else edit_id
    existing = {}
    if mode == "edit" and edit_id:
        row = df[df["Client ID"].astype(str) == str(edit_id)]
        if not row.empty:
            existing = row.iloc[0].to_dict()

    with st.expander(f"📝 {title}", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Client ID", value=new_id, disabled=True)
            company = st.text_input("Company Name *", value=str(existing.get("Company Name", "") or ""))
            contact = st.text_input("Contact Person", value=str(existing.get("CONTACT PERSON", "") or ""))
            categories = get_protein_categories()
            cur_cat = str(existing.get("PROTEIN CATEGORY", "") or "")
            if cur_cat and cur_cat not in categories:
                categories = [cur_cat] + categories
            cat_idx = categories.index(cur_cat) if cur_cat in categories else 0
            cat = st.selectbox("Protein Category *", categories, index=cat_idx if categories else 0)
            items = st.text_input("Items", value=str(existing.get("ITEMS", "") or ""))
        with c2:
            countries = get_countries()
            cur_country = str(existing.get("COUNTRY", "") or "")
            if cur_country and cur_country not in countries:
                countries = [cur_country] + countries
            country = st.selectbox("Country", [""] + countries,
                    index=([""] + countries).index(cur_country) if cur_country in ([""] + countries) else 0)
            email = st.text_input("Email", value=str(existing.get("Email", "") or ""))
            phone = st.text_input("Phone", value=str(existing.get("Phone", "") or ""))
            capacity = st.text_input("Monthly Capacity", value=str(existing.get("Monthly Capacity", "") or ""))
            notes = st.text_area("Notes", value=str(existing.get("Notes", "") or ""), height=85)

        cb1, cb2, _ = st.columns([1, 1, 4])
        with cb1: save_clicked = st.button("💾 Salva", type="primary", use_container_width=True)
        with cb2: cancel_clicked = st.button("✖ Annulla", use_container_width=True)

        if save_clicked:
            if not company.strip():
                st.error("Company Name è obbligatorio.")
            else:
                values = {
                    "Company Name": company.strip(),
                    "CONTACT PERSON": contact.strip() or None,
                    "PROTEIN CATEGORY": cat,
                    "ITEMS": items.strip() or None,
                    "COUNTRY": country or None,
                    "Email": email.strip() or None,
                    "Phone": phone.strip() or None,
                    "Monthly Capacity": capacity.strip() or None,
                    "Notes": notes.strip() or None,
                }
                try:
                    if mode == "add":
                        nid = add_row(SHEET, values)
                        st.success(f"Cliente aggiunto: {nid}")
                    else:
                        update_row(SHEET, edit_id, values)
                        st.success(f"Cliente {edit_id} aggiornato.")
                    st.session_state["cli_mode"] = None
                    st.session_state["cli_edit_id"] = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")
        if cancel_clicked:
            st.session_state["cli_mode"] = None
            st.session_state["cli_edit_id"] = None
            st.rerun()

if mode == "delete" and edit_id:
    st.warning(f"Cancellare **{edit_id}**?")
    cc1, cc2, _ = st.columns([1, 1, 4])
    with cc1:
        if st.button("🗑️ Sì, cancella", type="primary", use_container_width=True):
            try:
                delete_row(SHEET, edit_id)
                st.success(f"{edit_id} cancellato.")
                st.session_state["cli_mode"] = None
                st.session_state["cli_edit_id"] = None
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")
    with cc2:
        if st.button("Annulla", use_container_width=True):
            st.session_state["cli_mode"] = None
            st.session_state["cli_edit_id"] = None
            st.rerun()
