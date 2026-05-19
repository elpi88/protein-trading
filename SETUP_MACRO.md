# SETUP MACRO — versione 3.0 (18 maggio 2026)

## NOVITÀ v3.0 — gestione OFFERTE e BID

Ora puoi gestire anche le offerte dei fornitori (foglio `OFFERS`) e le richieste dei clienti (foglio `BIDS`) con form dedicati e macro complete:

| Foglio form | DB target | Prossimo ID | Cosa contiene                             |
|-------------|-----------|-------------|-------------------------------------------|
| `ADD_OFFER` | `OFFERS`  | `OFF-00016` | Offerte dei fornitori (15 colonne + 2 formule auto: USD/kg e Match Key) |
| `ADD_BID`   | `BIDS`    | `BID-00007` | Bid dei clienti (16 colonne + 1 formula auto: USD/kg) |

**Macro disponibili:**

| Operazione           | Offerte                          | Bid                          |
|----------------------|----------------------------------|------------------------------|
| Aggiungere           | `AggiungiOfferta`                | `AggiungiBid`                |
| Caricare per modifica| `CaricaOffertaPerModifica`       | `CaricaBidPerModifica`       |
| Salvare modifiche    | `SalvaModificheOfferta`          | `SalvaModificheBid`          |
| Cancellare per ID    | `CancellaOffertaPerID`           | `CancellaBidPerID`           |
| Annullare modifica   | `AnnullaModifica` (univ.)        | `AnnullaModifica` (univ.)    |

> **Nota importante**: nel form NON devi inserire i campi calcolati. **Price USD/kg** (e **Target USD/kg** per i BID) sono calcolati automaticamente da una formula che usa `FX_TABLE` e `WT_TABLE`. Il **Match Key** delle offerte è anch'esso una formula.

---



## Cosa è cambiato in questa versione

1. **Bug numerazione SUP- risolto.**
   - PRIMA: la macro calcolava l'ID dalla posizione di riga → produceva duplicati dopo le cancellazioni.
   - ORA: usa `MAX(numero esistente) + 1`.
   - Il prossimo fornitore sarà **`SUP-00441`** (corretto).
2. **Nuova macro `AggiungiCliente`** + nuovo foglio **`ADD_CLIENT`** (form per inserire clienti).
3. **Nuove macro `Modifica` per fornitori e clienti** (v2.1):
   - `CaricaFornitorePerModifica` / `SalvaModificheFornitore`
   - `CaricaClientePerModifica` / `SalvaModificheCliente`
   - `AnnullaModifica`
4. **Nuova categoria `POTATOES`** nei menu a tendina e nel codice colore.
5. **Nuova macro `CancellaClientePerID`**.
6. **Nuova macro `AggiornaProssimoID`** per rinfrescare l'anteprima ID nei form.
7. È stato creato un **backup automatico**: `Protein_Trading_ERP_FULL_BACKUP_2026_05_13.xlsm` nella stessa cartella. Se qualcosa va storto, basta ricopiare il backup.

---

## Stato attuale del database

- **Fornitori (`SUPPLIERS_CLEAN`):** 436 fornitori, ultimo ID = `SUP-00440`, prossimo = **`SUP-00441`**.
- **Clienti (`CLIENTS`):** 114 clienti, ultimo ID = `CLI-00115`, prossimo = **`CLI-00116`**.
- Gap numerici esistenti (clienti/fornitori cancellati in passato): SUP-432, 433, 434, 435 e CLI-00004. La nuova macro **non riempie i buchi** ma continua dal massimo: scelta corretta per non riusare ID già appartenuti ad altri.

---

## Come installare la nuova versione del codice (5 minuti, una volta sola)

Il file `Protein_Trading_ERP_FULL.xlsm` ha già il **nuovo foglio `ADD_CLIENT`** (pronto, con menu a tendina per Protein Category e Country).
Adesso devi **sostituire il modulo VBA** con la versione aggiornata.

### Passi

1. Apri `Protein_Trading_ERP_FULL.xlsm` in Excel.
2. Se compare la banda gialla in alto → clicca **"Abilita contenuto"**.
3. Premi **`Alt + F11`** → si apre l'editor VBA.
4. Nel pannello a sinistra ("Progetto"), espandi **`VBAProject (Protein_Trading_ERP_FULL.xlsm)` → `Moduli`**.
5. Click **destro** sul modulo esistente (di solito si chiama `Module1` o `AggiungiFornitore`) → **Rimuovi** → quando chiede "Vuoi esportare prima?" rispondi **No**.
6. Menu **File → Importa file...** → naviga nella cartella del progetto e seleziona **`AggiungiFornitore.bas`** → Apri.
7. Verifica che nel modulo compaiano le macro: `AggiungiFornitore`, `AggiungiCliente`, `CancellaFornitorePerID`, `CancellaClientePerID`, `TrovaECancellaDuplicati`, `AggiornaProssimoID`, `TestMinimo`, ecc.
8. Chiudi l'editor VBA con **`Alt + Q`**.
9. Salva con **`Ctrl + S`** (formato `.xlsm`).

### Verifica funzionamento

