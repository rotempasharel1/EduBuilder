#!/usr/bin/env bash
set -euo pipefail

API_URL="${TRACE_API_URL:-http://localhost:8000}"

echo "=== PoseAI Trainer EX3 Demo ==="
echo "1. Stopping any previous local stack..."
docker compose down -v >/dev/null 2>&1 || true

echo "2. Building and starting the stack..."
docker compose up -d --build

echo "3. Waiting for the API health endpoint..."
for i in {1..30}; do
  if curl -fsS "$API_URL/health" >/dev/null 2>&1; then
    echo "   API is healthy."
    break
  fi
  sleep 2
  if [ "$i" -eq 30 ]; then
    echo "API did not become healthy in time."
    exit 1
  fi
done

echo "4. Seeding sample data..."
uv run python scripts/seed.py

echo "5. Triggering the worker..."
docker compose run --rm worker python scripts/refresh.py

echo "6. Refreshing the Redis trace excerpt in docs/EX3-notes.md..."
uv run python scripts/capture_trace_excerpt.py

echo "7. Quick checks:"
curl "$API_URL/health"
echo
curl -I "$API_URL/plans" || true
echo

echo "8. Open these URLs:"
echo "   Frontend: http://localhost:8501"
echo "   API Docs: http://localhost:8000/docs"
