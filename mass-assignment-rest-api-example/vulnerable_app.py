"""Bookstore users API with a mass assignment vulnerability. Do not copy."""
import os

os.environ.setdefault("DB_URL", "sqlite:///vulnerable.db")

from fastapi import FastAPI, Header, HTTPException, Request
from sqlalchemy.orm import Session

from models import User, as_dict, engine, reset_db

app = FastAPI(title="Bookstore users API (vulnerable)")
reset_db()


def current_user(db: Session, user_id: str | None) -> User:
    # Demo authentication: the caller sends its user id in X-User-Id.
    # A real API reads the user from a verified token.
    user = db.get(User, int(user_id)) if user_id else None
    if user is None:
        raise HTTPException(401, "Unknown user")
    return user


@app.post("/users", status_code=201)
async def sign_up(request: Request):
    body = await request.json()
    with Session(engine) as db:
        user = User(**body)          # every key in the body becomes a column value
        db.add(user)
        db.commit()
        return as_dict(user)         # and every column goes back to the client


@app.patch("/users/me")
async def update_me(request: Request, x_user_id: str | None = Header(None)):
    body = await request.json()
    with Session(engine) as db:
        user = current_user(db, x_user_id)
        for key, value in body.items():
            setattr(user, key, value)
        db.commit()
        return as_dict(user)


@app.get("/users/me")
def read_me(x_user_id: str | None = Header(None)):
    with Session(engine) as db:
        return as_dict(current_user(db, x_user_id))
