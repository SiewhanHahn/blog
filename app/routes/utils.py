from flask import request
from flask_login import current_user
from app import db
from app.models import LogEntry

# Helper to log security events
def log_security_event(action, user_id=None, ip_address=None):
    if ip_address is None:
        ip_address = request.remote_addr
    log_entry = LogEntry(user_id=user_id, action=action, ip_address=ip_address)
    db.session.add(log_entry)
    db.session.commit()