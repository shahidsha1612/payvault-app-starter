#!/usr/bin/env bash
# Smoke test: POST a FAKE card charge to the deployed PayVault API.
# Uses a well-known test PAN only. Never send real cardholder data.
set -euo pipefail

API="${API:-}"
if [[ -z "$API" ]]; then
  echo "error: set API to the invoke URL, e.g. API=https://abc.execute-api...amazonaws.com" >&2
  exit 1
fi

echo "==> POST ${API%/}/charge"
curl -sS -X POST "${API%/}/charge" \
  -H 'content-type: application/json' \
  -d '{"pan":"4111111111111111","expiry":"12/29","cvv":"123","amount":4200,"currency":"USD"}'
echo
echo "==> if you see {\"txn_id\":...,\"status\":\"captured\"} the flawed workload is live."
