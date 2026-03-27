const $ = (id) => document.getElementById(id);

let lastAnalysis = null;
/** Previous risk tier for LOW→HIGH transition animation */
let lastRenderedRisk = null;

const statusEl = $("status");
const resultEl = $("result");
const reasonsEl = $("reasons");
const actionsEl = $("actions");
const extractedWrapEl = $("extractedWrap");
const extractedTextEl = $("extractedText");
const riskBadgeEl = $("riskBadge");
const scamBadgeEl = $("scamBadge");
const confidenceBadgeEl = $("confidenceBadge");
const modelBadgeEl = $("modelBadge");
const finalRiskEl = $("finalRisk");
const finalVerdictEl = $("finalVerdict");
const finalConfidenceEl = $("finalConfidence");
const finalModelEl = $("finalModel");
const ruleHitsEl = $("ruleHits");
const llmStatusEl = $("llmStatus");
const fbStatusEl = $("fbStatus");
const fbStatsEl = $("fbStats");
const fileInputEl = $("fileInput");
const filePreviewWrapEl = $("filePreviewWrap");
const filePreviewEl = $("filePreview");
const verboseToggleEl = $("verboseToggle");
const copyReportBtnEl = $("copyReportBtn");
const emptyStateEl = $("emptyState");
const evidencePanelEl = $("evidencePanel");
const statusBannerEl = $("statusBanner");
const statusBannerTitleEl = $("statusBannerTitle");
const statusBannerSubEl = $("statusBannerSub");
const confidenceFillEl = $("confidenceFill");
const confidenceTextEl = $("confidenceText");
const summaryTextEl = $("summaryText");
const ruleScoreEl = $("ruleScore");
const smartExplanationEl = $("smartExplanation");
const explainSectionsEl = $("explainSections");
const exHeadlineEl = $("exHeadline");
const exVerdictEl = $("exVerdict");
const exSummaryEl = $("exSummary");
const exDetailedEl = $("exDetailed");
const exTrickEl = $("exTrick");
const exStepsEl = $("exSteps");
const exGoldenEl = $("exGolden");
const exDangerWrapEl = $("exDangerWrap");
const exDangerEl = $("exDanger");
const confidenceNoteEl = $("confidenceNote");
const exStoryWrapEl = $("exStoryWrap");
const exScammerWantsEl = $("exScammerWants");
const exIfYouActEl = $("exIfYouAct");
const exWhyFooledEl = $("exWhyFooled");
const contextInsightEl = $("contextInsight");
const contextInsightBodyEl = $("contextInsightBody");
const ocrChatWrapEl = $("ocrChatWrap");
const personalizedRiskLineEl = $("personalizedRiskLine");
const whyYouWrapEl = $("whyYouWrap");
const whyYouBodyEl = $("whyYouBody");
const learningBadgeWrapEl = $("learningBadgeWrap");
const learningNoteEl = $("learningNote");
const learningPhrasesEl = $("learningPhrases");
const learningBarFillEl = $("learningBarFill");
const learningBoostValEl = $("learningBoostVal");

/** Demo: safe-looking message with "payment" so step 3 + learning can hit HIGH */
const DEMO_LEARN_MSG =
  "Hi, just checking in about your gift status and payment timing for the schedule we discussed. Thanks.";

/** 0=off, 1=waiting for user to mark SCAM, 2=re-analyze after learn */
let demoLearnPhase = 0;

function getContextParams() {
  return {
    sender_type: $("senderTypeSel")?.value || "unknown",
    transaction_context: $("transactionContextSel")?.value || "expected",
    user_type: $("userTypeSel")?.value || "general",
  };
}

function setStatus(msg, { kind = "info", loading = false } = {}) {
  statusEl.className = `status status--${kind}` + (loading ? " status--loading" : "");
  statusEl.innerHTML = loading
    ? `<span class="spinner" aria-hidden="true"></span><span>${escapeHtml(msg)}</span>`
    : `<span>${escapeHtml(msg)}</span>`;
  statusEl.classList.remove("hidden");
}

function clearStatus() {
  statusEl.classList.add("hidden");
  statusEl.textContent = "";
}

function setBadge(el, text, cls) {
  if (!el) return;
  el.className = "badge " + cls;
  el.textContent = text;
}

