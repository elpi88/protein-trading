"""
Layer di accesso al database SQLite per Protein Trading.

Sostituisce la lettura/scrittura su Excel (vedi data.py legacy).
Espone le stesse funzioni di data.py per minimizzare l'impatto
sulle pagine dell'app.

File DB: ../protein_trading.db (accanto al progetto).
Backup: ../backups/ (copie del file .db, rotazione automatica).
"""
from __future__ import annotations

import re
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# ----------------------------------------------------------------------
# Percorsi
# ----------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = APP_DIR.parent
DB_FILE = PROJECT_DIR / "protein_trading.db"
BACKUP_DIR = PROJECT_DIR / "backups"
ATTACH_DIR = PROJECT_DIR / "attachments"
BACKUP_DIR.mkdir(exist_ok=True)
ATTACH_DIR.mkdir(exist_ok=True)


# ----------------------------------------------------------------------
# Schema dei "fogli" (mantenuto identico ai nomi Excel)
# Mappiamo "nome foglio" -> "nome tabella SQLite" e lista colonne
# ----------------------------------------------------------------------
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

ID_PREFIX = {
    "SUPPLIERS_CLEAN": "SUP",
    "CLIENTS": "CLI",
    "OFFERS": "OFF",
    "BIDS": "BID",
    "SHIPMENTS": "SHP",
    "INVOICES": "INV",
}

# Tipi consigliati per colonne numeriche (default tutto TEXT)
NUMERIC_COLS = {
    "OFFERS": {"Price", "Price USD/kg"},
    "BIDS": {"Target Price", "Target USD/kg", "Volume (kg)"},
    "SHIPMENTS": {"Quantity", "Days in Transit"},
    "INVOICES": {"Quantity", "Unit Price", "Subtotal", "Subtotal USD",
                  "VAT %", "VAT Amount", "Total Invoice", "Total USD"},
}


# ----------------------------------------------------------------------
# Connessione
# ----------------------------------------------------------------------
@contextmanager
def get_conn():
    """Apre connessione SQLite. Da usare con `with get_conn() as c:`."""
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # NB: lasciamo journal mode di default (DELETE).
    # WAL non funziona su OneDrive/mount di rete.
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _quote(name: str) -> str:
    """Restituisce un identificatore SQLite quotato (per nomi con spazi)."""
    return '"' + name.replace('"', '""') + '"'


def _col_type(sheet: str, col: str) -> str:
    """Tipo SQLite consigliato per una colonna."""
    if col in NUMERIC_COLS.get(sheet, set()):
        return "REAL"
    return "TEXT"


