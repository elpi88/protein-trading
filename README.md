# Protein Trading — Piattaforma di gestione

Applicazione Streamlit per la gestione di:

- Fornitori (per paese e tipo di proteina)
- Clienti
- Offerte ricevute
- Bid / richieste
- Matching, margini, spedizioni, ordini

## Tipi di proteine gestiti

Fish, Pork Meat, Pork Offals, Beef Meat, Beef Offals, Poultry Meat, Lamb.

## Stack tecnico

- **Frontend**: Streamlit (Python)
- **Storage**: SQLite (in migrazione da Excel `.xlsm`)
- **Auth**: bcrypt + audit log
- **Deploy**: Streamlit Cloud + Supabase (in arrivo)

## Avvio locale

```bash
cd app
pip install -r requirements.txt
streamlit run app.py
```

L'app si apre su `http://localhost:8501`.

## Struttura

```
app/
  app.py              # entry point Streamlit
  lib/
    data.py           # accesso dati
    theme.py          # CSS / tema banking premium (responsive mobile incluso)
    pdf_export.py     # export PDF
  pages/
    1_Dashboard.py
    2_Fornitori.py
    3_Clienti.py
    4_Offerte.py
    5_Bid.py
    6_Impostazioni.py
    7_Matching.py
    8_Margini.py
    9_Notifiche.py
    10_Merge_Duplicati.py
    11_Spedizioni.py
    12_Ordini.py
    13_Storico.py
```

## Note

I dati business (file Excel, audit log, backup) **non** sono inclusi nel repository. Vedi `.gitignore`.
