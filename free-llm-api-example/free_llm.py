"""Calls free LLM API tiers through the OpenAI Python SDK, with a fallback chain.

Each provider is OpenAI-compatible, so only the base URL, the key and the model name change.
Keys come from environment variables. Providers without a key are skipped.
Usage: python free_llm.py "Explain HTTP 429 in one sentence."
"""
import os
import sys
import time

from openai import OpenAI, RateLimitError

PROVIDERS = [
    # name, base URL, env var for the key, model
    ("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY", "gemini-3.1-flash-lite"),
    ("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai/gpt-oss-20b"),
    ("openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "google/gemma-4-31b-it:free"),
    ("ollama", "http://localhost:11434/v1", "OLLAMA_API_KEY", "llama3.2"),  # local, any key value works
]
MAX_WAIT = 10  # seconds we are willing to wait for one Retry-After


def retry_after(err):
    """Seconds from the retry-after header, or 5 when it is missing or an HTTP date."""
    value = err.response.headers.get("retry-after", "5")
    return int(float(value)) if value.replace(".", "", 1).isdigit() else 5


def ask(name, base_url, key, model, prompt):
    client = OpenAI(base_url=base_url, api_key=key, max_retries=0, timeout=30)
    for attempt in range(1, 4):
        try:
            reply = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
            print(f"{name}: HTTP 200 on attempt {attempt}, {reply.usage.total_tokens} tokens")
            return reply.choices[0].message.content
        except RateLimitError as err:
            wait = retry_after(err)
            print(f"{name}: HTTP 429 on attempt {attempt}, retry-after {wait} s")
            if wait > MAX_WAIT:
                return None  # daily quota is gone, try the next provider
            time.sleep (wait)
    return None


def main(prompt):
    for name, base_url, key_var, model in PROVIDERS:
        base_url = os.environ.get(f"{name.upper()}_BASE_URL", base_url)  # override for local tests
        key = os.environ.get(key_var)
        if not key:
            print(f"{name}: skipped, {key_var} is not set")
            continue
        answer = ask(name, base_url, key, model, prompt)
        if answer:
            print(f"answer from {name}: {answer}")
            return
    sys.exit("no provider answered")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Explain HTTP 429 in one sentence.")
