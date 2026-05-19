# PROTEIN TRADING - App grafica

App locale moderna per gestire **fornitori, clienti, offerte e bid** con un'interfaccia bella, semplice e arricchibile nel tempo.

I dati restano nel tuo file Excel `Protein_Trading_ERP_FULL.xlsm`: l'app legge e scrive lì, niente database esterni, niente cloud, niente IT.

---

## Avvio rapido

1. **Doppio click** su `Avvia_App.bat`.
2. Aspetta qualche secondo. Si apre il browser su `http://localhost:8501`.
3. Usa il menu a sinistra per navigare.
4. Per chiudere l'app: chiudi la finestra nera del prompt dei comandi.

> **La prima volta** che avvii l'app, lo script installa automaticamente le librerie Python necessarie. Può richiedere 1-3 minuti. Le volte successive parte in 5 secondi.

---

## Prerequisito una-tantum: installare Python (solo se non l'hai)

Se la prima volta `Avvia_App.bat` ti dice "Python non è installato", segui questi passi:

1. Vai su <https://www.python.org/downloads/windows/>
2. Scarica l'ultima versione (Python 3.11 o superiore).
3. **IMPORTANTE**: durante l'installazione spunta la casella **"Add Python to PATH"** (in basso, prima di cliccare "Install").
4. Termina l'installazione.
5. Doppio click su `Avvia_App.bat`.

---

## Cosa trovi dentro l'app

### Sezioni nel menu a sinistra

| Sezione | Cosa contiene |
|---------|---------------|
| **Home** | Card di sintesi con i numeri chiave |
| **Dashboard** | Grafici interattivi: fornitori per categoria/paese, clienti per categoria, offerte per prodotto, bid per status |
| **Fornitori** | Tabella ricercabile e filtrabile per categoria. Aggiungi / Modifica / Cancella con form guidato |
| **Clienti** | Stessa esperienza dei fornitori |
| **Offerte** | Offerte ricevute dai fornitori. Aggiungi / Modifica / Cancella + **allegati** (PDF, foto, Excel). Price USD/kg calcolato automaticamente |
| **Bid** | Richieste dei clienti. Stesso pattern, con campo Status (OPEN, WON, LOST, ...) + **allegati** |
| **Impostazioni** | Crea backup manuale, forza il refresh dati, vedi le info sul file Excel |
| **Matching** | Incrocio automatico offerte↔bid sullo stesso prodotto, ordinati per margine. Dettaglio fornitore + cliente affiancati |
| **Margini** | Top 10 opportunità per valore, P&L potenziale, grafici per prodotto, scatter margine/volume, alert margini negativi + export PDF |
| **Notifiche** | Bid scaduti, bid in scadenza ≤14gg, offerte vecchie (>30gg), bid senza match. Aggiornata in tempo reale |
| **Merge duplicati** | UI side-by-side per fondere 2 fornitori/clienti duplicati scegliendo campo per campo il valore da mantenere. Aggiorna automaticamente i riferimenti in OFFERS / BIDS / SHIPMENTS / INVOICES |
| **Spedizioni** | Vessel tracking: gestione spedizioni con vessel, container, ETD/ETA, status (IN_TRANSIT, ARRIVED, DELAYED, ...). KPI per arrivi imminenti |
| **Ordini** | Fatture e ordini eseguiti con stato pagamento (PAID, PENDING, OVERDUE). KPI "da incassare" e alert per scaduti non pagati |
| **Storico** | Audit log: log automatico di ogni Aggiungi/Modifica/Cancella/Merge fatto dall'app. Filtri per foglio/azione, download CSV completo |

### Tipiche operazioni quotidiane

- **Aggiungere un nuovo fornitore**: Fornitori → pulsante "➕ Nuovo fornitore" in alto a destra → compila il form → "💾 Salva".
- **Modificare un cliente**: Clienti → scegli l'ID nella tendina in basso → "✏️ Modifica" → cambia i campi → "💾 Salva".
- **Cercare un'offerta**: Offerte → scrivi nella barra in alto (cerca in tutti i campi).
- **Filtrare bid aperti**: Bid → tendina Status → "OPEN".
- **Vedere i numeri**: Dashboard → si aggiorna in tempo reale ogni volta che apri la pagina.

---

## Sicurezza dei dati

- **L'app gira solo sul tuo computer.** Nessun dato viene caricato online.
- **Ogni modifica crea un backup automatico** nella cartella `backups/` (vengono mantenuti gli ultimi 20).
- **Le macro VBA continuano a funzionare**: puoi aprire Excel e usare le macro in parallelo all'app. Devi solo ricordarti di chiudere Excel prima di scrivere dall'app (Windows blocca i file aperti).

