Source code for the article [API Gateway vs Load Balancer vs Reverse Proxy](https://restfulapi.net/api-gateway-vs-load-balancer-vs-reverse-proxy/)

# One nginx, three roles: reverse proxy, load balancer and API gateway

The project runs four copies of a tiny bookstore service (three `books`, one `orders`) and one nginx process that plays three roles on three ports:

- a **reverse proxy** in front of one server: it hides the server, terminates HTTPS and adds `X-Forwarded-For` and `X-Forwarded-Proto`,
- a **load balancer** in front of three identical copies: round robin, and it skips a copy that is down,
- a small **API gateway** in front of the whole API: API key check (HTTP 401), routing by path, rate limit per client (HTTP 429), and it removes the API key before the request reaches a service.

A fourth port is an HTTPS edge in front of the gateway, to show a request passing through several layers.

`demo.sh` sends real requests to each role, stops service copies to show what each role does when a server dies, and prints the nginx logs.

The API keys in `nginx.conf.template` are fake demo keys. The TLS certificate is self-signed and created by `demo.sh` on the first run (in `certs/`, never commit it).

## Versions

- Python 3.13, fastapi 0.143.0, uvicorn 0.54.0 (pinned in requirements.txt)
- nginx 1.24.0 (the Ubuntu 24.04 package); any recent nginx works
- curl 8.5.0, openssl

## Files

| File | What it does |
|---|---|
| bookstore.py | The service. `SERVICE=books` serves `/books` and `/books/{id}`, `SERVICE=orders` serves `/orders/{id}`. Every response has an `X-Instance` header, and `/whoami` returns what the service saw (TCP peer, Host, X-Forwarded-For, X-Forwarded-Proto, X-Client-Id, X-API-Key) |
| nginx.conf.template | The three roles plus the edge. `demo.sh` fills in the ports and writes `nginx.conf` |
| demo.sh | Starts the services and nginx, runs every case with curl, stops everything at the end |
| OUTPUTS.txt | Output of one run of demo.sh |

## How to run

```bash
sudo apt-get install -y nginx      # macOS: brew install nginx
python3 -m venv .venv
source .venv/bin/activate          # Windows: use WSL
pip install -r requirements.txt
./demo.sh
```

nginx runs as your user with its prefix set to this folder (`nginx -p "$PWD" -c "$PWD/nginx.conf"`), so its logs go to `logs/` and nothing in `/etc/nginx` changes.

Default ports: reverse proxy 8080 (HTTP) and 8443 (HTTPS), load balancer 8081, gateway 8082, edge 9443, books 9001-9003, orders 9004. Change any of them with `RP_PORT`, `RP_TLS_PORT`, `LB_PORT`, `GW_PORT`, `EDGE_PORT`, `BOOKS1_PORT`, `BOOKS2_PORT`, `BOOKS3_PORT` and `ORDERS_PORT`.

curl sends its requests from `127.0.0.2`, so that the client address differs from the proxy address in the output. On macOS only `127.0.0.1` exists by default; run `CLIENT_IP=127.0.0.1 ./demo.sh` there.

To try requests by hand after starting the services and nginx the same way as `demo.sh`:

```bash
curl -i http://127.0.0.1:8081/books/1                                   # load balancer
curl -i -H 'X-API-Key: demo-key-mobile-123' http://127.0.0.1:8082/api/orders/1042   # gateway
```
