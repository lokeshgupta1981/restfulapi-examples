"""One SDK, three servers. Only the base URL, the key and the model name change."""

import os

from openai import OpenAI

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])                       # https://api.openai.com/v1
ollama_client = OpenAI(base_url="http://localhost:11434/v1/", api_key="ollama")    # key required but ignored
local_client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="demo-key")     # the example server

print(openai_client.base_url, ollama_client.base_url, local_client.base_url, sep="\n")
completion = local_client.chat.completions.create(model="echo-1", messages=[{"role": "user", "content": "hello"}])
print(completion.choices[0].message.content)
