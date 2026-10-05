Source code for the article [API Latency vs Response Time](https://restfulapi.net/api-latency-vs-response-time/)

# API latency vs response time example

A small Orders API that reports its own processing time in a `Server-Timing` header, a proxy that adds network delay, and a script that measures latency percentiles from the client side.

- `server.py`: Orders API (Python standard library only) on port 9200, HTTPS with `--tls`.
  - `GET /orders/{id}` takes about 10 ms; about 3% of calls take 300 to 600 ms (a simulated lock wait, fixed random seed). The response carries `Server-Timing: db;dur=..., app;dur=..., total;dur=...`.
  - `GET /orders/export` streams about 9.6 MB of JSON lines in 20 pages, so the first byte arrives early and the last byte arrives much later.
  - `--keep-nagle` leaves Nagle's algorithm on, to reproduce a 40 ms gap between the headers and the body.
- `delay_proxy.py`: TCP proxy on port 9201 that holds every chunk for 25 ms in each direction (one round trip = 50 ms). The TCP handshake between the client and the proxy is not delayed.
- `measure.py`: sends N requests, either on one reused connection or with a new connection each time, and prints mean, p50, p90, p95, p99 and max for connect time (TCP plus TLS), wait time (request sent until the headers arrive, the same as curl's `time_starttransfer` minus `time_pretransfer`), server time (from `Server-Timing`), network time (wait minus server time) and total response time. Percentiles use the nearest-rank method.
- `curl-timing.txt`: a `curl -w` format file that prints curl's timing variables.
- `demo.sh`: creates a self-signed certificate, starts the API and the proxy, runs all measurements and stops both processes.
- `nagle.sh`: measures the API straight on port 9200 with Nagle's algorithm left on and with it off (run `demo.sh` once first for the certificate).

## Versions

- Python 3.13.16 (any Python 3.10 or later; no packages to install)
- curl 8.5.0 (any curl 7.x or 8.x has these timing variables)
- OpenSSL 3.0.13 (only to create the self-signed certificate)

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/api-latency-vs-response-time-example
./demo.sh
./nagle.sh
```

Or step by step:

```bash
openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem \
  -days 365 -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost"
python3 server.py --tls                       # terminal 1
python3 delay_proxy.py --delay-ms 25          # terminal 2
curl -s -o /dev/null --cacert cert.pem -w @curl-timing.txt https://localhost:9201/orders/7
python3 measure.py --url https://localhost:9201/orders/42 -n 500
python3 measure.py --url https://localhost:9201/orders/42 -n 200 --new-connection
```

If your shell has an `HTTPS_PROXY` variable, add `localhost` to `NO_PROXY` so curl calls the local server.

The numbers you get depend on your machine. `OUTPUTS.txt` holds one run on a shared test machine.
