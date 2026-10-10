# Agent Client Protocol (ACP) Example

Source code for the article [Agent Client Protocol (ACP) Explained](https://restfulapi.net/agent-client-protocol/).

The example has both sides of ACP, written with the official Python SDK.

- `timeout_agent.py` is an ACP agent. It reads a Python file through the editor, shows a plan and a diff, asks permission, and adds `timeout=10` to every `requests.get()` call. It uses no language model, so it runs without an API key.
- `mini_editor.py` is an ACP client that plays the editor. It starts the agent as a subprocess, prints every JSON-RPC message on the wire, serves `fs/read_text_file` and `fs/write_text_file` from the `workspace` folder, and asks you before the agent writes.
- `samples/weather.py` is the file the agent changes. Each run copies it into a fresh `workspace` folder.

## Versions

- Python 3.10 or later
- `agent-client-protocol` 0.12.1 (ACP protocol version 1)

## Run

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python mini_editor.py "add timeouts to weather.py"          # type allow or reject
python mini_editor.py --yes "add timeouts to weather.py"    # approve without asking
```

## Expected output (wire messages trimmed)

```text
Connected to timeout-agent, ACP protocol version 1
USER: add timeouts to weather.py
PLAN: [in_progress] Read weather.py
PLAN: [pending] Add timeout=10 to requests.get() calls
TOOL call_5d8c1b8c: Add timeouts in weather.py (pending)
DIFF weather.py:
  - response = requests.get(f"https://api.example.com/weather?city={city}")
  + response = requests.get(f"https://api.example.com/weather?city={city}", timeout=10)
  ...
PERMISSION: allow (Allow once), reject (Reject) -> allow (--yes)
TOOL call_5d8c1b8c: (completed)
AGENT: Added timeout=10 to 2 requests.get() calls in weather.py.
Turn ended: end_turn
```

## Use the agent in a real editor

Zed (`settings.json`):

```json
{
  "agent_servers": {
    "Timeout Agent": {
      "type": "custom",
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/timeout_agent.py"],
      "env": {}
    }
  }
}
```

JetBrains IDEs (`~/.jetbrains/acp.json`):

```json
{
  "agent_servers": {
    "Timeout Agent": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/timeout_agent.py"]
    }
  }
}
```

Open a project that contains `weather.py`, start a thread with "Timeout Agent" and type "add timeouts to weather.py".
