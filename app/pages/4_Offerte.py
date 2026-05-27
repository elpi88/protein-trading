"""Gestione Offerte (OFFERS)."""
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

from lib.auth import require_login
require_login()


st.set_page_config(page_title="Offerte - Protein Trading", page_icon="📈", layout="wide")
apply_theme()

st.markdown(
    """
    <div class="page-title">Offerte ricevute dai fornitori</div>
    <div class="page-sub">Le colonne <b>Price USD/kg</b> e <b>Match Key</b> sono calcolate automaticamente in Excel.</div>
    """,
    unsafe_allow_html=True,
)

SHEET = "OFFERS"
df = read_sheet(SHEET)

left, mid, right = st.columns([3, 2, 1])
with left:
    q = st.text_input("Cerca", placeholder="Cerca fornitore, prodotto, paese, source...",
                      label_visibility="collapsed")
with mid:
    prod_opts = ["Tutti"] + sorted(df.get("Product", pd.Series()).dropna().astype(str).unique().tolist())
    prod_sel = st.selectbox("Prodotto", prod_opts, label_visibility="collapsed")
with right:
    if st.button("➕ Nuova offerta", use_container_width=True, type="primary"):
        st.session_state["off_mode"] = "add"
        st.session_state["off_edit_id"] = None

view = df.copy()
if q:
    qq = q.lower()
    view = view[view.apply(lambda r: qq in " ".join(str(v) for v in r.values).lower(), axis=1)]
if prod_sel != "Tutti" and "Product" in view.columns:
    view = view[view["Product"].astype(str) == prod_sel]

st.caption(f"**{len(view):,}** offerte".replace(",", "'") +
            (f" (filtrate su {len(df):,})".replace(",", "'") if len(view) != len(df) else ""))

display_cols = ["Offer ID", "Supplier", "Product", "Subproduct", "Price",
                "Currency", "Unit", "Price USD/kg", "Incoterm",
                "Country Destination", "Source"]
display_cols = [c for c in display_cols if c in view.columns]
st.dataframe(
    view[display_cols],
    use_container_width=True, hide_index=True, height=420,
    column_config={
        "Offer ID": st.column_config.TextColumn("ID", width="small"),
        "Price": st.column_config.NumberColumn("Prezzo", format="%.4f"),
        "Price USD/kg": st.column_config.NumberColumn("USD/kg", format="%.4f"),
    },
)

st.markdown("##### Azioni su un'offerta esistente")
col_id, col_b1, col_b2, col_b3 = st.columns([3, 1, 1, 1])
with col_id:
    sel_id = st.selectbox("ID offerta",
        options=[""] + view["Offer ID"].astype(str).tolist() if not view.empty else [""],
        label_visibility="collapsed", placeholder="Seleziona un'offerta...")
with col_b1:
    if st.button("✏️ Modifica", use_container_width=True, disabled=not sel_id):
        st.session_state["off_mode"] = "edit"; st.session_state["off_edit_id"] = sel_id
with col_b2:
    if st.button("🗑️ Cancella", use_container_width=True, disabled=not sel_id):
        st.session_state["off_mode"] = "delete"; st.session_state["off_edit_id"] = sel_id
