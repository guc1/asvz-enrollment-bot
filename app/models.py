# models.py

from app.extensions import db
from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
import logging
from sqlalchemy.types import LargeBinary
from cryptography.fernet import Fernet
from flask import current_app
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)

    # Encrypted fields
    ASVZ_ID_encrypted = db.Column(LargeBinary, nullable=True)
    ASVZ_Password_encrypted = db.Column(LargeBinary, nullable=True)

    # Additional fields
    URL = db.Column(db.String(200), nullable=True)
    # Add any other fields you had previously

    # Relationships
    oauth = db.relationship('OAuth', backref='user', lazy=True)
    enrollments = db.relationship('Enrollment', backref='user', lazy=True)

    def __repr__(self):
        return f"<User {self.email}>"

    # Encryption and decryption methods for ASVZ ID
    @property
    def ASVZ_ID(self):
        if self.ASVZ_ID_encrypted:
            try:
                fernet = Fernet(current_app.config['ENCRYPTION_KEY'])
                return fernet.decrypt(self.ASVZ_ID_encrypted).decode()
            except Exception as e:
                logging.error(f"Error decrypting ASVZ_ID: {e}")
                return None
        return None

    @ASVZ_ID.setter
    def ASVZ_ID(self, value):
        if value:
            fernet = Fernet(current_app.config['ENCRYPTION_KEY'])
            self.ASVZ_ID_encrypted = fernet.encrypt(value.encode())
        else:
            self.ASVZ_ID_encrypted = None

    # Encryption and decryption methods for ASVZ Password
    @property
    def ASVZ_Password(self):
        if self.ASVZ_Password_encrypted:
            try:
                fernet = Fernet(current_app.config['ENCRYPTION_KEY'])
                return fernet.decrypt(self.ASVZ_Password_encrypted).decode()
            except Exception as e:
                logging.error(f"Error decrypting ASVZ_Password: {e}")
                return None
        return None

    @ASVZ_Password.setter
    def ASVZ_Password(self, value):
        if value:
            fernet = Fernet(current_app.config['ENCRYPTION_KEY'])
            self.ASVZ_Password_encrypted = fernet.encrypt(value.encode())
        else:
            self.ASVZ_Password_encrypted = None

class Enrollment(db.Model):
    __tablename__ = 'enrollments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    asvz_id = db.Column(db.String(100), nullable=False)
    base_url = db.Column(db.String(200), nullable=False)
    task_id = db.Column(db.String(36), nullable=True)
    status = db.Column(db.String(50), nullable=True, default='PENDING')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    result = db.Column(db.Boolean, nullable=True)
    message = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Enrollment {self.id} for User {self.user_id}>"

class OAuth(OAuthConsumerMixin, db.Model):
    __tablename__ = 'oauth'

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f"<OAuth {self.provider} for User ID {self.user_id}>"










