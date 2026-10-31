"""Bookstore users API that binds requests to DTOs (allow-lists)."""
import os

os.environ.setdefault("DB_URL", "sqlite:///secure.db")

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from models import User, engine, reset_db

app = FastAPI(title="Bookstore users API (secure)")
reset_db()


EMAIL = r"^[^@\s]+@[^@\s]+$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")   # unknown fields -> HTTP 422


class SignUpRequest(StrictModel):
    email: str = Field(pattern=EMAIL)
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8)


class UpdateMeRequest(StrictModel):
    email: str | None = Field(default=None, pattern=EMAIL)
    name: str | None = Field(default=None, min_length=1, max_length=100)


class AdminUpdateRequest(StrictModel):
    role: str | None = Field(default=None, pattern="^(customer|editor|admin)$")
    store_credit: int | None = Field(default=None, ge=0)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str
    role: str
    store_credit: int
    email_verified: bool


def current_user(db: Session, user_id: str | None) -> User:
    user = db.get(User, int(user_id)) if user_id else None
    if user is None:
        raise HTTPException(401, "Unknown user")
    return user


@app.post("/users", status_code=201, response_model=UserResponse)
def sign_up(req: SignUpRequest):
    with Session(engine) as db:
        user = User(email=req.email, name=req.name, password=req.password)
        db.add(user)
        db.commit()
        return UserResponse.model_validate(user)


@app.patch("/users/me", response_model=UserResponse)
def update_me(req: UpdateMeRequest, x_user_id: str | None = Header(None)):
    with Session(engine) as db:
        user = current_user(db, x_user_id)
        changes = req.model_dump(exclude_unset=True)
        if "email" in changes and changes["email"] != user.email:
            user.email_verified = False          # the server decides this field
        for key, value in changes.items():
            setattr(user, key, value)            # keys come from the DTO only
        db.commit()
        return UserResponse.model_validate(user)


@app.patch("/admin/users/{user_id}", response_model=UserResponse)
def admin_update(user_id: int, req: AdminUpdateRequest, x_user_id: str | None = Header(None)):
    with Session(engine) as db:
        if current_user(db, x_user_id).role != "admin":
            raise HTTPException(403, "Admins only")
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(404, "No such user")
        for key, value in req.model_dump(exclude_unset=True).items():
            setattr(user, key, value)
        db.commit()
        return UserResponse.model_validate(user)


@app.get("/users/me", response_model=UserResponse)
def read_me(x_user_id: str | None = Header(None)):
    with Session(engine) as db:
        return UserResponse.model_validate(current_user(db, x_user_id))
