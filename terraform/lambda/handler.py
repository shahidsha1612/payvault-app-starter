"""
PayVault charge handler (INTENTIONALLY NON-COMPLIANT STARTER).

Do not rewrite the app logic. Your job is to govern it: encrypt what it stores,
lock down what it exposes, log what it does, and prove it with policy + OSCAL.

Flaws are tagged with their gap id (PV-0x); keep the tags.
"""

import json
import os
import uuid

import boto3

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

LEDGER_TABLE = os.environ.get("LEDGER_TABLE", "payvault-dev-ledger")
RECEIPTS_BUCKET = os.environ.get("RECEIPTS_BUCKET", "payvault-dev-receipts")


def handler(event, context):
    body = json.loads(event.get("body") or "{}")

    pan = body.get("pan", "")          # primary account number (the card number)
    expiry = body.get("expiry", "")
    cvv = body.get("cvv", "")          # sensitive authentication data
    amount = body.get("amount", 0)
    currency = body.get("currency", "USD")

    txn_id = str(uuid.uuid4())

    # PV-08: logging full PAN + CVV to CloudWatch in cleartext.
    print(f"[charge] txn={txn_id} pan={pan} cvv={cvv} amount={amount} {currency}")

    table = dynamodb.Table(LEDGER_TABLE)
    # PV-01: PAN stored in cleartext.  PV-02: CVV persisted after authorization
    # (storing sensitive authentication data is never allowed under PCI DSS).
    table.put_item(Item={
        "txn_id": txn_id,
        "pan": pan,
        "expiry": expiry,
        "cvv": cvv,
        "amount": str(amount),
        "currency": currency,
        "status": "captured",
    })

    # PV-01 / PV-04: receipt with full PAN written to a public bucket, unencrypted.
    receipt = {
        "txn_id": txn_id,
        "pan": pan,
        "amount": amount,
        "currency": currency,
    }
    s3.put_object(
        Bucket=RECEIPTS_BUCKET,
        Key=f"receipts/{txn_id}.json",
        Body=json.dumps(receipt).encode("utf-8"),
        ContentType="application/json",
        # PV-03: no ServerSideEncryption argument.
    )

    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps({"txn_id": txn_id, "status": "captured"}),
    }
