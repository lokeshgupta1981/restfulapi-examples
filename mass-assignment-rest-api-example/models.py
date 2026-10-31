"""Database model shared by both apps: one users table in SQLite."""
import os

from sqlalchemy import Boolean, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

DB_URL = os.environ.get("DB_URL", "sqlite:///users.db")
engine = create_engine(DB_URL)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    password: Mapped[str] = mapped_column(String)  # demo only: store a hash in real code
    role: Mapped[str] = mapped_column(String, default="customer")
    store_credit: Mapped[int] = mapped_column(Integer, default=0)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)


def reset_db():
    """Start every run with an empty table, then add one admin."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(email="admin@bookstore.test", name="Admin", password="demo-only",
                    role="admin", email_verified=True))
        db.commit()


def as_dict(user: User) -> dict:
    return {c.name: getattr(user, c.name) for c in User.__table__.columns}
