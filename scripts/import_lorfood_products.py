"""
Importa i prodotti Lorfood dal file Excel nel database (tabella supplier_products).
Uso: python scripts/import_lorfood_products.py <percorso_file_excel>
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import openpyxl

def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/import_lorfood_products.py <percorso_file_excel>")
        sys.exit(1)

    xlsx_path = sys.argv[1]
    if not os.path.exists(xlsx_path):
        print(f"File non trovato: {xlsx_path}")
        sys.exit(1)

    print(f"Lettura file: {xlsx_path}")
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb.active
    print(f"Foglio attivo: {ws.title}")

    products = []
    for row in ws.iter_rows(min_row=10, max_row=2000, min_col=1, max_col=2, values_only=True):
        name, code = row[0], row[1]
        if name and code:
            products.append((str(code).strip(), str(name).strip()))

    print(f"Prodotti trovati: {len(products)}")

    from lib.db import init_db, upsert_supplier_products
    init_db()

    n = upsert_supplier_products("Lorfood", products)
    print(f"✅ Importati/aggiornati {n} prodotti per fornitore 'Lorfood'")

    # Mostra i primi 5
    from lib.db import get_supplier_products
    df = get_supplier_products("Lorfood")
    print("\nPrimi 5 prodotti caricati:")
    for _, r in df.head(5).iterrows():
        print(f"  {r['product_code']} — {r['product_name']}")

if __name__ == "__main__":
    main()