# ----------------------------------------------------------------------
# Inizializzazione schema
# ----------------------------------------------------------------------
def init_db() -> None:
    """Crea tutte le tabelle se non esistono. Idempotente."""
    with get_conn() as conn:
        # Tabelle business
        for sheet, table in TABLE_NAMES.items():
            cols_def = []
            for i, c in enumerate(SCHEMAS[sheet]):
                pk = " PRIMARY KEY" if i == 0 else ""
                cols_def.append(f"{_quote(c)} {_col_type(sheet, c)}{pk}")
            sql = f'CREATE TABLE IF NOT EXISTS {_quote(table)} ({", ".join(cols_def)})'
            conn.execute(sql)

        # Lookup
        conn.execute("""
            CREATE TABLE IF NOT EXISTS protein_categories (
                name TEXT PRIMARY KEY,
                sort_order INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS countries (
                name TEXT PRIMARY KEY,
                sort_order INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS currencies (
                code TEXT PRIMARY KEY,
                rate_to_usd REAL,
                sort_order INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS units (
                code TEXT PRIMARY KEY,
                kg_factor REAL,
                sort_order INTEGER DEFAULT 0
            )
        """)

        # Audit log
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user TEXT,
                action TEXT,
                sheet TEXT,
                row_id TEXT,
                details TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS ix_audit_ts ON audit_log(timestamp)")

        # Tabella utenti (Fase 3, pre-creata)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TEXT,
                last_login TEXT,
                active INTEGER DEFAULT 1
            )
        """)


# ----------------------------------------------------------------------
# Cache (compatibile con Streamlit; se non in Streamlit, no-op)
# ----------------------------------------------------------------------
try:
    import streamlit as st
    _cache = st.cache_data(show_spinner=False, ttl=5)
except Exception:
    def _cache(fn=None, **kw):
        if fn is None:
            return lambda f: f
        return fn


# ----------------------------------------------------------------------
# Lettura
# ----------------------------------------------------------------------
@_cache
def read_sheet(sheet_name: str) -> pd.DataFrame:
    """Legge una 'tabella' come DataFrame, con le colonne nello stesso ordine
    e con gli stessi nomi del foglio Excel originale."""
    if sheet_name not in TABLE_NAMES:
        # fallback: ritorna df vuoto
        return pd.DataFrame()
    table = TABLE_NAMES[sheet_name]
    columns = SCHEMAS[sheet_name]
    cols_sql = ", ".join(_quote(c) for c in columns)
    with get_conn() as conn:
        df = pd.read_sql_query(f"SELECT {cols_sql} FROM {_quote(table)}", conn)
    # tipi: pandas decide. ID resta stringa.
    if not df.empty:
        df[columns[0]] = df[columns[0]].astype(str)
    return df.reset_index(drop=True)


def clear_cache() -> None:
    """Reset cache letture (chiamato dopo ogni scrittura)."""
    try:
        read_sheet.clear()
    except Exception:
        pass


# ----------------------------------------------------------------------
# Backup
# ----------------------------------------------------------------------
def make_backup() -> Optional[Path]:
    """Copia di sicurezza del file .db. Tiene gli ultimi 20."""
    if not DB_FILE.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"backup_{ts}_protein_trading.db"
    shutil.copy(DB_FILE, dest)
    # rotazione
    backups = sorted(BACKUP_DIR.glob("backup_*_protein_trading.db"))
    for old in backups[:-20]:
        try:
            old.unlink()
        except Exception:
            pass
    return dest


# ----------------------------------------------------------------------
# ID generation
# ----------------------------------------------------------------------
def next_id(sheet_name: str) -> str:
    """Prossimo ID: prefix + (MAX numerico esistente + 1), zero-padded a 5."""
    prefix = ID_PREFIX[sheet_name]
    table = TABLE_NAMES[sheet_name]
    id_col = SCHEMAS[sheet_name][0]
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT {_quote(id_col)} FROM {_quote(table)}"
        ).fetchall()
    max_num = 0
    pat = re.compile(rf"{prefix}-?(\d+)", re.IGNORECASE)
    for r in rows:
        v = r[0] or ""
        m = pat.match(str(v))
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"{prefix}-{max_num + 1:05d}"


# ----------------------------------------------------------------------
# CRUD
# ----------------------------------------------------------------------
def add_row(sheet_name: str, values: dict) -> str:
    """Inserisce una nuova riga. Genera ID. Calcola USD/kg dove serve.
    Ritorna l'ID generato."""
    new_id = next_id(sheet_name)
    table = TABLE_NAMES[sheet_name]
    columns = SCHEMAS[sheet_name]
    id_col = columns[0]

    # Costruisci il dizionario completo
    row = {id_col: new_id}
    for c in columns[1:]:
        row[c] = values.get(c)

    # Calcola colonne derivate (USD/kg e Match Key)
    _compute_derived(sheet_name, row)

    make_backup()
    cols_sql = ", ".join(_quote(c) for c in columns)
    placeholders = ", ".join("?" for _ in columns)
    vals = [row.get(c) for c in columns]
    with get_conn() as conn:
        conn.execute(
            f"INSERT INTO {_quote(table)} ({cols_sql}) VALUES ({placeholders})",
            vals,
        )
    clear_cache()
    _log("ADD", sheet_name, new_id,
         str(values.get("Company Name") or values.get("Supplier") or values.get("Client") or "")[:200])
    return new_id


