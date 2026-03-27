# Impact Model — UPI Scam Shield  
*(Quantified estimate — assumptions stated; back-of-envelope math)*

## 1. Problem scale (context)

- UPI transaction volume in India is **very large** (billions/month); scam reports and user complaints continue to rise.
- **Assumption A:** A meaningful fraction of scams start with a **single message** (SMS/WhatsApp) that users could **screen before acting**.

We do **not** claim to stop all fraud—only to **reduce** incidents where a quick, explainable check changes user behavior.

---

## 2. Metric 1 — Time saved (support / fraud desk)

**Story:** Each ambiguous message that currently becomes a **5–10 minute** support call could be **triaged in &lt; 30 seconds** with automated risk + reasons.

| Assumption | Value |
|------------|--------|
| B1 — Tickets/calls per day that are “message triage” (bank/UPI scale) | **500** (illustrative mid-size) |
| B2 — Minutes saved per automated triage vs manual | **4 min** (8 min → 4 min) |
| B3 — Working days / year | **250** |

**Annual minutes saved** = 500 × 4 × 250 = **500,000 minutes** ≈ **8,333 hours** / year.

**FTE equivalent (rough):** 8,333 ÷ (8 × 250) ≈ **4.2 FTE** of pure triage time *if* all that time were reassigned (upper bound; reality is partial adoption).

**Assumptions to state in pitch:** B1–B3 are **illustrative**; real ops would replace B1 with internal ticket data.

---

## 3. Metric 2 — Loss avoided (user side, conservative)

**Story:** If the product prevents **one** high-value scam approval per **N** active users per month, aggregate loss avoided grows with adoption.

| Assumption | Value |
|------------|--------|
| C1 — Average prevented loss per true-positive stop | **₹5,000** (many scams aim higher; we stay conservative) |
| C2 — Probability a user **follows** “HIGH risk → don’t pay” when shown | **20%** (education + friction helps; not everyone complies) |
| C3 — Monthly active users (MAU) of the tool | **10,000** (pilot / bank partnership scale) |
| D — Share of MAU who receive **at least one** HIGH-risk message per month | **5%** |

**Expected HIGH-risk exposures/month** = 10,000 × 0.05 = **500**.

**Expected scams prevented/month** (if HIGH is right often enough) ≈ 500 × 0.20 × *detection precision*.

**Assumption C4 — Precision of HIGH** (of all HIGH alerts, fraction that would have led to loss): **30%** (conservative; many HIGH are precautionary).

**Rough loss avoided / month** = 500 × 0.20 × 0.30 × ₹5,000 = **₹1,50,000 / month** ≈ **₹18 L/year** at these toy numbers.

**Sensitivity:** If MAU = **50k** and D = **8%**, same formula scales ~**4×** (linear in MAU and D).

---

## 4. Metric 3 — Cost of running (rough)

| Item | Order of magnitude |
|------|---------------------|
| OpenRouter LLM | Usage-based; **optional** — rules-only mode ≈ **API cost ₹0** for inference |
| Hosting (small VM / container) | **₹500–3,000/month** depending on provider |
| Engineering maintenance | One small team iteration |

**Net:** For NGOs / banks, **cost per check** can be driven very low vs **cost per fraud incident**.

---

## 5. How to say this in the pitch (one paragraph)

> “We anchor impact on **time saved at triage** (minutes × ticket volume) and **loss avoided** using **conservative** assumptions on MAU, share of risky messages, user compliance, and precision. Numbers are **order-of-magnitude**; replacing assumptions with partner data (ticket counts, fraud loss reports) would tighten the model.”

---

## 6. Limitations

- Field **precision/recall** depends on message mix and adversarial evolution of scams.
- **Screenshot OCR** quality varies; Hindi support depends on Tesseract language packs.
- **Adaptive learning** improves over feedback volume—cold start is rules-heavy.

---

*This document satisfies “quantified estimate + assumptions”; refine B/C/D with any real data you obtain from pilots.*
