"""
Migrazione dati da SQLite locale a PostgreSQL su Supabase.

COME USARLO:
1. Apri il file credenziali.env e assicurati che DATABASE_URL sia impostato
2. Esegui da terminale nella cartella del progetto:

   set DATABASE_URL=postgresql://postgres.voznbtdipnxvwvmojckh:TUAPASSWORD@aws-1-eu-central-1.pooler.supabase.com:6543/postgres
   python scripts/migrate_sqlite_to_supabase.py

Lo script:
- Crea tutte le tabelle su Supabase (se non esistono)
- Copia tutti i dati da SQLite a PostgreSQL
- E' IDEMPOTENTE: se eseguito due volte non duplica i dati
"""

import os
import sys
import sqlite3
from pathlib import Path

# --- Aggiungi la cartella app al path ---
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
APP_DIR = PROJECT_DIR / "app"
sys.path.insert(0, str(APP_DIR))

DB_FILE = PROJECT_DIR / "protein_trading.db"

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERRORE: la variabile DATABASE_URL non è impostata.")
    print("Esegui prima:")
    print('  set DATABASE_URL=postgresql://postgres.voznbtdipnxvwvmojckh:TUAPASSWORD@aws-1-eu-central-1.pooler.supabase.com:6543/postgres')
    sys.exit(1)

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERRORE: psycopg2 non installato.")
    print("Esegui: pip install psycopg2-binary")
    sys.exit(1)

# --- Definizione tabelle (stesso ordine di db.py) ---
TABLE_NAMES = {
    "SUPPLIERS_CLEAN": "suppliers_clean",
    "CLIENTS": "clients",
    "OFFERS": "offers",
    "BIDS": "bids",
    "SHIPMENTS": "shipments",
    "INVOICES": "invoices",
}

SCHEMAS = {
    "SUPPLIERS_CLEAN": [
        "Supplier ID", "Company Name", "Contact Person", "Protein Category",
        "Country", "Email", "Phone", "Website", "Address", "Products",
        "Tax/VAT", "Registration", "Notes",
    ],
    "CLIENTS": [
        "Client ID", "Company Name", "CONTACT PERSON", "PROTEIN CATEGORY",
        "ITEMS", "COUNTRY", "Email", "Phone", "Monthly Capacity", "Notes",
    ],
    "OFFERS": [
        "Offer ID", "Supplier", "Product", "Subproduct", "Specifics",
        "Packaging", "Price", "Currency", "Unit", "Price USD/kg", "Incoterm",
        "Country Destination", "Load Ready Date", "Offer Date", "Source",
        "Notes", "Match Key",
    ],
    "BIDS": [
        "Bid ID", "Client", "Product", "Subproduct", "Specifics", "Packaging",
        "Target Price", "Currency", "Unit", "Target USD/kg", "Volume (kg)",
        "Incoterm", "Origin Country", "Need By Date", "Bid Date", "Status",
        "Notes",
    ],
    "SHIPMENTS": [
        "Shipment ID", "Invoice ID", "Bid ID", "Client", "Product",
        "Quantity", "Unit", "Origin Port", "Destination Port",
        "Carrier/Vessel", "Container #", "Container Type", "Incoterm",
        "ETD", "ETA", "Days in Transit", "Status", "Tracking #", "Notes",
    ],
    "INVOICES": [
        "Invoice ID", "Date", "Bid ID", "Client", "Product",
        "Quantity", "Unit", "Unit Price", "Currency",
        "Subtotal", "Subtotal USD", "VAT %", "VAT Amount",
        "Total Invoice", "Total USD", "Payment Status",
        "Due Date", "Paid Date", "Notes",
    ],
}

NUMERIC_COLS = {
    "OFFERS": {"Price", "Price USD/kg"},
    "BIDS": {"Target Price", "Target USD/kg", "Volume (kg)"},
    "SHIPMENTS": {"Quantity", "Days in Transit"},
    "INVOICES": {"Quantity", "Unit Price", "Subtotal", "Subtotal USD",
                  "VAT %", "VAT Amount", "Total Invoice", "Total USD"},
}


def q(name: str) -> str:
    """Quota un nome colonna per evitare problemi con spazi e parole riservate."""
    return '"' + name.replace('"', '""') + '"'


def col_type_pg(sheet: str, col: str) -> str:
    if col in NUMERIC_COLS.get(sheet, set()):
        return "NUMERIC"
    return "TEXT"


def create_tables(pg_cur):
    print("Creazione tabelle su Supabase...")

    # Tabelle business
    for sheet, table in TABLE_NAMES.items():
        cols_def = []
        for i, c in enumerate(SCHEMAS[sheet]):
            pk = " PRIMARY KEY" if i == 0 else ""
            cols_def.append(f"{q(c)} {col_type_pg(sheet, c)}{pk}")
        sql = f'CREATE TABLE IF NOT EXISTS {q(table)} ({", ".join(cols_def)})'
        pg_cur.execute(sql)
        print(f"  tabella '{table}' OK")

    # Lookup tables
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS protein_categories (
            name TEXT PRIMARY KEY,
            sort_order INTEGER DEFAULT 0
        )
    """)
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS countries (
            name TEXT PRIMARY KEY,
            sort_order INTEGER DEFAULT 0
        )
    """)
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS currencies (
            code TEXT PRIMARY KEY,
            rate_to_usd NUMERIC,
            sort_order INTEGER DEFAULT 0
        )
    """)
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS units (
            code TEXT PRIMARY KEY,
            kg_factor NUMERIC,
            sort_order INTEGER DEFAULT 0
        )
    """)

    # Audit log
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            timestamp TEXT NOT NULL,
            "user" TEXT,
            action TEXT,
            sheet TEXT,
            row_id TEXT,
            details TEXT
        )
    """)

    # Utenti
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TEXT,
            last_login TEXT,
            active INTEGER DEFAULT 1
        )
    """)

    print("  tabelle di sistema OK")


