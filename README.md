# UPI Scam Shield – AI-Powered Fraud Detection System

Hybrid scam detection for UPI/payment-related scams from **text messages** and **screenshots** (OCR), combining:

- **Rule-based detection** (fast, deterministic, explainable)
- **AI-based detection** (OpenRouter LLM; optional with graceful fallback)

## Project Overview

UPI Scam Shield helps reduce **UPI scam losses** by giving users (and support teams) a fast, explainable **risk score**, **scam verdict**, and **next actions** from either:

- **Text** (SMS/WhatsApp message copy)
- **Screenshot** (OCR → analysis)

### Why this is useful (business impact)

- **Consumer safety**: flags common high-loss patterns (OTP/UPI PIN requests, collect-to-receive trick, remote access apps).
- **Support efficiency**: consistent, explainable triage (“why flagged”) → faster resolution & fewer false escalations.
- **Enterprise readiness**: deterministic rules + safety-first defaults; AI is optional and can be disabled.

### What’s innovative here

- **Hybrid decisioning**: rules-first explainability + optional LLM generalization with fallback.
- **Screenshot-ready**: OCR pipeline makes the demo real-world (WhatsApp/SMS screenshots are common in India).
- **Evidence + feedback loop**: UI shows rule hits + stores local feedback (SQLite) for tuning.

## Architecture (Hybrid Pipeline)

User Input (Text/Image)  
→ Input Agent  
→ OCR Agent (image only)  
→ Rule-Based Engine  
→ AI Detection Engine (OpenRouter; fallback models)  
→ Risk Scoring Agent  
→ Decision Engine (merge rule + AI)  
→ Explanation Agent  
→ Final Output (risk + reasons + actions)

### Architecture diagram (for reviewers)

```text
                 ┌───────────────────────────┐
Text / Screenshot│        Frontend UI        │
   (Upload/Copy) └─────────────┬─────────────┘
                               │
                               v
                       ┌───────────────┐
                       │   FastAPI API  │
                       └───────┬───────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          v                    v                    v
   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
   │ OCR Agent    │      │ Rule Engine  │      │ LLM Engine   │
   │ (Tesseract)  │      │ (determin.)  │      │ (OpenRouter) │
   └──────┬──────┘      └──────┬──────┘      └──────┬──────┘
          │                    │                    │
          └──────────────┬─────┴──────────────┬─────┘
                         v                    v
                    ┌─────────────────────────────┐
                    │ Decision Engine (merge)      │
                    │ Risk score + verdict + why   │
                    └───────────────┬─────────────┘
                                    v
                           ┌─────────────────┐
                           │ Output + Actions │
                           └─────────────────┘
```

## Project Structure

- `backend/` FastAPI API + pipeline
- `frontend/` static UI (dark theme)
- `docs/` **Full project brief** (architecture, APIs, PPT outline): `docs/PROJECT_FULL_BRIEF.md` — open `docs/PROJECT_FULL_BRIEF.html` in browser → **Print → Save as PDF**
- **Submission pack:** `docs/SUBMISSION_CHECKLIST.md` · **Architecture (1–2 pages):** `docs/ARCHITECTURE_SUBMISSION.md` · **Impact model:** `docs/IMPACT_MODEL.md`

## Requirements

- Python 3.10+ (recommended 3.11)
- Tesseract OCR installed (for image analysis)
  - Windows: install Tesseract and ensure `tesseract.exe` is on PATH, or set `TESSERACT_CMD`.
  - Optional: install Hindi language data for Tesseract (so OCR can read Hindi screenshots). The app falls back to English OCR if Hindi data isn't available.

## Setup

### 1) Create venv and install deps

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2) (Optional) Configure OpenRouter

Create `backend/.env` from `backend/env.example`:

- `OPENROUTER_API_KEY`: your key
- `OPENROUTER_MODELS`: comma-separated model ids (fallback order)

If you don’t set a key, the system still works using **rules-only** mode.

### 3) Run the server

```bash
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open the UI at: `http://localhost:8000/`

## Docker (recommended for deploy & demos)

- **Image:** `Dockerfile` at repo root — Python 3.11, **Tesseract** (OCR), FastAPI, static `frontend/`.
- **Compose:** `docker-compose.yml` maps port **8000**, persists SQLite on volume `feedback_data` (adaptive learning survives restarts).
- **Health check:** `GET /health`