def update_row(sheet_name: str, row_id: str, values: dict) -> bool:
    """Aggiorna i campi della riga `row_id`. Ricalcola le derivate."""
    table = TABLE_NAMES[sheet_name]
    columns = SCHEMAS[sheet_name]
    id_col = columns[0]

    # Leggi riga corrente per fare il merge con i values
    with get_conn() as conn:
        cur = conn.execute(
            f"SELECT * FROM {_quote(table)} WHERE {_quote(id_col)} = ?",
            (row_id,),
        )
        existing = cur.fetchone()
    if existing is None:
        return False
    row = {c: existing[c] for c in existing.keys()}
    for c in columns[1:]:
        if c in values:
            row[c] = values.get(c)

    _compute_derived(sheet_name, row)

    make_backup()
    set_sql = ", ".join(f"{_quote(c)} = ?" for c in columns[1:])
    vals = [row.get(c) for c in columns[1:]] + [row_id]
    with get_conn() as conn:
        conn.execute(
            f"UPDATE {_quote(table)} SET {set_sql} WHERE {_quote(id_col)} = ?",
            vals,
        )
    clear_cache()
    _log("UPDATE", sheet_name, row_id,
         str(values.get("Company Name") or values.get("Supplier") or values.get("Client") or "")[:200])
    return True


def delete_row(sheet_name: str, row_id: str) -> bool:
    """Cancella riga (delete fisico)."""
    table = TABLE_NAMES[sheet_name]
    id_col = SCHEMAS[sheet_name][0]
    make_backup()
    with get_conn() as conn:
        cur = conn.execute(
            f"DELETE FROM {_quote(table)} WHERE {_quote(id_col)} = ?",
            (row_id,),
        )
        deleted = cur.rowcount > 0
    clear_cache()
    if deleted:
        _log("DELETE", sheet_name, row_id, "")
    return deleted


# ----------------------------------------------------------------------
# Calcolo colonne derivate (Price USD/kg, Target USD/kg, Match Key)
# ----------------------------------------------------------------------
def _compute_derived(sheet_name: str, row: dict) -> None:
    """Aggiorna in-place le colonne calcolate."""
    if sheet_name == "OFFERS":
        usd = compute_usd_kg(row.get("Price"), row.get("Currency"), row.get("Unit"))
        if usd is not None:
            row["Price USD/kg"] = usd
        # Match Key = "<Product>|<usd_kg con 4 decimali>"
        try:
            prod = row.get("Product") or ""
            mk_val = row.get("Price USD/kg")
            row["Match Key"] = f"{prod}|{float(mk_val):.4f}" if mk_val is not None else prod
        except Exception:
            row["Match Key"] = row.get("Product") or ""
    elif sheet_name == "BIDS":
        usd = compute_usd_kg(row.get("Target Price"), row.get("Currency"), row.get("Unit"))
        if usd is not None:
            row["Target USD/kg"] = usd


# ======================================================================
# Lookup (protein categories, countries, currencies, units)
# ======================================================================
@_cache
def get_protein_categories() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT name FROM protein_categories ORDER BY sort_order, name"
        ).fetchall()
    out = [r[0] for r in rows if r[0]]
    if not out:
        return ["FISH", "PORK", "BEEF", "POULTRY", "LAMB",
                "TRADER", "POTATOES", "OTHER", "UNCLASSIFIED"]
    return out


@_cache
def get_countries() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT name FROM countries ORDER BY sort_order, name"
        ).fetchall()
    out = [r[0] for r in rows if r[0]]
    if not out:
        return ["Switzerland", "Italy", "Germany", "Other"]
    return out


@_cache
def get_currencies() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT code FROM currencies ORDER BY sort_order, code"
        ).fetchall()
    out = [r[0] for r in rows if r[0]]
    if not out:
        return ["USD", "EUR", "CHF", "GBP", "CNY"]
    return out


@_cache
def get_units() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT code FROM units ORDER BY sort_order, code"
        ).fetchall()
    out = [r[0] for r in rows if r[0]]
    if not out:
        return ["KG", "LB", "MT"]
    return out


@_cache
def get_fx_table() -> dict[str, float]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT code, rate_to_usd FROM currencies WHERE rate_to_usd IS NOT NULL"
        ).fetchall()
    out = {str(r[0]).strip().upper(): float(r[1]) for r in rows if r[0] and r[1] is not None}
    if not out:
        out = {"USD": 1.0}
    return out


