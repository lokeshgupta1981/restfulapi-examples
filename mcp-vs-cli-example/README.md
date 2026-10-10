# MCP vs CLI Example

Source code for the article [MCP vs CLI for AI Agents](https://restfulapi.net/mcp-vs-cli/).

The example exposes one small order service in two ways and measures how many tokens each way puts into a model's context for the same task, "What is the total of the paid orders of customer C-5?".

- `orders_core.py` holds 40 sample orders and the functions `list_orders`, `get_order` and `cancel_order`.
- `orders_cli.py` is a command-line tool over the core, with `--help`, `--json` and `--fields`.
- `orders_mcp_server.py` is an MCP server (stdio) with the tools `list_orders`, `get_order` and `cancel_order` over the same core.
- `measure.py` starts the MCP server, lists its tools and calls `list_orders`, runs the CLI, and counts tokens with tiktoken (encoding o200k_base).

## Versions

- Python 3.10 or later
- `mcp` 2.3.0 (MCP protocol version 2026-07-28)
- `tiktoken` 0.12.0 (downloads the o200k_base encoding on first use)

## Run

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python orders_cli.py --help
python orders_cli.py list --customer C-5 --status paid
python orders_cli.py list --customer C-5 --status paid --fields id,total --json
python measure.py
```

## Expected output of measure.py

```text
MCP        tool definitions (3 tools), in context from the start          356 tokens
MCP        list_orders result (full orders)                               824 tokens
MCP        list_orders result with fields=[id, total]                      84 tokens
CLI        orders --help + orders list --help, when the model runs them   185 tokens
CLI        list output (table)                                             68 tokens
CLI        list output with --fields id,total --json                       69 tokens
Code mode  script written by the model + printed result                    37 tokens

answer via MCP: 1403.5 EUR, via CLI: 1403.5 EUR
```

Token counts depend on the tokenizer, so other models give other numbers. The ratios between the rows are the point.

To use the MCP server from an MCP host, add it to the host's configuration with the absolute path of your Python interpreter as `command` and the absolute path of `orders_mcp_server.py` in `args`.