function renderList(ul, items) {
  ul.innerHTML = "";
  (items || []).forEach((x) => {
    const li = document.createElement("li");
    li.textContent = x;
    ul.appendChild(li);
  });
}

function riskClass(level) {
  if (level === "HIGH") return "high";
  if (level === "MEDIUM") return "medium";
  return "low";
}

function riskEmoji(level) {
  if (level === "HIGH") return "🔴";
  if (level === "MEDIUM") return "🟡";
  return "🟢";
}

function applyTheme(theme) {
  const t = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = t;
  try {
    localStorage.setItem("upi_scam_shield_theme", t);
  } catch {
    // ignore
  }
  document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
    btn.textContent = t === "dark" ? "Light Mode" : "Dark Mode";
  });
}

function initTheme() {
  let saved = null;
  try {
    saved = localStorage.getItem("upi_scam_shield_theme");
  } catch {
    // ignore
  }
  if (saved === "dark" || saved === "light") {
    applyTheme(saved);
    return;
  }
  const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(prefersDark ? "dark" : "light");
}

function wireThemeToggle() {
  document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const cur = document.documentElement.dataset.theme === "dark" ? "dark" : "light";
      applyTheme(cur === "dark" ? "light" : "dark");
    });
  });
}

function renderOcrChat(data) {
  const hints = data.ocr_line_hints;
  if (!extractedTextEl) return;
  if (hints && hints.length && ocrChatWrapEl) {
    ocrChatWrapEl.innerHTML = "";
    ocrChatWrapEl.classList.remove("hidden");
    extractedTextEl.classList.add("hidden");
    hints.forEach((h) => {
      const div = document.createElement("div");
      div.className = `chatBubble chatBubble--${h.risk_level || "low"}`;
      div.title = h.tooltip || "";
      div.textContent = h.line;
      ocrChatWrapEl.appendChild(div);
    });
  } else {
    ocrChatWrapEl?.classList.add("hidden");
    extractedTextEl.classList.remove("hidden");
    extractedTextEl.textContent = data.extracted_text || "";
  }
}

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function safeReadError(resp) {
  try {
    const ct = resp.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      const j = await resp.json();
      return j?.detail || JSON.stringify(j);
    }
  } catch {
    // ignore
  }
  try {
    const t = await resp.text();
    return t || "Request failed.";
  } catch {
    return "Request failed.";
  }
}

async function analyzeText() {
  const text = $("textInput").value.trim();
  if (!text) {
    setStatus("Please paste a message first.", { kind: "warn" });
    return;
  }

  clearStatus();
  const loadingMsgs = ["Analyzing message patterns…", "Detecting fraud signals…", "Scoring risk…"];
  let idx = 0;
  setStatus(loadingMsgs[idx], { loading: true });
  const t = setInterval(() => {
    idx = (idx + 1) % loadingMsgs.length;
    setStatus(loadingMsgs[idx], { loading: true });
  }, 900);

  try {
    const verbose = !!verboseToggleEl?.checked;
    const ctx = getContextParams();
    const qp = new URLSearchParams({
      text,
      sender_type: ctx.sender_type,
      transaction_context: ctx.transaction_context,
      user_type: ctx.user_type,
    });
    const url = `${verbose ? "/analyze-verbose" : "/analyze"}?${qp.toString()}`;
    const resp = await fetch(url);
    if (!resp.ok) {
      const msg = await safeReadError(resp);
      setStatus(msg, { kind: "error" });
      return;
    }
    const data = await resp.json();
    renderResult(data);
  } catch {
    setStatus("Backend unavailable. Please restart the server and try again.", { kind: "error" });
  } finally {
    clearInterval(t);
  }
}

