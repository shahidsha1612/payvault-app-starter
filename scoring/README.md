# scoring/

Deterministic self-evaluation for the PayVault capstone.

| File | What it is |
|------|------------|
| `score.py` | The engine. Pure Python stdlib, no network, no clock, no randomness. Runs the checks in `rubric.json` against your checkout and prints a score out of 100 plus a SHA-256 receipt. |
| `rubric.json` | The **authoritative** rubric: every category, check, point value, and the exact regex/glob each check uses. This is the spec — read it. |
| `controls.json` | The PCI DSS 4.0 control ids the OSCAL check will accept. Prevents "mapping" to control ids that don't exist. |
| `score-report.json` | Written on each run (git-ignored). The machine-readable version of your last score, including per-check details and the receipt. |

## Run

```bash
python3 scoring/score.py            # human-readable report
python3 scoring/score.py --json     # machine-readable JSON
python3 scoring/score.py --quiet    # one line: SCORE + receipt
python3 scoring/score.py --advisory # also run opa/terraform if present (NOT graded)
```

Requires Python 3.8+. Nothing else.

## Why it's reproducible

Every input is a file on disk; every file listing is sorted before use; the
report carries no timestamp. So the score — and the receipt hash over it — is
identical for identical repo contents, everywhere, forever. See `../SCORING.md`
for the full explanation and the anti-gaming design of the coverage/OSCAL
checks.

## Extending the rubric (advanced)

If you add a control to `controls.json` or tighten a check, you are changing the
spec — note it in `WRITEUP.md` so a reviewer understands why your fork scores
what it does. The engine supports these check `type`s: `exists`, `absent`,
`contains_all`, `contains_any`, `not_contains`, `glob_min`, `rego_rules_min`,
`rego_tests_min`, `json_valid`, `oscal_controls`, `gap_coverage`.
