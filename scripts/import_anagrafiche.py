"""
Script di importazione da '2017, Anagrafiche-nb-04-2-OK.xlsx' → Supabase.

Importa 4 sezioni dal foglio 'Anagrafiche':
  - CLIENTI       → tabella clients (solo i nuovi, salta duplicati)
  - DESTINAZIONI  → tabella client_destinations
  - MACELLI       → tabella suppliers_clean (come fornitori)
  - TRASPORTATORI → tabella transporters (categoria: Terra Europa)

Esegui dal cmd:
    set DATABASE_URL=postgresql://...
    python scripts/import_anagrafiche.py
"""

import os, sys
import pandas as pd
from pathlib import Path

# -----------------------------------------------------------------------
# Percorso file Excel
# -----------------------------------------------------------------------
FNAME = "2017, Anagrafiche-nb-04-2-OK.xlsx"
SEARCH = [
    Path(__file__).parent / FNAME,
    Path(__file__).parent.parent / FNAME,
    Path(r"C:\temp_import") / FNAME,
]
EXCEL_PATH = next((p for p in SEARCH if p.exists()), None)
if not EXCEL_PATH:
    print(f"ERRORE: file '{FNAME}' non trovato.")
    print("Copialo nella cartella scripts/ oppure in C:\\temp_import\\")
    sys.exit(1)
print(f"File trovato: {EXCEL_PATH}")

# -----------------------------------------------------------------------
# DATABASE_URL
# -----------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERRORE: variabile DATABASE_URL non impostata.")
    print("  set DATABASE_URL=postgresql://postgres.<id>:<pwd>@aws-1-eu-central-1.pooler.supabase.com:6543/postgres")
    sys.exit(1)

try:
    import psycopg2, psycopg2.extras
except ImportError:
    print("ERRORE: psycopg2 non installato. Esegui: pip install psycopg2-binary")
    sys.exit(1)

print("Connessione a Supabase...")
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

# -----------------------------------------------------------------------
# Crea tabelle se non esistono
# -----------------------------------------------------------------------
cur.execute("""
    CREATE TABLE IF NOT EXISTS transporters (
        id SERIAL PRIMARY KEY,
        "Company Name" TEXT NOT NULL,
        "Category" TEXT,
        "Country" TEXT,
        "City" TEXT,
        "Address" TEXT,
        "Phone" TEXT,
        "Email" TEXT,
        "VAT" TEXT,
        "Notes" TEXT
    )
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS client_destinations (
        id SERIAL PRIMARY KEY,
        "Cod. Destinazione" TEXT,
        "Cod. Cliente" TEXT,
        "Dest. Name" TEXT,
        "Address" TEXT,
        "City" TEXT,
        "Province" TEXT,
        "Country" TEXT,
        "Phone" TEXT,
        "Email" TEXT,
        "VAT" TEXT,
        "Notes" TEXT
    )
""")
cur.execute('ALTER TABLE clients ADD COLUMN IF NOT EXISTS "Indirizzo Scarico" TEXT')
cur.execute('ALTER TABLE clients ADD COLUMN IF NOT EXISTS "Metodo di Pagamento" TEXT')
conn.commit()

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------
def clean(val):
    s = str(val or '').strip()
    return None if s.lower() in ('nan', '', 'none', '-', '--', '---') else s

def phone_clean(val):
    s = clean(val)
    if not s:
        return None
    if all(c in '-_ \t' for c in s):
        return None
    return s

# -----------------------------------------------------------------------
# Leggi foglio Anagrafiche (raw)
# -----------------------------------------------------------------------
df_raw = pd.read_excel(EXCEL_PATH, sheet_name='Anagrafiche', header=None)

# Sezioni (indici riga):
# Riga 2  = header colonne (usato per tutte le sezioni)
# Riga 3-590   = CLIENTI
# Riga 591     = label "DESTINAZIONI"
# Riga 592     = header destinazioni
# Riga 593-837 = DESTINAZIONI
# Riga 838     = label "MACELLI"
# Riga 839     = header macelli
# Riga 840-927 = MACELLI
# Riga 928     = label "TRASPORTATORI"
# Riga 929     = header trasportatori
# Riga 930+    = TRASPORTATORI

df_clienti      = df_raw.iloc[3:591].copy()
df_destinazioni = df_raw.iloc[593:838].copy()
df_macelli      = df_raw.iloc[840:928].copy()
df_trasportatori = df_raw.iloc[930:].copy()

