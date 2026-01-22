import os

from dotenv import load_dotenv

# Load .env file
load_dotenv()

CLASSIFICATION_MODE = "llm" # llm


# Gmail / Google Cloud API
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
GMAIL_CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
GMAIL_TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "token.json")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH")
GMAIL_TOKEN_JSON = os.getenv("GMAIL_TOKEN_JSON")

# Twilio / WhatsApp
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM")
TWILIO_WHATSAPP_TO = os.getenv("TWILIO_WHATSAPP_TO")
BITLY_ACCESS_TOKEN = os.getenv("BITLY_ACCESS_TOKEN")

# LLM / Model
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "openai")

# Scheduler / System Config
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")
BATCH_SEND_HOUR = int(os.getenv("BATCH_SEND_HOUR", 20))
WEEKLY_SEND_DAY = os.getenv("WEEKLY_SEND_DAY", "Sunday")



