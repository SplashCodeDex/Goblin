#!/bin/bash
set -euo pipefail

echo "Starting Tor..."
tor &

echo "Waiting for Tor to be ready..."
# Wait for port 9050 to be open
timeout=60
while ! (echo > /dev/tcp/127.0.0.1/9050) >/dev/null 2>&1; do
    if [ "$timeout" -le 0 ]; then
        echo "Tor failed to start on port 9050."
        exit 1
    fi
    sleep 1
    timeout=$((timeout - 1))
done

echo "Tor is ready."
echo "Starting Robin - AI-Powered Dark Web OSINT Tool..."

exec python main.py "$@"