# -----------------------------------------------------------------------
# 1. CLIENTI
# -----------------------------------------------------------------------
print("\n── CLIENTI ──────────────────────────────────")

cur.execute('SELECT "Client ID", "Company Name" FROM clients')
existing = cur.fetchall()
existing_names = set(str(r[1] or '').strip().lower() for r in existing)
max_num = max(
    (int(r[0].replace('CLI-','')) for r in existing if str(r[0] or '').startswith('CLI-')),
    default=0
)
print(f"  Già presenti: {len(existing_names)}  (ID max: CLI-{max_num:03d})")

ins_c = 0
skip_c = 0
counter = max_num

for _, r in df_clienti.iterrows():
    # colonne: 1=CodAna, 2=RagSoc, 5=Indirizzo, 6=Cap, 7=Città, 8=Prov, 9=Country,
    #          10=PIva, 12=Tel, 14=Email, 16=Cell, 17=Note
    company = clean(r.iloc[2])
    if not company:
        skip_c += 1
        continue
    if company.strip().lower() in existing_names:
        skip_c += 1
        continue

    counter += 1
    client_id = f"CLI-{counter:03d}"
    address_parts = [clean(r.iloc[5]), clean(r.iloc[6]), clean(r.iloc[7])]
    address = ', '.join(p for p in address_parts if p) or None
    city = clean(r.iloc[7]) if len(r) > 7 else None

    cur.execute(
        """INSERT INTO clients
           ("Client ID","Company Name","CONTACT PERSON","PROTEIN CATEGORY","ITEMS",
            "COUNTRY","Email","Phone","Monthly Capacity","Notes",
            "Indirizzo Scarico","Metodo di Pagamento")
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (client_id, company, None, None, None,
         clean(r.iloc[9]) if len(r) > 9 else None,
         clean(r.iloc[14]) if len(r) > 14 else None,
         phone_clean(r.iloc[12]) if len(r) > 12 else None,
         None,
         clean(r.iloc[17]) if len(r) > 17 else None,
         address, None)
    )
    existing_names.add(company.strip().lower())
    ins_c += 1

conn.commit()
print(f"  Inseriti: {ins_c}  |  Saltati: {skip_c}")

# -----------------------------------------------------------------------
# 2. DESTINAZIONI
# -----------------------------------------------------------------------
print("\n── DESTINAZIONI ────────────────────────────")

# Colonne: 1=CodDest, 2=NomeDest, 3=Cliente(ragSoc), 4=Indirizzo, 5=Cap,
#          6=Città, 7=Prov, 8=Country, 10=PIva, 12=Tel, 14=Email, 16=Cell, 17=Note,
#          20=CodCliente(anagrafica)

# Leggi già presenti (per evitare duplicati su Cod. Destinazione)
cur.execute('SELECT "Cod. Destinazione" FROM client_destinations')
existing_dest = set(str(r[0] or '') for r in cur.fetchall())

ins_d = 0
skip_d = 0

for _, r in df_destinazioni.iterrows():
    dest_name = clean(r.iloc[2])
    if not dest_name:
        skip_d += 1
        continue
    cod_dest = clean(r.iloc[1]) or ''
    if cod_dest and cod_dest in existing_dest:
        skip_d += 1
        continue

    cur.execute(
        """INSERT INTO client_destinations
           ("Cod. Destinazione","Cod. Cliente","Dest. Name","Address","City",
            "Province","Country","Phone","Email","VAT","Notes")
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            cod_dest or None,
            clean(r.iloc[20]) if len(r) > 20 else None,   # Cod. Anagrafica
            dest_name,
            clean(r.iloc[4]) if len(r) > 4 else None,     # Indirizzo
            clean(r.iloc[6]) if len(r) > 6 else None,     # Città
            clean(r.iloc[7]) if len(r) > 7 else None,     # Provincia
            clean(r.iloc[8]) if len(r) > 8 else None,     # Country
            phone_clean(r.iloc[11]) if len(r) > 11 else None,
            clean(r.iloc[13]) if len(r) > 13 else None,   # Email
            clean(r.iloc[9]) if len(r) > 9 else None,     # P.Iva
            clean(r.iloc[16]) if len(r) > 16 else None,   # Note
        )
    )
    if cod_dest:
        existing_dest.add(cod_dest)
    ins_d += 1

