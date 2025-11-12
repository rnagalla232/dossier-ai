#!/bin/bash

# Startup script for running both the main application and worker process
set -e

echo "Starting document processing worker..."
python -m src.worker &
WORKER_PID=$!
echo "Worker started with PID: $WORKER_PID"

# Function to cleanup on exit
cleanup() {
    echo "Shutting down..."
    echo "Stopping worker (PID: $WORKER_PID)..."
    kill -TERM $WORKER_PID 2>/dev/null || true
    wait $WORKER_PID 2>/dev/null || true
    exit 0
}

# Trap SIGINT and SIGTERM
trap cleanup SIGINT SIGTERM

echo "Starting main application..."
# Run uvicorn in foreground
uvicorn src.api.route:app --host 0.0.0.0 --port 8000 &
APP_PID=$!

# Wait for both processes
wait -n $APP_PID $WORKER_PID

# If either process exits, cleanup and exit
EXIT_CODE=$?
cleanup
exit $EXIT_CODE

