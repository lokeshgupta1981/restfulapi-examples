from fastapi.testclient import TestClient

from app import app

client = TestClient(app, follow_redirects=False)


def test_invoice_pdf_is_a_temporary_redirect():
    response = client.get("/invoices/1001/pdf")
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/storage/invoices/1001.pdf")
    assert response.headers["Cache-Control"] == "no-store"


def test_redirect_target_returns_the_file():
    response = client.get("/invoices/1001/pdf", follow_redirects=True)
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"
