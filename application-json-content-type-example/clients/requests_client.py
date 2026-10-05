import json

import requests

URL = "http://127.0.0.1:9300/orders"
order = {"item": "keyboard", "quantity": 2}

with_json = requests.post(URL, json=order, headers={"X-Client": "requests json="})
print(with_json.text)

with_dict = requests.post(URL, data=order, headers={"X-Client": "requests data=dict"})
print(with_dict.text)

with_string = requests.post(URL, data=json.dumps(order), headers={"X-Client": "requests data=str"})
print(with_string.text)
