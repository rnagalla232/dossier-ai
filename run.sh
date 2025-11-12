#!/bin/bash

# Install playwright chromium if needed
NODE_TLS_REJECT_UNAUTHORIZED=0 python -m playwright install chromium

# Start the background worker in the background
echo "Starting document processing worker..."
python -m src.worker &
WORKER_PID=$!
echo "Worker started with PID: $WORKER_PID"

# Function to cleanup on exit
cleanup() {
    echo "Shutting down..."
    echo "Stopping worker (PID: $WORKER_PID)..."
    kill $WORKER_PID 2>/dev/null
    exit 0
}

# Trap SIGINT and SIGTERM
trap cleanup SIGINT SIGTERM

# Start the main application
echo "Starting main application..."
uvicorn src.api.route:app --reload --port 8000 &
APP_PID=$!

# Wait for both processes
wait $APP_PID $WORKER_PID