# Mango Cultivar Identification 🥭

AI-assisted mango cultivar identification developed for University of Florida Senior Design (CIS 4914) in collaboration with Dr. Jha's research group.

This tool helps agricultural growers and exporters—such as commercial orchards in the São Francisco Valley (Petrolina/Juazeiro, Brazil)—accurately identify mango varieties from photos of whole exterior fruit and cut interior flesh.

---

## Quick Start (Run Locally in 2 Minutes)

You only need **Node.js 18+** and **Python 3.12** with [`uv`](https://docs.astral.sh/uv/) (recommended) or standard `pip`.

### 1. Start the Backend
The backend runs in **Mock Inference Mode** by default for evaluation, meaning you do not need GPU hardware or large model weight files to test the complete user experience.

```bash
cd server
uv sync
MOCK_INFERENCE=true uv run uvicorn app.main:app --port 8080
```
*(On Windows PowerShell, use: `$env:MOCK_INFERENCE="true"; uv run uvicorn app.main:app --port 8080`)*

The API server will run at `http://localhost:8080`. Interactive Swagger docs are available at `http://localhost:8080/docs`.

### 2. Start the Frontend
In a new terminal window:

```bash
cd client
npm install
npm run dev
```

Open **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## Key Features for Evaluators

- **Bilingual Interface (`🇺🇸 EN` / `🇧🇷 PT`)**: Click the flag button in the top navigation bar to toggle between English and Brazilian Portuguese.
- **Example Photo Guidance**: Click **"See an Example 👁️"** on either upload card to view reference photos and framing tips for exterior fruit or cut flesh views.
- **Interactive Results**: Ranked predictions with confidence match scores, fruit descriptions, and expandable cultivar traits.
- **Data Privacy (LGPD Compliance)**: Uploaded photos are processed strictly in-memory and are never stored, logged, or shared (LGPD Lei nº 13.709/2018).
- **Secure File Validation**: Client and server reject non-image files, corrupted images, and uploads exceeding 10 MB per photo.

---

## Running the Automated Test Suite

To verify system reliability and code quality across the stack:

```bash
# 1. Test backend API routes & validation (7 tests)
cd server && uv run pytest

# 2. Test ML data pipelines & augmentation (41 tests)
cd ../ml-models && uv run pytest

# 3. Test frontend TypeScript & build
cd ../client && npm run build
```

---

## Repository Structure

| Folder | Technology | Description |
|---|---|---|
| [`client/`](client/) | Next.js 16, React 19, Tailwind CSS | Web app with responsive UI, photo upload previews, and i18n support |
| [`server/`](server/) | FastAPI, Python 3.12, ONNX Runtime, UV | REST API handling image preprocessing, security validation, and inference routing |
| [`ml-models/`](ml-models/) | PyTorch, Albumentations, UV | Model training experiments, data augmentation, and ONNX export pipelines |

---

## License

This project is open-source under the [MIT License](LICENSE).
