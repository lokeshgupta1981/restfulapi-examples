"""Load asyncapi.yaml and find the message schema for an MQTT topic."""
import re
from pathlib import Path

import yaml
from jsonschema import Draft7Validator, FormatChecker

HERE = Path(__file__).parent


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve(node, file_path, cache):
    """Replace every $ref with the object it points to (local files and #/ pointers)."""
    if isinstance(node, list):
        return [resolve(item, file_path, cache) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        ref = node["$ref"]
        target_file, _, pointer = ref.partition("#")
        target_path = (file_path.parent / target_file).resolve() if target_file else file_path
        if target_path not in cache:
            cache[target_path] = load_yaml(target_path)
        target = cache[target_path]
        for part in [p for p in pointer.split("/") if p]:
            target = target[part]
        return resolve(target, target_path, cache)
    return {key: resolve(value, file_path, cache) for key, value in node.items()}


def address_to_regex(address):
    """orders/{orderId}/status -> ^orders/(?P<orderId>[^/]+)/status$"""
    pattern = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", address)
    return re.compile("^" + pattern + "$")


class Contract:
    def __init__(self, path=HERE / "asyncapi.yaml"):
        path = Path(path).resolve()
        self.doc = resolve(load_yaml(path), path, {})
        self.channels = []
        for channel_id, channel in self.doc["channels"].items():
            messages = list(channel["messages"].values())
            self.channels.append((channel_id, address_to_regex(channel["address"]), messages))

    def subscription(self, channel_id):
        """MQTT topic filter for a channel: {param} becomes the + wildcard."""
        address = self.doc["channels"][channel_id]["address"]
        return re.sub(r"\{\w+\}", "+", address)

    def check(self, topic, payload):
        """Return (message name, list of errors) for a payload received on a topic.

        A payload must match one, and only one, of the channel's messages.
        """
        for channel_id, regex, messages in self.channels:
            if regex.match(topic):
                results = {}
                for message in messages:
                    validator = Draft7Validator(message["payload"], format_checker=FormatChecker())
                    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
                    results[message["name"]] = [
                        f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in errors
                    ]
                matches = [name for name, errors in results.items() if not errors]
                if len(matches) == 1:
                    return matches[0], []
                if len(matches) > 1:
                    return None, [f"payload matches several messages: {matches}"]
                if len(results) == 1:
                    return next(iter(results.items()))
                return None, [f"payload matches none of {list(results)}"]
        return None, [f"topic {topic} is not in asyncapi.yaml"]
