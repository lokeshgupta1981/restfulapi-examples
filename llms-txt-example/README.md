# llms.txt for API Documentation Example

Source code for the article [llms.txt for API Documentation](https://restfulapi.net/llms-txt/).

The example turns an OpenAPI document into an llms.txt file, Markdown pages and an llms-full.txt, serves them the way an LLM-friendly docs site does, and validates the result.

- `openapi.yaml` describes a small Acme Orders API.
- `guides/` holds hand-written Markdown guides (authentication, errors, changelog).
- `generate.py` writes `site/docs/llms.txt`, `site/docs/llms-full.txt` and one `.md` page per OpenAPI tag.
- `serve.py` serves `site/` on port 8000 with `Content-Type: text/markdown` and a `Link: rel="describedby"` header.
- `validate.py` checks the structure of an llms.txt file, parses it with the `llms-txt` package from Answer.AI and requests every link.

## Versions

- Python 3.10 or later
- `llms-txt` 0.0.7, `PyYAML` 6.0.3

## Run

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python generate.py                 # optional argument: the base URL, default http://127.0.0.1:8000
python serve.py                    # in a second terminal
python validate.py http://127.0.0.1:8000/docs/llms.txt
curl -I http://127.0.0.1:8000/docs/orders.md
```

To publish the files, run `python generate.py https://docs.example.com` and copy `site/docs/` to your docs host.

## Expected output of validate.py

```text
GET http://127.0.0.1:8000/docs/llms.txt -> HTTP 200, text/markdown; charset=utf-8, 994 bytes, 118 words
title:    Acme Orders API
summary:  REST API for creating and tracking orders in the Acme shop. Base URL https://api.acme.example/v1, API version 2026-09-01.
section:  Guides (2 links)
  200 text/markdown; charset=utf-8   267 bytes  Authentication
  200 text/markdown; charset=utf-8   410 bytes  Errors
section:  API reference (2 links)
  200 text/markdown; charset=utf-8  1557 bytes  Orders
  200 text/markdown; charset=utf-8   547 bytes  Customers
section:  Optional (2 links)
  200 text/markdown; charset=utf-8   146 bytes  Changelog
  200 application/yaml              3520 bytes  OpenAPI document
OK
```
