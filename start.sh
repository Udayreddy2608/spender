#!/bin/bash
# Spender — Start the app
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "⚡ Starting Spender Mission Budget..."
echo "   Backend: http://localhost:8000"
echo "   Press Ctrl+C to stop"
echo ""

venv/bin/uvicorn backend.main:app --reload --port 8000 --app-dir .
