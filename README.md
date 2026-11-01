# Mango cultivar identification

Upload photos of a mango tree's fruit or leaves and get the 10 most likely cultivars.

| Folder | What it is |
|---|---|
| `client/` | Next.js web app ([client/README.md](client/README.md)) |
| `server/` | FastAPI backend that runs the models on Triton ([server/README.md](server/README.md)) |
| `ml-models/` | Model training and experiments ([ml-models/README.md](ml-models/README.md)) |

## Run locally

Until trained models exist, the backend runs in mock mode with random but repeatable scores.

**Backend**, in PowerShell (first time: create the venv and install, see `server/README.md`):

```powershell
cd server
$env:MOCK_INFERENCE="true"; .venv\Scripts\uvicorn app.main:app --port 8080
```

**Frontend**, in a second terminal (first time: `npm ci`):

```powershell
cd client
npm run dev
```

Open http://localhost:3000. API docs are at http://localhost:8080/docs.
