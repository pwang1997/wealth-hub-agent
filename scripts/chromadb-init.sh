#!/bin/sh
set -e

CHROMA_PORT="${CHROMA_PORT:-8000}"
uvicorn chromadb.app:app --host 0.0.0.0 --port "${CHROMA_PORT}" &
server_pid=$!

retries=0
until curl -fsS "http://localhost:${CHROMA_PORT}/api/v1/heartbeat" >/dev/null 2>&1; do
  retries=$((retries + 1))
  if [ "${retries}" -ge 60 ]; then
    echo "ChromaDB did not become ready in time" >&2
    kill "${server_pid}" 2>/dev/null || true
    exit 1
  fi
  sleep 1
done

if [ -n "${CHROMA_TENANT:-}" ] && [ -n "${CHROMA_DATABASE:-}" ]; then
  curl -fsS -X POST "http://localhost:${CHROMA_PORT}/api/v1/databases" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"${CHROMA_DATABASE}\",\"tenant\":\"${CHROMA_TENANT}\"}" \
    >/dev/null 2>&1 || true
fi

wait "${server_pid}"
