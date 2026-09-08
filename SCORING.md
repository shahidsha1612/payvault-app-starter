# SCORING.md — how PayVault is graded

You grade yourself. Run:

```bash
python3 scoring/score.py
```

You get a category-by-category breakdown, a total out of 100, a letter grade,
and a **receipt** (a SHA-256 over the report). No AWS account, no network, and
no other tools are required to compute your score.

## The determinism guarantee

The score is a **pure function of the files in your checkout.** The scorer:

- uses only the Python standard library;
- never calls the network, a clock, or a random number generator;
- sorts every directory listing before reading it;
- writes a report with **no timestamps**.

Consequences you can rely on:

1. **Same repo state → same score, byte-for-byte, on any machine.** Re-run it a
   hundred times; the number and the receipt never move unless you change files.
2. **Different people → different scores.** The score reflects *your* fork's
   contents, so everyone who forks this gets their own independent result.
3. **The receipt is a fingerprint.** Two people with the same receipt built
   identical-scoring work; a changed receipt means the graded inputs changed.

> Tools like `terraform` and `opa` are **not** part of the score precisely
> because their version/availability differs per machine and would break
> reproducibility. You can still run them for your own benefit:
> `python3 scoring/score.py --advisory` will run `opa test` and `terraform fmt`
> if they're installed and print the results, clearly marked as *not counted*.

## The 100 points

| Category | Points | What earns them |
|----------|-------:|-----------------|
| Terraform GRC baseline | 25 | KMS CMK, DynamoDB/S3 SSE, public-access block, CloudTrail, no wildcard IAM, TLS floor, Object Lock vault |
| OPA / Rego policy suite | 25 | ≥5 policies, ≥8 tests, ≥6 deny rules, PCI control refs, **every gap referenced** |
| GitHub Actions GRC gate | 15 | plan → policy check → apply, signing, evidence upload |
| OSCAL component | 20 | valid JSON, component-definition shape, **≥6 valid PCI controls mapped**, PCI framework ref, README |
| Evidence chain | 15 | verify script, SHA-256, signature verification, Object Lock immutability check |

The full, authoritative rubric — every check, its points, and the exact regex it
looks for — is `scoring/rubric.json`. Read it. It is not a black box; it is the
spec. "Teaching to the test" here *is* learning the controls.

## Grades

| % | Grade |
|---|-------|
| ≥90 | A — audit-ready |
| ≥80 | B — strong |
| ≥70 | C — passing |
| ≥50 | D — in progress |
| <50 | F — starter (no remediation yet) |

A freshly-forked starter scores near the bottom by design. That is the point:
watch the number climb as you close gaps.

## Running it in CI

`.github/workflows/score.yml` runs the scorer on every push and prints the
result to the GitHub Actions **job summary**, so your fork is auto-graded and
you can see the receipt in the run. It never fails the build on a low score — it
just reports.

## A note on honesty

The gap-coverage and OSCAL checks are designed so you cannot score well by
gaming strings: coverage requires the *gap id* to appear in a real artifact, and
OSCAL control ids must exist in the framework catalog. But this is a **self**
evaluation — the person you'd be cheating is you. Use `WRITEUP.md` to explain
any judgement calls; a human reviewer (or future you) reads that alongside the
number.
