Source code for the article [A2A Protocol Explained (A2A vs MCP)](https://restfulapi.net/a2a-protocol/)

# A2A protocol example

An Expense Policy Agent that other agents call over A2A 1.0 (JSON-RPC binding), and two clients.

- `expense_agent.py` (port 9999) is written at the wire level with FastAPI. It serves the Agent Card at `/.well-known/agent-card.json` and answers `SendMessage`, `SendStreamingMessage`, `GetTask` and `CancelTask` at `/a2a`. It checks the `A2A-Version` header (a missing or empty header means 0.3, which the agent rejects with error -32009), pauses a task in `TASK_STATE_INPUT_REQUIRED` when the receipt id is missing, and streams an audit over server-sent events. The agent logic is a few fixed rules instead of a model.
- `client.py` calls every operation with plain HTTP and prints the JSON.
- `sdk_client.py` sends one message with the official A2A Python SDK (a2a-sdk) to check interoperability.

## Versions

Python 3.13, FastAPI 0.143.0, Uvicorn 0.54.0, a2a-sdk 1.2.2.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: run the script in Git Bash or WSL
pip install -r requirements.txt
./run_demo.sh
```

`OUTPUTS.txt` holds the output of a real run.