@_cache
def get_wt_table() -> dict[str, float]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT code, kg_factor FROM units WHERE kg_factor IS NOT NULL"
        ).fetchall()
    out = {str(r[0]).strip().upper(): float(r[1]) for r in rows if r[0] and r[1] is not None}
    if not out:
        out = {"KG": 1.0, "LB": 0.453592, "MT": 1000.0}
    return out


def compute_usd_kg(price, currency, unit) -> Optional[float]:
    """price * FX[currency] / WT[unit]"""
    try:
        p = float(price)
        if p <= 0:
            return None
        fx = get_fx_table().get(str(currency).strip().upper())
        wt = get_wt_table().get(str(unit).strip().upper())
        if not fx or not wt:
            return None
        return p * fx / wt
    except Exception:
        return None


# ======================================================================
# KPIs e matching
# ======================================================================
def get_kpis() -> dict:
    """Numeri per la dashboard / home."""
    with get_conn() as conn:
        n_sup = conn.execute('SELECT COUNT(*) FROM suppliers_clean').fetchone()[0]
        n_cli = conn.execute('SELECT COUNT(*) FROM clients').fetchone()[0]
        n_off = conn.execute('SELECT COUNT(*) FROM offers').fetchone()[0]
        n_bid = conn.execute('SELECT COUNT(*) FROM bids').fetchone()[0]
        n_open = conn.execute(
            'SELECT COUNT(*) FROM bids WHERE UPPER(COALESCE("Status",\'\')) = \'OPEN\''
        ).fetchone()[0]
    out = {
        "n_suppliers": n_sup,
        "n_clients": n_cli,
        "n_offers": n_off,
        "n_bids": n_bid,
        "n_bids_open": n_open,
    }
    # Pipeline USD = sum(Target USD/kg * Volume) per bid OPEN
    try:
        b = read_sheet("BIDS")
        b_open = b[b["Status"].astype(str).str.upper() == "OPEN"].copy()
        b_open["Target USD/kg"] = pd.to_numeric(b_open["Target USD/kg"], errors="coerce")
        b_open["Volume (kg)"] = pd.to_numeric(b_open["Volume (kg)"], errors="coerce")
        out["pipeline_usd"] = float((b_open["Target USD/kg"] * b_open["Volume (kg)"]).sum(skipna=True))
    except Exception:
        out["pipeline_usd"] = 0.0
    return out


def normalize_product(s) -> str:
    if not s or pd.isna(s):
        return ""
    return " ".join(str(s).upper().split())


def _ensure_usd_kg(df: pd.DataFrame, price_col: str, usd_kg_col: str) -> pd.DataFrame:
    df = df.copy()
    df[usd_kg_col] = pd.to_numeric(df.get(usd_kg_col), errors="coerce")
    miss = df[usd_kg_col].isna()
    if miss.any() and price_col in df.columns:
        df.loc[miss, usd_kg_col] = df.loc[miss].apply(
            lambda r: compute_usd_kg(r.get(price_col), r.get("Currency"), r.get("Unit")),
            axis=1
        )
    return df


def get_matches(open_bids_only: bool = True) -> pd.DataFrame:
    offers = read_sheet("OFFERS")
    bids = read_sheet("BIDS")
    if offers.empty or bids.empty:
        return pd.DataFrame()

    offers = _ensure_usd_kg(offers, "Price", "Price USD/kg")
    bids = _ensure_usd_kg(bids, "Target Price", "Target USD/kg")

    if open_bids_only and "Status" in bids.columns:
        bids = bids[bids["Status"].astype(str).str.upper() == "OPEN"].copy()

    offers["_pkey"] = offers["Product"].apply(normalize_product)
    bids["_pkey"] = bids["Product"].apply(normalize_product)

    merged = bids.merge(offers, on="_pkey", how="inner",
                         suffixes=(" (bid)", " (offer)"))
    if merged.empty:
        return pd.DataFrame()

    merged["Margin USD/kg"] = (
        pd.to_numeric(merged["Target USD/kg"], errors="coerce")
        - pd.to_numeric(merged["Price USD/kg"], errors="coerce")
    )
    merged["Volume (kg)"] = pd.to_numeric(merged["Volume (kg)"], errors="coerce").fillna(0)
    merged["Margin USD"] = merged["Margin USD/kg"] * merged["Volume (kg)"]

    cols = [
        "Bid ID", "Client", "Offer ID", "Supplier",
        "Product (bid)", "Subproduct (bid)", "Subproduct (offer)",
        "Target USD/kg", "Price USD/kg", "Margin USD/kg",
        "Volume (kg)", "Margin USD",
        "Status", "Need By Date", "Offer Date",
    ]
    cols = [c for c in cols if c in merged.columns]
    return merged[cols].sort_values("Margin USD/kg", ascending=False,
                                     na_position="last").reset_index(drop=True)