async function analyzeImage() {
  const f = fileInputEl?.files?.[0];
  if (!f) {
    setStatus("Please choose an image first.", { kind: "warn" });
    return;
  }

  clearStatus();
  const loadingMsgs = ["Scanning screenshot…", "Reading text with OCR…", "Analyzing message patterns…"];
  let idx = 0;
  setStatus(loadingMsgs[idx], { loading: true });
  const t = setInterval(() => {
    idx = (idx + 1) % loadingMsgs.length;
    setStatus(loadingMsgs[idx], { loading: true });
  }, 900);

  const form = new FormData();
  form.append("file", f);
  const ctx = getContextParams();
  form.append("sender_type", ctx.sender_type);
  form.append("transaction_context", ctx.transaction_context);
  form.append("user_type", ctx.user_type);

  try {
    const verbose = !!verboseToggleEl?.checked;
    const endpoint = verbose ? "/analyze-image-verbose" : "/analyze-image";
    const resp = await fetch(endpoint, { method: "POST", body: form });
    if (!resp.ok) {
      const msg = await safeReadError(resp);
      setStatus(msg || "Could not read text from image. Try a clearer screenshot.", { kind: "error" });
      return;
    }
    const data = await resp.json();
    renderResult(data);
  } catch {
    setStatus("Backend unavailable. Please restart the server and try again.", { kind: "error" });
  } finally {
    clearInterval(t);
  }
}

async function fetchFeedbackStats() {
  try {
    const resp = await fetch("/feedback-stats");
    if (!resp.ok) return;
    const s = await resp.json();
    fbStatsEl.textContent = `Feedback stats: total=${s.total}, scam=${s.scam}, not_scam=${s.not_scam}`;
  } catch {
    // ignore
  }
}

async function submitFeedback(label) {
  if (!lastAnalysis) {
    fbStatusEl.textContent = "Analyze something first.";
    return;
  }
  fbStatusEl.textContent = "Submitting feedback...";
  try {
    const risk = lastAnalysis.final_decision?.risk;
    const isScam = lastAnalysis.final_decision?.is_scam === "YES";
    const payload = {
      input_text: lastAnalysis.input,
      extracted_text: lastAnalysis.extracted_text,
      predicted_risk_level: risk,
      predicted_is_scam: isScam,
      user_label: label,
      analysis_log_id: lastAnalysis.analysis_log_id ?? null,
    };
    const resp = await fetch("/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      fbStatusEl.textContent = "Feedback failed. Try again.";
      return;
    }
    fbStatusEl.textContent = "Thanks! Feedback saved locally.";
    await fetchFeedbackStats();

    if (demoLearnPhase === 1 && label === "SCAM") {
      demoLearnPhase = 2;
      setStatus("System learned from feedback and updated detection. Re-analyzing…", { kind: "info", loading: true });
      $("senderTypeSel").value = "unknown";
      $("transactionContextSel").value = "unexpected";
      $("userTypeSel").value = "elderly";
      await analyzeText();
      demoLearnPhase = 0;
      clearStatus();
      setStatus(
        "Demo complete: risk should jump to HIGH — check the Learning badge and adaptive boost bar.",
        { kind: "info" }
      );
      fbStatusEl.textContent = "Learning demo: compare scores above.";
    }
  } catch {
    fbStatusEl.textContent = "Feedback failed. Try again.";
  }
}

async function runLearningDemo() {
  demoLearnPhase = 1;
  const st = $("senderTypeSel");
  const tc = $("transactionContextSel");
  const ut = $("userTypeSel");
  const ta = $("textInput");
  if (st) st.value = "known";
  if (tc) tc.value = "expected";
  if (ut) ut.value = "general";
  if (ta) ta.value = DEMO_LEARN_MSG;
  setStatus("Demo step 1/3: First analysis (safe-looking message)…", { loading: true });
  await analyzeText();
  clearStatus();
  setStatus(
    "Demo step 2/3: If the risk looks too low, click “Mark as Scam” to simulate a missed scam (false negative).",
    { kind: "warn" }
  );
}

