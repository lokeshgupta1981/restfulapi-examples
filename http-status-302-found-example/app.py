"""Invoices API that answers with HTTP 302 Found (and 303, 307 for comparison)."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse

app = FastAPI()

INVOICES = {"1001": {"id": "1001", "status": "PAID", "total": "49.90", "currency": "EUR"}}


@app.get("/invoices/{invoice_id}/pdf")
def invoice_pdf(invoice_id: str):
    # The PDF is stored in a separate file store today; the location can change,
    # so clients keep calling /invoices/{id}/pdf and follow the redirect.
    storage_url = f"/storage/invoices/{invoice_id}.pdf?expires=1791200000&sig=3f9a1c"
    response = RedirectResponse(storage_url, status_code=302)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/storage/invoices/{file_name}")
def stored_file(file_name: str):
    return PlainTextResponse(f"%PDF-1.7 (content of {file_name})", media_type="application/pdf")


@app.api_route("/redirect/{code}", methods=["GET", "POST", "PUT", "DELETE"])
def redirect_with(code: int, request: Request):
    # Sends any method to /echo with the requested 3xx status code.
    target = request.query_params.get("to", "/echo")
    return RedirectResponse(target, status_code=code)


@app.api_route("/echo", methods=["GET", "POST", "PUT", "DELETE"])
async def echo(request: Request):
    body = await request.body()
    return JSONResponse({
        "method": request.method,
        "body_bytes": len(body),
        "authorization": "Authorization" in request.headers,
    })


@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    return INVOICES.get(invoice_id, {})
