Source code for the article [Webhooks vs API Polling](https://restfulapi.net/webhooks-vs-polling/)

# Webhooks vs API polling: a measured comparison

One small Orders API publishes the same stream of 30 order events in two ways, and several clients measure what each way costs.

- `provider.py`: the Orders API (port 9140). It publishes events on a change feed, `GET /events?after=<seq>`, with an `ETag` so pollers can send `If-None-Match` and get HTTP 304. It also POSTs every event to a webhook URL, signed with HMAC-SHA256 (`webhook-id`, `webhook-timestamp`, `webhook-signature` headers), and retries a failed delivery after 1 s, 2 s and 4 s before it gives up. It uses this fixed schedule and does not read `Retry-After`.
- `poller.py`: a polling client with a fixed interval. It records requests, empty answers, HTTP 304 answers and the delay between an event's creation and the moment the client sees it.
- `receiver.py`: a webhook receiver (port 9141). It checks the signature and timestamp, drops duplicate event ids, answers HTTP 204 at once and processes the event from a queue. With `--reconcile-every N` it also reads the change feed every N seconds and processes any event it never got by webhook (the hybrid pattern). With `--outage START:END` it answers HTTP 503 in that window.
- `run_experiment.py`: runs both scenarios and prints the tables.
  - Scenario 1: pollers at 1 s, 5 s and 15 s (with ETag), one poller at 5 s without ETag, and the webhook receiver, all watching the same 30 events.
  - Scenario 2: the receiver is down for 21 s, the provider gives up on some events, and the reconciliation poll recovers them.
- `demo.sh`: starts one provider with 2 events, sends its webhooks to a test receiver on port 9142 that prints the first raw request, and calls the change feed with curl (HTTP 200, then HTTP 304).

The events are generated from a fixed random seed, so the event times are the same on every run. Delays and request counts change a little between runs because of thread timing.

## Versions

- Python 3.13 (tested with 3.13.16). Standard library only, no packages to install.
- curl (for `demo.sh`)

The demo uses ports 9140 to 9143 on 127.0.0.1.

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/webhooks-vs-polling-example
python3 run_experiment.py      # about 3 minutes
./demo.sh
```

Start the provider alone (feed only, no webhooks) to try the curl calls by hand:

```bash
python3 provider.py
curl -i "http://127.0.0.1:9140/events?after=0"
```

Run the parts by hand:

```bash
python3 receiver.py --reconcile-every 20 --duration 120 --out hybrid.json     # terminal 1
python3 provider.py --webhook-url http://127.0.0.1:9141/webhooks/orders        # terminal 2
python3 poller.py --interval 5 --duration 90 --out poll-5.json                 # terminal 3
```

The webhook secret `whsec_demo_secret` is for the demo only. In production, keep secrets out of source code and serve the webhook endpoint over HTTPS.