1. Foglio `ADD_SUPPLIER` → cella **C5** = `SUP-00441` ✓
2. Foglio `ADD_CLIENT` → cella **C5** = `CLI-00116` ✓
3. `Alt + F8` → seleziona `TestMinimo` → Esegui → tutti gli step devono passare ✓

---

## Come usare le macro

| Operazione                          | Come fare                                                                    |
|-------------------------------------|------------------------------------------------------------------------------|
| Aggiungere un **fornitore**         | Foglio `ADD_SUPPLIER` → compila celle gialle → `Alt+F8` → `AggiungiFornitore`|
| Aggiungere un **cliente**           | Foglio `ADD_CLIENT` → compila celle gialle → `Alt+F8` → `AggiungiCliente`    |
| **Modificare** un fornitore         | `Alt+F8` → `CaricaFornitorePerModifica` → cambia → `SalvaModificheFornitore` |
| **Modificare** un cliente           | `Alt+F8` → `CaricaClientePerModifica` → cambia → `SalvaModificheCliente`     |
| Annullare modifica in corso         | `Alt+F8` → `AnnullaModifica`                                                 |
| Cancellare fornitore per ID         | `Alt+F8` → `CancellaFornitorePerID`                                          |
| Cancellare cliente per ID           | `Alt+F8` → `CancellaClientePerID`                                            |
| Trovare duplicati nei fornitori     | `Alt+F8` → `TrovaECancellaDuplicati`                                         |
| Aggiornare anteprima ID nei form    | `Alt+F8` → `AggiornaProssimoID`                                              |
| Diagnostica file                    | `Alt+F8` → `TestMinimo`                                                      |

### Procedura MODIFICA (passo per passo)

Esempio: vuoi correggere l'email del fornitore SUP-00050.

1. `Alt+F8` → seleziona **`CaricaFornitorePerModifica`** → Esegui.
2. Excel chiede l'ID → scrivi `SUP-00050` → OK.
3. I dati esistenti vengono caricati nelle celle gialle del foglio `ADD_SUPPLIER`. La cella C5 mostra `MODIFICA SUP-00050` (= sei in modalità modifica).
4. **Modifica solo le celle che ti interessano** (es. correggi C10 con la nuova email).
5. `Alt+F8` → seleziona **`SalvaModificheFornitore`** → Esegui.
6. Excel chiede conferma → Sì → fatto. La riga in `SUPPLIERS_CLEAN` è aggiornata e il form si pulisce.

**Annullare**: se non vuoi più salvare le modifiche, lancia `AnnullaModifica`. Il form viene pulito e torni in modalità "nuovo".

**Per i clienti**: identica procedura, ma con `CaricaClientePerModifica` e `SalvaModificheCliente` sul foglio `ADD_CLIENT`.

> **Nota di sicurezza**: se sei in modalità MODIFICA e per sbaglio lanci `AggiungiFornitore` (o `AggiungiCliente`), la macro **non procede**: ti avvisa che il form è in modalità modifica e ti suggerisce di usare `SalvaModificheFornitore` o `AnnullaModifica`. Così non puoi creare duplicati per distrazione.

---

## Opzionale: pulsanti grafici sui form

Se vuoi un pulsante "Aggiungi" visibile sul foglio (più comodo di `Alt+F8`):

1. Sul foglio `ADD_SUPPLIER` (o `ADD_CLIENT`): menu **Inserisci → Forme → Rettangolo** → disegnalo.
2. Click **destro** sulla forma → **Assegna macro** → scegli `AggiungiFornitore` (o `AggiungiCliente`).
3. Sul foglio `ADD_SUPPLIER` il pulsante verde dovrebbe già esserci dalla versione precedente — verifica che sia ancora collegato a `AggiungiFornitore` (click destro → Assegna macro).

---

## Procedura "tutti i giorni"

1. Apri `Protein_Trading_ERP_FULL.xlsm`.
2. Clicca "Abilita contenuto" se compare la banda gialla.
3. Vai su `ADD_SUPPLIER` o `ADD_CLIENT`.
4. Compila le caselle gialle.
5. Lancia la macro (pulsante o `Alt+F8`).
6. Conferma. Fatto.

---

## Risoluzione problemi

**"L'ID nel form non si aggiorna dopo un inserimento"**
Esegui `AggiornaProssimoID` (`Alt+F8`).

**"La macro non compare nell'elenco `Alt+F8`"**
Il modulo VBA non è stato importato. Ripeti la procedura di importazione del `.bas`.

**"Errore: macro disabilitate"**
File → Opzioni → Centro protezione → Impostazioni macro → "Disattiva tutte le macro con notifica" (poi clicca "Abilita contenuto" quando apre il file).

**"Voglio tornare alla versione di ieri"**
Rinomina il file attuale, poi rinomina `Protein_Trading_ERP_FULL_BACKUP_2026_05_13.xlsm` rimuovendo `_BACKUP_2026_05_13`.

---

## Domande?

Se qualcosa non funziona durante l'importazione del nuovo modulo o l'inserimento del primo cliente, dimmelo e ti guido passo passo.
