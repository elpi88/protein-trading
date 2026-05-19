# Come testare l'app dal telefono (rete locale)

Mentre l'app gira sul tuo PC, puoi aprirla dal cellulare se PC e telefono sono sulla **stessa rete WiFi**.

## Passo 1 — Trova l'indirizzo IP locale del PC

1. Apri il **Prompt dei comandi** (premi tasto Windows, digita `cmd`, premi Invio)
2. Scrivi:
   ```
   ipconfig
   ```
3. Premi Invio. Tra le righe che escono, cerca **"Indirizzo IPv4"** o **"IPv4 Address"**.
4. Sara' qualcosa tipo `192.168.1.42` o `192.168.0.105`. Annotalo.

## Passo 2 — Avvia l'app accettando connessioni dalla rete

1. Doppio click su `Avvia_App.bat` (come fai normalmente)
2. Nella finestra nera che si apre, Streamlit ti mostra DUE indirizzi:
   ```
   Local URL: http://localhost:8501
   Network URL: http://192.168.1.42:8501
   ```
3. Usa il **Network URL** dal telefono.

## Passo 3 — Apri sul telefono

1. Connetti il telefono alla **stessa rete WiFi** del PC
2. Apri il browser (Safari su iPhone, Chrome su Android)
3. Digita nell'URL: `http://192.168.1.42:8501` (sostituisci con il tuo IP)
4. Premi Vai

L'app si apre sul telefono. Controlla che:

- [ ] Le colonne si impilano verticalmente (non affiancate)
- [ ] I pulsanti sono abbastanza grandi da toccare con il dito
- [ ] La sidebar si apre dal pulsante in alto a sinistra
- [ ] Le tabelle scorrono lateralmente con il dito
- [ ] Il testo si legge senza dover zoomare

## Se non funziona

**"Impossibile raggiungere il sito"** -> probabilmente il **firewall di Windows** blocca la porta 8501.
Soluzione:
1. Windows Security -> Firewall e protezione rete -> "Consenti app tramite firewall"
2. Cerca Python o aggiungilo manualmente
3. Spunta "Privata" (rete domestica)

In alternativa, possiamo passare direttamente alla Fase 4 (deploy online) e testare li'.
