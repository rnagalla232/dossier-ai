#!/usr/bin/env bash
set -euo pipefail

# -------- Config (override via env vars) --------
QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
COLLECTION="${COLLECTION:-web_embeddings}"
EMBED_DIM="${EMBED_DIM:-1536}"
DISTANCE="${DISTANCE:-Cosine}"     # Cosine | Dot | Euclid
INDEX_FIELD="${INDEX_FIELD:-doc_id}"
INDEX_SCHEMA="${INDEX_SCHEMA:-keyword}"  # keyword|integer|float|text|bool|uuid|datetime|geo
API_KEY_HEADER=""
[[ -n "${QDRANT_API_KEY:-}" ]] && API_KEY_HEADER="-H api-key:${QDRANT_API_KEY}"

# ------------------------------------------------
say() { echo "[qdrant-init] $*"; }

http_code() {
  # Print only HTTP status code
  curl -sS -o /dev/null -w "%{http_code}" $API_KEY_HEADER "$@"
}

ensure_collection() {
  say "Checking collection '$COLLECTION' ..."
  code=$(http_code "${QDRANT_URL}/collections/${COLLECTION}")
  if [[ "$code" == "200" ]]; then
    say "Collection exists."
    return 0
  fi

  if [[ "$code" == "404" ]]; then
    say "Creating collection '$COLLECTION' (size=${EMBED_DIM}, distance=${DISTANCE}) ..."
    curl -sS -X PUT "${QDRANT_URL}/collections/${COLLECTION}" \
      -H "Content-Type: application/json" $API_KEY_HEADER \
      --data @- <<EOF >/dev/null
{
  "vectors": {
    "size": ${EMBED_DIM},
    "distance": "${DISTANCE}"
  }
}
EOF
    say "Collection created."
  else
    say "Unexpected status checking collection: $code"
    exit 1
  fi
}

ensure_payload_index() {
  say "Ensuring payload index on field '${INDEX_FIELD}' (schema=${INDEX_SCHEMA}) ..."
  # Creating an index is safe to call repeatedly; it will (re)create/update as needed.
  curl -sS -X PUT "${QDRANT_URL}/collections/${COLLECTION}/index" \
    -H "Content-Type: application/json" $API_KEY_HEADER \
    --data @- <<EOF >/dev/null
{
  "field_name": "${INDEX_FIELD}",
  "field_schema": "${INDEX_SCHEMA}"
}
EOF
  say "Payload index ensured."
}

main() {
  ensure_collection
  ensure_payload_index
  say "Done. Collection '${COLLECTION}' is ready at ${QDRANT_URL}."
  say "Try: curl -s ${QDRANT_URL}/collections | jq ."
}

main "$@"