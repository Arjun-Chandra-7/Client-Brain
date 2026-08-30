import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/client_brain.db")
if DATABASE_URL.startswith("sqlite:///"):
    Path(DATABASE_URL.removeprefix("sqlite:///")) .parent.mkdir(parents=True, exist_ok=True)

sqlite_options = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}
# A shared connection is required for SQLite :memory: databases used by FastAPI's threaded TestClient.
if DATABASE_URL == "sqlite:///:memory:":
    sqlite_options["poolclass"] = StaticPool
engine = create_engine(DATABASE_URL, **sqlite_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
