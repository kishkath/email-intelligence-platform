"""
unified_email_classifier.py
----------------------------------------------------
Handles email classification using either:
1. Python-based regex classifier (fast, cost-free)
2. LLM-based classifier via Azure OpenAI (semantic)
with automatic fallback and centralized control.
----------------------------------------------------
"""

import json
import re
from pathlib import Path
from typing import List, Dict

from configurations.config import CLASSIFICATION_MODE
from email_ops.email_reader import read_read_emails
from llm_gateway.azure_openai_llm import classify_with_llm  # new helper file
from prompts.email_agent_prompts import EMAIL_CLASSIFIER_PROMPTS

# ---------------------------------------------------------
# 🔹 Load Rules from JSON
# ---------------------------------------------------------
RULES_PATH = Path("configurations/priority_rules.json")

with open(RULES_PATH, "r") as f:
    rules = json.load(f)

HIGH_PRIORITY_KEYWORDS = []
for category, keywords in rules["high_priority"].items():
    HIGH_PRIORITY_KEYWORDS.extend(keywords)

LOW_PRIORITY_TERMS = rules["low_priority"]
THRESHOLD = rules.get("threshold", 2)


# ---------------------------------------------------------
# 🔹 Scoring-based Regex Classifier
# ---------------------------------------------------------
def is_high_priority(text: str) -> bool:
    """Weighted keyword scoring for improved accuracy."""
    text_lower = text.lower()
    score = 0

    for keyword in HIGH_PRIORITY_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword.lower())}\b", text_lower):
            score += 2

    for bad_word in LOW_PRIORITY_TERMS:
        if re.search(rf"\b{re.escape(bad_word.lower())}\b", text_lower):
            score -= 3

    return score >= THRESHOLD


def classify_email_python(email: Dict[str, str]) -> str:
    """Classify using keyword-based logic from JSON config."""
    subject = email.get("subject", "")
    body = email.get("body", "")
    combined = f"{subject} {body}"

    if is_high_priority(combined):
        print(f"[PY-Classifier] ✅ High Priority: {subject}")
        return "High Priority"
    else:
        print(f"[PY-Classifier] Low Priority: {subject}")
        return "Low Priority"


# ---------------------------------------------------------
# 🔹 LLM-based classifier (via Azure OpenAI)
# ---------------------------------------------------------
def classify_email_llm(email: Dict[str, str]) -> str:
    """
    Classify email using Azure OpenAI model.
    Expected return: 'High Priority' or 'Low Priority'.
    """
    subject = email.get("subject", "")
    body = email.get("body", "")
    prompt = EMAIL_CLASSIFIER_PROMPTS + f" Subject: {subject} \n" + f" Body: {body}\n"

    try:
        label = classify_with_llm(prompt).strip().lower()
        if "high" in label:
            print(f"[LLM-Classifier] ✅ High Priority: {subject}")
            return "High Priority"
        elif "low" in label:
            print(f"[LLM-Classifier] Low Priority: {subject}")
            return "Low Priority"
        else:
            print(f"[LLM-Classifier] ⚠️ Unexpected response → {label}. Falling back to Python.")
            return classify_email_python(email)
    except Exception as e:
        print(f"[LLM-Classifier] ❌ Error: {e}. Falling back to Python classifier.")
        return classify_email_python(email)


# ---------------------------------------------------------
# 🔹 Unified bulk classification
# ---------------------------------------------------------
def classify_emails_bulk(emails: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Classify emails using either LLM or Python regex, with fallback."""
    mode = CLASSIFICATION_MODE.lower()
    print(f"\n[Classifier] 🧠 Using mode: {mode.upper()}")
    classified = []

    for e in emails:
        if mode == "llm":
            e["priority"] = classify_email_llm(e)
        else:
            e["priority"] = classify_email_python(e)
        classified.append(e)

    print(f"[Classifier] ✅ Completed classification for {len(classified)} emails.\n")
    return classified


# ---------------------------------------------------------
# 🔹 Entry point for testing
# ---------------------------------------------------------
if __name__ == "__main__":
    START_DATE = "29-10-2025"
    END_DATE = "01-11-2025"
    LIMIT = 3

    print("[MAIN] Fetching unread emails from Gmail...")
    emails = read_read_emails(START_DATE, END_DATE, LIMIT)
    print(f"[MAIN] Retrieved {len(emails)} emails.\n")

    labeled = classify_emails_bulk(emails)

    for e in labeled:
        print("=" * 60)
        print(f"Subject: {e['subject']}")
        print(f"Priority: {e['priority']}")
        print(f"From: {e['from']}")
        print(f"Date: {e['date']}")
