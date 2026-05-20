"""
LAYER DI ACCESSO DATI - facade su lib/db.py (SQLite).

Mantiene la firma pubblica del vecchio data.py (Excel) per non
toccare le 13 pagine. Tutte le letture/scritture passano da db.py.

Il vecchio modulo Excel e' in data_excel_legacy.py (recuperabile in
caso serva ripristinare la versione precedente).
"""
from __future__ import annotations

from pathlib import Path

# Re-export di tutte le funzioni e classi pubbliche da db.py
from lib.db import (
    # Path / costanti
    APP_DIR, PROJECT_DIR, DB_FILE, BACKUP_DIR, ATTACH_DIR,
    # Schemi e mappe
    SCHEMAS, TABLE_NAMES, ID_PREFIX, NUMERIC_COLS,
    # Lettura
    read_sheet, clear_cache,
    # Backup
    make_backup,
    # IDs
    next_id,
    # CRUD
    add_row, update_row, delete_row,
    # Lookup
    get_protein_categories, get_countries, get_currencies, get_units,
    get_fx_table, get_wt_table, compute_usd_kg,
    # KPIs / matching
    get_kpis, get_matches, normalize_product,
    # Audit
    log_action, read_audit_log,
    # Attachments
    attachments_dir, list_attachments, save_attachment, delete_attachment,
    # Duplicati
    find_potential_duplicates, find_fuzzy_duplicates,
    merge_records, merge_records_concat,
    # Export
    export_to_excel,
    # DB connection (per script avanzati)
    get_conn, init_db,
)

# ----------------------------------------------------------------------
# Compat: costanti che le pagine importano
# ----------------------------------------------------------------------
# EXCEL_FILE -> path al file Excel originale (continua a esistere su disco,
# letto solo da export funzioni o pagina Impostazioni per riferimento)
EXCEL_FILE: Path = PROJECT_DIR / "Protein_Trading_ERP_FULL.xlsm"

# AUDIT_LOG -> path al CSV legacy (mantenuto per download in 13_Storico).
# Le NUOVE righe di audit pero' finiscono nel DB (tabella audit_log).
AUDIT_LOG: Path = PROJECT_DIR / "audit_log.csv"

# Inizializza il DB al primo import (crea tabelle se mancano).
init_db()
