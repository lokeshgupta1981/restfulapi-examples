#!/usr/bin/env bash
# Runs the Python pipeline, then the JavaScript jsonrepair comparison.
PY=${PYTHON:-python3}
echo "######## demo.py (Python, json-repair + Pydantic)"
$PY demo.py
echo; echo "######## js/repair.mjs (Node.js, jsonrepair)"
(cd js && npm install --silent && node repair.mjs)
