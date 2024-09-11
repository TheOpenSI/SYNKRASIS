#!/bin/sh

# requirements
if [-f /usr/src/app/requirements.txt]; then
    echo "[PIP] Installing requirements"
    pip3 install -r /usr/src/app/requirements.txt
fi

# main
if [-f /usr/src/app/main.py]; then
    echo "[PYTHON] Running main.py"
    python3 /usr/src/app/main.py
else
    echo "Nothing to execute, shutting down"
fi