#!/bin/bash
# Startup script for ECG Processing Service

# Set working directory
cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Set PYTHONPATH
export PYTHONPATH="$(pwd)"

# Run the server
uvicorn app.main:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}" --reload
