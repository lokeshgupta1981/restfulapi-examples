"""Serves site/ on http://127.0.0.1:8000 the way an llms.txt-friendly docs site does.

- .md and .txt files are sent as text/markdown with UTF-8.
- Every docs page gets a Link header that points to the llms.txt covering it
  (rel="describedby"), and Markdown pages say they are the alternate of the HTML page.
Usage: python serve.py
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SITE = Path(__file__).parent / "site"


class DocsHandler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      ".md": "text/markdown; charset=utf-8",
                      ".txt": "text/markdown; charset=utf-8",
                      ".yaml": "application/yaml"}

    def end_headers(self):
        path = self.path.split("?")[0]
        if path.startswith("/docs/") and not path.endswith("llms.txt"):
            links = ['</docs/llms.txt>; rel="describedby"']
            if path.endswith(".html"):
                links.insert(0, f'<{path[:-5]}.md>; rel="alternate"; type="text/markdown"')
            self.send_header("Link", ", ".join(links))
        super().end_headers()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), partial(DocsHandler, directory=str(SITE)))
    print("Serving site/ on http://127.0.0.1:8000/docs/llms.txt")
    server.serve_forever()
