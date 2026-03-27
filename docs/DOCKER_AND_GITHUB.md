# Docker + GitHub — step-by-step (UPI Scam Shield)

Yeh guide assume karti hai: Windows ya Linux, **Docker Desktop** installed (Windows par WSL2 backend recommended).

---

## 1) Docker se pehle — kyun useful hai?

| Fayda | Explanation |
|--------|-------------|
| **Same environment everywhere** | Judges / server par “mere laptop pe chal raha tha” wala issue kam |
| **Tesseract bundled** | Image analysis ke liye alag se Tesseract install karne ki zaroorat nahi (container ke andar hai) |
| **Deploy easy** | Railway, Render, VPS, AWS — Dockerfile push karo, run karo |
| **SQLite persistence** | `docker-compose` volume se feedback DB delete nahi hoti har restart par |

**Dhyan:** Docker image mein **OpenRouter API key bake mat karo**. Runtime par env se do (`.env` ya host secrets).

---

## 2) Local pe Docker test karna

### A) Docker Desktop on karo

### B) Terminal — project **root** folder (jahan `Dockerfile` hai)

```bash
cd path/to/UPI-SCAM_SHIELD03
docker compose up --build
```

Pehli baar **build** thoda time lega (Tesseract + pip install).

### C) Browser

- **App:** http://localhost:8000/
- **Analyzer:** http://localhost:8000/analyzer
- **Health:** http://localhost:8000/health → `{"status":"ok",...}`

### D) Optional: LLM enable (OpenRouter)

1. Repo root mein `.env.example` ko copy karke `.env` banao:
   - Windows PowerShell: `Copy-Item .env.example .env`
2. `.env` kholo, `OPENROUTER_API_KEY=` ke baad apni key likho.
3. `docker compose down` phir `docker compose up --build` (ya sirf `up` agar image same hai).

Key nahi doge to bhi app **rules-only** mode mein chalegi — demo ke liye theek hai.

### E) Band karna

Terminal mein `Ctrl+C`, phir:

```bash
docker compose down
```

Volume data (SQLite) **named volume** mein rehti hai — `docker compose down` se delete nahi hoti; poora hataane ke liye `docker compose down -v` (optional, **feedback wipe** ho jayega).

---

## 3) Sirf `docker build` / `docker run` (compose ke bina)

```bash
docker build -t upi-scam-shield .
docker run --rm -p 8000:8000 -e FEEDBACK_DB_PATH=/data/feedback.sqlite3 -v upi_data:/data upi-scam-shield
```

Compose use karna zyada aasaan hai (ports + volume + env ek jagah).

---

## 4) GitHub pe upload — safe tareeka

### A) `.gitignore` check (already repo mein)

Commit **mat** karo:

- `backend/.env`, root **`.env`** (secrets)
- `backend/.venv/`
- `backend/feedback.sqlite3` (local DB)
- `__pycache__`

### B) Pehli baar Git (agar repo abhi git init nahi hai)

```bash
cd UPI-SCAM_SHIELD03
git init
git add .
git status   # .env files na dikhen — agar dikhen to unhe ignore karo
git commit -m "Initial commit: UPI Scam Shield"
```

### C) GitHub par naya repository

1. github.com → **New repository** (public/private).
2. **README** GitHub par mat banao agar tumhare paas already README hai — warna merge conflict.

### D) Remote add + push

```bash
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

`YOUR_USERNAME` / `YOUR_REPO` apne hisaab se.

---

## 5) Deploy ke time CORS

Jab app **kisi domain** par chale (e.g. `https://upi-demo.onrender.com`), server ko batana padta hai ki browser se request allow ho.

Root `.env` mein:

```env
CORS_ALLOW_ORIGINS=https://your-app.onrender.com,http://localhost:8000
```

Phir container / platform par yeh env set karo (har platform alag UI: Environment variables).

---

## 6) Common issues

| Problem | Fix |
|---------|-----|
| Port 8000 busy | `docker-compose.yml` mein `"8001:8000"` karke `http://localhost:8001` use karo |
| OCR fail | Container mein Tesseract hai; agar custom build ho to `Dockerfile` mein `tesseract-ocr` verify karo |
| API key kaam nahi | `.env` repo **root** (compose ke saath), variable naam `OPENROUTER_API_KEY` |
| GitHub par `.env` leak ho gaya | Turant key **rotate** karo OpenRouter dashboard se; history se hataana mushkil — nayi repo safer |

---

## 7) Files jo is Docker setup se judi hain

- `Dockerfile` — image build
- `docker-compose.yml` — run + volume + env
- `.dockerignore` — build chhota / fast
- `.env.example` — template (commit safe)
- `backend/app/feedback_db.py` — `FEEDBACK_DB_PATH` env support
- `GET /health` — `main.py` (load balancers)

---

*Short version README mein **Docker** section mein bhi hai.*