```bash
# Repo root (where Dockerfile lives)
docker compose up --build
# → http://localhost:8000/   |   http://localhost:8000/analyzer
```

**Optional LLM in Docker:** copy `.env.example` → `.env` in the **repo root** and set `OPENROUTER_API_KEY` (Compose reads it). No key → **rules-only** still works.

**Deploy:** set `CORS_ALLOW_ORIGINS` in `.env` to your **public https origin(s)** (comma-separated). Never commit real `.env` or API keys.

Step-by-step (Docker + GitHub): see **`docs/DOCKER_AND_GITHUB.md`**.

## Live Demo Script (2–3 minutes)

### Demo Step 1 (baseline: safe message)

Paste:
- “Your order shipped. Track it in the app.”

Expected:
- **LOW risk**, scam verdict likely **NO**, minimal reasons.

### Demo Step 2 (classic scam: OTP + urgency + link)

Paste:
- “Your account blocked. Click link immediately. Share OTP to activate UPI.”

Expected:
- **HIGH risk**, scam verdict **YES**
- Reasons mention **OTP** + **urgency/threat** + **suspicious link**

### Demo Step 3 (India-first scam: collect-to-receive)

Paste:
- “To receive money, accept the collect request in your UPI app.”

Expected:
- **HIGH risk**, scam verdict **YES**
- Reason mentions collect request is **payment approval**

### Demo Step 4 (high impact: remote access takeover)

Paste:
- “Install AnyDesk for bank refund support and share the code.”

Expected:
- **HIGH risk**, scam verdict **YES**

### Demo Step 5 (screenshot OCR)

Upload a WhatsApp/SMS screenshot containing scam text (OTP/collect/link). Show:
- Extracted text panel (OCR)
- Evidence (rule hits) + suggested actions

## API

- `GET /analyze?text=...`  
  Optional query params (personalized risk): `sender_type` (`unknown`|`known`), `transaction_context` (`expected`|`unexpected`), `user_type` (`general`|`elderly`|`new_user`).
- `POST /analyze-image` (multipart: `file`, optional form fields `sender_type`, `transaction_context`, `user_type`)
- `GET /analyze-verbose?text=...` (includes internal evidence; same context params as above)
- `POST /analyze-image-verbose` (same form fields as image analyze)

**Response extras (backward compatible):** `analysis_log_id` (link feedback to this run), `intent`, `adaptive` (learned-pattern boost), `personalization`, `ocr_line_hints` (for chat-style OCR UI).

**Feedback:** `POST /feedback` JSON may include optional `analysis_log_id` from the last analyze response; misclassified **scam** messages (user marks SCAM, model said safe) update the **adaptive phrase library** in SQLite.

## Demo pack

- Demo messages (English + Hindi): `demo_assets/DEMO_MESSAGES.md`
- One-command demo run (Windows): `run_demo.ps1`
- **Adaptive learning demo** (live): open `/analyzer?demo=learn` or click **Learning demo** on the analyzer — step 1 runs a safe-looking message (LOW), step 2 asks you to **Mark as Scam**, step 3 re-analyzes with stricter context and shows **HIGH** + **Learning** badge when phrases are learned.

## Configuration (important for demos)

Create `backend/.env` (see `backend/env.example`). Optional knobs:

- `OPENROUTER_API_KEY`: enables AI; without it system runs **rules-only**
- `CORS_ALLOW_ORIGINS`: comma-separated origins (default local)
- `MAX_UPLOAD_MB`: max image upload size (default 6)
- `ALLOWED_IMAGE_CONTENT_TYPES`: e.g. `image/png,image/jpeg,image/webp`

## Example Test Cases

- “Your account blocked click link” → **HIGH**
- “Share OTP to verify account” → **HIGH**
- “Your order shipped” → **LOW**

## Notes (OCR)

If OCR fails due to missing Tesseract:
- Install it, then restart the server.
- Or set `TESSERACT_CMD` in `backend/.env` (full path to `tesseract.exe`).

## Quick Windows commands (copy/paste)

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### One-command demo run (recommended)

```powershell
.\run_demo.ps1
```

