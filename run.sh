#!/bin/bash
# Simple run script for development

cd "$(dirname "$0")"

# Set PYTHONPATH to current directory
export PYTHONPATH="$(pwd)"

# Run with the virtual environment's Python
echo "Starting ECG Processing Service on http://localhost:8000"
echo "API documentation: http://localhost:8000/docs"
echo ""

.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