def migrate_table(sqlite_conn, pg_cur, sheet: str, table: str):
    columns = SCHEMAS[sheet]
    id_col = columns[0]

    # Leggi tutti i dati da SQLite
    sqlite_cur = sqlite_conn.cursor()
    cols_sql = ", ".join(q(c) for c in columns)
    sqlite_cur.execute(f"SELECT {cols_sql} FROM {q(table)}")
    rows = sqlite_cur.fetchall()

    if not rows:
        print(f"  '{table}': vuota, skip")
        return 0

    # Inserisci su PostgreSQL con ON CONFLICT DO NOTHING (idempotente)
    placeholders = ", ".join(["%s"] * len(columns))
    col_names = ", ".join(q(c) for c in columns)
    pk_col = q(id_col)
    # psycopg2 interpreta % come formato: il % in "VAT %" va raddoppiato in %% nell'SQL
    # Strategia: sostituiamo %s con segnaposto, raddoppiamo i % rimasti, rimettiamo %s
    raw_sql = f"INSERT INTO {q(table)} ({col_names}) VALUES ({placeholders}) ON CONFLICT ({pk_col}) DO NOTHING"
    sql = raw_sql.replace("%s", "\x00PH\x00").replace("%", "%%").replace("\x00PH\x00", "%s")

    inserted = 0
    for row in rows:
        vals = list(row)
        pg_cur.execute(sql, vals)
        if pg_cur.rowcount > 0:
            inserted += 1

    return inserted


def migrate_lookup_table(sqlite_conn, pg_cur, table: str, pk_col: str):
    sqlite_cur = sqlite_conn.cursor()
    try:
        sqlite_cur.execute(f"SELECT * FROM {table}")
        rows = sqlite_cur.fetchall()
    except Exception:
        return 0

    if not rows:
        return 0

    cols = [desc[0] for desc in sqlite_cur.description]
    placeholders = ", ".join(["%s"] * len(cols))
    col_names = ", ".join(q(c) for c in cols)
    sql = (
        f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) "
        f'ON CONFLICT ({q(pk_col)}) DO NOTHING'
    )
    inserted = 0
    for row in rows:
        pg_cur.execute(sql, list(row))
        if pg_cur.rowcount > 0:
            inserted += 1
    return inserted


def migrate_users(sqlite_conn, pg_cur):
    sqlite_cur = sqlite_conn.cursor()
    try:
        sqlite_cur.execute("SELECT username, password_hash, role, created_at, last_login, active FROM users")
        rows = sqlite_cur.fetchall()
    except Exception:
        return 0

    inserted = 0
    for row in rows:
        pg_cur.execute("""
            INSERT INTO users (username, password_hash, role, created_at, last_login, active)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
        """, list(row))
        if pg_cur.rowcount > 0:
            inserted += 1
    return inserted


def main():
    print("=" * 60)
    print("MIGRAZIONE SQLite → Supabase PostgreSQL")
    print("=" * 60)

    if not DB_FILE.exists():
        print(f"ERRORE: file SQLite non trovato: {DB_FILE}")
        sys.exit(1)

    print(f"\nSorgente:    {DB_FILE}")
    print(f"Destinazione: Supabase ({DATABASE_URL[:50]}...)\n")

    # Connessione PostgreSQL
    print("Connessione a Supabase...")
    try:
        pg_conn = psycopg2.connect(DATABASE_URL)
        pg_cur = pg_conn.cursor()
        print("Connessione OK\n")
    except Exception as e:
        print(f"ERRORE connessione: {e}")
        sys.exit(1)

    # Connessione SQLite
    sqlite_conn = sqlite3.connect(str(DB_FILE))
    sqlite_conn.row_factory = sqlite3.Row

    try:
        # Crea tabelle
        create_tables(pg_cur)
        pg_conn.commit()

        # Migra tabelle business
        print("\nMigrazione dati...")
        totale = 0
        for sheet, table in TABLE_NAMES.items():
            n = migrate_table(sqlite_conn, pg_cur, sheet, table)
            print(f"  {table}: {n} righe inserite")
            totale += n
        pg_conn.commit()

        # Migra lookup tables
        print("\nMigrazione lookup tables...")
        for tbl, pk in [("protein_categories", "name"), ("countries", "name"),
                         ("currencies", "code"), ("units", "code")]:
            n = migrate_lookup_table(sqlite_conn, pg_cur, tbl, pk)
            print(f"  {tbl}: {n} righe inserite")
        pg_conn.commit()

        # Migra utenti
        print("\nMigrazione utenti...")
        n = migrate_users(sqlite_conn, pg_cur)
        print(f"  users: {n} utenti inseriti")
        pg_conn.commit()

        print(f"\n{'=' * 60}")
        print(f"MIGRAZIONE COMPLETATA - {totale} record totali migrati")
        print("=" * 60)

    except Exception as e:
        pg_conn.rollback()
        print(f"\nERRORE durante la migrazione: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        sqlite_conn.close()
        pg_cur.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
