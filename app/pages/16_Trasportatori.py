"""Trasportatori — gestione per categoria (Gelo / Navi / Terra Europa)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from lib import auth
from lib.theme import apply_theme
from lib.db import get_conn, init_db

auth.require_login()
apply_theme()

st.markdown(
    '<div class="page-title">🚚 Trasportatori</div>'
    '<div class="page-sub">Gestione trasportatori divisi per categoria: Gelo · Navi · Terra Europa</div>',
    unsafe_allow_html=True,
)

CATEGORIES = ["Terra Europa", "Gelo", "Navi"]

# Inizializza DB (crea tabelle se non esistono)
init_db()


# -----------------------------------------------------------------------
# Funzioni DB
# -----------------------------------------------------------------------
def load_transporters() -> pd.DataFrame:
    with get_conn() as conn:
        cur = conn.execute("""
            SELECT id, "Company Name", "Category", "Country", "City",
                   "Address", "Phone", "Email", "VAT", "Notes"
            FROM transporters
            ORDER BY "Category", "Company Name"
        """)
        rows = cur.fetchall()
    if not rows:
        return pd.DataFrame(columns=["id", "Company Name", "Category", "Country",
                                      "City", "Address", "Phone", "Email", "VAT", "Notes"])
    return pd.DataFrame([dict(r) for r in rows])


def add_transporter(data: dict) -> int:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO transporters
               ("Company Name","Category","Country","City","Address","Phone","Email","VAT","Notes")
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (data["Company Name"], data["Category"], data.get("Country"),
             data.get("City"), data.get("Address"), data.get("Phone"),
             data.get("Email"), data.get("VAT"), data.get("Notes"))
        )


def update_transporter(tid: int, data: dict):
    with get_conn() as conn:
        conn.execute(
            """UPDATE transporters SET
               "Company Name"=?, "Category"=?, "Country"=?, "City"=?,
               "Address"=?, "Phone"=?, "Email"=?, "VAT"=?, "Notes"=?
               WHERE id=?""",
            (data["Company Name"], data["Category"], data.get("Country"),
             data.get("City"), data.get("Address"), data.get("Phone"),
             data.get("Email"), data.get("VAT"), data.get("Notes"), tid)
        )


def delete_transporter(tid: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM transporters WHERE id=?", (tid,))


# -----------------------------------------------------------------------
# Carica dati
# -----------------------------------------------------------------------
df = load_transporters()

# -----------------------------------------------------------------------
# Toolbar
# -----------------------------------------------------------------------
col_search, col_cat, col_add = st.columns([3, 2, 1])
with col_search:
    q = st.text_input("Cerca", placeholder="Cerca per nome, città, paese...",
                      label_visibility="collapsed")
with col_cat:
    cat_filter = st.selectbox("Categoria", ["Tutte"] + CATEGORIES,
                               label_visibility="collapsed")
with col_add:
    if st.button("➕ Nuovo", use_container_width=True, type="primary"):
        st.session_state["tr_mode"] = "add"
        st.session_state["tr_edit_id"] = None

# Filtra
view = df.copy()
if q:
    qq = q.lower()
    view = view[view.apply(lambda r: qq in " ".join(str(v) for v in r.values).lower(), axis=1)]
if cat_filter != "Tutte":
    view = view[view["Category"] == cat_filter]

st.caption(f"**{len(view):,}** trasportatori".replace(",", "'") +
           (f" (filtrati su {len(df):,})".replace(",", "'") if len(view) != len(df) else ""))

# -----------------------------------------------------------------------
# Tabelle per categoria
# -----------------------------------------------------------------------
if view.empty:
    st.info("Nessun trasportatore trovato.")
else:
    for cat in CATEGORIES:
        cat_df = view[view["Category"] == cat]
        if cat_df.empty:
            continue
        icons = {"Gelo": "❄️", "Navi": "🚢", "Terra Europa": "🚛"}
        st.markdown(f"### {icons.get(cat, '🚚')} {cat} ({len(cat_df)})")
        show_cols = ["Company Name", "Country", "City", "Phone", "Email", "Notes"]
        show_cols = [c for c in show_cols if c in cat_df.columns]
        st.dataframe(
            cat_df[show_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Company Name": st.column_config.TextColumn("Ragione sociale", width="large"),
                "Country": st.column_config.TextColumn("Paese", width="small"),
                "City": st.column_config.TextColumn("Città", width="small"),
                "Phone": st.column_config.TextColumn("Telefono"),
                "Email": st.column_config.TextColumn("Email"),
            }
        )

# -----------------------------------------------------------------------
# Azioni su trasportatore esistente
# -----------------------------------------------------------------------
st.markdown("##### Azioni su un trasportatore esistente")
col_id, col_b1, col_b2 = st.columns([3, 1, 1])
with col_id:
    tr_options = {f"{r['Company Name']} ({r['Category']})": r["id"]
                  for _, r in (view.iterrows() if not view.empty else df.iterrows())}
    sel_label = st.selectbox("Trasportatore",
                              options=[""] + list(tr_options.keys()),
                              label_visibility="collapsed",
                              placeholder="Seleziona un trasportatore...")
    sel_id = tr_options.get(sel_label)
with col_b1:
    if st.button("✏️ Modifica", use_container_width=True, disabled=not sel_id):
        st.session_state["tr_mode"] = "edit"
        st.session_state["tr_edit_id"] = sel_id
with col_b2:
    if st.button("🗑️ Cancella", use_container_width=True, disabled=not sel_id):
        st.session_state["tr_mode"] = "delete"
        st.session_state["tr_edit_id"] = sel_id

# -----------------------------------------------------------------------
# Form aggiunta / modifica
# -----------------------------------------------------------------------
mode = st.session_state.get("tr_mode")
edit_id = st.session_state.get("tr_edit_id")

if mode in ("add", "edit"):
    title = "Nuovo trasportatore" if mode == "add" else "Modifica trasportatore"
    existing = {}
    if mode == "edit" and edit_id:
        row = df[df["id"] == edit_id]
        if not row.empty:
            existing = row.iloc[0].to_dict()

    with st.expander(f"📝 {title}", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            company = st.text_input("Ragione sociale *",
                                    value=str(existing.get("Company Name", "") or ""))
            cur_cat = str(existing.get("Category", "Terra Europa") or "Terra Europa")
            cat_idx = CATEGORIES.index(cur_cat) if cur_cat in CATEGORIES else 0
            category = st.selectbox("Categoria *", CATEGORIES, index=cat_idx)
            country = st.text_input("Paese", value=str(existing.get("Country", "") or ""))
            city = st.text_input("Città", value=str(existing.get("City", "") or ""))
        with c2:
            address = st.text_input("Indirizzo", value=str(existing.get("Address", "") or ""))
            phone = st.text_input("Telefono", value=str(existing.get("Phone", "") or ""))
            email = st.text_input("Email", value=str(existing.get("Email", "") or ""))
            vat = st.text_input("P.IVA / VAT", value=str(existing.get("VAT", "") or ""))
        notes = st.text_area("Note", value=str(existing.get("Notes", "") or ""), height=70)

        cb1, cb2, _ = st.columns([1, 1, 4])
        with cb1:
            save_clicked = st.button("💾 Salva", type="primary", use_container_width=True)
        with cb2:
            cancel_clicked = st.button("✖ Annulla", use_container_width=True)

        if save_clicked:
            if not company.strip():
                st.error("La ragione sociale è obbligatoria.")
            else:
                data = {
                    "Company Name": company.strip(),
                    "Category": category,
                    "Country": country.strip() or None,
                    "City": city.strip() or None,
                    "Address": address.strip() or None,
                    "Phone": phone.strip() or None,
                    "Email": email.strip() or None,
                    "VAT": vat.strip() or None,
                    "Notes": notes.strip() or None,
                }
                try:
                    if mode == "add":
                        add_transporter(data)
                        st.success(f"Trasportatore '{company.strip()}' aggiunto.")
                    else:
                        update_transporter(int(edit_id), data)
                        st.success(f"Trasportatore aggiornato.")
                    st.session_state["tr_mode"] = None
                    st.session_state["tr_edit_id"] = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

        if cancel_clicked:
            st.session_state["tr_mode"] = None
            st.session_state["tr_edit_id"] = None
            st.rerun()

if mode == "delete" and edit_id:
    row = df[df["id"] == edit_id]
    name = row.iloc[0]["Company Name"] if not row.empty else str(edit_id)
    st.warning(f"Cancellare **{name}**?")
    cc1, cc2, _ = st.columns([1, 1, 4])
    with cc1:
        if st.button("🗑️ Sì, cancella", type="primary", use_container_width=True):
            delete_transporter(int(edit_id))
            st.success(f"{name} cancellato.")
            st.session_state["tr_mode"] = None
            st.session_state["tr_edit_id"] = None
            st.rerun()
    with cc2:
        if st.button("Annulla", use_container_width=True):
            st.session_state["tr_mode"] = None
            st.session_state["tr_edit_id"] = None
            st.rerun()
