#!/bin/bash
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "Python not found. Install from https://python.org"
    exit 1
fi
$PYTHON -m pip install -r requirements.txt --quiet
$PYTHON main.py
