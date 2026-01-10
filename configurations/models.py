import email.utils
import json
import logging
import os
from datetime import datetime

import pytz
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from configurations.utils import ensure_cache_dir

Base = declarative_base()


class Email(Base):
    __tablename__ = 'emails'

    id = Column(String(100), primary_key=True)
    subject = Column(String(500))
    from_address = Column(String(200))
    date = Column(DateTime)
    content = Column(Text)
    embedding = Column(Text)  # Store embedding as JSON string
    last_updated = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'subject': self.subject,
            'from': self.from_address,
            'date': self.date.isoformat() if self.date else None,
            'content': self.content,
            'embedding': json.loads(self.embedding) if self.embedding else None
        }

    @classmethod
    def from_dict(cls, data):
        # Handle date parsing
        date = None
        if data.get('date'):
            try:
                # If date is already in ISO format
                date = datetime.fromisoformat(data['date'])
            except ValueError:
                try:
                    # Try parsing as Gmail format
                    parsed_date = email.utils.parsedate_to_datetime(data['date'])
                    if parsed_date.tzinfo is None:
                        parsed_date = pytz.UTC.localize(parsed_date)
                    date = parsed_date
                except Exception as e:
                    logging.error(f"Error parsing date {data['date']}: {str(e)}")

        return cls(
            id=data['id'],
            subject=data['subject'],
            from_address=data['from'],
            date=date,
            content=data['content'],
            embedding=json.dumps(data['embedding']) if data.get('embedding') else None
        )


# Database setup
def init_db():
    """Initialize database in cache directory"""
    cache_dir = ensure_cache_dir()
    db_path = os.path.join(cache_dir, 'emails.db')
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
