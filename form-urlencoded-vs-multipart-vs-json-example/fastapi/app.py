"""Tickets API in FastAPI with one endpoint per body format.

Run: uvicorn app:app --port 9172
"""
from typing import Annotated

from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel

app = FastAPI()


class Customer(BaseModel):
    id: str
    plan: str


class TicketJson(BaseModel):
    subject: str
    priority: str = "normal"
    tags: list[str] = []
    customer: Customer | None = None


class TicketForm(BaseModel):
    subject: str
    priority: str = "normal"
    tags: list[str] = []


@app.post("/tickets", status_code=201)
def create_from_json(ticket: TicketJson):
    return {"parsedAs": "json", "ticket": ticket}


@app.post("/tickets/form", status_code=201)
def create_from_form(ticket: Annotated[TicketForm, Form()]):
    return {"parsedAs": "form", "ticket": ticket}


@app.post("/tickets/upload", status_code=201)
async def create_with_attachment(
    subject: Annotated[str, Form()],
    attachment: Annotated[UploadFile, File()],
    priority: Annotated[str, Form()] = "normal",
):
    content = await attachment.read()
    return {
        "parsedAs": "multipart",
        "subject": subject,
        "priority": priority,
        "attachment": {
            "filename": attachment.filename,
            "contentType": attachment.content_type,
            "size": len(content),
        },
    }
