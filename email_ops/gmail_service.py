import base64
import email
import email.utils
import logging
import re
from datetime import datetime, timedelta
from email.mime.text import MIMEText

import pytz
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GmailService:
    def __init__(self):
        self.service = None

    def build_service(self, credentials):
        """Build Gmail API service"""
        try:
            self.service = build('gmail', 'v1', credentials=credentials)
            return True
        except Exception as e:
            logger.error(f"Error building Gmail service: {str(e)}")
            return False

    def _parse_email_date(self, date_str):
        """Parse Gmail date string to ISO format"""
        try:
            # Parse the email date string
            parsed_date = email.utils.parsedate_to_datetime(date_str)
            # Convert to UTC if not already
            if parsed_date.tzinfo is None:
                parsed_date = pytz.UTC.localize(parsed_date)
            return parsed_date.isoformat()
        except Exception as e:
            logger.error(f"Error parsing date {date_str}: {str(e)}")
            return None

    def get_emails(self, credentials, date_range=None):
        """Get emails from Gmail with proper data structure"""
        try:
            if not self.service:
                self.service = build('gmail', 'v1', credentials=credentials)

            # Build query
            query = []
            if date_range:
                start_date = date_range.get('start')
                end_date = date_range.get('end')
                if start_date:
                    query.append(f'after:{start_date}')
                if end_date:
                    query.append(f'before:{end_date}')

            # Get messages
            results = self.service.users().messages().list(
                userId='me',
                q=' '.join(query) if query else None
            ).execute()

            messages = results.get('messages', [])
            emails = []

            for message in messages:
                try:
                    msg = self.service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()

                    # Extract headers
                    headers = msg['payload']['headers']
                    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                    from_address = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
                    date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), None)

                    # Parse date
                    date = self._parse_email_date(date_str) if date_str else None

                    # Extract content
                    content = ''
                    if 'parts' in msg['payload']:
                        for part in msg['payload']['parts']:
                            if part['mimeType'] == 'text/plain':
                                content = base64.urlsafe_b64decode(part['body']['data']).decode()
                                break
                    elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
                        content = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode()

                    # Create email object with consistent structure
                    email = {
                        'id': message['id'],
                        'subject': subject,
                        'from': from_address,
                        'date': date,
                        'content': content
                    }
                    emails.append(email)

                except Exception as e:
                    logger.error(f"Error processing message {message['id']}: {str(e)}")
                    continue

            logger.info(f"Retrieved {len(emails)} emails from Gmail")
            return emails

        except Exception as e:
            logger.error(f"Error fetching emails from Gmail: {str(e)}")
            raise

    def _construct_date_query(self, date_range):
        """Construct Gmail search query for date range."""
        try:
            if date_range['type'] == 'custom':
                start_date = datetime.strptime(date_range['start'], '%Y-%m-%d')
                end_date = datetime.strptime(date_range['end'], '%Y-%m-%d')
                return f'after:{start_date.strftime("%Y/%m/%d")} before:{end_date.strftime("%Y/%m/%d")}'
            elif date_range['type'] == 'month':
                year = int(date_range['year'])
                month = int(date_range['month'])
                start_date = datetime(year, month, 1)
                if month == 12:
                    end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime(year, month + 1, 1) - timedelta(days=1)
                return f'after:{start_date.strftime("%Y/%m/%d")} before:{end_date.strftime("%Y/%m/%d")}'
            elif date_range['type'] == 'year':
                year = int(date_range['year'])
                start_date = datetime(year, 1, 1)
                end_date = datetime(year, 12, 31)
                return f'after:{start_date.strftime("%Y/%m/%d")} before:{end_date.strftime("%Y/%m/%d")}'
            else:
                raise ValueError(f"Invalid date range type: {date_range['type']}")
        except Exception as e:
            logger.error(f"Error constructing date query: {str(e)}")
            raise

    def _extract_email_data(self, message):
        """Extract relevant data from email message."""
        try:
            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')

            # Get message body
            body = self._get_email_body(message['payload'])
            if not body:
                logger.warning(f"No body found for message {message['id']}")
                return None

            return {
                'id': message['id'],
                'subject': subject,
                'from': sender,
                'date': date,
                'content': body
            }
        except Exception as e:
            logger.error(f"Error extracting email data: {str(e)}")
            return None

    def _get_email_body(self, payload):
        """Extract email body from message payload."""
        try:
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        return base64.urlsafe_b64decode(part['body']['data']).decode()
                    elif part['mimeType'] == 'text/html':
                        # Remove HTML tags for plain text
                        html_content = base64.urlsafe_b64decode(part['body']['data']).decode()
                        return re.sub('<[^<]+?>', '', html_content)

            # If no parts, try to get body directly
            if 'body' in payload and 'data' in payload['body']:
                return base64.urlsafe_b64decode(payload['body']['data']).decode()

            return ''
        except Exception as e:
            logger.error(f"Error getting email body: {str(e)}")
            return ''

    def send_email(self, to, subject, message_text):
        """Send an email using Gmail API"""
        try:
            if not self.service:
                raise ValueError("Gmail service not initialized")

            message = MIMEText(message_text)
            message['to'] = to
            message['subject'] = subject

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            self.service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
