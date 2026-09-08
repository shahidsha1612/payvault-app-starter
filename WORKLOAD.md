# WORKLOAD.md — what PayVault does

PayVault is a minimal, serverless **card-payment intake and ledger**. It is the
kind of thing a startup slaps together in a weekend and then has to make
audit-defensible before it can process real cards.

## Architecture

```
client ──POST /charge──▶ API Gateway (HTTP API)
                              │
                              ▼
                        Lambda: charge
                         │        │
              put_item   │        │  put_object
                         ▼        ▼
                   DynamoDB     S3 receipts
                   (ledger)     (public!)
```

- **API Gateway (HTTP API)** — single route `POST /charge`, no auth.
- **Lambda `charge`** — validates nothing, captures the payment, writes a ledger
  row and a JSON receipt.
- **DynamoDB `ledger`** — one row per transaction (`txn_id` hash key).
- **S3 `receipts`** — one JSON object per transaction.

## Request / response

```bash
curl -s -X POST "$API/charge" \
  -H 'content-type: application/json' \
  -d '{"pan":"4111111111111111","expiry":"12/29","cvv":"123","amount":4200,"currency":"USD"}'
# => {"txn_id":"...","status":"captured"}
```

## Ground rules

- **Do not change the app's behaviour or contract.** The `POST /charge`
  interface must keep working. You are governing the workload, not rewriting it.
- The one exception is **PV-02**: you must stop *persisting* the CVV, because
  storing it is categorically prohibited. The request may still accept a `cvv`
  field (processors need it in-flight) — it just must never be written to the
  ledger, the receipt, or the logs.
- Everything else is fixed with a **governance baseline** (new Terraform),
  **policy-as-code**, a **CI gate**, an **OSCAL** component, and an **evidence
  chain** — exactly the layers the scorer looks for.

See `README.md` for deploy/test/destroy and `GAPS.md` for the work list.
