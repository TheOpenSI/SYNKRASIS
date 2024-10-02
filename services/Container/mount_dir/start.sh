#!/bin/bash

# List files in the /usr/src/app directory
# ls /usr/src/app

# Check for requirements.txt
if [ -f /usr/src/app/requirements.txt ]; then
    echo "[PIP] Installing requirements"
    pip3 install -r /usr/src/app/requirements.txt
    rm /usr/src/app/requirements.txt # TODO: FOR DS1000
fi

# Check for main.py
if [ -f /usr/src/app/main.py ]; then
    echo "[PYTHON] Running main.py"
    python3 /usr/src/app/main.py
else
    echo "Nothing to execute, shutting down"
fi
