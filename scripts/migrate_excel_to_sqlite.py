"""
Migrazione one-shot: Excel -> SQLite.

Legge Protein_Trading_ERP_FULL.xlsm e popola protein_trading.db
con i dati delle 6 tabelle business + lookup (proteine, paesi, valute, unita').

L'Excel NON viene modificato.
Lo script e' idempotente: ri-eseguirlo svuota le tabelle e re-importa.

Uso:
    python scripts/migrate_excel_to_sqlite.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Assicura che 'app/lib' sia importabile
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import openpyxl
import pandas as pd

from lib import db as DB


EXCEL_FILE = ROOT / "Protein_Trading_ERP_FULL.xlsm"


# ----------------------------------------------------------------------
def banner(text: str) -> None:
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def read_excel_sheet_raw(sheet: str) -> pd.DataFrame:
    """Legge un foglio Excel con i valori calcolati (data_only=True)."""
    df = pd.read_excel(EXCEL_FILE, sheet_name=sheet, engine="openpyxl")
    df = df.dropna(how="all")
    if len(df.columns) > 0:
        first = df.columns[0]
        df[first] = df[first].astype(str).replace("nan", "")
        df = df[df[first].str.strip() != ""]
    return df.reset_index(drop=True)


def import_business_table(sheet_excel: str) -> int:
    """Importa una tabella business (SUPPLIERS_CLEAN, OFFERS, etc.)."""
    table = DB.TABLE_NAMES[sheet_excel]
    columns = DB.SCHEMAS[sheet_excel]
    df = read_excel_sheet_raw(sheet_excel)

    # Allinea colonne al nostro schema (drop extra, aggiungi mancanti)
    for c in columns:
        if c not in df.columns:
            df[c] = None
    df = df[columns]

    # Tipi: prova a convertire le colonne numeriche
    for c in DB.NUMERIC_COLS.get(sheet_excel, set()):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Pulizia: NaN -> None per SQLite
    df = df.where(pd.notna(df), None)

    # Converti Timestamp/datetime in stringa (SQLite non li supporta nativamente)
    # e NaN/NaT/numpy types in None/python type.
    import numpy as np
    from datetime import datetime, date

    def _sanitize(v):
        # None resta None
        if v is None:
            return None
        # NaN / NaT
        try:
            if pd.isna(v):
                return None
        except (TypeError, ValueError):
            pass
        # Pandas Timestamp
        if isinstance(v, pd.Timestamp):
            try:
                if v.hour == 0 and v.minute == 0 and v.second == 0:
                    return v.strftime("%Y-%m-%d")
                return v.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                return str(v)
        # datetime / date nativi
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(v, date):
            return v.strftime("%Y-%m-%d")
        # Numpy scalars -> python native
        if isinstance(v, np.generic):
            return v.item()
        return v

    rows = [tuple(_sanitize(v) for v in r)
            for r in df.itertuples(index=False, name=None)]
    cols_sql = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join("?" for _ in columns)

    with DB.get_conn() as conn:
        conn.execute(f"DELETE FROM \"{table}\"")
        if rows:
            conn.executemany(
                f"INSERT INTO \"{table}\" ({cols_sql}) VALUES ({placeholders})",
                rows
            )
    return len(rows)


def import_protein_categories() -> int:
    """REFERENCE_LISTS, colonna A righe 4..N"""
    df = pd.read_excel(EXCEL_FILE, sheet_name="REFERENCE_LISTS",
                       engine="openpyxl", header=None)
    vals = df.iloc[3:, 0].dropna().astype(str).tolist()
    vals = [v.strip() for v in vals if v.strip()]
    with DB.get_conn() as conn:
        conn.execute("DELETE FROM protein_categories")
        for i, v in enumerate(vals):
            conn.execute(
                "INSERT OR IGNORE INTO protein_categories (name, sort_order) VALUES (?, ?)",
                (v, i)
            )
    return len(vals)


def import_countries() -> int:
    """REFERENCE_LISTS, colonna C righe 4..N"""
    df = pd.read_excel(EXCEL_FILE, sheet_name="REFERENCE_LISTS",
                       engine="openpyxl", header=None)
    vals = df.iloc[3:, 2].dropna().astype(str).tolist()
    vals = [v.strip() for v in vals if v.strip()]
    with DB.get_conn() as conn:
        conn.execute("DELETE FROM countries")
        for i, v in enumerate(vals):
            conn.execute(
                "INSERT OR IGNORE INTO countries (name, sort_order) VALUES (?, ?)",
                (v, i)
            )
    return len(vals)


def import_currencies() -> int:
    """CONVERSIONS A6:C25 -> currencies(code, rate_to_usd)"""
    df = pd.read_excel(EXCEL_FILE, sheet_name="CONVERSIONS",
                       engine="openpyxl", header=None)
    out = []
    for i in range(5, 25):
        code = df.iat[i, 0] if i < len(df) else None
        rate = df.iat[i, 2] if i < len(df) else None
        if pd.notna(code) and str(code).strip():
            try:
                rate_f = float(rate) if pd.notna(rate) else None
            except Exception:
                rate_f = None
            out.append((str(code).strip().upper(), rate_f))
    with DB.get_conn() as conn:
        conn.execute("DELETE FROM currencies")
        for i, (code, rate) in enumerate(out):
            conn.execute(
                "INSERT OR REPLACE INTO currencies (code, rate_to_usd, sort_order) "
                "VALUES (?, ?, ?)",
                (code, rate, i)
            )
    return len(out)


def import_units() -> int:
    """CONVERSIONS A30:C36 -> units(code, kg_factor)"""
    df = pd.read_excel(EXCEL_FILE, sheet_name="CONVERSIONS",
                       engine="openpyxl", header=None)
    out = []
    for i in range(29, 36):
        code = df.iat[i, 0] if i < len(df) else None
        factor = df.iat[i, 2] if i < len(df) else None
        if pd.notna(code) and str(code).strip():
            try:
                f = float(factor) if pd.notna(factor) else None
            except Exception:
                f = None
            out.append((str(code).strip().upper(), f))
    with DB.get_conn() as conn:
        conn.execute("DELETE FROM units")
        for i, (code, factor) in enumerate(out):
            conn.execute(
                "INSERT OR REPLACE INTO units (code, kg_factor, sort_order) "
                "VALUES (?, ?, ?)",
                (code, factor, i)
            )
    return len(out)


def import_audit_log_csv() -> int:
    """Importa audit_log.csv (se esiste) nella tabella audit_log."""
    csv_path = ROOT / "audit_log.csv"
    if not csv_path.exists():
        return 0
    df = pd.read_csv(csv_path)
    n = 0
    with DB.get_conn() as conn:
        for _, r in df.iterrows():
            conn.execute(
                "INSERT INTO audit_log (timestamp, user, action, sheet, row_id, details) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (str(r.get("timestamp", "")),
                 str(r.get("user", "")),
                 str(r.get("action", "")),
                 str(r.get("sheet", "")),
                 str(r.get("row_id", "")),
                 str(r.get("details", ""))[:500])
            )
            n += 1
    return n


# ----------------------------------------------------------------------

def recompute_derived_columns() -> tuple[int, int]:
    """Ricalcola Price USD/kg (OFFERS) e Target USD/kg (BIDS) usando FX/WT del DB."""
    with DB.get_conn() as conn:
        # OFFERS
        rows = conn.execute(
            'SELECT "Offer ID", "Price", "Currency", "Unit", "Product" FROM offers'
        ).fetchall()
        n_off = 0
        for r in rows:
            usd = DB.compute_usd_kg(r["Price"], r["Currency"], r["Unit"])
            mk = (r["Product"] or "")
            if usd is not None:
                mk = f"{r['Product'] or ''}|{usd:.4f}"
            conn.execute(
                'UPDATE offers SET "Price USD/kg" = ?, "Match Key" = ? WHERE "Offer ID" = ?',
                (usd, mk, r["Offer ID"])
            )
            n_off += 1
        # BIDS
        rows = conn.execute(
            'SELECT "Bid ID", "Target Price", "Currency", "Unit" FROM bids'
        ).fetchall()
        n_bid = 0
        for r in rows:
            usd = DB.compute_usd_kg(r["Target Price"], r["Currency"], r["Unit"])
            conn.execute(
                'UPDATE bids SET "Target USD/kg" = ? WHERE "Bid ID" = ?',
                (usd, r["Bid ID"])
            )
            n_bid += 1
    return n_off, n_bid

def main() -> None:
    banner("PROTEIN TRADING - Migrazione Excel -> SQLite")
    print(f"Excel sorgente: {EXCEL_FILE}")
    print(f"DB destinazione: {DB.DB_FILE}")

    if not EXCEL_FILE.exists():
        print("ERRORE: file Excel non trovato.")
        sys.exit(1)

    banner("1/3  Creazione schema DB")
    DB.init_db()
    print("  -> tabelle create / verificate")

    banner("2/3  Import dati business")
    counts = {}
    for sheet in DB.SCHEMAS:
        n = import_business_table(sheet)
        counts[sheet] = n
        print(f"  {sheet:25s} -> {n:5d} record importati")

    banner("3/3  Import lookup tables")
    n = import_protein_categories(); print(f"  protein_categories  -> {n:5d}")
    n = import_countries();          print(f"  countries           -> {n:5d}")
    n = import_currencies();         print(f"  currencies          -> {n:5d}")
    n = import_units();              print(f"  units               -> {n:5d}")
    n = import_audit_log_csv();      print(f"  audit_log (da CSV)  -> {n:5d}")

    banner("4/4  Ricalcolo colonne derivate (USD/kg)")
    n_off, n_bid = recompute_derived_columns()
    print(f"  offers  -> {n_off:5d} righe ricalcolate")
    print(f"  bids    -> {n_bid:5d} righe ricalcolate")

    banner("FATTO")
    total = sum(counts.values())
    print(f"Totale record business migrati: {total}")
    print(f"File DB: {DB.DB_FILE} ({DB.DB_FILE.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
