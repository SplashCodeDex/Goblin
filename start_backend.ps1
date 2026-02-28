# Robin Backend Startup Script
# This script sets PYTHONPATH and starts the FastAPI server

Write-Host "Starting Robin Backend API Server..." -ForegroundColor Cyan

# Set PYTHONPATH to src directory
$env:PYTHONPATH = "$PSScriptRoot/src"

# Start uvicorn with hot reload
python -m uvicorn robin.api.server:app --reload --port 8000
