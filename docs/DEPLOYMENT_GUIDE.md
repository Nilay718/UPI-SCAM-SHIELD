# UPI Scam Shield — Deployment Guide (Render Free Tier)

Yeh guide aapko UPI Scam Shield application ko **Render (Free Tier)** par deploy karne mein madad karegi taaki aap ise apne LinkedIn network aur resume par live link ke sath share kar sakein.

---

## Prerequisites (Taiyari)

1. Ek **GitHub Account** jahan aapne apni repository `Nilay718/UPI-SCAM-SHIELD` push ki hui hai.
2. Ek **Render Account** (Aap free mein signup kar sakte hain [render.com](https://render.com/) par GitHub ke zariye).
3. (Optional) Ek **OpenRouter API Key** agar aap AI detection enable karna chahte hain (agar nahi hai, toh system fallback karke deterministic rules se chalega).

---

## Step 1: Push Latest Changes to GitHub

Humne aapki `render.yaml` file ko modify karke persistent disk ki requirement hata di hai taaki yeh Render ke **Free Tier** par bina kisi payment details ke deploy ho sake. 

Humne is change ko local git repository mein commit kar diya hai. Ab aapko ise GitHub par push karna hai. Apne terminal mein project root directory (`UPI-SCAM_SHIELD03`) par jaakar niche di gayi command chalayein:

```bash
git push origin main
```

---

## Step 2: Create a Web Service on Render

1. **Render Dashboard** ([dashboard.render.com](https://dashboard.render.com/)) par login karein.
2. Top-right corner mein **New +** button par click karein aur **Web Service** select karein.
3. **Connect a repository** section mein, apni GitHub repository search karein: `UPI-SCAM-SHIELD` aur **Connect** par click karein.
4. Niche di gayi details configure karein:
   - **Name**: `upi-scam-shield` (ya jo bhi aapko pasand ho)
   - **Region**: `Singapore (Southeast Asia)` or `Oregon (US West)` (Aapke location ke hisab se Singapore fast rahega)
   - **Branch**: `main`
   - **Root Directory**: *Khali chhodein (blank)*
   - **Runtime**: `Docker` (Render ise automatically detect kar lega humare root level `Dockerfile` se)
   - **Instance Type**: Select **Free** ($0/month)

---

## Step 3: Configure Environment Variables

Kuch settings aur API Keys connect karne ke liye, Deployment page par scroll down karke **Advanced** dropdown par click karein ya **Environment Variables** tab mein niche diye gaye keys add karein:

| Key | Value | Explanation |
|-----|-------|-------------|
| `FEEDBACK_DB_PATH` | `/app/feedback.sqlite3` | SQLite database location inside container. |
| `OPENROUTER_API_KEY` | `YOUR_API_KEY_HERE` | *Optional:* Aapki OpenRouter API Key (AI features ke liye). Agar key nahi hai toh ise add na karein, rules-based mode automatically active ho jayega. |
| `CORS_ALLOW_ORIGINS` | `http://localhost:8000` | Local and default allowed origins. |

---

## Step 4: Deploy and Verify

1. **Deploy Web Service** par click karein.
2. Render image build aur deployment start karega (Isme 4-6 minutes lag sakte hain kyunki Docker container ke andar Tesseract OCR aur Python dependencies install hoti hain).
3. Jab deployment status **Live** show hone lage, tab top-left corner mein diye gaye URL (jaise `https://upi-scam-shield.onrender.com`) par click karein.
4. **Health Check Verify karein**: `https://your-app-name.onrender.com/health` par jaakar dekhein ki `{"status":"ok"}` response aa raha hai ya nahi.
5. `/analyzer` open karke SMS/Screenshot analysis test karein!

---

## Step 5: Draft your LinkedIn Post!

Aapki deployment link taiyar hone ke baad, aap niche di gayi template ko use karke LinkedIn par post kar sakte hain taaki maximum engagement aur appreciation mile:

```text
🚀 Excited to share my latest project: UPI Scam Shield — An AI-powered hybrid fraud detection system!

With UPI/payment scams on the rise (OTP frauds, collect-to-receive scams, remote screen sharing takeovers), I built a system designed to protect users by evaluating transaction threats in real-time.

💡 What makes UPI Scam Shield unique:
1️⃣ Hybrid Engine: Combines deterministic, rule-based checks (for speed, cost-efficiency, and transparent evidence) with an LLM-powered engine (OpenRouter API with Gemini/GPT fallbacks) for contextual understanding.
2️⃣ Screen-ready OCR: Users can upload WhatsApp/SMS screenshots directly. The Tesseract OCR pipeline extracts text and matches common social-engineering indicators.
3️⃣ Adaptive Learning: Integrates a local SQLite-backed feedback loop that learns from user-reported false negatives to capture evolving scam patterns.

🛠️ Tech Stack:
- Backend: FastAPI (Python)
- OCR Engine: Tesseract OCR
- AI Orchestration: OpenRouter (Gemini & GPT)
- Database: SQLite
- Frontend: HTML5, CSS3 (sleek dark theme with micro-animations), Vanilla JS

🔗 Live Demo: [PASTE_YOUR_RENDER_URL_HERE]/analyzer
📁 GitHub Repository: https://github.com/Nilay718/UPI-SCAM-SHIELD

Feedback and suggestions are highly welcome! Let me know what you think. 👇

#python #fastapi #ai #security #fintech #ocr #productdevelopment #softwareengineering #fraudprevention
```

---

## Important Tips for Portfolio Demos

- **Cold Starts**: Render ke Free Tier services inactive hone par sleep mode mein chali jaati hain. Agar aap 15-20 mins baad website open karenge, toh use build wake-up hone mein ~50 seconds lag sakte hain. LinkedIn post mein likh sakte hain: *"Note: Live demo may take 40-50 seconds to load initially due to Render free tier cold starts."*
- **Persistent Data**: Kyunki hum Free tier use kar rahe hain bina disk volume ke, SQLite data app restart hone par reset ho jayega. Demo and feedback testing ke liye yeh bilkul safe aur expected hai.
