"""Impostazioni - info file, backup, refresh cache."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime
import streamlit as st

from lib.data import EXCEL_FILE, BACKUP_DIR, make_backup
from lib.theme import apply_theme

st.set_page_config(page_title="Impostazioni - Protein Trading", page_icon="⚙️", layout="wide")
apply_theme()

st.markdown(
    """
    <div class="page-title">Impostazioni</div>
    <div class="page-sub">Backup, ricarica dati e informazioni sul file.</div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# File info
# ---------------------------------------------------------------------
st.markdown("### File dati")
st.markdown(f"**Percorso:** `{EXCEL_FILE}`")
if EXCEL_FILE.exists():
    stat = EXCEL_FILE.stat()
    size_mb = stat.st_size / (1024 * 1024)
    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    c1, c2, c3 = st.columns(3)
    c1.metric("Dimensione", f"{size_mb:.2f} MB")
    c2.metric("Ultima modifica", mtime)
    c3.metric("Esiste", "Sì ✓")
else:
    st.error("File Excel non trovato.")

st.markdown("---")

# ---------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------
st.markdown("### Backup")
st.markdown(f"I backup vengono salvati in `{BACKUP_DIR}`. Ne mantengo automaticamente gli ultimi 20.")

col1, col2 = st.columns(2)
with col1:
    if st.button("💾 Crea backup ora", type="primary", use_container_width=True):
        try:
            dest = make_backup()
            st.success(f"Backup creato: {dest.name}")
        except Exception as e:
            st.error(f"Errore: {e}")
with col2:
    if st.button("🔄 Ricarica dati (forza)", use_container_width=True):
        st.cache_data.clear()
        st.success("Cache svuotata. I prossimi dati verranno letti freschi dall'Excel.")

st.markdown("##### Backup esistenti")
backups = sorted(BACKUP_DIR.glob("backup_*.xlsm"), reverse=True)
if backups:
    for b in backups[:10]:
        size_kb = b.stat().st_size / 1024
        st.text(f"• {b.name}   ({size_kb:,.0f} KB)".replace(",", "'"))
    if len(backups) > 10:
        st.caption(f"... e altri {len(backups) - 10} backup più vecchi")
else:
    st.info("Nessun backup ancora. Verranno creati automaticamente alla prima modifica.")

st.markdown("---")

# ---------------------------------------------------------------------
# Info app
# ---------------------------------------------------------------------
st.markdown("### App")
st.markdown(
    """
    - **Versione**: 1.0
    - **Tecnologia**: Streamlit (Python) + Excel come fonte di verità
    - **Sviluppato per**: Nicolas Colombo

    **Note di sicurezza**: l'app è interamente locale. Nessun dato viene inviato su internet.
    Le macro VBA del file Excel continuano a funzionare in parallelo.
    """
)
