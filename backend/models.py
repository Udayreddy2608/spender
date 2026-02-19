from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class CategoryEnum(str, enum.Enum):
    food       = "food"
    travel     = "travel"
    clothes    = "clothes"
    skincare   = "skincare"
    studies    = "studies"
    rent       = "rent"
    emi        = "emi"
    health     = "health"
    subscriptions = "subscriptions"
    misc       = "misc"


class MoodEnum(str, enum.Enum):
    calm     = "calm"
    stressed = "stressed"
    bored    = "bored"
    happy    = "happy"


class Goal(Base):
    __tablename__ = "goals"

    id               = Column(Integer, primary_key=True, index=True)
    target_amount    = Column(Integer, nullable=False)
    deadline         = Column(Date,    nullable=False)
    monthly_income   = Column(Integer, nullable=False)
    emi              = Column(Integer, nullable=False, default=0)
    rent             = Column(Integer, nullable=False, default=0)
    clothing_cap     = Column(Integer, nullable=False, default=10000)
    initial_savings  = Column(Integer, nullable=False, default=0)
    created_at       = Column(DateTime, default=datetime.utcnow)


class Expense(Base):
    __tablename__ = "expenses"

    id           = Column(Integer, primary_key=True, index=True)
    amount       = Column(Integer, nullable=False)
    category     = Column(String,  nullable=False)
    date         = Column(Date,    nullable=False)
    note         = Column(Text,    nullable=True)
    mood         = Column(String,  nullable=True)
    payment_mode = Column(String,  nullable=False, default="upi")  # 'upi' | 'card'


class WeeklyLimit(Base):
    __tablename__ = "weekly_limits"

    id              = Column(Integer, primary_key=True, index=True)
    week_start_date = Column(Date,    nullable=False, unique=True)
    weekly_cap      = Column(Integer, nullable=False, default=4000)
    spent_this_week = Column(Integer, nullable=False, default=0)


class WeeklyHistory(Base):
    """Snapshot of each completed week for analytics."""
    __tablename__ = "weekly_history"

    id              = Column(Integer, primary_key=True, index=True)
    week_start_date = Column(Date,    nullable=False, unique=True)
    weekly_cap      = Column(Integer, nullable=False)
    spent           = Column(Integer, nullable=False)
    saved           = Column(Integer, nullable=False)  # cap - spent (can be negative)


class BalanceLedger(Base):
    """
    Every row is one event that changes the balance:
      type='set'    → user manually set balance (e.g. after checking bank app)
      type='credit' → money came in (salary, transfer, etc.)
      type='debit'  → expense deducted automatically when an expense is logged
    Current balance = last 'set' amount + sum(credits) - sum(debits) since that 'set'.
    """
    __tablename__ = "balance_ledger"

    id          = Column(Integer,  primary_key=True, index=True)
    type        = Column(String,   nullable=False)   # 'set' | 'credit' | 'debit'
    amount      = Column(Integer,  nullable=False)   # always positive
    note        = Column(Text,     nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)
