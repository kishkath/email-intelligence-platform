import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]
TOKEN_PATH = r"C:\Users\saikir\learnings\tmlc\week4_email_notifying_agent\email_ops\token.json"


def get_access_token() -> str:
    """Return a valid Gmail API access token using refresh token if needed."""
    print("🔐 Checking for existing credentials...")
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        print("✅ Loaded credentials from token.json")
    else:
        print("⚠️ token.json not found. Please run OAuth flow manually once.")

    if not creds or not creds.valid:
        print("🔄 Credentials invalid or expired.")
        if creds and creds.expired and creds.refresh_token:
            print("♻️ Refreshing access token using refresh token...")
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())
            print("✅ Token refreshed and saved.")
        else:
            raise Exception("Run OAuth flow first using the googleapiclient method.")
    else:
        print("✅ Credentials are valid.")

    return creds.token


# def parse_email_payload(payload: Dict[str, Any]) -> str:
#     """Extract text/plain part of an email body."""
#     print("📦 Parsing email payload...")
#     body = ""
#     if 'parts' in payload:
#         for part in payload['parts']:
#             mime_type = part.get('mimeType', '')
#             data = part.get('body', {}).get('data')
#             if mime_type == 'text/plain' and data:
#                 decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
#                 body += decoded
#     elif 'body' in payload and 'data' in payload['body']:
#         data = payload['body']['data']
#         body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
#
#     print(f"✅ Email body extracted ({len(body)} characters).")
#     return body.strip()

import base64
from bs4 import BeautifulSoup
import re


def clean_html_to_text(html_content: str) -> str:
    """Convert HTML to plain text safely."""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style"]):
        tag.extract()
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_email_payload(payload):
    """Extract the main body text from Gmail message payload."""
    if not payload:
        return ""

    parts = payload.get("parts", [])
    body_data = None
    mime_type = None

    # Case 1️⃣: If single part (no attachments)
    if not parts:
        body = payload.get("body", {}).get("data")
        if body:
            body_data = base64.urlsafe_b64decode(body).decode("utf-8", errors="ignore")
            mime_type = payload.get("mimeType", "")
    else:
        # Case 2️⃣: Multipart email — iterate over parts
        for part in parts:
            mime_type = part.get("mimeType", "")
            body = part.get("body", {}).get("data")
            if body and "text/plain" in mime_type:
                # Prefer plain text first
                body_data = base64.urlsafe_b64decode(body).decode("utf-8", errors="ignore")
                break
            elif body and "text/html" in mime_type and not body_data:
                # Fallback: take HTML if plain text isn’t found yet
                body_data = base64.urlsafe_b64decode(body).decode("utf-8", errors="ignore")

    if not body_data:
        return ""

    # Clean HTML if necessary
    if "html" in (mime_type or "").lower():
        body_data = clean_html_to_text(body_data)

    return body_data.strip()


# =========================================================
# ⏱️ Rolling Time Window Helper (NEW)
# =========================================================
def compute_date_range(hours_back: int):
    """Compute Gmail-compatible date range for last N hours."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours_back)

    return (
        start_time.strftime("%Y/%m/%d"),
        end_time.strftime("%Y/%m/%d"),
    )


# =========================================================
# 📥 Core Fetcher
# =========================================================
def _fetch_emails(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    print(f"\n🚀 Fetching emails | Query='{query}' | Limit={limit}")

    headers = {"Authorization": f"Bearer {get_access_token()}"}
    list_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?q={query}&maxResults={limit}"

    response = requests.get(list_url, headers=headers)
    response.raise_for_status()

    messages = response.json().get("messages", [])
    print(f"📬 Found {len(messages)} message(s).")

    emails = []

    for idx, msg in enumerate(messages, start=1):
        msg_id = msg["id"]
        print(f"🔍 [{idx}/{len(messages)}] Fetching message {msg_id}")

        msg_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
        msg_resp = requests.get(msg_url, headers=headers)
        msg_resp.raise_for_status()

        message = msg_resp.json()
        payload = message.get("payload", {})
        headers_list = payload.get("headers", [])

        subject = next((h["value"] for h in headers_list if h["name"] == "Subject"), "(No Subject)")
        sender = next((h["value"] for h in headers_list if h["name"] == "From"), "(Unknown)")
        date = next((h["value"] for h in headers_list if h["name"] == "Date"), None)

        body = parse_email_payload(payload)

        emails.append({
            "id": msg_id,
            "from": sender,
            "subject": subject,
            "body": body,
            "date": date,
            "timestamp": datetime.utcnow().isoformat(),
        })

    print("✅ Email fetch complete.\n")
    return emails


# =========================================================
# 📧 Public APIs
# =========================================================
def read_unread_emails(
    start_date: str = None,
    end_date: str = None,
    limit: int = 10,
    hours_back: int = None,
) -> List[Dict[str, Any]]:
    print("\n📧 Reading UNREAD emails...")

    query_parts = ["is:unread", "label:INBOX"]

    if hours_back:
        after, before = compute_date_range(hours_back)
        query_parts += [f"after:{after}", f"before:{before}"]
        print(f"🕒 Last {hours_back} hours window applied")

    else:
        if start_date:
            after = datetime.strptime(start_date, "%d-%m-%Y").strftime("%Y/%m/%d")
            query_parts.append(f"after:{after}")

        if end_date:
            before = datetime.strptime(end_date, "%d-%m-%Y").strftime("%Y/%m/%d")
            query_parts.append(f"before:{before}")

    return _fetch_emails(" ".join(query_parts), limit)


def read_read_emails(
    start_date: str = None,
    end_date: str = None,
    limit: int = 10,
    hours_back: int = None,
) -> List[Dict[str, Any]]:
    print("\n📨 Reading READ emails...")

    query_parts = ["is:read", "label:INBOX"]

    if hours_back:
        after, before = compute_date_range(hours_back)
        query_parts += [f"after:{after}", f"before:{before}"]
        print(f"🕒 Last {hours_back} hours window applied")

    else:
        if start_date:
            after = datetime.strptime(start_date, "%d-%m-%Y").strftime("%Y/%m/%d")
            query_parts.append(f"after:{after}")

        if end_date:
            before = datetime.strptime(end_date, "%d-%m-%Y").strftime("%Y/%m/%d")
            query_parts.append(f"before:{before}")

    return _fetch_emails(" ".join(query_parts), limit)


# =========================================================
# 🧪 Local Debug
# =========================================================
if __name__ == "__main__":
    emails = read_unread_emails(hours_back=4, limit=2)

    for e in emails:
        print("=" * 80)
        print(f"From   : {e['from']}")
        print(f"Subject: {e['subject']}")
        print(f"Date   : {e['date']}")
        print(f"Body   : {e['body'][:300]}...")

