import sqlite3
from typing import List, Dict, Any
from datetime import datetime
import os

from email_ops.email_reader import read_read_emails

DB_PATH = "emails_info.db"


def init_db():
    """Initialize SQLite database and create table if not exists."""
    print("[DB] Initializing database...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id TEXT PRIMARY KEY,
            sender TEXT,
            subject TEXT,
            body TEXT,
            date TEXT,
            timestamp TEXT,
            priority TEXT DEFAULT 'Unclassified'
        )
    """)
    conn.commit()
    conn.close()
    print("[DB] ✅ Table 'emails' (with 'priority' column) ready.\n")


def email_exists(email_id: str) -> bool:
    """Check if an email already exists in the DB by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM emails WHERE id = ?", (email_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def insert_emails(emails: List[Dict[str, Any]]):
    """Insert only new email records into the database."""
    if not emails:
        print("[DB] ⚠️ No new emails to insert.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    new_count, skipped_count = 0, 0

    print(f"[DB] 📨 Starting insertion of {len(emails)} email(s)...")

    for email in emails:
        email_id = email.get("id")
        if email_exists(email_id):
            print(f"[DB] ⏩ Skipping duplicate email ID: {email_id}")
            skipped_count += 1
            continue

        try:
            cursor.execute("""
                INSERT INTO emails (id, sender, subject, body, date, timestamp, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                email_id,
                email.get("from"),
                email.get("subject"),
                email.get("body"),
                email.get("date"),
                email.get("timestamp", datetime.now().isoformat()),
                email.get("priority", "Unclassified")
            ))
            new_count += 1
            print(f"[DB] ✅ Inserted email ID: {email_id}")
        except Exception as e:
            print(f"[DB] ⚠️ Error inserting email ID {email_id}: {e}")

    conn.commit()
    conn.close()
    print(f"\n[DB] ✅ Summary: {new_count} new email(s) inserted, {skipped_count} duplicate(s) skipped.\n")


def fetch_all_emails(limit: int = 10):
    """Fetch and display recent emails from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, sender, subject, date, priority FROM emails ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()

    print(f"[DB] 📬 Retrieved {len(rows)} stored email(s):\n")
    for row in rows:
        print(f"ID: {row[0]}\nFrom: {row[1]}\nSubject: {row[2]}\nDate: {row[3]}\nPriority: {row[4]}\n{'-'*70}")
    return rows


if __name__ == "__main__":
    # Step 1: Initialize DB
    init_db()

    # Step 2: Fetch read emails from Gmail
    START_DATE = "29-10-2025"
    END_DATE = "01-11-2025"
    LIMIT = 3
    print("[MAIN] 🚀 Fetching read emails from Gmail API...")
    emails = read_read_emails(START_DATE, END_DATE, LIMIT)
    print(f"[MAIN] ✅ Retrieved {len(emails)} email(s) from Gmail.\n")

    # Step 3: Insert into DB (duplicates skipped)
    insert_emails(emails)

    # Step 4: Display last few emails
    fetch_all_emails(limit=5)