with col_b3:
    if sel_id:
        try:
            from lib.pdf_generator import generate_offer_pdf
            row_data = df[df["Offer ID"].astype(str) == str(sel_id)]
            if not row_data.empty:
                pdf_bytes = generate_offer_pdf(row_data.iloc[0].to_dict())
                st.download_button(
                    "📄 PDF", data=pdf_bytes,
                    file_name=f"offer_{sel_id}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        except Exception as ex:
            st.caption(f"PDF err: {ex}")


mode = st.session_state.get("off_mode")
edit_id = st.session_state.get("off_edit_id")

if mode in ("add", "edit"):
    title = "Nuova offerta" if mode == "add" else f"Modifica {edit_id}"
    new_id = next_id(SHEET) if mode == "add" else edit_id
    existing = {}
    if mode == "edit" and edit_id:
        row = df[df["Offer ID"].astype(str) == str(edit_id)]
        if not row.empty:
            existing = row.iloc[0].to_dict()

    with st.expander(f"📝 {title}", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Offer ID", value=new_id, disabled=True)
            supplier = st.text_input("Supplier *", value=str(existing.get("Supplier", "") or ""))
            product = st.text_input("Product *", value=str(existing.get("Product", "") or ""))
            subproduct = st.text_input("Subproduct", value=str(existing.get("Subproduct", "") or ""))
            specifics = st.text_input("Specifics", value=str(existing.get("Specifics", "") or ""))
            packaging = st.text_input("Packaging", value=str(existing.get("Packaging", "") or ""))
            price_val = existing.get("Price") if existing.get("Price") is not None else 0.0
            try:
                price = st.number_input("Price *", value=float(price_val), step=0.01, format="%.4f")
            except Exception:
                price = st.number_input("Price *", value=0.0, step=0.01, format="%.4f")

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
            cur_country = str(existing.get("Country Destination", "") or "")
            if cur_country and cur_country not in countries:
                countries = [cur_country] + countries
            country_dest = st.selectbox("Country Destination", [""] + countries,
                index=([""] + countries).index(cur_country) if cur_country in ([""] + countries) else 0)
            source = st.selectbox("Source",
                ["", "EMAIL", "whatsapp", "alibaba", "phone", "trade show", "referral", "other"],
                index=0)
            notes = st.text_area("Notes", value=str(existing.get("Notes", "") or ""), height=70)

        c3, c4 = st.columns(2)
        with c3:
            lrd_default = existing.get("Load Ready Date") if mode == "edit" else None
            try:
                lrd = st.date_input("Load Ready Date", value=pd.to_datetime(lrd_default).date()
                                     if lrd_default and pd.notna(lrd_default) else None)
            except Exception:
                lrd = st.date_input("Load Ready Date", value=None)
        with c4:
            od_default = existing.get("Offer Date") if mode == "edit" else date.today()
            try:
                od = st.date_input("Offer Date", value=pd.to_datetime(od_default).date()
                                     if od_default and pd.notna(od_default) else date.today())
            except Exception:
                od = st.date_input("Offer Date", value=date.today())

        # --- Allegati (solo in modalita' MODIFICA, perche' servono un ID) ---
        if mode == "edit":
            st.markdown("---")
            st.markdown("##### 📎 Allegati")
            existing_files = list_attachments("OFFERS", edit_id)
            if existing_files:
                for f in existing_files:
                    fc1, fc2, fc3 = st.columns([5, 1, 1])
                    with fc1:
                        st.markdown(f"📄 **{f.name}**  *({f.stat().st_size/1024:.0f} KB)*")
                    with fc2:
                        with open(f, "rb") as fh:
                            st.download_button("⬇", fh.read(), file_name=f.name,
                                                 key=f"off_dl_{f.name}",
                                                 use_container_width=True)
                    with fc3:
                        if st.button("🗑", key=f"off_del_{f.name}", use_container_width=True):
                            delete_attachment("OFFERS", edit_id, f.name)
                            st.rerun()
            else:
                st.caption("Nessun allegato.")
            new_files = st.file_uploader("Aggiungi file (PDF, immagini, Excel, ...)",
                                            accept_multiple_files=True,
                                            key=f"off_upload_{edit_id}")
            if new_files:
                for f in new_files:
                    save_attachment("OFFERS", edit_id, f.name, f.getvalue())
                st.success(f"{len(new_files)} file caricati.")
                st.rerun()
            st.markdown("---")

        cb1, cb2, _ = st.columns([1, 1, 4])
        with cb1: save_clicked = st.button("💾 Salva", type="primary", use_container_width=True)
        with cb2: cancel_clicked = st.button("✖ Annulla", use_container_width=True)

        if save_clicked:
            if not supplier.strip() or not product.strip():
                st.error("Supplier e Product sono obbligatori.")
            else:
                values = {
                    "Supplier": supplier.strip(),
                    "Product": product.strip(),
                    "Subproduct": subproduct.strip() or None,
                    "Specifics": specifics.strip() or None,
                    "Packaging": packaging.strip() or None,
                    "Price": float(price),
                    "Currency": currency,
                    "Unit": unit,
                    "Incoterm": incoterm.strip() or None,
                    "Country Destination": country_dest or None,
                    "Load Ready Date": lrd if lrd else None,
                    "Offer Date": od if od else None,
                    "Source": source if source else None,
                    "Notes": notes.strip() or None,
                }
                try:
                    if mode == "add":
                        nid = add_row(SHEET, values)
                        st.success(f"Offerta aggiunta: {nid}")
                    else:
                        update_row(SHEET, edit_id, values)
                        st.success(f"Offerta {edit_id} aggiornata.")
                    st.session_state["off_mode"] = None
                    st.session_state["off_edit_id"] = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")
        if cancel_clicked:
            st.session_state["off_mode"] = None
            st.session_state["off_edit_id"] = None
            st.rerun()

if mode == "delete" and edit_id:
    st.warning(f"Cancellare l'offerta **{edit_id}**?")
    cc1, cc2, _ = st.columns([1, 1, 4])
    with cc1:
        if st.button("🗑️ Sì, cancella", type="primary", use_container_width=True):
            delete_row(SHEET, edit_id)
            st.success(f"{edit_id} cancellata.")
            st.session_state["off_mode"] = None
            st.session_state["off_edit_id"] = None
            st.rerun()
    with cc2:
        if st.button("Annulla", use_container_width=True):
            st.session_state["off_mode"] = None
            st.session_state["off_edit_id"] = None
            st.rerun()