# ======================================================================
# Audit log (in tabella, non piu' CSV)
# ======================================================================
def _log(action: str, sheet: str, row_id: str = "", details: str = "") -> None:
    user = "system"
    try:
        import streamlit as st
        user = st.session_state.get("user", "system")
    except Exception:
        pass
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (timestamp, user, action, sheet, row_id, details) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             user, action, sheet, row_id, (details or "")[:500])
        )


def log_action(action: str, sheet: str, row_id: str = "", details: str = "") -> None:
    """Wrapper pubblico (compat con data.py)."""
    _log(action, sheet, row_id, details)


def read_audit_log(limit: int = 500) -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT timestamp, user, action, sheet, row_id, details "
            "FROM audit_log ORDER BY id DESC LIMIT ?",
            conn, params=(limit,)
        )
    return df


# ======================================================================
# Attachments (file fisici, NON in DB - resta uguale a data.py)
# ======================================================================
def attachments_dir(sheet: str, row_id: str) -> Path:
    d = ATTACH_DIR / sheet / row_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_attachments(sheet: str, row_id: str) -> list[Path]:
    d = ATTACH_DIR / sheet / row_id
    if not d.exists():
        return []
    return sorted([p for p in d.iterdir() if p.is_file()])


def save_attachment(sheet: str, row_id: str, filename: str, content: bytes) -> Path:
    safe = "".join(c for c in filename if c.isalnum() or c in "._- ()[]").strip()
    if not safe:
        safe = "file"
    d = attachments_dir(sheet, row_id)
    dest = d / safe
    if dest.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = d / f"{dest.stem}_{ts}{dest.suffix}"
    dest.write_bytes(content)
    return dest


def delete_attachment(sheet: str, row_id: str, filename: str) -> bool:
    p = ATTACH_DIR / sheet / row_id / filename
    if p.exists() and p.is_file():
        p.unlink()
        return True
    return False


# ======================================================================
# Duplicati (esatti + fuzzy) - portati direttamente da data.py
# ======================================================================
from difflib import SequenceMatcher

_LEGAL_SUFFIXES = {
    "srl", "s.r.l", "s.r.l.", "spa", "s.p.a", "s.p.a.", "sa", "s.a", "s.a.",
    "ag", "gmbh", "g.m.b.h", "ltd", "ltd.", "limited", "inc", "inc.",
    "llc", "l.l.c", "l.l.c.", "co", "co.", "corp", "corp.", "corporation",
    "company", "trading", "trade", "international", "intl", "group",
    "holding", "holdings", "bv", "b.v", "b.v.", "nv", "n.v", "n.v.",
    "kg", "ohg", "se", "plc", "p.l.c",
}


def _norm_company(s) -> str:
    if not s or pd.isna(s):
        return ""
    txt = str(s).lower().replace(".", "")
    txt = re.sub(r"[^a-z0-9\s]", " ", txt)
    tokens = [t for t in txt.split() if t and t not in _LEGAL_SUFFIXES]
    return " ".join(tokens)


def find_potential_duplicates(sheet: str) -> pd.DataFrame:
    df = read_sheet(sheet)
    if df.empty or "Company Name" not in df.columns:
        return pd.DataFrame()
    id_col = df.columns[0]

    def norm(s):
        if not s or pd.isna(s): return ""
        return "".join(c.lower() for c in str(s) if c.isalnum())

    df = df.copy()
    df["_norm"] = df["Company Name"].apply(norm)
    df = df[df["_norm"] != ""]
    grp = df.groupby("_norm").filter(lambda g: len(g) >= 2)
    if grp.empty:
        return pd.DataFrame()
    pairs = []
    for _, g in grp.groupby("_norm"):
        rows = g.to_dict("records")
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                pairs.append({
                    "Keep candidate": rows[i][id_col],
                    "Duplicate candidate": rows[j][id_col],
                    "Name (keep)": rows[i]["Company Name"],
                    "Name (dup)": rows[j]["Company Name"],
                })
    return pd.DataFrame(pairs)


