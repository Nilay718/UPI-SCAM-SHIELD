# Submission checklist

Use this against your **submission requirements** (GitHub, video, architecture, impact).

---

## 1. Public GitHub repository

| Task | Status |
|------|--------|
| Repo **public** | ☐ |
| **All source code** pushed (backend + frontend + Docker files) | ☐ |
| **README** has clear setup: local Python path + **Docker** path | ☐ |
| **No secrets** in repo (`.env` gitignored; only `env.example` / `.env.example`) | ☐ |
| **Commit history** shows build over time — **not** only one giant “final” commit | ☐ |

### Commit history tip

- Make **several meaningful commits**, e.g. order: `feat: backend pipeline` -> `feat: frontend analyzer` -> `chore: docker` -> `docs: README + architecture` -> `docs: impact model`.
- If everything is already one commit locally, you can still **split** with interactive history *only if you know Git well*; easier: **add docs now** and push **new commits** so history shows evolution.

---

## 2. 3-minute pitch video

| Must include | Your project angle |
|--------------|-------------------|
| **Problem** | UPI/SMS scams, OTP/collect/remote access |
| **Solution** | Hybrid rules + optional AI, text + screenshot OCR |
| **Demo** | **Start -> finish:** paste safe text -> show LOW -> paste scam -> show HIGH + reasons -> optional **image upload** OR **learning demo** (`/analyzer?demo=learn`) |
| **Agent workflow** | Narrate: Input -> (OCR if image) -> rules + intent -> LLM optional -> decision -> explanation (see `docs/ARCHITECTURE_SUBMISSION.md`) |

**Length:** ~3 minutes; rehearse with a timer.

---

## 3. Architecture document (1-2 pages)

| Deliverable | Location in repo |
|-------------|------------------|
| Diagram + description | **`docs/ARCHITECTURE_SUBMISSION.md`** |
| Optional | Export same content to **PDF** or paste key diagram into PPT |

Covers: **agent roles**, **how modules connect**, **tools** (Tesseract, OpenRouter, SQLite), **error handling**.

---

## 4. Impact model (quantified)

| Deliverable | Location |
|-------------|----------|
| Assumptions + back-of-envelope math | **`docs/IMPACT_MODEL.md`** |

You can add **one slide** in PPT summarizing **two numbers** (e.g. support hours saved + illustrative loss avoided) and say "assumptions in appendix."

---

## 5. Quick links

- README: setup + Docker  
- `docs/ARCHITECTURE_SUBMISSION.md`  
- `docs/IMPACT_MODEL.md`  
- `docs/PROJECT_FULL_BRIEF.md` (optional extra context)

---

*Tick each box before final upload.*
