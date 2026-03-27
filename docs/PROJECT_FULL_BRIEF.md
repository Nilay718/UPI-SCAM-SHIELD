# UPI Scam Shield — Complete Project Brief  
*(Documentation for reports & 6–7 slide PPT)*

---

## 1. One-line pitch

**UPI Scam Shield** is a **hybrid AI + rule-based** system that detects **UPI/payment scams** from **text** or **screenshots (OCR)**, returns **risk level**, **scam verdict**, **explainable reasons**, and **actionable steps**—with optional **LLM enrichment** and **adaptive learning** from user feedback (SQLite).

**Target context:** product demo / enterprise pilot—consumer safety + support triage.

---

## 2. Problem & why it matters

| Problem | Impact |
|--------|--------|
| UPI/SMS/WhatsApp scams (OTP, fake links, collect-request tricks, remote access) | Direct financial loss, account takeover |
| Users can’t quickly judge message safety | Wrong trust → payment / credential leak |
| Support teams need consistent triage | Faster resolution, fewer false escalations |

**Solution:** Fast, **explainable** analysis with **India-relevant patterns** (OTP, collect request, AnyDesk, etc.) + **screenshot OCR** for real chat UI.

---

## 3. High-level architecture

```
User (Web UI)
    │
    ▼
FastAPI (backend/app/main.py)
    │
    ├── Text path ─────────────────────────────────────┐
    │                                                   │
    └── Image path ──► OCR (Tesseract) ──► text ──────┤
                                                        │
                                                        ▼
                                            Pipeline (pipeline.py)
    ┌───────────────────────────────────────────────────────────┐
    │ 1. Rules engine (deterministic patterns, severity)         │
    │ 2. Intent layer (message intent + risk boost)              │
    │ 3. Context layer (sender / transaction / user type)       │
    │ 4. Adaptive phrases (SQLite: learned from feedback)       │
    │ 5. LLM (OpenRouter) — optional intent + explanation enrich  │
    │ 6. Risk scoring → LOW / MEDIUM / HIGH                     │
    │ 7. Decision merge (rules + AI)                            │
    │ 8. Explanation generator (structured + optional LLM)       │
    └───────────────────────────────────────────────────────────┘
                                                        │
                                                        ▼
JSON: risk, is_scam, confidence, reasons, actions,
      explanation, intent, personalization, adaptive, analysis_log_id, …
```

**Design principles**

- **Rules-first:** Works without API keys (**rules-only** mode).
- **Hybrid:** LLM adds generalization; merge logic keeps outputs consistent.
- **Traceability:** Verbose mode exposes rule hits / internal evidence for demos.

---

## 4. Component map (backend)

| Module / area | Role |
|---------------|------|
| `app/main.py` | FastAPI routes, static frontend, CORS, startup DB init |
| `app/pipeline.py` | End-to-end `analyze_text` / `analyze_text_verbose` orchestration |
| `app/agents/rules.py` | Pattern matching, rule hits, scores |
| `app/agents/risk.py` | Score → risk tier |
| `app/agents/decision.py` | Merge rule + LLM outputs |
| `app/agents/intent_layer.py` | Intent detection + boosts |
| `app/agents/context_layer.py` | User/sender/transaction context → personalization |
| `app/agents/llm.py` | OpenRouter calls (intent, enrich, etc.) |
| `app/agents/explanation_generator.py` | Rich explanations, “why risky for you” |
| `app/agents/ocr.py` | Image → text (Tesseract) |
| `app/agents/ocr_line_hints.py` | Hints for OCR chat UI |
| `app/feedback_db.py` | SQLite: feedback, analysis logs, adaptive phrases |
| `app/schemas.py` | Pydantic models for API responses |
| `app/settings.py` | Env-based configuration |

**Frontend**

| File | Role |
|------|------|
| `frontend/index.html` | Landing |
| `frontend/analyzer.html` | Main analyzer UI |
| `frontend/app.js` | API calls, rendering, learning demo, micro-animations |
| `frontend/styles.css` | Theme, learning badge, risk transitions |

---

## 5. Tech stack

| Layer | Technology |
|-------|------------|
| API | **FastAPI** (async) |
| Language | **Python 3.10+** (3.11 recommended) |
| OCR | **Tesseract** (optional Hindi data) |
| AI (optional) | **OpenRouter** (multi-model fallback list in `env.example`) |
| Storage | **SQLite** (feedback + adaptive phrases) |
| Frontend | Static **HTML/CSS/JS** (served under `/static`) |