def find_fuzzy_duplicates(sheet: str, threshold: float = 0.85) -> pd.DataFrame:
    df = read_sheet(sheet)
    if df.empty or "Company Name" not in df.columns:
        return pd.DataFrame()
    id_col = df.columns[0]
    items = []
    for _, r in df.iterrows():
        nid = str(r[id_col])
        name = str(r["Company Name"]) if pd.notna(r["Company Name"]) else ""
        if not name.strip():
            continue
        items.append((nid, name, _norm_company(name)))
    pairs = []
    n = len(items)
    for i in range(n):
        id_a, name_a, norm_a = items[i]
        if not norm_a:
            continue
        for j in range(i + 1, n):
            id_b, name_b, norm_b = items[j]
            if not norm_b:
                continue
            sim = SequenceMatcher(None, norm_a, norm_b).ratio()
            if sim >= threshold:
                pairs.append({
                    "ID 1": id_a, "Nome 1": name_a,
                    "ID 2": id_b, "Nome 2": name_b,
                    "Similarità %": round(sim * 100, 1),
                })
    if not pairs:
        return pd.DataFrame()
    return pd.DataFrame(pairs).sort_values("Similarità %", ascending=False).reset_index(drop=True)


# ======================================================================
# Merge record (concat values + aggiorna riferimenti)
# ======================================================================
def _concat_values(v1, v2, sep: str = "; ") -> Optional[str]:
    def is_empty(x):
        return x is None or (isinstance(x, float) and pd.isna(x)) or \
               (isinstance(x, str) and not x.strip())
    if is_empty(v1) and is_empty(v2):
        return None
    if is_empty(v1):
        return str(v2).strip()
    if is_empty(v2):
        return str(v1).strip()
    s1, s2 = str(v1).strip(), str(v2).strip()
    if s1.lower() == s2.lower():
        return s1
    parts1 = [p.strip() for p in s1.split(sep) if p.strip()]
    parts2 = [p.strip() for p in s2.split(sep) if p.strip()]
    seen, out = set(), []
    for p in parts1 + parts2:
        if p.lower() not in seen:
            seen.add(p.lower()); out.append(p)
    return sep.join(out)


def merge_records_concat(sheet: str, keep_id: str, drop_id: str) -> dict:
    """Fonde drop_id dentro keep_id concatenando i campi (mantiene Company Name del keep).
       Aggiorna i riferimenti per nome in OFFERS/BIDS/SHIPMENTS/INVOICES."""
    table = TABLE_NAMES[sheet]
    columns = SCHEMAS[sheet]
    id_col = columns[0]

    with get_conn() as conn:
        keep = conn.execute(
            f"SELECT * FROM {_quote(table)} WHERE {_quote(id_col)} = ?", (keep_id,)
        ).fetchone()
        drop = conn.execute(
            f"SELECT * FROM {_quote(table)} WHERE {_quote(id_col)} = ?", (drop_id,)
        ).fetchone()
        if keep is None or drop is None:
            return {"ok": False, "error": "ID non trovato"}

        old_name = str(drop["Company Name"] or "")
        keep_name = str(keep["Company Name"] or "")

        merged_row = {c: keep[c] for c in keep.keys()}
        fields_merged = []
        for c in columns[2:]:  # skip ID e Company Name
            merged_val = _concat_values(keep[c], drop[c])
            if merged_val != keep[c]:
                merged_row[c] = merged_val
                fields_merged.append(c)

        make_backup()
        # update keep
        set_sql = ", ".join(f"{_quote(c)} = ?" for c in columns[1:])
        vals = [merged_row.get(c) for c in columns[1:]] + [keep_id]
        conn.execute(
            f"UPDATE {_quote(table)} SET {set_sql} WHERE {_quote(id_col)} = ?", vals
        )
        # delete drop
        conn.execute(
            f"DELETE FROM {_quote(table)} WHERE {_quote(id_col)} = ?", (drop_id,)
        )

        # update refs
        refs_updated = 0
        if sheet == "SUPPLIERS_CLEAN" and old_name and old_name != keep_name:
            cur = conn.execute(
                'UPDATE offers SET "Supplier" = ? WHERE "Supplier" = ?',
                (keep_name, old_name)
            )
            refs_updated += cur.rowcount
        elif sheet == "CLIENTS" and old_name and old_name != keep_name:
            for tbl in ("bids", "shipments", "invoices"):
                cur = conn.execute(
                    f'UPDATE {tbl} SET "Client" = ? WHERE "Client" = ?',
                    (keep_name, old_name)
                )
                refs_updated += cur.rowcount

    clear_cache()
    _log("MERGE_CONCAT", sheet, keep_id,
         f"merged {drop_id} into {keep_id}; fields: {','.join(fields_merged) or '(none)'}; "
         f"refs updated: {refs_updated}")
    return {
        "ok": True, "keep_id": keep_id, "drop_id": drop_id,
        "fields_merged": fields_merged, "refs_updated": refs_updated
    }


