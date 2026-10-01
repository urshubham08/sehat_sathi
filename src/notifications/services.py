import os
import smtplib
from email.message import EmailMessage
from sqlalchemy.orm import Session
from src.database.models import Notification, User


def notify(db: Session, user_id: int, title: str, message: str):
    item = Notification(user_id=user_id, title=title, message=message, is_read=False)
    db.add(item)
    db.flush()
    return item


def send_email(user: User, subject: str, body: str):
    host=os.getenv('SMTP_HOST'); port=int(os.getenv('SMTP_PORT','587')); sender=os.getenv('SMTP_FROM'); username=os.getenv('SMTP_USERNAME'); password=os.getenv('SMTP_PASSWORD')
    if not host or not sender or not user.email:
        return False
    msg=EmailMessage(); msg['Subject']=subject; msg['From']=sender; msg['To']=user.email; msg.set_content(body)
    try:
        with smtplib.SMTP(host,port,timeout=10) as server:
            server.starttls()
            if username and password: server.login(username,password)
            server.send_message(msg)
        return True
    except Exception:
        return False