function renderResult(data) {
  lastAnalysis = data;
  const prevRiskForAnim = lastRenderedRisk;
  clearStatus();
  emptyStateEl?.classList.add("hidden");
  resultEl.classList.remove("hidden");
  resultEl.classList.add("fadeIn");
  setTimeout(() => resultEl.classList.remove("fadeIn"), 220);
  fbStatusEl.textContent = "";

  const risk = data.final_decision.risk;
  const isScam = data.final_decision.is_scam === "YES";
  const conf = data.final_decision.confidence;
  const modelUsed = data.model_used || "rules-only";
  const theme = riskClass(risk);

  setBadge(riskBadgeEl, `${riskEmoji(risk)} ${risk}`, riskClass(risk));
  setBadge(scamBadgeEl, isScam ? "SCAM" : "SAFE", isScam ? "yes" : "no");
  setBadge(confidenceBadgeEl, `CONFIDENCE: ${conf}%`, "neutral");
  setBadge(modelBadgeEl, `MODEL: ${modelUsed}`, "neutral");

  if (finalRiskEl) finalRiskEl.textContent = `${riskEmoji(risk)} ${risk}`;
  if (finalVerdictEl) finalVerdictEl.textContent = isScam ? "YES (Scam)" : "NO (Safe)";
  if (finalConfidenceEl) finalConfidenceEl.textContent = `${conf}%`;
  if (finalModelEl) finalModelEl.textContent = modelUsed;

  // Status banner + glow
  if (statusBannerEl) {
    statusBannerEl.className = `statusBanner statusBanner--${riskClass(risk)}`;
    if (isScam || risk === "HIGH") {
      statusBannerTitleEl.textContent = "🚨 SCAM DETECTED";
      statusBannerSubEl.textContent = "Strong scam signals found. Do not proceed with payment/OTP/PIN.";
    } else if (risk === "MEDIUM") {
      statusBannerTitleEl.textContent = "⚠️ SUSPICIOUS";
      statusBannerSubEl.textContent = "Some scam-like patterns detected. Verify via official channels.";
    } else {
      statusBannerTitleEl.textContent = "✅ SAFE";
      statusBannerSubEl.textContent = "No strong scam signals detected. Stay cautious with links/OTP/PIN.";
    }
  }
  // Confidence bar animation
  if (confidenceFillEl) {
    confidenceFillEl.style.width = "0%";
    // trigger reflow
    void confidenceFillEl.offsetWidth;
    confidenceFillEl.style.width = `${Math.max(0, Math.min(100, conf))}%`;
    confidenceFillEl.className = `confidenceFill confidenceFill--${riskClass(risk)}`;
  }
  if (confidenceTextEl) confidenceTextEl.textContent = `${conf}%`;

  // Summary (client-side fallback, only when explanation is missing)
  if (summaryTextEl) {
    const r = (data.final_decision.reason || []).join(" ").toLowerCase();
    let summary = "";
    if (risk === "HIGH") summary = "This looks like a high-risk scam attempt using strong fraud signals.";
    else if (risk === "MEDIUM") summary = "This message is suspicious and may be attempting social engineering.";
    else summary = "This message appears generally safe, with no strong scam indicators detected.";
    if (r.includes("otp")) summary = "Likely scam: requesting OTP is a strong fraud signal.";
    else if (r.includes("collect")) summary = "Likely scam: collect requests can trick you into paying instead of receiving.";
    else if (r.includes("remote") || r.includes("screen") || r.includes("anydesk") || r.includes("teamviewer")) summary = "Likely scam: remote access/screen sharing is commonly used for account takeover.";
    else if (r.includes("link") || r.includes("phishing")) summary = "Likely phishing: link bait and urgency patterns detected.";
    summaryTextEl.textContent = summary;
  }

  // Smart explanation (optional, backward compatible)
  const ex = data.explanation;
  if (ex && smartExplanationEl && explainSectionsEl) {
    smartExplanationEl.classList.remove("hidden");
    explainSectionsEl.classList.remove("hidden");
    smartExplanationEl.className = `panel smartExplain smartExplain--${theme}`;

    if (exHeadlineEl) exHeadlineEl.textContent = ex.headline || "Smart Explanation";
    if (exVerdictEl) exVerdictEl.textContent = ex.one_line_verdict || "";
    if (exSummaryEl) exSummaryEl.textContent = ex.summary || "";

    const whyTxt = (data.personalization && data.personalization.why_risky_for_you) || "";
    if (whyYouWrapEl && whyYouBodyEl) {
      const w = String(whyTxt).trim();
      whyYouBodyEl.textContent = w || "—";
      whyYouWrapEl.classList.toggle("hidden", !w);
    }

    const ad = data.adaptive;
    const boost = ad && typeof ad.adaptive_score_boost === "number" ? ad.adaptive_score_boost : 0;
    const phrases = (ex.learning_matched_phrases && ex.learning_matched_phrases.length
      ? ex.learning_matched_phrases
      : (ad && ad.matched_learned_phrases) || []
    ).filter(Boolean);
    const showLearn = boost > 0 || (ex.learning_note && String(ex.learning_note).trim());
    if (learningBadgeWrapEl) {
      learningBadgeWrapEl.classList.toggle("hidden", !showLearn);
      if (showLearn) {
        learningBadgeWrapEl.classList.remove("learningBadgeWrap--shown");
        if (learningNoteEl) {
          learningNoteEl.textContent =
            (ex.learning_note && ex.learning_note.trim()) ||
            "This pattern was learned from real user-reported scam cases.";
        }
        if (learningPhrasesEl) {
          learningPhrasesEl.innerHTML = "";
          phrases.slice(0, 12).forEach((p, i) => {
            const s = document.createElement("span");
            s.className = "learningChip";
            s.textContent = p;
            s.style.animationDelay = `${i * 48}ms`;
            learningPhrasesEl.appendChild(s);
          });
        }
        const cap = 25;
        const b = Math.min(cap, boost);
        const pct = Math.min(100, (b / cap) * 100);
        if (learningBarFillEl) {
          learningBarFillEl.style.width = "0%";
        }
        if (learningBoostValEl) learningBoostValEl.textContent = `${b}/${cap}`;
        void learningBadgeWrapEl.offsetWidth;
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            learningBadgeWrapEl.classList.add("learningBadgeWrap--shown");
            if (learningBarFillEl) {
              learningBarFillEl.style.width = `${pct}%`;
            }
          });
        });
      } else {
        learningBadgeWrapEl.classList.remove("learningBadgeWrap--shown");
      }
    }

    // Remove duplication: when explanation is present, hide the banner and fallback summary card
    statusBannerEl?.classList.add("hidden");
    $("summaryBox")?.classList.add("hidden");

    const danger = (ex.danger_for_you || "").trim();
    if (exDangerWrapEl && exDangerEl) {
      exDangerEl.textContent = danger || "";
      exDangerWrapEl.classList.toggle("hidden", !danger);
    }

    renderList(exDetailedEl, ex.detailed_analysis || []);
    renderList(exTrickEl, ex.common_trick || []);
    renderList(exStepsEl, ex.action_steps || []);
    if (exGoldenEl) exGoldenEl.textContent = ex.golden_rule || "";

    const sw = (ex.scammer_wants || "").trim();
    const iy = (ex.if_you_act || "").trim();
    const wy = (ex.why_people_fooled || "").trim();
    const hasStory = !!(sw || iy || wy);
    if (exStoryWrapEl) exStoryWrapEl.classList.toggle("hidden", !hasStory);
    if (exScammerWantsEl) exScammerWantsEl.textContent = sw || "—";
    if (exIfYouActEl) exIfYouActEl.textContent = iy || "—";
    if (exWhyFooledEl) exWhyFooledEl.textContent = wy || "—";

    if (confidenceNoteEl) {
      const note = ex.confidence_note || "";
      confidenceNoteEl.textContent = note;
      confidenceNoteEl.classList.toggle("hidden", !note);
    }
  } else {
    smartExplanationEl?.classList.add("hidden");
    explainSectionsEl?.classList.add("hidden");
    statusBannerEl?.classList.remove("hidden");
    $("summaryBox")?.classList.remove("hidden");
    if (exDangerWrapEl && exDangerEl) {
      exDangerEl.textContent = "";
      exDangerWrapEl.classList.add("hidden");
    }
    exStoryWrapEl?.classList.add("hidden");
    whyYouWrapEl?.classList.add("hidden");
    learningBadgeWrapEl?.classList.add("hidden");
    learningBadgeWrapEl?.classList.remove("learningBadgeWrap--shown");
    if (confidenceNoteEl) {
      confidenceNoteEl.textContent = "";
      confidenceNoteEl.classList.add("hidden");
    }
  }

  renderList(reasonsEl, data.final_decision.reason);
  renderList(actionsEl, data.final_decision.actions);

  if (data.personalization && personalizedRiskLineEl) {
    personalizedRiskLineEl.classList.remove("hidden");
    personalizedRiskLineEl.textContent = `Personalized risk score: ${data.personalization.personalized_risk_score}/100 — ${data.personalization.context_reason}`;
  } else {
    personalizedRiskLineEl?.classList.add("hidden");
  }

  if (data.intent && contextInsightEl && contextInsightBodyEl) {
    contextInsightEl.classList.remove("hidden");
    const parts = [
      `Intent: ${data.intent.intent_type.replace(/_/g, " ")} (${data.intent.intent_confidence}% confidence)`,
    ];
    const ad = data.adaptive;
    if (ad && ad.adaptive_score_boost > 0) {
      const m = (ad.matched_learned_phrases || []).slice(0, 4).join(", ");
      parts.push(`Learned-pattern boost: +${ad.adaptive_score_boost}${m ? ` (${m})` : ""}`);
    }
    contextInsightBodyEl.textContent = parts.join(" · ");
  } else {
    contextInsightEl?.classList.add("hidden");
  }

  if (data.extracted_text) {
    extractedWrapEl.classList.remove("hidden");
    renderOcrChat(data);
  } else {
    extractedWrapEl.classList.add("hidden");
    extractedTextEl.textContent = "";
    ocrChatWrapEl?.classList.add("hidden");
    extractedTextEl?.classList.remove("hidden");
  }

  // Evidence panel
  ruleHitsEl.innerHTML = "";
  const verboseOn = !!verboseToggleEl?.checked;
  if (evidencePanelEl) evidencePanelEl.classList.toggle("hidden", !verboseOn);
  if (!verboseOn) {
    // keep old state clean
    llmStatusEl.textContent = "";
    if (ruleScoreEl) ruleScoreEl.textContent = "—";
  } else if (data.internal?.rule_hits?.length) {
    if (ruleScoreEl) ruleScoreEl.textContent = String(data.internal?.rule_score ?? "—");
    data.internal.rule_hits.forEach((h) => {
      const li = document.createElement("li");
      const terms = (h.matched_terms || []).length ? ` — matched: ${(h.matched_terms || []).join(", ")}` : "";
      li.textContent = `${h.title} (severity ${h.severity}/100)${terms}`;
      ruleHitsEl.appendChild(li);
    });
  } else {
    if (ruleScoreEl) ruleScoreEl.textContent = String(data.internal?.rule_score ?? "—");
    const li = document.createElement("li");
    li.textContent = "No rule hits.";
    ruleHitsEl.appendChild(li);
  }

  if (verboseOn && data.internal?.ai_note) {
    llmStatusEl.textContent = data.internal.ai_note;
  } else if (verboseOn) {
    llmStatusEl.textContent = modelUsed === "rules-only" ? "AI unavailable (running in safe mode)." : `AI enabled (${modelUsed})`;
  }

  // Risk tier change micro-animation (e.g. LOW → HIGH in learning demo)
  if (prevRiskForAnim !== null && prevRiskForAnim !== risk) {
    resultEl.classList.remove("riskShift--to-high", "riskShift--to-medium", "riskShift--to-low");
    void resultEl.offsetWidth;
    if (
      (prevRiskForAnim === "LOW" && risk === "HIGH") ||
      (prevRiskForAnim === "MEDIUM" && risk === "HIGH")
    ) {
      resultEl.classList.add("riskShift--to-high");
      setTimeout(() => resultEl.classList.remove("riskShift--to-high"), 1100);
    } else if (prevRiskForAnim === "LOW" && risk === "MEDIUM") {
      resultEl.classList.add("riskShift--to-medium");
      setTimeout(() => resultEl.classList.remove("riskShift--to-medium"), 900);
    } else if ((prevRiskForAnim === "HIGH" || prevRiskForAnim === "MEDIUM") && risk === "LOW") {
      resultEl.classList.add("riskShift--to-low");
      setTimeout(() => resultEl.classList.remove("riskShift--to-low"), 700);
    }
  }
  lastRenderedRisk = risk;

  fetchFeedbackStats();
}

