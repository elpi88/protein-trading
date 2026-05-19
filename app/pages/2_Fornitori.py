"""Gestione Fornitori - tabella + Aggiungi / Modifica / Cancella."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from lib.data import (
    read_sheet, add_row, update_row, delete_row, next_id,
    get_protein_categories, get_countries,
)
from lib.theme import apply_theme, PROTEIN_COLORS
try:
    from lib.pdf_export import supplier_card
    PDF_OK = True
except Exception:
    PDF_OK = False
    supplier_card = None

st.set_page_config(page_title="Fornitori - Protein Trading", page_icon="🏭", layout="wide")
apply_theme()

st.markdown(
    """
    <div class="page-title">Fornitori</div>
    <div class="page-sub">Anagrafica completa. Cerca, filtra, aggiungi e modifica.</div>
    """,
    unsafe_allow_html=True,
)

SHEET = "SUPPLIERS_CLEAN"
df = read_sheet(SHEET)

# -----------------------------------------------------------------
# Toolbar
# -----------------------------------------------------------------
left, mid, right = st.columns([3, 2, 1])
with left:
    q = st.text_input("Cerca per nome, contatto, paese, email...",
                      placeholder="Inizia a digitare per filtrare la lista",
                      label_visibility="collapsed")
with mid:
    cat_options = ["Tutte"] + sorted(set(get_protein_categories() +
                                          df.get("Protein Category", pd.Series()).dropna().astype(str).str.upper().unique().tolist()))
    cat_sel = st.selectbox("Categoria", cat_options, label_visibility="collapsed")
with right:
    if st.button("➕ Nuovo fornitore", use_container_width=True, type="primary"):
        st.session_state["sup_mode"] = "add"
        st.session_state["sup_edit_id"] = None

# -----------------------------------------------------------------
# Filtri applicati
# -----------------------------------------------------------------
view = df.copy()
if q:
    qq = q.lower()
    mask = view.apply(lambda r: qq in " ".join(str(v) for v in r.values).lower(), axis=1)
    view = view[mask]
if cat_sel != "Tutte" and "Protein Category" in view.columns:
    view = view[view["Protein Category"].astype(str).str.upper() == cat_sel.upper()]

st.caption(f"**{len(view):,}** fornitori".replace(",", "'") +
            (f" (filtrati su {len(df):,})".replace(",", "'") if len(view) != len(df) else ""))

# -----------------------------------------------------------------
# Tabella
# -----------------------------------------------------------------
display_cols = ["Supplier ID", "Company Name", "Protein Category", "Country",
                "Contact Person", "Email", "Phone"]
display_cols = [c for c in display_cols if c in view.columns]
view_display = view[display_cols].copy()

st.dataframe(
    view_display,
    use_container_width=True,
    hide_index=True,
    height=420,
    column_config={
        "Supplier ID": st.column_config.TextColumn("ID", width="small"),
        "Company Name": st.column_config.TextColumn("Nome azienda", width="large"),
        "Protein Category": st.column_config.TextColumn("Categoria", width="small"),
        "Country": st.column_config.TextColumn("Paese", width="small"),
        "Contact Person": st.column_config.TextColumn("Contatto"),
        "Email": st.column_config.TextColumn("Email"),
        "Phone": st.column_config.TextColumn("Telefono"),
    },
)

# -----------------------------------------------------------------
# Selezione per Modifica / Cancella
# -----------------------------------------------------------------
st.markdown("##### Azioni su un fornitore esistente")
col_id, col_b1, col_b2, col_b3 = st.columns([3, 1, 1, 1])
with col_id:
    sel_id = st.selectbox(
        "Seleziona ID fornitore",
        options=[""] + view["Supplier ID"].astype(str).tolist() if not view.empty else [""],
        label_visibility="collapsed",
        placeholder="Seleziona un fornitore...",
    )
with col_b1:
    if st.button("✏️ Modifica", use_container_width=True, disabled=not sel_id):
        st.session_state["sup_mode"] = "edit"
        st.session_state["sup_edit_id"] = sel_id
with col_b2:
    if st.button("🗑️ Cancella", use_container_width=True, disabled=not sel_id):
        st.session_state["sup_mode"] = "delete"
        st.session_state["sup_edit_id"] = sel_id
with col_b3:
    if sel_id and PDF_OK:
        row_sel = df[df["Supplier ID"].astype(str) == str(sel_id)]
        if not row_sel.empty:
            try:
                pdf_bytes = supplier_card(row_sel.iloc[0].to_dict())
                st.download_button("📄 PDF", pdf_bytes,
                                     file_name=f"Fornitore_{sel_id}.pdf",
                                     mime="application/pdf",
                                     use_container_width=True)
            except Exception as e:
                st.caption(f"PDF non disponibile: {e}")
    elif sel_id and not PDF_OK:
        st.caption("📄 PDF non disponibile (manca reportlab)")


# =====================================================================
# Form modale: Aggiungi / Modifica
# =====================================================================
mode = st.session_state.get("sup_mode")
edit_id = st.session_state.get("sup_edit_id")

if mode in ("add", "edit"):
    title = "Nuovo fornitore" if mode == "add" else f"Modifica {edit_id}"
    new_id = next_id(SHEET) if mode == "add" else edit_id

    with st.expander(f"📝 {title}", expanded=True):
        # Recupera valori esistenti se modifica
        existing = {}
        if mode == "edit" and edit_id:
            row = df[df["Supplier ID"].astype(str) == str(edit_id)]
            if not row.empty:
                existing = row.iloc[0].to_dict()

        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Supplier ID", value=new_id, disabled=True, key="sup_form_id")
            company = st.text_input("Company Name *", value=str(existing.get("Company Name", "") or ""))
            contact = st.text_input("Contact Person", value=str(existing.get("Contact Person", "") or ""))
            categories = get_protein_categories()
            cur_cat = str(existing.get("Protein Category", "") or "")
            if cur_cat and cur_cat not in categories:
                categories = [cur_cat] + categories
            cat_idx = categories.index(cur_cat) if cur_cat in categories else 0
            cat = st.selectbox("Protein Category *", categories, index=cat_idx if categories else 0)
            countries = get_countries()
            cur_country = str(existing.get("Country", "") or "")
            if cur_country and cur_country not in countries:
                countries = [cur_country] + countries
            country = st.selectbox("Country", [""] + countries,
                                    index=([""] + countries).index(cur_country) if cur_country in ([""] + countries) else 0)
            email = st.text_input("Email", value=str(existing.get("Email", "") or ""))
            phone = st.text_input("Phone", value=str(existing.get("Phone", "") or ""))

        with c2:
            website = st.text_input("Website", value=str(existing.get("Website", "") or ""))
            address = st.text_area("Address", value=str(existing.get("Address", "") or ""), height=70)
            products = st.text_area("Products", value=str(existing.get("Products", "") or ""), height=70)
            tax = st.text_input("Tax/VAT", value=str(existing.get("Tax/VAT", "") or ""))
            registration = st.text_input("Registration", value=str(existing.get("Registration", "") or ""))
            notes = st.text_area("Notes", value=str(existing.get("Notes", "") or ""), height=70)

        cb1, cb2, _ = st.columns([1, 1, 4])
        with cb1:
            save_clicked = st.button("💾 Salva", type="primary", use_container_width=True)
        with cb2:
            cancel_clicked = st.button("✖ Annulla", use_container_width=True)

        if save_clicked:
            if not company.strip():
                st.error("Company Name è obbligatorio.")
            else:
                values = {
                    "Company Name": company.strip(),
                    "Contact Person": contact.strip() or None,
                    "Protein Category": cat,
                    "Country": country or None,
                    "Email": email.strip() or None,
                    "Phone": phone.strip() or None,
                    "Website": website.strip() or None,
                    "Address": address.strip() or None,
                    "Products": products.strip() or None,
                    "Tax/VAT": tax.strip() or None,
                    "Registration": registration.strip() or None,
                    "Notes": notes.strip() or None,
                }
                try:
                    if mode == "add":
                        nid = add_row(SHEET, values)
                        st.success(f"Fornitore aggiunto: {nid}")
                    else:
                        ok = update_row(SHEET, edit_id, values)
                        if ok:
                            st.success(f"Fornitore {edit_id} aggiornato.")
                        else:
                            st.error(f"Fornitore {edit_id} non trovato.")
                    st.session_state["sup_mode"] = None
                    st.session_state["sup_edit_id"] = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

        if cancel_clicked:
            st.session_state["sup_mode"] = None
            st.session_state["sup_edit_id"] = None
            st.rerun()


# =====================================================================
# Conferma cancellazione
# =====================================================================
if mode == "delete" and edit_id:
    st.warning(f"Sei sicuro di voler cancellare **{edit_id}**? L'operazione non è annullabile.")
    cc1, cc2, _ = st.columns([1, 1, 4])
    with cc1:
        if st.button("🗑️ Sì, cancella", type="primary", use_container_width=True):
            try:
                if delete_row(SHEET, edit_id):
                    st.success(f"Fornitore {edit_id} cancellato.")
                else:
                    st.error(f"Fornitore {edit_id} non trovato.")
                st.session_state["sup_mode"] = None
                st.session_state["sup_edit_id"] = None
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")
    with cc2:
        if st.button("Annulla", use_container_width=True):
            st.session_state["sup_mode"] = None
            st.session_state["sup_edit_id"] = None
            st.rerun()