---

## Cosa succede se commetto un errore

Tutti i passaggi distruttivi chiedono conferma prima di procedere. Inoltre:

- **Backup automatico** prima di ogni Aggiungi/Modifica/Cancella.
- **Cartella `backups/`** con timestamp: `backup_20260518_103015_Protein_Trading_ERP_FULL.xlsm`.
- Per ripristinare: chiudi l'app, vai in `backups/`, copia il file scelto e rinominalo `Protein_Trading_ERP_FULL.xlsm` nella cartella principale.

---

## Estendere l'app nel tempo

L'app ha già le pagine principali. Idee per le prossime iterazioni (richiedono qualche minuto di setup in più):

- **Email automatiche**: spedire offerte/bid via email al cliente direttamente dall'app. Serve configurare SMTP (server email aziendale o Gmail con app password).
- **OCR offerte PDF**: trascinare un PDF di offerta nell'app e farne estrarre prezzo/prodotto/Incoterm automaticamente. Serve installare Tesseract o usare API esterne.
- **Multiutente in rete**: condivisione su rete aziendale (richiederebbe però un piccolo coordinamento IT per esporre la porta 8501 e gestire i permessi).
- **Mobile**: l'app è già responsive (Streamlit funziona da telefono se ti colleghi all'IP del PC). Per una vera app mobile servirebbe un'app nativa, fuori scope.
- **Statistiche cliente/fornitore**: per ogni anagrafica mostra storico ordini, margine medio, lead time.
- **Notifiche email/Telegram**: invio automatico quando un bid sta per scadere.

---

## Convivenza con le macro VBA esistenti

Le macro che abbiamo costruito nei giorni scorsi (`AggiungiFornitore.bas`, ecc.) continuano a funzionare normalmente in Excel. Puoi:

- Usare **solo l'app** per Aggiungi/Modifica/Cancella → operazioni più veloci e con UI moderna.
- Usare **solo Excel/macro** → workflow classico con `Alt+F8`.
- **Mischiare** → ad esempio aggiungi un fornitore dall'app e poi apri Excel per usare la macro `TrovaECancellaDuplicati`.

L'unico vincolo: **un solo programma alla volta deve scrivere** sul file. Se Excel è aperto e stai per salvare dall'app, l'app ti darà errore. Soluzione: chiudi Excel, poi riprova.

---

## Struttura cartella

```
PIATTAFORMA TRADING/
├─ Protein_Trading_ERP_FULL.xlsm     (file dati principale)
├─ AggiungiFornitore.bas             (macro VBA - importabile in Excel)
├─ SETUP_MACRO.md                    (guida macro VBA)
├─ Avvia_App.bat                     (DOPPIO CLICK per lanciare l'app)
├─ README_APP.md                     (questo file)
├─ backups/                          (backup automatici)
├─ attachments/                      (file allegati a offerte/bid)
└─ app/
   ├─ app.py                         (entry point)
   ├─ requirements.txt
   ├─ .streamlit/config.toml         (tema)
   ├─ .venv/                         (creato al primo avvio)
   ├─ lib/
   │  ├─ data.py                     (lettura/scrittura Excel + matching + allegati)
   │  └─ theme.py                    (CSS custom)
   └─ pages/
      ├─ 1_Dashboard.py
      ├─ 2_Fornitori.py
      ├─ 3_Clienti.py
      ├─ 4_Offerte.py
      ├─ 5_Bid.py
      ├─ 6_Impostazioni.py
      ├─ 7_Matching.py
      ├─ 8_Margini.py
      ├─ 9_Notifiche.py
      ├─ 10_Merge_Duplicati.py
      ├─ 11_Spedizioni.py
      ├─ 12_Ordini.py
      └─ 13_Storico.py
```

---

## FAQ rapide

**L'app non si apre nel browser.**
Apri manualmente <http://localhost:8501>.

**Vedo "USD 0k" nella pipeline.**
Le formule del foglio Excel non sono ancora state calcolate. Apri il file in Excel una volta, salva e chiudi. La prossima volta l'app vede i valori calcolati.

**Voglio cambiare la porta 8501.**
Modifica `Avvia_App.bat` aggiungendo `--server.port=8502` all'ultima riga `streamlit run`.

**Voglio una nuova pagina.**
Aggiungi un file `7_Mia_Pagina.py` in `app/pages/`. Verrà mostrata automaticamente nel menu.

---

## Domande?

Se qualcosa non funziona, fammi sapere. Possiamo iterare: ogni sezione si può rifinire, espandere o ripensare quando ne avrai voglia.
