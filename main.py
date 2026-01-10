from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from classifier.smart_email_classifier import classify_emails_bulk
from databases.email_db import init_db, insert_emails
from email_ops.email_reader import read_read_emails, read_unread_emails
from notifiers.whatsapp_notifiers import (
    send_whatsapp_message,
    send_sandbox_expiry_notification,
)

# # =========================================================
# # FastAPI App
# # =========================================================
# app = FastAPI(
#     title="Email Intelligence Pipeline",
#     version="1.0.0",
#     description="Headless email ingestion, classification & WhatsApp alert system",
# )
#
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # tighten later
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# =========================================================
# Init DB once (important for GitHub Actions / cron runs)
# =========================================================
init_db()

#
# # =========================================================
# # Health Check (Recommended)
# # =========================================================
# @app.get("/health")
# def health():
#     return {
#         "status": "ok",
#         "service": "email-intel",
#         "timestamp": datetime.utcnow().isoformat(),
#     }
#
#
# # =========================================================
# # Core Pipeline (v1)
# # =========================================================
# @app.post("/run-pipeline")
# async def run_pipeline(
#     start_date: str,
#     end_date: str,
#     limit: int = 5,
#     unread: bool = False,
# ):
#     """
#     Headless pipeline:
#     - Fetch emails
#     - Classify
#     - Store
#     - Notify (WhatsApp)
#     """
#
#     try:
#         print("\n======================================================")
#         print("📧 EMAIL PIPELINE STARTED (v1)")
#         print("======================================================")
#
#         # -------------------------------------------------
#         # 1️⃣ Fetch Emails
#         # -------------------------------------------------
#         if unread:
#             print("[STEP 1] Fetching UNREAD emails...")
#             emails = read_unread_emails(start_date, end_date, limit)
#         else:
#             print("[STEP 1] Fetching READ emails...")
#             emails = read_read_emails(start_date, end_date, limit)
#
#         if not emails:
#             print("[INFO] No emails found.")
#             return {
#                 "status": "success",
#                 "processed_emails": 0,
#                 "alerts_sent": 0,
#                 "message": "No emails found",
#             }
#
#         print(f"[INFO] Retrieved {len(emails)} email(s).")
#
#         # -------------------------------------------------
#         # 2️⃣ Classify
#         # -------------------------------------------------
#         print("[STEP 2] Classifying emails...")
#         classified_emails = classify_emails_bulk(emails)
#
#         # -------------------------------------------------
#         # 3️⃣ Store (idempotent)
#         # -------------------------------------------------
#         print("[STEP 3] Storing emails in DB...")
#         insert_emails(classified_emails)
#
#         # -------------------------------------------------
#         # 4️⃣ Notify High Priority
#         # -------------------------------------------------
#         high_priority = [
#             e for e in classified_emails
#             if e.get("priority") == "High Priority"
#         ]
#
#         print(f"[STEP 4] Sending {len(high_priority)} WhatsApp alert(s)...")
#
#         alerts_sent = 0
#
#         for email in high_priority:
#             try:
#                 send_whatsapp_message(
#                     subject=email.get("subject", "No Subject"),
#                     sender=email.get("from", "Unknown"),
#                     priority=email.get("priority"),
#                     snippet=email.get("body", ""),
#                 )
#                 alerts_sent += 1
#
#             except Exception as e:
#                 error_msg = str(e)
#
#                 # -------------------------------------------------
#                 # 🛑 Sandbox Expiry Detection
#                 # -------------------------------------------------
#                 if "63016" in error_msg:
#                     print("[WARN] WhatsApp sandbox expired.")
#                     send_sandbox_expiry_notification()
#                     break  # stop retrying WhatsApp
#
#                 print(f"[ERROR] WhatsApp send failed: {error_msg}")
#
#         print("======================================================")
#         print("✅ PIPELINE COMPLETED")
#         print("======================================================")
#
#         return {
#             "status": "success",
#             "processed_emails": len(classified_emails),
#             "alerts_sent": alerts_sent,
#             "timestamp": datetime.utcnow().isoformat(),
#         }
#
#     except Exception as e:
#         print(f"[FATAL] Pipeline failed: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


