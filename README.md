# PayVault — GRC Engineering Capstone Starter 💳

> A working, **deliberately non-compliant** serverless payments workload.
> Fork it, govern it, and prove it — then score yourself, deterministically.

PayVault captures card payments (`POST /charge`), writes a ledger row to
DynamoDB, and drops a receipt in S3. It also stores card numbers in the clear,
keeps CVVs it should never keep, serves receipts from a public bucket, runs on a
god-mode IAM role, and logs PANs to CloudWatch. Your job is to make it
**audit-defensible against PCI DSS 4.0** *without rewriting the app* — by adding
the five governance layers a real GRC engineer would.

This is a sibling of [`GRCEngClub/cgep-app-starter`](https://github.com/GRCEngClub/cgep-app-starter).
Same skill stack (Terraform · OPA/Rego · GitHub Actions · OSCAL · evidence
chain), new domain (fintech), new framework (PCI), fresh gaps.

## The mission

| Layer | Deliverable | Lives in |
|-------|-------------|----------|
| 1. GRC baseline | Terraform that encrypts, isolates, and audits the workload | `terraform/` (add new `.tf` files) |
| 2. Policy suite | ≥5 OPA/Rego policies that *detect* the gaps, with tests | `policies/` |
| 3. CI gate | GitHub Actions: plan → policy check → apply → sign → upload evidence | `.github/workflows/` |
| 4. OSCAL | Component definition mapping controls to PCI DSS 4.0 | `oscal/` |
| 5. Evidence chain | Script proving integrity (SHA-256), signing (cosign), immutability (Object Lock) | `scripts/` |

Everything you must fix is enumerated in **[GAPS.md](GAPS.md)** (10 gaps,
`PV-01`…`PV-10`). The control mapping primer is **[FRAMEWORKS.md](FRAMEWORKS.md)**.

## Score yourself (deterministic)

```bash
python3 scoring/score.py
```

Same repo state → same score, on any machine, no network needed. See
**[SCORING.md](SCORING.md)** for the guarantee and the full 100-point rubric
(`scoring/rubric.json`). A fresh fork scores near zero — that's the baseline you
climb from.

## Deploy the starter (optional, to see it work)

You need AWS credentials for a **throwaway sandbox** account and Terraform.

```bash
make deploy AWS_PROFILE=<sandbox>     # terraform init + apply
make test   AWS_PROFILE=<sandbox>     # POST a fake charge, see it captured
make destroy AWS_PROFILE=<sandbox>    # tear everything down
```

Cost is ~\$0 if you `make destroy` within a day (all pay-per-use). **Only ever
deploy this into a sandbox** — it is insecure on purpose. Use fake card numbers
only (e.g. `4111111111111111`); never real cardholder data.

## Suggested workflow

1. Fork this repo (keep the fork **public** so your lineage and Actions runs
   are visible), then `git clone` your fork.
2. Read `GAPS.md`, `WORKLOAD.md`, `FRAMEWORKS.md`, `SCORING.md`.
3. Work gap-by-gap: prevention (Terraform) → detection (Rego) → attestation
   (OSCAL / `WRITEUP.md`). Run `python3 scoring/score.py` as you go.
4. Wire the CI gate and the evidence chain last; aim for an **A**.
5. Write `WRITEUP.md`: your framework declaration, one paragraph per gap, and
   any judgement calls. This is what a human reviewer reads next to your score.

## Repo layout

```
payvault-app-starter/
├── README.md WORKLOAD.md GAPS.md FRAMEWORKS.md SCORING.md
├── Makefile
├── terraform/           # the flawed workload (+ your baseline .tf)
│   ├── main.tf variables.tf outputs.tf
│   └── lambda/handler.py
├── test/smoke.sh        # POST a fake charge
├── scoring/
│   ├── score.py         # deterministic scorer (stdlib only)
│   ├── rubric.json      # the authoritative 100-point rubric
│   ├── controls.json    # valid PCI DSS 4.0 control ids
│   └── README.md
├── docs/CAPSTONE.md     # deliverable checklist
└── .github/workflows/score.yml   # auto-scores every push

# you will create:  policies/  oscal/  scripts/  WRITEUP.md
```

## Ethics & scope

For authorized learning and portfolio use. The workload models real PCI failure
modes so you can practice fixing them — deploy only to sandboxes you own, never
process real cards, and never point this at anyone else's infrastructure.

License: MIT.
