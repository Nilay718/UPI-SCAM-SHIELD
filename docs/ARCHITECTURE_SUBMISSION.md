# Architecture Document — UPI Scam Shield  
*(~1–2 pages — agent roles, communication, tools, error handling)*

## 1. System overview

**UPI Scam Shield** is a **hybrid pipeline**: deterministic **rule & intent** components run first; an optional **LLM** (via OpenRouter) enriches detection and explanations; **SQLite** stores feedback and **adaptive learned phrases**. All orchestration happens in **`backend/app/pipeline.py`**; the **FastAPI** layer (`main.py`) exposes REST endpoints and serves the static UI.

---

## 2. Architecture diagram

```text
┌─────────────┐     ┌──────────────┐     ┌─────────────────────────────────────────┐
│   Browser   │────▶│   FastAPI    │────▶│  Pipeline (async)                        │
│  (UI/JSON)  │◀────│  main.py     │◀────│  _run_pipeline → analyze_text / verbose  │
└─────────────┘     └──────┬───────┘     └──────────────────┬──────────────────────┘
                           │                                │
         Image upload      │                                │
                           ▼                                ▼
                    ┌─────────────┐              ┌─────────────────────┐
                    │ OCR Agent   │              │ Intent (local+LLM)  │
                    │ ocr.py      │              │ intent_layer + llm  │
                    │ Tesseract   │              └──────────┬──────────┘
                    └──────┬──────┘                         │
                           │ text                           │
                           └──────────────┬─────────────────┘
                                          ▼
                    ┌─────────────────────────────────────────────┐
                    │ Rules Engine + Adaptive phrases (SQLite)     │
                    │ rules.py + feedback_db.get_adaptive_phrases  │
                    └─────────────────────┬───────────────────────┘
                                          ▼
                    ┌─────────────────────────────────────────────┐
                    │ LLM Detection Agent (optional)               │
                    │ llm.call_openrouter → merge_decision        │
                    └─────────────────────┬───────────────────────┘
                                          ▼
                    ┌─────────────────────────────────────────────┐
                    │ Context & personalization                    │
                    │ context_layer.apply_user_context             │
                    └─────────────────────┬───────────────────────┘
                                          ▼
                    ┌─────────────────────────────────────────────┐
                    │ Risk tier + verdict + actions + explanation  │
                    │ risk.py, explanation_generator, optional     │
                    │ LLM enrich (explain)                         │
                    └─────────────────────┬───────────────────────┘
                                          ▼
                                    JSON response
```

**Communication pattern:** synchronous in-process function calls (Python); **no message broker**. The only **external I/O** is **HTTP** to OpenRouter (optional) and **SQLite** file I/O for feedback/adaptive data.

---

## 3. Agent / module roles (mapping to “agents”)

| Role | Module(s) | Responsibility |
|------|-----------|------------------|
| **Input** | `main.py` | Accept text or image; validate size/type. |
| **OCR Agent** | `agents/ocr.py` | Extract text from screenshots using **Tesseract**; return text + optional warning. |
| **Intent Agent** | `agents/intent_layer.py` + `agents/llm.py` | Local keyword/heuristic intent; optional **LLM** intent; **merge** when LLM confidence beats local. |
| **Rules Agent** | `agents/rules.py` | Pattern/severity scoring; applies **adaptive boost** from learned phrases. |
| **LLM Detection Agent** | `agents/llm.py` | JSON-structured scam classification; **multi-model fallback** list. |
| **Decision Agent** | `agents/decision.py` | Merges rule output with LLM output (conservative merge). |
| **Context Agent** | `agents/context_layer.py` | Adjusts personalized risk from sender/transaction/user profile. |
| **Risk Agent** | `agents/risk.py` | Maps score → **LOW / MEDIUM / HIGH**. |
| **Explanation Agent** | `agents/explanation_generator.py`, `explain.py`, optional LLM enrich | Headline, bullets, education blocks, “why risky for you”. |
| **Memory / Learning** | `feedback_db.py` | Logs analysis; stores feedback; **adaptive_phrases** for future boosts. |

---

## 4. Tool integrations

| Tool | Purpose |
|------|---------|
| **Tesseract OCR** | Offline text extraction from uploaded images (`pytesseract`). |
| **OpenRouter API** | Optional cloud LLMs for intent, scam JSON, explanation polish; **no key ⇒ rules-only**. |
| **SQLite** | Local `feedback.sqlite3` (path overridable via `FEEDBACK_DB_PATH` in Docker). |
| **FastAPI + Uvicorn** | HTTP API and static file hosting for `frontend/`. |

---

## 5. Error-handling logic (high level)

| Failure | Behavior |
|---------|----------|
| **No OpenRouter API key** | LLM returns `available=False`; pipeline uses **rules + local intent**; `model_used` shows rules-only. |
| **LLM HTTP / timeout / bad JSON** | `llm.py` tries **next model** in `OPENROUTER_MODELS`; on total failure, falls back to **rule-only** decision path; errors captured in response metadata where applicable. |
| **JSON parse** | `_safe_json_extract` trims to first `{...}` block to tolerate model verbosity. |
| **OCR failure** | Image endpoints return **422** with user-facing message; no partial analyze on empty text. |
| **Image too large / wrong type** | **413 / 415** from `main.py` before OCR. |
| **SQLite** | Connections use context managers; `init_db` creates tables on startup; adaptive cache degrades gracefully if DB missing (defensive). |

---

## 6. Deployment note

**Docker** (`Dockerfile` + `docker-compose.yml`) bundles Python, Tesseract, and app code; SQLite persisted via volume. **`GET /health`** for uptime checks.

---

*End of architecture document (print-friendly; diagram can be redrawn in Canva/PPT from this ASCII.)*
