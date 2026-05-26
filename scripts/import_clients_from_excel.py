"""
Script di importazione clienti da CONTACT INFO UPDATED 2025.xlsx → Supabase.
Legge i fogli 'contacts-info' e 'ITALY', rimuove i duplicati già presenti,
e inserisce i nuovi clienti nel database.

Esegui dal cmd nella cartella del progetto:
    set DATABASE_URL=postgresql://...la tua stringa di connessione...
    python scripts/import_clients_from_excel.py
"""

import os
import sys
import pandas as pd
from pathlib import Path

# Percorso Excel — lo script cerca in questi posti nell'ordine:
SEARCH_PATHS = [
    Path(__file__).parent / "CONTACT INFO UPDATED 2025.xlsx",          # scripts/
    Path(__file__).parent.parent / "CONTACT INFO UPDATED 2025.xlsx",   # progetto/
    Path(r"C:\temp_import\CONTACT INFO UPDATED 2025.xlsx"),            # cartella temp
]

EXCEL_PATH = None
for p in SEARCH_PATHS:
    if p.exists():
        EXCEL_PATH = p
        break

if EXCEL_PATH is None:
    print("ERRORE: file Excel non trovato.")
    print("Copia 'CONTACT INFO UPDATED 2025.xlsx' in una di queste cartelle:")
    for p in SEARCH_PATHS:
        print(f"  {p}")
    sys.exit(1)

print(f"File trovato: {EXCEL_PATH}")

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERRORE: variabile DATABASE_URL non impostata.")
    print("Esegui prima:")
    print('  set DATABASE_URL=postgresql://postgres.<id>:<password>@aws-1-eu-central-1.pooler.supabase.com:6543/postgres')
    sys.exit(1)

# -----------------------------------------------------------------------
# Connessione
# -----------------------------------------------------------------------
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERRORE: psycopg2 non installato. Esegui: pip install psycopg2-binary")
    sys.exit(1)

print("Connessione a Supabase...")
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

# -----------------------------------------------------------------------
# Aggiungi colonne se mancanti (migrazione sicura)
# -----------------------------------------------------------------------
for col_sql in [
    'ALTER TABLE clients ADD COLUMN IF NOT EXISTS "Indirizzo Scarico" TEXT',
    'ALTER TABLE clients ADD COLUMN IF NOT EXISTS "Metodo di Pagamento" TEXT',
]:
    try:
        cur.execute(col_sql)
        conn.commit()
    except Exception:
        conn.rollback()

# -----------------------------------------------------------------------
# Leggi clienti già presenti
# -----------------------------------------------------------------------
cur.execute('SELECT "Client ID", "Company Name" FROM clients')
existing_rows = cur.fetchall()
existing_names = set(str(r[1] or '').strip().lower() for r in existing_rows)

# Trova il massimo numero ID (formato CLI-NNN)
max_num = 0
for r in existing_rows:
    cid = str(r[0] or '')
    if cid.startswith('CLI-'):
        try:
            num = int(cid.replace('CLI-', ''))
            if num > max_num:
                max_num = num
        except Exception:
            pass

print(f"Clienti già presenti: {len(existing_names)}  (ID max: CLI-{max_num:03d})")

# -----------------------------------------------------------------------
# Leggi e normalizza Excel
# -----------------------------------------------------------------------
def clean(val):
    s = str(val or '').strip()
    return None if s.lower() in ('nan', '', 'none') else s

def phone_clean(val):
    s = clean(val)
    if not s:
        return None
    if all(c in '-_ \t' for c in s):
        return None
    return s

rows_to_insert = []

# Foglio contacts-info
df1 = pd.read_excel(EXCEL_PATH, sheet_name='contacts-info')
df1 = df1.dropna(subset=['COMPANY'])
for _, r in df1.iterrows():
    company = clean(r.get('COMPANY'))
    if not company:
        continue
    name = f"{clean(r.get('NAME','')) or ''} {clean(r.get('LAST NAME','')) or ''}".strip() or None
    rows_to_insert.append({
        'Company Name': company,
        'CONTACT PERSON': name,
        'COUNTRY': clean(r.get('COUNTRY/REGION')),
        'Email': clean(r.get('EMAIL')),
        'Phone': phone_clean(r.get('TELEPHONE')),
        'Notes': clean(r.get('POSITION')),
    })

# Foglio ITALY (no header)
df2 = pd.read_excel(EXCEL_PATH, sheet_name='ITALY', header=None)
df2.columns = ['_skip', 'NAME', 'LAST NAME', 'COMPANY', 'POSITION', 'EMAIL',
               'COUNTRY1', 'COUNTRY2', 'TELEPHONE']
df2 = df2.dropna(subset=['COMPANY'])
for _, r in df2.iterrows():
    company = clean(r.get('COMPANY'))
    if not company:
        continue
    name = f"{clean(r.get('NAME','')) or ''} {clean(r.get('LAST NAME','')) or ''}".strip() or None
    country = clean(r.get('COUNTRY1')) or clean(r.get('COUNTRY2')) or 'Italy'
    rows_to_insert.append({
        'Company Name': company,
        'CONTACT PERSON': name,
        'COUNTRY': country,
        'Email': clean(r.get('EMAIL')),
        'Phone': phone_clean(r.get('TELEPHONE')),
        'Notes': clean(r.get('POSITION')),
    })

print(f"Contatti nel file Excel: {len(rows_to_insert)}")

# -----------------------------------------------------------------------
# Filtra duplicati e inserisci
# -----------------------------------------------------------------------
inserted = 0
skipped = 0
counter = max_num

for row in rows_to_insert:
    key = row['Company Name'].strip().lower()
    if key in existing_names:
        skipped += 1
        continue

    counter += 1
    client_id = f"CLI-{counter:03d}"

    cur.execute(
        """
        INSERT INTO clients
            ("Client ID","Company Name","CONTACT PERSON","PROTEIN CATEGORY",
             "ITEMS","COUNTRY","Email","Phone","Monthly Capacity","Notes",
             "Indirizzo Scarico","Metodo di Pagamento")
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            client_id,
            row['Company Name'],
            row['CONTACT PERSON'],
            None,   # PROTEIN CATEGORY — da compilare in app
            None,   # ITEMS
            row['COUNTRY'],
            row['Email'],
            row['Phone'],
            None,   # Monthly Capacity
            row['Notes'],
            None,   # Indirizzo Scarico
            None,   # Metodo di Pagamento
        )
    )
    existing_names.add(key)
    inserted += 1

    if inserted % 50 == 0:
        conn.commit()
        print(f"  ... {inserted} inseriti finora")

conn.commit()
cur.close()
conn.close()

print(f"\n✅ IMPORTAZIONE COMPLETATA")
print(f"   Inseriti: {inserted}")
print(f"   Saltati (già presenti): {skipped}")
print(f"   Totale clienti nel DB: {len(existing_names)}")
