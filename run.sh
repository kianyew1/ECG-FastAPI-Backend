#!/bin/bash
# Simple run script for development

cd "$(dirname "$0")"

# Set PYTHONPATH to current directory
export PYTHONPATH="$(pwd)"

# Run with the virtual environment's Python
echo "Starting ECG Processing Service on http://localhost:8001"
echo "API documentation: http://localhost:8001/docs"
echo ""

# Detect platform and use appropriate Python executable
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    # Windows (Git Bash, Cygwin, or native)
    .venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
else
    # Linux/Mac
    .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
fi