from datetime import datetime, timedelta
from fastapi import HTTPException

from classifier.smart_email_classifier import classify_emails_bulk
from databases.email_db import insert_emails
from email_ops.email_reader import read_read_emails, read_unread_emails
from notifiers.whatsapp_notifiers import (
    send_whatsapp_message,
    send_sandbox_expiry_notification,
)


async def run_pipeline(
    hours_back: int = 48,
    limit: int = 4,
    unread: bool = True,
):
    """
    Headless pipeline (GitHub Actions friendly):

    - Computes time window dynamically (now - hours_back)
    - Fetch emails
    - Classify
    - Store
    - Notify (WhatsApp)
    """

    try:
        print("\n======================================================")
        print("📧 EMAIL PIPELINE STARTED (v1 - Scheduled Mode)")
        print("======================================================")

        # -------------------------------------------------
        # ⏱️ Compute rolling time window (UTC)
        # -------------------------------------------------
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)

        # Gmail reader expects dd-mm-yyyy
        start_date = start_time.strftime("%d-%m-%Y")
        end_date = end_time.strftime("%d-%m-%Y")

        print(f"[TIME] Window: last {hours_back} hours")
        print(f"[TIME] Start: {start_time.isoformat()} UTC")
        print(f"[TIME] End  : {end_time.isoformat()} UTC")

        # -------------------------------------------------
        # 1️⃣ Fetch Emails
        # -------------------------------------------------
        if unread:
            print("[STEP 1] Fetching UNREAD emails...")
            emails = read_unread_emails(start_date, end_date, limit)
        else:
            print("[STEP 1] Fetching READ emails...")
            emails = read_read_emails(start_date, end_date, limit)

        if not emails:
            print("[INFO] No emails found in this window.")
            return {
                "status": "success",
                "processed_emails": 0,
                "alerts_sent": 0,
                "message": "No new emails in last window",
            }

        print(f"[INFO] Retrieved {len(emails)} email(s).")

        # -------------------------------------------------
        # 2️⃣ Classify
        # -------------------------------------------------
        print("[STEP 2] Classifying emails...")
        classified_emails = classify_emails_bulk(emails)

        # -------------------------------------------------
        # 3️⃣ Store (idempotent via email ID)
        # -------------------------------------------------
        print("[STEP 3] Storing emails in DB...")
        insert_emails(classified_emails)

        # -------------------------------------------------
        # 4️⃣ Notify High Priority
        # -------------------------------------------------
        high_priority = [
            e for e in classified_emails
            if e.get("priority") == "High Priority"
        ]

        print(f"[STEP 4] Sending {len(high_priority)} WhatsApp alert(s)...")

        alerts_sent = 0

        for email in high_priority:
            try:
                send_whatsapp_message(
                    subject=email.get("subject", "No Subject"),
                    sender=email.get("from", "Unknown"),
                    priority=email.get("priority"),
                    snippet=email.get("body", ""),
                    received_time=email.get("date"),
                )
                alerts_sent += 1

            except Exception as e:
                error_msg = str(e)

                # -------------------------------------------------
                # 🛑 Sandbox Expiry Detection
                # -------------------------------------------------
                if "63016" in error_msg:
                    print("[WARN] WhatsApp sandbox expired.")
                    send_sandbox_expiry_notification()
                    break  # Stop further attempts

                print(f"[ERROR] WhatsApp send failed: {error_msg}")

        print("======================================================")
        print("✅ PIPELINE COMPLETED")
        print("======================================================")

        return {
            "status": "success",
            "processed_emails": len(classified_emails),
            "alerts_sent": alerts_sent,
            "window_hours": hours_back,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        print(f"[FATAL] Pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# Local run (manual testing only)
# =========================================================
if __name__ == "__main__":
    import asyncio
    asyncio.run(run_pipeline())
