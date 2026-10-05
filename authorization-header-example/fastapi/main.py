import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import (HTTPAuthorizationCredentials, HTTPBasic,
                              HTTPBasicCredentials, HTTPBearer)

# Demo values for local tests only.
DEMO_USER = "reports-app"
DEMO_PASSWORD = "demo-pass-123"
DEMO_TOKEN = (Path(__file__).parent.parent / "demo-token.txt").read_text().strip()

app = FastAPI()
basic_scheme = HTTPBasic(realm="orders")
bearer_scheme = HTTPBearer()


@app.get("/basic/orders")
def basic_orders(credentials: HTTPBasicCredentials = Depends(basic_scheme)):
    user_ok = secrets.compare_digest(credentials.username, DEMO_USER)
    password_ok = secrets.compare_digest(credentials.password, DEMO_PASSWORD)
    if not (user_ok and password_ok):
        raise HTTPException(status_code=401, detail="invalid credentials",
                            headers={"WWW-Authenticate": 'Basic realm="orders"'})
    return {"user": credentials.username, "orders": [1001, 1002]}


@app.get("/bearer/orders")
def bearer_orders(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if not secrets.compare_digest(credentials.credentials, DEMO_TOKEN):
        raise HTTPException(status_code=401, detail="invalid token",
                            headers={"WWW-Authenticate": 'Bearer realm="orders"'})
    return {"user": DEMO_USER, "orders": [1001, 1002]}
