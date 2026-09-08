# FRAMEWORKS.md — mapping PayVault to PCI DSS 4.0

Your **primary** framework is **PCI DSS 4.0** (SOC 2 is a fine secondary lens,
but map your OSCAL controls to PCI). PCI is the natural fit because PayVault
handles the two data types PCI cares about most:

- **CHD** — Cardholder Data (the PAN, expiry, cardholder name).
- **SAD** — Sensitive Authentication Data (CVV/CVC, full track data, PIN). SAD
  must **never** be stored after authorization. This is not "encrypt it well";
  it is "do not keep it."

## The requirements you will touch

| PCI DSS 4.0 area | Requirement(s) | PayVault relevance |
|------------------|----------------|--------------------|
| Network security controls | 1.2.x, 1.3.x, 1.4.x | Lock the public receipts bucket; restrict egress |
| Do not store SAD | 3.3.1 | Stop persisting CVV (PV-02) |
| Protect stored CHD | 3.4.1, 3.5.1 | Encrypt / tokenize PAN at rest (PV-01, PV-03) |
| Key management | 3.6.1, 3.7.1, 3.7.6 | CMK, rotation, protect the HMAC/processor keys (PV-09) |
| Encrypt in transit | 4.2.1, 4.2.2 | TLS floor on the API edge (PV-05) |
| Least privilege | 7.2.1, 7.3.1 | Kill the wildcard IAM (PV-06) |
| Authenticate access | 8.3.x, 8.6.x | Add an authorizer; stop hardcoding secrets (PV-05, PV-09) |
| Log and monitor | 10.2.1, 10.3.1, 10.5.1 | CloudTrail + access logs; stop logging PAN (PV-07, PV-08) |

## How to write a control id the scorer accepts

Use the **bare PCI requirement number** as the OSCAL `control-id`, e.g.
`"3.4.1"`. The scorer validates each mapped control id against
`scoring/controls.json`; ids that are not in that catalog do not count (this
stops "mapping" to control ids that don't exist). If you need a requirement
that isn't listed, add it to `controls.json` in your fork and say why in
`WRITEUP.md` — that's a legitimate, reviewable decision.

## Suggested primary-framework declaration (put this in your WRITEUP.md)

> **Primary framework:** PCI DSS 4.0.
> **Scope:** the PayVault cardholder data environment (CDE) — the charge Lambda,
> the ledger table, the receipts bucket, and the audit/evidence path.
> **Out of scope:** the client, and any tokenization service you choose to stub.
