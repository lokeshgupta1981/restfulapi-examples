Source code for the article [AsyncAPI vs OpenAPI](https://restfulapi.net/asyncapi-vs-openapi/)

One Orders service described twice: `openapi.yaml` (OpenAPI 3.1.1) for its REST endpoints and `asyncapi.yaml` (AsyncAPI 3.1.0) for the events it sends and receives on an MQTT broker. Both documents use the same schema files in `schemas/`.

## Versions
- Python 3.13, FastAPI 0.142.2, uvicorn 0.54.0, aiomqtt 2.5.1, amqtt 0.12.1 (MQTT 3.1.1 broker), jsonschema 4.26.0, PyYAML 6.0.3
- Node.js 22, @asyncapi/cli 6.2.0, @redocly/cli 2.57.0

## Files
- `openapi.yaml`: POST /orders, GET /orders/{orderId} and an `orderStatusChanged` webhook
- `asyncapi.yaml`: channels `orders/placed`, `orders/{orderId}/status`, `payments/{orderId}/completed` and the three operations of the Orders service
- `asyncapi-broken.yaml`: a copy with two mistakes, to see what the validator reports
- `schemas/`: shared JSON Schema files
- `app.py`: the Orders service (REST API plus MQTT events), port 9210
- `shipping.py`: a consumer that checks every message against `asyncapi.yaml`
- `contract.py`: loads `asyncapi.yaml`, resolves `$ref` and matches topics to channels
- `publish.py`: sends one MQTT message
- `broker.yaml`: amqtt broker on port 9211

## Run
```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm install

./check.sh   # lint openapi.yaml, validate asyncapi.yaml and asyncapi-broken.yaml
./demo.sh    # start broker, API and consumer, send requests and events, stop everything
```

On Windows, run the commands from `demo.sh` one by one in separate terminals.