conn.commit()
print(f"  Inserite: {ins_d}  |  Saltate: {skip_d}")

# -----------------------------------------------------------------------
# 3. MACELLI → suppliers_clean
# -----------------------------------------------------------------------
print("\n── MACELLI (Fornitori) ─────────────────────")

cur.execute('SELECT "Company Name" FROM suppliers_clean')
existing_sup = set(str(r[0] or '').strip().lower() for r in cur.fetchall())

cur.execute('SELECT "Supplier ID" FROM suppliers_clean')
sup_ids = [str(r[0] or '') for r in cur.fetchall()]
max_sup = max(
    (int(s.replace('SUP-','')) for s in sup_ids if s.startswith('SUP-')),
    default=0
)

ins_m = 0
skip_m = 0
sup_counter = max_sup

# Colonne macelli: 1=CodForn, 2=RagSoc, 4=Indirizzo, 5=Cap, 6=Città,
#                  7=Prov, 8=Country, 9=PIva, 11=Tel, 13=Email, 15=Cell, 16=Note

for _, r in df_macelli.iterrows():
    company = clean(r.iloc[2])
    if not company:
        skip_m += 1
        continue
    if company.strip().lower() in existing_sup:
        skip_m += 1
        continue

    sup_counter += 1
    sup_id = f"SUP-{sup_counter:03d}"

    cur.execute(
        """INSERT INTO suppliers_clean
           ("Supplier ID","Company Name","Contact Person","Protein Category",
            "Country","Email","Phone","Website","Address","Products","Tax/VAT","Registration","Notes")
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            sup_id, company, None, None,
            clean(r.iloc[8]) if len(r) > 8 else None,
            clean(r.iloc[13]) if len(r) > 13 else None,
            phone_clean(r.iloc[11]) if len(r) > 11 else None,
            None,
            clean(r.iloc[4]) if len(r) > 4 else None,
            None,
            clean(r.iloc[9]) if len(r) > 9 else None,
            None,
            clean(r.iloc[16]) if len(r) > 16 else None,
        )
    )
    existing_sup.add(company.strip().lower())
    ins_m += 1

conn.commit()
print(f"  Inseriti: {ins_m}  |  Saltati: {skip_m}")

# -----------------------------------------------------------------------
# 4. TRASPORTATORI
# -----------------------------------------------------------------------
print("\n── TRASPORTATORI ───────────────────────────")

cur.execute('SELECT "Company Name" FROM transporters')
existing_tr = set(str(r[0] or '').strip().lower() for r in cur.fetchall())

ins_t = 0
skip_t = 0

# Colonne trasportatori: 2=RagSoc, 4=Indirizzo, 5=Cap, 6=Città, 7=Prov,
#                        8=Country, 9=PIva, 11=Tel, 13=Email, 15=Cell, 16=Note

for _, r in df_trasportatori.iterrows():
    company = clean(r.iloc[2])
    if not company:
        skip_t += 1
        continue
    if company.strip().lower() in existing_tr:
        skip_t += 1
        continue

    cur.execute(
        """INSERT INTO transporters
           ("Company Name","Category","Country","City","Address","Phone","Email","VAT","Notes")
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            company,
            "Terra Europa",   # tutti dal file sono trasportatori terra
            clean(r.iloc[8]) if len(r) > 8 else None,
            clean(r.iloc[6]) if len(r) > 6 else None,
            clean(r.iloc[4]) if len(r) > 4 else None,
            phone_clean(r.iloc[11]) if len(r) > 11 else None,
            clean(r.iloc[13]) if len(r) > 13 else None,
            clean(r.iloc[9]) if len(r) > 9 else None,
            clean(r.iloc[16]) if len(r) > 16 else None,
        )
    )
    existing_tr.add(company.strip().lower())
    ins_t += 1

conn.commit()
cur.close()
conn.close()

print(f"  Inseriti: {ins_t}  |  Saltati: {skip_t}")

print(f"""
╔══════════════════════════════════════════╗
║  ✅  IMPORTAZIONE COMPLETATA             ║
╠══════════════════════════════════════════╣
║  Clienti inseriti:        {ins_c:<6}          ║
║  Destinazioni inserite:   {ins_d:<6}          ║
║  Macelli (fornitori):     {ins_m:<6}          ║
║  Trasportatori:           {ins_t:<6}          ║
╚══════════════════════════════════════════╝
""")
