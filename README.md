# Mystery Case Solver

A small detective investigation game built with HTML, CSS, vanilla JavaScript, Flask, PyMongo, and MongoDB. The three cases are deterministic and fictional. Case solutions stay on the server until an accusation is submitted.

## Requirements

- Python 3.10 or newer
- MongoDB Community Server running locally, or a MongoDB connection URI
- MongoDB Compass (for the class demonstration)

## Run locally

From this project folder, open PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

If MongoDB is running locally, the example URI works as written:

```text
MONGO_URI=mongodb://localhost:27017/mystery_case_solver
```

Edit `.env` on your computer if your MongoDB connection uses a different URI. Do not commit `.env` or share a URI containing a password.

Seed the three built-in cases and start Flask:

```powershell
py -m backend.seed
py -m backend.app
```

Open <http://127.0.0.1:5000>. The home page opens on each visit. If a browser has a saved investigation, use **Resume investigation** to continue it. Starting the seed command again refreshes the case documents and preserves investigation documents.

## MongoDB Compass demonstration

Connect Compass to the same MongoDB server from `.env` (for a local server, `mongodb://localhost:27017`). Open database `mystery_case_solver`:

- `cases`: three case documents with embedded `suspects`, `evidence`, and `timeline` arrays, plus a server-side `solution` object.
- `investigations`: one document for each investigation, with evidence ID arrays, embedded notes and connections, theory, accusation, and result.

In the website, open a case, begin investigating, investigate or mark evidence, add a note, add evidence to the board, save a theory, and submit an accusation. Refreshing returns to the home page; use **Resume investigation** to continue the saved case. In Compass, refresh the `investigations` collection to inspect persisted changes. The solution endpoint refuses access before an accusation is stored.

## API overview

- `GET /api/health`, `GET /api/cases`, `GET /api/cases/CASE001`
- `POST /api/investigations` with `{"caseId":"CASE001"}`
- `GET /api/investigations/<id>`
- `PATCH /api/investigations/<id>/evidence/<evidenceId>` with action `investigate`, `important`, or `board`
- `POST /api/investigations/<id>/notes`
- `POST` / `DELETE /api/investigations/<id>/connections`
- `PUT /api/investigations/<id>/theory`
- `POST /api/investigations/<id>/accuse`
- `GET /api/investigations/<id>/solution` (only after submission)

All case and investigation data is stored in MongoDB; browser storage only remembers the current investigation ID so it can be resumed.
