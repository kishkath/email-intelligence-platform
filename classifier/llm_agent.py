import re
from typing import List, Dict
from openai import AzureOpenAI
import os
from dotenv import load_dotenv

from email_ops.email_reader import read_read_emails

# ---------------------------------------------------------
# 🔹 Load environment
# ---------------------------------------------------------
load_dotenv()

AZURE_OPENAI_API_KEY = os.getenv("azure_openai_apikey")
AZURE_OPENAI_ENDPOINT = os.getenv("azure_openai_endpoint")
AZURE_OPENAI_API_VERSION = os.getenv("azure_openai_api_version")
AZURE_OPENAI_DEPLOYMENT = os.getenv("azure_openai_deployment")  # your LLM deployment name

client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

# ---------------------------------------------------------
# 🔹 LLM-based Classification Functions
# ---------------------------------------------------------
def classify_email_llm(email: Dict[str, str]) -> str:
    """Use Azure OpenAI to classify email priority based on context."""
    subject = email.get("subject", "")
    body = email.get("body", "")
    combined = f"Subject: {subject}\n\nBody: {body}"

    prompt = f"""
You are an intelligent email classifier.

Your task:
- Determine if this email is *High Priority* or *Low Priority*.
- High priority includes job opportunities, recruiter messages, interviews, AI/ML project offers, urgent tasks, or time-sensitive work.
- Low priority includes newsletters, ads, or casual discussions.

Output format: only respond with one of these exactly:
- High Priority
- Low Priority

Email content:
{combined}
"""

    try:
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )

        raw_output = response.choices[0].message.content.strip()
        print(f"[LLM Raw Output] {raw_output}")

        # -------------------------------------------------
        # ✅ Robust normalization and regex fallback
        # -------------------------------------------------
        if re.search(r"\bhigh\b", raw_output, re.IGNORECASE):
            return "High Priority"
        elif re.search(r"\blow\b", raw_output, re.IGNORECASE):
            return "Low Priority"
        else:
            print("[LLM Classifier] ⚠️ Unclear output, defaulting to Low Priority.")
            return "Low Priority"

    except Exception as e:
        print(f"[LLM Classifier] ❌ Failed to classify email: {e}")
        return "Low Priority"


def classify_emails_bulk_llm(emails: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Classify multiple emails using Azure OpenAI."""
    classified = []
    print(f"[LLM Classifier] Starting classification for {len(emails)} emails...")

    for e in emails:
        e["priority"] = classify_email_llm(e)
        classified.append(e)

    print(f"[LLM Classifier] ✅ Completed classification for {len(classified)} emails.")
    return classified


# ---------------------------------------------------------
# 🔹 Example Run
# ---------------------------------------------------------
if __name__ == "__main__":
    START_DATE = "29-10-2025"
    END_DATE = "01-11-2025"
    LIMIT = 2

    print("[MAIN] Fetching unread emails from Gmail...")
    emails = read_read_emails(START_DATE, END_DATE, LIMIT)
    print(f"[MAIN] Retrieved {len(emails)} emails.\n")

    print("[Main] Running LLM-based classification...")
    labeled = classify_emails_bulk_llm(emails)

    for e in labeled:
        print("=" * 60)
        print(f"Subject: {e['subject']}")
        print(f"Priority: {e['priority']}")
        print(f"From: {e['from']}")
        print(f"Date: {e['date']}")