---

## 6. API summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Landing page |
| GET | `/analyzer` | Analyzer UI |
| GET | `/analyze?text=...` | Standard analysis |
| GET | `/analyze-verbose?text=...` | Analysis + internal evidence |
| POST | `/analyze-image` | Multipart image → OCR → analyze |
| POST | `/analyze-image-verbose` | Image + verbose evidence |
| POST | `/feedback` | User label (SCAM / NOT_SCAM); optional `analysis_log_id` |
| GET | `/feedback-stats` | Aggregate feedback stats |

**Context query/form fields (personalization):**

- `sender_type`: `unknown` \| `known`
- `transaction_context`: `expected` \| `unexpected`
- `user_type`: `general` \| `elderly` \| `new_user`

**Response highlights:** `final_decision`, `explanation`, `intent`, `personalization`, `adaptive`, `analysis_log_id`, `extracted_text` (images), `ocr_line_hints`, `model_used`.

---

## 7. Adaptive learning (feedback loop)

1. Each analysis can log an **`analysis_log_id`**.
2. User submits **feedback** with optional linkage to that log.
3. Misclassified cases (e.g. user marks **SCAM** when model was lenient) can contribute **learned phrases** stored in SQLite.
4. Future runs may apply an **adaptive score boost** when those phrases match—surfaced in UI as **Learning** badge / boost bar.

**Demo:** `/analyzer?demo=learn` or **Learning demo** button (LOW → feedback → re-analyze → HIGH + learning UI).

---

## 8. Configuration (`backend/.env` from `env.example`)

- `OPENROUTER_API_KEY` — enables LLM paths; empty → **rules-only**
- `OPENROUTER_MODELS` — comma-separated fallback models
- `OPENROUTER_MODEL_INTENT`, `OPENROUTER_MODEL_ENRICH` — optional stronger models
- `LLM_INTENT_ENABLED`, `LLM_EXPLANATION_ENRICH_ENABLED`
- `TESSERACT_CMD` — Windows path to `tesseract.exe` if not on PATH
- `CORS_ALLOW_ORIGINS`, `MAX_UPLOAD_MB`, `ALLOWED_IMAGE_CONTENT_TYPES` (via settings)

---

## 9. Project folder layout

```
UPI-SCAM_SHIELD03/
├── README.md
├── run_demo.ps1              # Windows one-command demo
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── pipeline.py
│   │   ├── settings.py
│   │   ├── schemas.py
│   │   ├── feedback_db.py
│   │   └── agents/           # rules, risk, llm, ocr, intent, context, …
│   ├── requirements.txt
│   └── env.example
├── frontend/
│   ├── index.html
│   ├── analyzer.html
│   ├── app.js
│   └── styles.css
├── demo_assets/
│   └── DEMO_MESSAGES.md
└── docs/
    └── PROJECT_FULL_BRIEF.md   # this file
```

---

## 10. Suggested 6–7 slide outline (PPT)

| Slide | Title | Content to copy |
|-------|--------|-----------------|
| **1** | Title | UPI Scam Shield — Hybrid AI + Rules Fraud Detection |
| **2** | Problem & impact | Consumer losses, OTP/collect/remote access scams; need fast explainable triage |
| **3** | Solution overview | Text + screenshot OCR; risk + verdict + reasons + actions |
| **4** | Architecture | Diagram from §3 + “rules-first, optional LLM, SQLite learning” |
| **5** | Innovation | Hybrid explainability, India-first patterns, OCR, feedback loop |
| **6** | Demo flow | Safe message → scam message → optional image; learning demo URL |
| **7** | Tech & roadmap | FastAPI, Tesseract, OpenRouter, SQLite; future: more languages, API hardening |

---

## 11. Run commands (reference)

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

UI: `http://127.0.0.1:8000/` — Analyzer: `/analyzer`

---

## 12. How to get a PDF from this repo

1. Open **`docs/PROJECT_FULL_BRIEF.html`** in **Chrome / Edge**.
2. **Ctrl+P** → Destination: **Save as PDF** → Save.

*(Same content as this Markdown, formatted for A4 print.)*

---

*Generated for documentation and presentation prep — aligned with `README.md` and current codebase structure.*
