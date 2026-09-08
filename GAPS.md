# GAPS.md — PayVault deliberate compliance gaps

PayVault is a working payment-intake + ledger API that is **intentionally
non-compliant**. Each gap below is real, is reachable from the deployed
workload, and is tagged in the source (`terraform/*.tf`, `lambda/handler.py`)
with its id. Your capstone closes every gap and *proves* it.

> Keep the `PV-0x` tags in the code. The scorer checks that each gap id is
> referenced by one of your remediation artifacts (policy, terraform, OSCAL,
> or WRITEUP.md). That is how it knows you addressed it — not just deleted it.

| ID | Severity | Gap | Where | Primary PCI DSS 4.0 req |
|------|----------|-----|-------|--------------------------|
| **PV-01** | Critical | Full PAN (card number) stored in cleartext in DynamoDB and in S3 receipts | `handler.py`, `main.tf` | 3.4.1 / 3.5.1 |
| **PV-02** | Critical | CVV (sensitive authentication data) is persisted after authorization | `handler.py` | 3.3.1 |
| **PV-03** | High | No encryption at rest — DynamoDB and S3 use no customer-managed key | `main.tf` | 3.5.1 |
| **PV-04** | Critical | Receipts bucket is world-readable (public-read ACL, no public access block) | `main.tf` | 1.3.1 / 1.4.4 |
| **PV-05** | High | Charge API has no authorizer, no WAF, no throttling — anonymous access | `main.tf` | 7.2.1 / 8.6.1 |
| **PV-06** | Critical | Lambda role grants `Action:"*"` on `Resource:"*"` (no least privilege) | `main.tf` | 7.2.1 / 7.3.1 |
| **PV-07** | High | No CloudTrail / no API access logging — no audit trail of CHD access | `main.tf` | 10.2.1 / 10.3.1 |
| **PV-08** | High | Handler logs full PAN + CVV to CloudWatch in cleartext | `handler.py` | 3.4.1 / 10.5.1 |
| **PV-09** | Medium | Processor API key and HMAC key hardcoded as plaintext env vars | `main.tf` | 3.7.1 / 8.6.2 |
| **PV-10** | Medium | No immutable evidence retention (no Object Lock, no key rotation) | (missing) | 10.5.1 / 3.7.6 |

## What "closing a gap" means here

For each gap you should be able to point to **three** things:

1. **Prevention** — Terraform in your baseline that makes the secure state real
   (e.g. a CMK + `server_side_encryption` for PV-03).
2. **Detection** — a Rego policy that *fails* if the insecure pattern comes back
   (e.g. `deny` when a DynamoDB table has no SSE).
3. **Attestation** — an OSCAL `implemented-requirement` (or a WRITEUP.md entry)
   that names the gap id and the PCI requirement it satisfies.

The two "stretch" gaps (PV-09, PV-10) are what separate a B from an A. PV-02 is
the one people miss: you cannot *encrypt* CVV to fix it — SAD must **never** be
stored at all, so the fix is to stop persisting it and to have a policy that
denies any schema/field named `cvv`, `cvc`, or `sensitive_auth_data`.

See `FRAMEWORKS.md` for the control-mapping primer and `SCORING.md` for exactly
how points are awarded.
