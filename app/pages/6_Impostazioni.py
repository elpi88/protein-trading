"""Impostazioni - info DB, backup, gestione utenti (admin)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime
import streamlit as st

from lib.data import DB_FILE, BACKUP_DIR, make_backup, export_to_excel
from lib.db import DATABASE_URL
from lib.theme import apply_theme
from lib import auth

from lib.auth import require_login
require_login()


st.set_page_config(page_title="Impostazioni - Protein Trading",
                   page_icon="⚙️", layout="wide")
apply_theme()

st.markdown(
    '''
    <div class="page-title">Impostazioni</div>
    <div class="page-sub">Database, backup, gestione utenti.</div>
    ''',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# Database info
# ---------------------------------------------------------------------
st.markdown("### Database")
if DATABASE_URL:
    st.success("✅ Database: **PostgreSQL su Supabase** (cloud)")
    host = DATABASE_URL.split("@")[-1].split("/")[0] if "@" in DATABASE_URL else "Supabase"
    st.markdown(f"**Host:** `{host}`")
    c1, c2, c3 = st.columns(3)
    c1.metric("Tipo", "PostgreSQL")
    c2.metric("Provider", "Supabase")
    c3.metric("Stato", "Online ✅")
elif DB_FILE.exists():
    st.markdown(f"**Percorso:** `{DB_FILE}`")
    stat = DB_FILE.stat()
    size_kb = stat.st_size / 1024
    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    c1, c2, c3 = st.columns(3)
    c1.metric("Dimensione", f"{size_kb:.1f} KB")
    c2.metric("Ultima modifica", mtime)
    c3.metric("Stato", "OK")
else:
    st.error("File database non trovato. Esegui prima migrate_excel_to_sqlite.py")

st.markdown("---")

# ---------------------------------------------------------------------
# Backup e export
# ---------------------------------------------------------------------
st.markdown("### Backup ed export")
st.markdown(
    f"I backup del database vengono salvati in `{BACKUP_DIR}`. "
    "Ne mantengo automaticamente gli ultimi 20."
)

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("💾 Backup ora", type="primary", use_container_width=True):
        try:
            dest = make_backup()
            st.success(f"Backup creato: {dest.name if dest else '(DB non trovato)'}")
        except Exception as e:
            st.error(f"Errore: {e}")
with col2:
    if st.button("📥 Esporta in Excel", use_container_width=True):
        try:
            dest = export_to_excel()
            st.success(f"Export creato: {dest.name}")
            with open(dest, "rb") as f:
                st.download_button(
                    "⬇ Scarica .xlsx",
                    f.read(),
                    file_name=dest.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
        except Exception as e:
            st.error(f"Errore: {e}")
with col3:
    if st.button("🔄 Ricarica dati", use_container_width=True):
        st.cache_data.clear()
        st.success("Cache svuotata.")

st.markdown("##### Backup esistenti")
backups = sorted(BACKUP_DIR.glob("backup_*_protein_trading.db"), reverse=True)
if backups:
    for b in backups[:10]:
        size_kb = b.stat().st_size / 1024
        st.text(f"• {b.name}   ({size_kb:,.0f} KB)".replace(",", "'"))
    if len(backups) > 10:
        st.caption(f"... e altri {len(backups) - 10} backup piu vecchi")
else:
    st.info("Nessun backup ancora. Verra creato alla prima modifica.")

st.markdown("---")

# ---------------------------------------------------------------------
# Gestione utenti (solo admin)
# ---------------------------------------------------------------------
if auth.is_admin():
    st.markdown("### Gestione utenti")
    st.caption("Sezione riservata agli amministratori.")

    users = auth.list_users()
    if users:
        import pandas as pd
        df = pd.DataFrame(users)
        df["active"] = df["active"].map({1: "Sì", 0: "No"})
        df = df.rename(columns={
            "username": "Username", "role": "Ruolo",
            "created_at": "Creato il", "last_login": "Ultimo accesso",
            "active": "Attivo"
        })
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Nuovo utente
    with st.expander("➕ Crea nuovo utente"):
        with st.form("new_user", clear_on_submit=True):
            nu = st.text_input("Username")
            np1 = st.text_input("Password", type="password")
            np2 = st.text_input("Ripeti password", type="password")
            nrole = st.selectbox("Ruolo", ["user", "admin"])
            sub = st.form_submit_button("Crea utente", type="primary")
        if sub:
            if not nu or not np1:
                st.error("Compila tutti i campi.")
            elif len(np1) < 8:
                st.error("Password minimo 8 caratteri.")
            elif np1 != np2:
                st.error("Le password non coincidono.")
            elif auth.create_user(nu, np1, nrole):
                st.success(f"Utente '{nu}' creato.")
                st.rerun()
            else:
                st.error("Username gia esistente.")

    # Modifica utente
    with st.expander("✏️ Modifica utente (password / ruolo / stato)"):
        usernames = [u["username"] for u in users]
        sel = st.selectbox("Utente", usernames, key="edit_user_sel")
        c1, c2, c3 = st.columns(3)
        with c1:
            new_pwd = st.text_input("Nuova password (lascia vuoto per non cambiare)",
                                    type="password", key="edit_pwd")
        with c2:
            new_role = st.selectbox("Ruolo", ["user", "admin"], key="edit_role")
        with c3:
            new_active = st.checkbox("Attivo", value=True, key="edit_active")

        if st.button("Salva modifiche", type="primary"):
            pwd_arg = new_pwd if new_pwd else None
            if pwd_arg and len(pwd_arg) < 8:
                st.error("Password minimo 8 caratteri.")
            else:
                if auth.update_user(sel, password=pwd_arg,
                                     role=new_role, active=new_active):
                    st.success(f"Utente '{sel}' aggiornato.")
                    st.rerun()
                else:
                    st.error("Errore nell\'aggiornamento.")

    st.markdown("---")

# ---------------------------------------------------------------------
# Import Excel diretto
# ---------------------------------------------------------------------
st.markdown("### 📥 Import dati da Excel")
st.markdown(
    "Carica un file `.xlsx` con righe di **Fornitori** o **Clienti** "
    "e importale in blocco nel database."
)

import pandas as pd
from lib.data import read_sheet, add_row, next_id

import_type = st.radio("Tipo di dati da importare", ["Fornitori", "Clienti"], horizontal=True)
sheet_map  = {"Fornitori": "SUPPLIERS_CLEAN", "Clienti": "CLIENTS"}
id_col_map = {"Fornitori": "Supplier ID", "Clienti": "Client ID"}
SHEET_IMP  = sheet_map[import_type]
ID_COL     = id_col_map[import_type]

uploaded = st.file_uploader(
    "Carica file Excel (.xlsx)", type=["xlsx"],
    help="Il file deve avere una riga di intestazione. Le colonne non riconosciute vengono ignorate."
)

if uploaded:
    try:
        xl = pd.ExcelFile(uploaded)
        sheet_names = xl.sheet_names
        sel_sheet = st.selectbox("Foglio Excel da importare", sheet_names)
        raw = xl.parse(sel_sheet)
        raw.columns = raw.columns.astype(str).str.strip()

        from lib.db import SCHEMAS
        target_cols = SCHEMAS[SHEET_IMP]

        # Mappatura automatica colonne (case-insensitive)
        auto_map = {}
        raw_lower = {c.lower(): c for c in raw.columns}
        for tc in target_cols[1:]:  # salta ID
            if tc.lower() in raw_lower:
                auto_map[tc] = raw_lower[tc.lower()]

        st.markdown(f"**{len(raw)} righe trovate** nel foglio. "
                    f"Colonne riconosciute: **{len(auto_map)}/{len(target_cols)-1}**")

        # Mappatura manuale per colonne non trovate
        with st.expander("🔧 Mappatura colonne (opzionale)", expanded=len(auto_map) < 3):
            st.caption("Associa le colonne del tuo Excel alle colonne del database.")
            col_opts = ["(ignora)"] + list(raw.columns)
            manual_map = {}
            cols_grid = st.columns(2)
            for i, tc in enumerate(target_cols[1:]):
                default = auto_map.get(tc, "(ignora)")
                default_idx = col_opts.index(default) if default in col_opts else 0
                with cols_grid[i % 2]:
                    sel = st.selectbox(tc, col_opts, index=default_idx,
                                       key=f"map_{tc}")
                    if sel != "(ignora)":
                        manual_map[tc] = sel

        if not manual_map:
            st.warning("Mappa almeno una colonna per poter importare.")
        else:
            # Anteprima prime 5 righe
            preview_df = pd.DataFrame()
            for tc, xc in manual_map.items():
                preview_df[tc] = raw[xc].astype(str).replace("nan", "")
            st.markdown("**Anteprima (prime 5 righe):**")
            st.dataframe(preview_df.head(5), use_container_width=True, hide_index=True)

            skip_dupes = st.checkbox("Salta righe con Company Name già presente", value=True)
            existing = read_sheet(SHEET_IMP)

            if st.button(f"⬆️ Importa {len(raw)} righe in {import_type}", type="primary"):
                imported = 0
                skipped  = 0
                errors   = 0
                existing_names = set()
                if skip_dupes and not existing.empty and "Company Name" in existing.columns:
                    existing_names = set(existing["Company Name"].astype(str).str.lower())

                for _, row_raw in raw.iterrows():
                    try:
                        new_row = {ID_COL: next_id(SHEET_IMP)}
                        for tc, xc in manual_map.items():
                            val = row_raw.get(xc, "")
                            new_row[tc] = "" if str(val) == "nan" else str(val)

                        cname = new_row.get("Company Name", "").strip()
                        if not cname:
                            skipped += 1
                            continue
                        if skip_dupes and cname.lower() in existing_names:
                            skipped += 1
                            continue

                        add_row(SHEET_IMP, new_row)
                        existing_names.add(cname.lower())
                        imported += 1
                    except Exception:
                        errors += 1

                if imported:
                    st.success(f"✅ Importati **{imported}** record. "
                               f"Saltati: {skipped}. Errori: {errors}.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning(f"Nessun record importato. Saltati: {skipped}, Errori: {errors}.")
    except Exception as e:
        st.error(f"Errore nella lettura del file: {e}")

st.markdown("---")

# ---------------------------------------------------------------------
# Info app
# ---------------------------------------------------------------------
st.markdown("### App")
st.markdown(
    """
    - **Versione**: 2.0
    - **Tecnologia**: Streamlit + SQLite + bcrypt
    - **Sviluppato per**: Nicolas Colombo

    **Sicurezza**: password cifrate con bcrypt. Audit log automatico
    delle modifiche. Backup giornaliero del database.
    """
)
