import secrets
from datetime import datetime, date

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import validates

from .extensions import db
from .config import classify_tier

_hasher = PasswordHasher()


class CoupleGroup(db.Model):
    __tablename__ = "couple_groups"

    id = db.Column(db.Integer, primary_key=True)
    invite_token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship("User", back_populates="couple_group", foreign_keys="User.couple_group_id")
    categories = db.relationship("Category", back_populates="couple_group", cascade="all, delete-orphan")

    def is_full(self):
        return len(self.members) >= 2

    def partner_of(self, user):
        for m in self.members:
            if m.id != user.id:
                return m
        return None


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    couple_group_id = db.Column(db.Integer, db.ForeignKey("couple_groups.id"), nullable=True, index=True)
    preferred_currency = db.Column(db.String(3), nullable=False, default="USD")
    points = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    couple_group = db.relationship("CoupleGroup", back_populates="members", foreign_keys=[couple_group_id])
    spend_entries = db.relationship("SpendEntry", back_populates="user", cascade="all, delete-orphan")
    goals = db.relationship("Goal", back_populates="owner", cascade="all, delete-orphan", foreign_keys="Goal.owner_id")
    tripwires_set = db.relationship("TripWire", back_populates="setter", foreign_keys="TripWire.setter_id")

    @validates("email")
    def _normalize_email(self, key, value):
        return value.strip().lower() if value else value

    @validates("preferred_currency")
    def _upper_currency(self, key, value):
        return value.upper() if value else value

    def set_password(self, password: str):
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        self.password_hash = _hasher.hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        try:
            _hasher.verify(self.password_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            return False
        if _hasher.check_needs_rehash(self.password_hash):
            self.password_hash = _hasher.hash(password)
        return True


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    couple_group_id = db.Column(db.Integer, db.ForeignKey("couple_groups.id"), nullable=False, index=True)

    couple_group = db.relationship("CoupleGroup", back_populates="categories")

    __table_args__ = (
        UniqueConstraint("couple_group_id", "name", name="uq_category_per_group"),
    )


class SpendEntry(db.Model):
    __tablename__ = "spend_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    original_currency = db.Column(db.String(3), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    description = db.Column(db.String(255), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="spend_entries")
    category = db.relationship("Category")


class FXRate(db.Model):
    __tablename__ = "fx_rates"

    id = db.Column(db.Integer, primary_key=True)
    from_currency = db.Column(db.String(3), nullable=False)
    to_currency = db.Column(db.String(3), nullable=False)
    rate = db.Column(db.Numeric(20, 10), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)

    __table_args__ = (
        UniqueConstraint("from_currency", "to_currency", "date", name="uq_fx_per_day"),
    )


class Goal(db.Model):
    __tablename__ = "goals"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    label = db.Column(db.String(120), nullable=False)
    goal_type = db.Column(db.String(10), nullable=False, default="cap")  # 'cap' | 'target'
    condition_type = db.Column(db.String(20), nullable=False)  # 'total' | 'category'
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    threshold = db.Column(db.Numeric(14, 2), nullable=False)
    threshold_currency = db.Column(db.String(3), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending|active|met|expired|rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship("User", back_populates="goals", foreign_keys=[owner_id])
    category = db.relationship("Category")

    @property
    def tier(self):
        return classify_tier(self.start_date, self.end_date)


class TripWire(db.Model):
    __tablename__ = "tripwires"

    id = db.Column(db.Integer, primary_key=True)
    setter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    target_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    label = db.Column(db.String(120), nullable=False)
    condition_type = db.Column(db.String(20), nullable=False)  # 'total' | 'category'
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    threshold = db.Column(db.Numeric(14, 2), nullable=False)
    threshold_currency = db.Column(db.String(3), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")  # active|tripped|expired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    setter = db.relationship("User", back_populates="tripwires_set", foreign_keys=[setter_id])
    target = db.relationship("User", foreign_keys=[target_user_id])
    category = db.relationship("Category")

    @property
    def tier(self):
        return classify_tier(self.start_date, self.end_date)


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    type = db.Column(db.String(40), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    payload = db.Column(db.String(500), nullable=True)  # e.g. "goal:42" — for inline actions
    read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
