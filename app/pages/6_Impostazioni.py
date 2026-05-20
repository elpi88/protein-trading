"""Impostazioni - info DB, backup, gestione utenti (admin)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime
import streamlit as st

from lib.data import DB_FILE, BACKUP_DIR, make_backup, export_to_excel
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
st.markdown(f"**Percorso:** `{DB_FILE}`")
if DB_FILE.exists():
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
