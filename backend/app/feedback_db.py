from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

_default_db = Path(__file__).resolve().parents[1] / "feedback.sqlite3"
DB_PATH = Path(os.environ["FEEDBACK_DB_PATH"]) if os.environ.get("FEEDBACK_DB_PATH") else _default_db

# In-memory adaptive phrase weights (refreshed on startup + after feedback)
_adaptive_cache: Dict[str, float] = {}

_STOPWORDS = frozenset(
    """
    the a an is are was were be been being to of and or for in on at by with as from
    this that these those it its you your we our they their me my he she his her
    not no yes so if but do does did has have had will would could should can may
    just very much more most some any all each every other another such only own
    same than then them there when where which who how what why also into out up down
    हम आप का की के को से में पर
    """.split()
)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _refresh_adaptive_cache() -> None:
    global _adaptive_cache
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT phrase, weight FROM adaptive_phrases ORDER BY weight DESC LIMIT 300"
            ).fetchall()
        _adaptive_cache = {str(r["phrase"]): float(r["weight"]) for r in rows}
    except Exception:
        _adaptive_cache = {}


def get_adaptive_phrases() -> Dict[str, float]:
    """Copy of current adaptive phrase -> weight map."""
    return dict(_adaptive_cache)


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              input_text TEXT NOT NULL,
              extracted_text TEXT,
              predicted_risk_level TEXT NOT NULL,
              predicted_is_scam INTEGER NOT NULL,
              user_label TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_log (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              message_text TEXT NOT NULL,
              extracted_text TEXT,
              predicted_is_scam INTEGER NOT NULL,
              predicted_risk_level TEXT NOT NULL,
              predicted_confidence INTEGER,
              user_feedback_label TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS adaptive_phrases (
              phrase TEXT PRIMARY KEY,
              weight REAL NOT NULL DEFAULT 1.0,
              hit_count INTEGER NOT NULL DEFAULT 0,
              updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()
    _refresh_adaptive_cache()


def extract_learning_phrases(text: str) -> List[str]:
    """
    Bigrams/trigrams that appear as real substrings in normalized text.
    (We keep stopwords in the chain so phrases still match the user's message.)
    """
    tn = re.sub(r"\s+", " ", (text or "").strip().lower())
    words = re.findall(r"[a-z0-9\u0900-\u097f]+", tn)
    if len(words) < 2:
        return []
    phrases: List[str] = []
    for i in range(len(words) - 1):
        bi = f"{words[i]} {words[i + 1]}"
        if len(bi) >= 5 and bi in tn:
            phrases.append(bi)
    for i in range(len(words) - 2):
        tri = f"{words[i]} {words[i + 1]} {words[i + 2]}"
        if len(tri) >= 8 and tri in tn:
            phrases.append(tri)
    # de-dup preserve order
    seen = set()
    out: List[str] = []
    for p in phrases:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out[:60]


def _upsert_adaptive_phrases(phrases: List[str]) -> None:
    if not phrases:
        return
    with _connect() as conn:
        for ph in phrases:
            ph = ph.strip()[:200]
            if len(ph) < 4:
                continue
            w = min(15.0, 5.0 + len(ph) / 28.0)
            conn.execute(
                """
                INSERT INTO adaptive_phrases (phrase, weight, hit_count, updated_at)
                VALUES (?, ?, 1, datetime('now'))
                ON CONFLICT(phrase) DO UPDATE SET
                  weight = adaptive_phrases.weight + excluded.weight,
                  hit_count = adaptive_phrases.hit_count + 1,
                  updated_at = datetime('now')
                """,
                (ph, w),
            )
        conn.commit()
    _refresh_adaptive_cache()


def _is_misclassification(predicted_is_scam: bool, user_label: str) -> bool:
    user_says_scam = user_label == "SCAM"
    return predicted_is_scam != user_says_scam


def learn_from_false_negative(message_text: str) -> None:
    """User marked SCAM but model said safe → boost phrases from message."""
    phrases = extract_learning_phrases(message_text)
    _upsert_adaptive_phrases(phrases)


def insert_analysis_log(
    *,
    message_text: str,
    extracted_text: Optional[str],
    predicted_is_scam: bool,
    predicted_risk_level: str,
    predicted_confidence: Optional[int],
) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO analysis_log (
              message_text, extracted_text, predicted_is_scam,
              predicted_risk_level, predicted_confidence
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                message_text,
                extracted_text,
                1 if predicted_is_scam else 0,
                predicted_risk_level,
                predicted_confidence,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def update_analysis_log_feedback(log_id: int, user_label: str) -> Optional[sqlite3.Row]:
    """Set user_feedback_label; return row for misclassification check."""
    label = "SCAM" if user_label == "SCAM" else "NOT_SCAM"
    with _connect() as conn:
        conn.execute(
            "UPDATE analysis_log SET user_feedback_label = ? WHERE id = ?",
            (label, log_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM analysis_log WHERE id = ?", (log_id,)).fetchone()
    return row


def insert_feedback(
    *,
    input_text: str,
    extracted_text: Optional[str],
    predicted_risk_level: str,
    predicted_is_scam: bool,
    user_label: str,
    analysis_log_id: Optional[int] = None,
) -> None:
    """Legacy feedback row + optional analysis_log update + adaptive learning."""
    ul = "SCAM" if user_label == "SCAM" else "NOT_SCAM"
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO feedback (input_text, extracted_text, predicted_risk_level, predicted_is_scam, user_label)
            VALUES (?, ?, ?, ?, ?)
            """,
            (input_text, extracted_text, predicted_risk_level, 1 if predicted_is_scam else 0, ul),
        )
        conn.commit()

    msg = input_text or ""
    pred_scam = predicted_is_scam

    if analysis_log_id is not None:
        row = update_analysis_log_feedback(analysis_log_id, ul)
        if row:
            msg = row["message_text"] or msg
            pred_scam = bool(row["predicted_is_scam"])

    if _is_misclassification(pred_scam, ul):
        if ul == "SCAM" and not pred_scam:
            learn_from_false_negative(msg)


def stats() -> Dict[str, int]:
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM feedback").fetchone()["c"]
        scam = conn.execute("SELECT COUNT(*) AS c FROM feedback WHERE user_label='SCAM'").fetchone()["c"]
        not_scam = conn.execute(
            "SELECT COUNT(*) AS c FROM feedback WHERE user_label='NOT_SCAM'"
        ).fetchone()["c"]
    return {"total": int(total), "scam": int(scam), "not_scam": int(not_scam)}


def misclassification_stats() -> Dict[str, int]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT predicted_is_scam, user_feedback_label, COUNT(*) AS c
            FROM analysis_log
            WHERE user_feedback_label IS NOT NULL
            GROUP BY predicted_is_scam, user_feedback_label
            """
        ).fetchall()
    out = {"false_negative": 0, "false_positive": 0, "agreement": 0}
    for r in rows:
        pred = bool(r["predicted_is_scam"])
        user_scam = r["user_feedback_label"] == "SCAM"
        c = int(r["c"])
        if pred == user_scam:
            out["agreement"] += c
        elif user_scam and not pred:
            out["false_negative"] += c
        else:
            out["false_positive"] += c
    return out