def merge_records(sheet: str, keep_id: str, drop_id: str,
                  chosen: dict[str, str]) -> bool:
    """Compat legacy: come merge_records_concat ma con scelta esplicita keep/drop per colonna."""
    table = TABLE_NAMES[sheet]
    columns = SCHEMAS[sheet]
    id_col = columns[0]
    with get_conn() as conn:
        keep = conn.execute(
            f"SELECT * FROM {_quote(table)} WHERE {_quote(id_col)} = ?", (keep_id,)
        ).fetchone()
        drop = conn.execute(
            f"SELECT * FROM {_quote(table)} WHERE {_quote(id_col)} = ?", (drop_id,)
        ).fetchone()
        if keep is None or drop is None:
            return False
        old_name = str(drop["Company Name"] or "") if "Company Name" in keep.keys() else ""
        keep_name_before = str(keep["Company Name"] or "") if "Company Name" in keep.keys() else ""

        merged_row = {c: keep[c] for c in keep.keys()}
        for c in columns[1:]:
            choice = chosen.get(c, "keep")
            if choice == "keep":
                pass
            elif choice == "drop":
                merged_row[c] = drop[c]
            else:
                merged_row[c] = choice
        keep_name_after = merged_row.get("Company Name", keep_name_before)

        make_backup()
        set_sql = ", ".join(f"{_quote(c)} = ?" for c in columns[1:])
        vals = [merged_row.get(c) for c in columns[1:]] + [keep_id]
        conn.execute(
            f"UPDATE {_quote(table)} SET {set_sql} WHERE {_quote(id_col)} = ?", vals
        )
        conn.execute(
            f"DELETE FROM {_quote(table)} WHERE {_quote(id_col)} = ?", (drop_id,)
        )

        refs_updated = 0
        if sheet == "SUPPLIERS_CLEAN" and old_name and old_name != keep_name_after:
            cur = conn.execute(
                'UPDATE offers SET "Supplier" = ? WHERE "Supplier" = ?',
                (keep_name_after, old_name)
            )
            refs_updated += cur.rowcount
        elif sheet == "CLIENTS" and old_name and old_name != keep_name_after:
            for tbl in ("bids", "shipments", "invoices"):
                cur = conn.execute(
                    f'UPDATE {tbl} SET "Client" = ? WHERE "Client" = ?',
                    (keep_name_after, old_name)
                )
                refs_updated += cur.rowcount

    clear_cache()
    _log("MERGE", sheet, keep_id,
         f"merged {drop_id} into {keep_id}; refs updated: {refs_updated}")
    return True


# ======================================================================
# Esporta tutto in Excel (per email / backup manuale)
# ======================================================================
def export_to_excel(dest_path: Optional[Path] = None) -> Path:
    """Genera un .xlsx con tutte le tabelle. Default: ../export_<timestamp>.xlsx"""
    if dest_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = PROJECT_DIR / f"export_{ts}.xlsx"
    with pd.ExcelWriter(dest_path, engine="openpyxl") as xl:
        for sheet in SCHEMAS:
            df = read_sheet(sheet)
            df.to_excel(xl, sheet_name=sheet, index=False)
    return dest_path
