# screenshot-app

## Backend HTTP MVP

Install test dependencies, then run `screenshot-api` (default `127.0.0.1:8080`, storage root `./data`). Upload one or more files with `POST /imports` as multipart field `files`; query a manifest with `GET /imports/{id}`. The service stores originals by SHA-256 under the immutable originals zone, never overwrites them, and returns `processing`, `completed`, or `duplicate` (invalid input is `failed`).

Example: `curl -F files=@screen.png http://127.0.0.1:8080/imports`.

## Installazione mobile (PWA)

Il frontend è installabile come PWA su Android e iOS senza modificare API o originali. In produzione serve HTTPS; in sviluppo basta `localhost`.

```bash
npm start
```

Apri `http://localhost:4173` e scegli “Installa app”. Su iOS usa Safari → Condividi → “Aggiungi alla schermata Home”. Il service worker memorizza il guscio dell’app; import e dati backend richiedono la connessione API. La build MVP copre picker multiplo, limite 50 file, avanzamento, duplicati, errori e revisione; non include store publishing o dati sensibili reali.

## Local API server

Run `python3 server.py --store .screenshot-data --port 4173`, then open `http://127.0.0.1:4173`. The browser UI uploads to `POST /api/ingest`; the native client uses the same real HTTP contract. Originals are content-addressed by SHA-256, write-once, and never returned for editing. Re-uploading identical bytes returns `duplicate` with the existing stable ID. Run `npm test`, `pytest`, and `swift test --package-path iOS`.
