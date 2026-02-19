from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base

DATABASE_URL = "sqlite:///./spender.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate():
    """Add new columns to existing tables if they don't exist (SQLite-safe)."""
    with engine.connect() as conn:
        # Check and add initial_savings to goals
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(goals)"))]
        if "initial_savings" not in cols:
            conn.execute(text("ALTER TABLE goals ADD COLUMN initial_savings INTEGER NOT NULL DEFAULT 0"))
            conn.commit()

        # Check and add payment_mode to expenses
        ecols = [row[1] for row in conn.execute(text("PRAGMA table_info(expenses)"))]
        if "payment_mode" not in ecols:
            conn.execute(text("ALTER TABLE expenses ADD COLUMN payment_mode TEXT NOT NULL DEFAULT 'upi'"))
            conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
