#!/usr/bin/env bash
set -euo pipefail

ES_URL="${ELASTICSEARCH_URL:-http://localhost:9200}"
INDEX="${ELASTICSEARCH_INDEX:-logs}"

curl -sS -X PUT "$ES_URL/$INDEX" \
  -H 'Content-Type: application/json' \
  --data-binary @scripts/index-mapping.json || true

curl -sS -X POST "$ES_URL/_bulk" \
  -H 'Content-Type: application/x-ndjson' \
  --data-binary @data/events.ndjson

echo
echo "Indexed synthetic events into $INDEX"