function _wireAnalyzerPage() {
  const analyzeBtn = $("analyzeBtn");
  if (!analyzeBtn) return; // Not on analyzer page

  analyzeBtn.addEventListener("click", analyzeText);
  $("analyzeImgBtn")?.addEventListener("click", analyzeImage);

  $("fbScamBtn")?.addEventListener("click", () => submitFeedback("SCAM"));
  $("fbNotScamBtn")?.addEventListener("click", () => submitFeedback("NOT_SCAM"));

  $("fillScamBtn")?.addEventListener("click", async () => {
    $("textInput").value = "Your account blocked. Click this link immediately to verify. Share OTP to activate UPI.";
    await analyzeText();
  });

  $("fillNormalBtn")?.addEventListener("click", async () => {
    $("textInput").value = "Your order shipped. Track it in the app. Thank you for shopping with us.";
    await analyzeText();
  });

  $("learningDemoBtn")?.addEventListener("click", () => {
    runLearningDemo().catch(() => setStatus("Learning demo failed to run.", { kind: "error" }));
  });

  fileInputEl?.addEventListener("change", () => {
    const f = fileInputEl.files?.[0];
    if (!f) {
      filePreviewWrapEl?.classList.add("hidden");
      if (filePreviewEl) filePreviewEl.src = "";
      return;
    }
    const url = URL.createObjectURL(f);
    if (filePreviewEl) filePreviewEl.src = url;
    filePreviewWrapEl?.classList.remove("hidden");
  });

  // Auto demo tour from query param
  try {
    const p = new URLSearchParams(window.location.search);
    if (p.get("demo") === "learn") {
      runLearningDemo().catch(() => {});
    } else if (p.get("demo") === "1") {
      (async () => {
        $("textInput").value = "Your order shipped. Track it in the app.";
        await analyzeText();
        await new Promise((r) => setTimeout(r, 800));
        $("textInput").value = "Your account blocked. Click link immediately. Share OTP to activate UPI.";
        await analyzeText();
      })();
    }
  } catch {
    // ignore
  }

  // Persist verbose toggle
  try {
    const saved = localStorage.getItem("upi_scam_shield_verbose");
    if (verboseToggleEl && (saved === "1" || saved === "0")) verboseToggleEl.checked = saved === "1";
  } catch {}
  verboseToggleEl?.addEventListener("change", () => {
    try {
      localStorage.setItem("upi_scam_shield_verbose", verboseToggleEl.checked ? "1" : "0");
    } catch {}

    // Re-run analysis so evidence updates immediately
    if (!lastAnalysis) return;
    const hasText = !!$("textInput")?.value?.trim();
    const hasFile = !!fileInputEl?.files?.[0];
    if (hasText) {
      analyzeText();
    } else if (hasFile) {
      analyzeImage();
    }
  });

  copyReportBtnEl?.addEventListener("click", async () => {
    if (!lastAnalysis) {
      setStatus("Analyze something first to generate a report.", { kind: "warn" });
      return;
    }
    const fd = lastAnalysis.final_decision || {};
    const lines = [
      "UPI Scam Shield – Analysis Report",
      "",
      `Input: ${lastAnalysis.input || ""}`,
      lastAnalysis.extracted_text ? `Extracted text: ${lastAnalysis.extracted_text}` : null,
      `Risk: ${fd.risk || ""}`,
      `Scam: ${fd.is_scam || ""}`,
      `Confidence: ${fd.confidence != null ? fd.confidence + "%" : ""}`,
      `Model used: ${lastAnalysis.model_used || "rules-only"}`,
      "",
      "Reasons:",
      ...(fd.reason || []).map((r) => `- ${r}`),
      "",
      "Suggested actions:",
      ...(fd.actions || []).map((a) => `- ${a}`),
    ].filter(Boolean);
    const report = lines.join("\n");
    try {
      await navigator.clipboard.writeText(report);
      setStatus("Report copied to clipboard.", { kind: "info" });
    } catch {
      // Fallback
      try {
        const ta = document.createElement("textarea");
        ta.value = report;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        document.execCommand("copy");
        ta.remove();
        setStatus("Report copied to clipboard.", { kind: "info" });
      } catch {
        setStatus("Could not copy automatically. Please copy manually from the console.", { kind: "warn" });
        // eslint-disable-next-line no-console
        console.log(report);
      }
    }
  });
}

_wireAnalyzerPage();

initTheme();
wireThemeToggle();

