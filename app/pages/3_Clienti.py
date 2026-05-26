"""Gestione Clienti."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.db import get_conn, init_db
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

st.set_page_config(page_title="Clienti - Protein Trading", page_icon="\U0001f6d2", layout="wide")
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

PAYMENT_METHODS = [
    "",
    "100% CAD, 7 days before ETA",
    "100% prepayment",
    "30 days from invoice date, if credit is enough",
    "30% prepayment 2 weeks before loading, 70% downpayment 2 weeks before ETA",
    "LC",
]

left, mid, right = st.columns([3, 2, 1])
with left:
    q = st.text_input("Cerca", placeholder="Cerca per nome, contatto, paese, email...",
                      label_visibility="collapsed")
with mid:
    cat_opts = ["Tutte"] + sorted(set(get_protein_categories() +
                df.get("PROTEIN CATEGORY", pd.Series()).dropna().astype(str).str.upper().unique().tolist()))
    cat_sel = st.selectbox("Categoria", cat_opts, label_visibility="collapsed")
with right:
    if st.button("+ Nuovo cliente", use_container_width=True, type="primary"):
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
        "Monthly Capacity": st.column_config.TextColumn("Capacita mensile"),
    },
)

st.markdown("##### Azioni su un cliente esistente")
col_id, col_b1, col_b2, col_b3 = st.columns([3, 1, 1, 1])
with col_id:
    sel_id = st.selectbox("ID cliente",
        options=[""] + view["Client ID"].astype(str).tolist() if not view.empty else [""],
        label_visibility="collapsed", placeholder="Seleziona un cliente...")
with col_b1:
    if st.button("Modifica", use_container_width=True, disabled=not sel_id):
        st.session_state["cli_mode"] = "edit"
        st.session_state["cli_edit_id"] = sel_id
with col_b2:
    if st.button("Cancella", use_container_width=True, disabled=not sel_id):
        st.session_state["cli_mode"] = "delete"
        st.session_state["cli_edit_id"] = sel_id
with col_b3:
    if sel_id and PDF_OK:
        row_sel = df[df["Client ID"].astype(str) == str(sel_id)]
        if not row_sel.empty:
            try:
                pdf_bytes = client_card(row_sel.iloc[0].to_dict())
                st.download_button("PDF", pdf_bytes,
                                     file_name=f"Cliente_{sel_id}.pdf",
                                     mime="application/pdf",
                                     use_container_width=True)
            except Exception as e:
                st.caption(f"PDF non disponibile: {e}")
    elif sel_id and not PDF_OK:
        st.caption("PDF non disponibile (manca reportlab)")


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

    with st.expander(f"Modifica: {title}", expanded=True):
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
            notes = st.text_area("Notes", value=str(existing.get("Notes", "") or ""), height=60)

        ca, cb = st.columns(2)
        with ca:
            indirizzo = st.text_input("Indirizzo Scarico",
                                      value=str(existing.get("Indirizzo Scarico", "") or ""))
        with cb:
            cur_pay_m = str(existing.get("Metodo di Pagamento", "") or "")
            if cur_pay_m not in PAYMENT_METHODS:
                cur_pay_m = ""
            pay_method = st.selectbox(
                "Metodo di Pagamento",
                PAYMENT_METHODS,
                index=PAYMENT_METHODS.index(cur_pay_m),
                help="Seleziona il metodo di pagamento standard per questo cliente",
            )

        cb1, cb2, _ = st.columns([1, 1, 4])
        with cb1:
            save_clicked = st.button("Salva", type="primary", use_container_width=True)
        with cb2:
            cancel_clicked = st.button("Annulla", use_container_width=True)

        if save_clicked:
            if not company.strip():
                st.error("Company Name e obbligatorio.")
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
                    "Indirizzo Scarico": indirizzo.strip() or None,
                    "Metodo di Pagamento": pay_method or None,
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
        if st.button("Si, cancella", type="primary", use_container_width=True):
            try:
                delete_row(SHEET, edit_id)
                st.success(f"{edit_id} cancellato.")
                st.session_state["cli_mode"] = None
                st.session_state["cli_edit_id"] = None
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")
    with cc2:
        if st.button("Annulla", key="del_cancel", use_container_width=True):
            st.session_state["cli_mode"] = None
            st.session_state["cli_edit_id"] = None
            st.rerun()

# ===================================================================
# SEZIONE DESTINAZIONI DI SCARICO
# ===================================================================
st.markdown("---")
st.markdown("### Destinazioni di scarico")

init_db()


def load_destinations(company_name=None):
    with get_conn() as conn:
        cur = conn.execute("""
            SELECT id, "Cod. Destinazione", "Cod. Cliente", "Dest. Name",
                   "Address", "City", "Province", "Country",
                   "Phone", "Email", "VAT", "Notes"
            FROM client_destinations
            ORDER BY "Dest. Name"
        """)
        rows = cur.fetchall()
    if not rows:
        return pd.DataFrame()
    dest_df = pd.DataFrame([dict(r) for r in rows])
    if company_name:
        kw = company_name.strip().lower()[:15]
        mask = dest_df["Dest. Name"].fillna("").str.lower().str.contains(kw, na=False)
        return dest_df[mask]
    return dest_df


def add_destination(data):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO client_destinations
               ("Cod. Destinazione","Cod. Cliente","Dest. Name","Address","City",
                "Province","Country","Phone","Email","VAT","Notes")
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (data.get("Cod. Destinazione"), data.get("Cod. Cliente"),
             data.get("Dest. Name"), data.get("Address"), data.get("City"),
             data.get("Province"), data.get("Country"), data.get("Phone"),
             data.get("Email"), data.get("VAT"), data.get("Notes"))
        )


def delete_destination(did):
    with get_conn() as conn:
        conn.execute("DELETE FROM client_destinations WHERE id=?", (did,))


# Recupera nome del cliente selezionato
selected_company = None
if sel_id and not df.empty:
    row_sel2 = df[df["Client ID"].astype(str) == str(sel_id)]
    if not row_sel2.empty:
        selected_company = str(row_sel2.iloc[0].get("Company Name", "") or "")

col_dest_search, col_dest_add = st.columns([4, 1])
with col_dest_search:
    dest_q = st.text_input(
        "Cerca destinazione",
        placeholder="Cerca per nome, citta, paese...",
        label_visibility="collapsed",
        key="dest_search"
    )
with col_dest_add:
    if st.button("+ Nuova destinazione", use_container_width=True, key="btn_new_dest"):
        st.session_state["dest_mode"] = "add"

# Carica e filtra destinazioni
if dest_q:
    dest_df = load_destinations()
    qq2 = dest_q.lower()
    if not dest_df.empty:
        dest_df = dest_df[dest_df.apply(
            lambda r: qq2 in " ".join(str(v) for v in r.values).lower(), axis=1
        )]
elif selected_company:
    dest_df = load_destinations(selected_company)
    if dest_df.empty:
        dest_df = load_destinations()
        if not dest_df.empty:
            st.info(f"Nessuna destinazione trovata per **{selected_company}**. Mostro tutte le destinazioni.")
else:
    dest_df = load_destinations()

if selected_company and not dest_q:
    st.caption(f"Destinazioni per **{selected_company}** — {len(dest_df)} trovate. Usa la ricerca per cercare altre.")
else:
    st.caption(f"**{len(dest_df)}** destinazioni totali")

if not dest_df.empty:
    show_dest_cols = ["Dest. Name", "Address", "City", "Province", "Country", "Phone", "Email"]
    show_dest_cols = [c for c in show_dest_cols if c in dest_df.columns]
    st.dataframe(
        dest_df[show_dest_cols],
        use_container_width=True,
        hide_index=True,
        height=300,
        column_config={
            "Dest. Name": st.column_config.TextColumn("Destinazione", width="large"),
            "Address": st.column_config.TextColumn("Indirizzo", width="medium"),
            "City": st.column_config.TextColumn("Citta", width="small"),
            "Province": st.column_config.TextColumn("Prov.", width="small"),
            "Country": st.column_config.TextColumn("Paese", width="small"),
        }
    )

    with st.expander("Elimina una destinazione"):
        dest_options = {
            f"{r['Dest. Name']} - {r.get('City','') or ''} ({r.get('Country','') or ''})": r["id"]
            for _, r in dest_df.iterrows()
        }
        del_label = st.selectbox("Seleziona destinazione da eliminare",
                                  [""] + list(dest_options.keys()),
                                  key="dest_del_sel")
        del_did = dest_options.get(del_label)
        if del_did and st.button("Elimina", key="dest_del_btn", type="secondary"):
            delete_destination(int(del_did))
            st.success("Destinazione eliminata.")
            st.rerun()
else:
    st.info("Nessuna destinazione trovata.")

# Form nuova destinazione
if st.session_state.get("dest_mode") == "add":
    with st.expander("Nuova destinazione", expanded=True):
        da1, da2 = st.columns(2)
        with da1:
            d_name = st.text_input("Nome destinazione *", key="d_name")
            d_address = st.text_input("Indirizzo", key="d_address")
            d_city = st.text_input("Citta", key="d_city")
            d_province = st.text_input("Provincia", key="d_province")
        with da2:
            d_country = st.text_input("Paese", key="d_country")
            d_phone = st.text_input("Telefono", key="d_phone")
            d_email = st.text_input("Email", key="d_email")
            d_vat = st.text_input("P.IVA", key="d_vat")
        d_notes = st.text_input("Note", key="d_notes")

        dsave, dcancel, _ = st.columns([1, 1, 4])
        with dsave:
            if st.button("Salva destinazione", type="primary", use_container_width=True, key="d_save"):
                if not d_name.strip():
                    st.error("Il nome destinazione e obbligatorio.")
                else:
                    add_destination({
                        "Cod. Destinazione": None,
                        "Cod. Cliente": sel_id or None,
                        "Dest. Name": d_name.strip(),
                        "Address": d_address.strip() or None,
                        "City": d_city.strip() or None,
                        "Province": d_province.strip() or None,
                        "Country": d_country.strip() or None,
                        "Phone": d_phone.strip() or None,
                        "Email": d_email.strip() or None,
                        "VAT": d_vat.strip() or None,
                        "Notes": d_notes.strip() or None,
                    })
                    st.success(f"Destinazione aggiunta.")
                    st.session_state["dest_mode"] = None
                    st.rerun()
        with dcancel:
            if st.button("Annulla", key="d_cancel", use_container_width=True):
                st.session_state["dest_mode"] = None
                st.rerun()
