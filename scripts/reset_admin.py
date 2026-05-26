"""
Reset / creazione utente admin su Supabase.

COME USARLO:
1. Apri cmd nella cartella del progetto
2. Esegui:
   set DATABASE_URL=postgresql://...
   python scripts/reset_admin.py
"""

import os
import sys
from pathlib import Path

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERRORE: DATABASE_URL non impostata.")
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print("ERRORE: psycopg2 non installato. Esegui: pip install psycopg2-binary")
    sys.exit(1)

try:
    import bcrypt
except ImportError:
    print("ERRORE: bcrypt non installato. Esegui: pip install bcrypt")
    sys.exit(1)

# Credenziali nuove admin
USERNAME = "admin"
PASSWORD = "Admin2024!"

# Hash della password
pw_hash = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("""
    INSERT INTO users (username, password_hash, role, created_at, active)
    VALUES (%s, %s, 'admin', NOW()::text, 1)
    ON CONFLICT (username) DO UPDATE
        SET password_hash = EXCLUDED.password_hash,
            role = 'admin',
            active = 1
""", (USERNAME, pw_hash))

conn.commit()
cur.close()
conn.close()

print("=" * 40)
print("Admin creato/resettato con successo!")
print(f"  Username: {USERNAME}")
print(f"  Password: {PASSWORD}")
print("Cambia la password dopo il primo accesso.")
print("=" * 40)
