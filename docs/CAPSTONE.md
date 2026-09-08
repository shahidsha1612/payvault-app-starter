# CAPSTONE.md — deliverable checklist

Tick these off and your score follows. Point values in brackets map to
`scoring/rubric.json`.

## Gate — the must-pass checklist (fail if not met)

`python3 scoring/score.py --gate` (and CI) **FAILS** unless you score **≥ 70**
*and* every one of these required deliverables is fully present. Items marked
**⛔ REQUIRED** below are the gate; the rest raise your grade toward an A.

- ⛔ S3 public access fully blocked (`s3_public_block`)
- ⛔ No wildcard IAM actions (`no_wildcard_iam`)
- ⛔ ≥5 Rego policy files (`policy_count`)
- ⛔ ≥6 deny/violation rules (`deny_rules`)
- ⛔ Every gap attested (`gap_coverage`)
- ⛔ Valid OSCAL JSON (`oscal_json`)
- ⛔ ≥6 valid PCI controls mapped (`oscal_controls`)
- ⛔ Evidence verification script present (`verify_script`)

## 1. Terraform GRC baseline  `terraform/`  [25]

Add new `.tf` files (don't edit the flawed workload beyond removing what a fix
requires):

- [ ] Customer-managed **KMS key** with rotation enabled `[4]`
- [ ] DynamoDB **encrypted at rest** with your CMK (`server_side_encryption`) `[4]`
- [ ] S3 receipts **SSE-KMS** `[3]`
- [ ] S3 **public access block** (all four flags `true`) + drop the public ACL `[3]`
- [ ] **CloudTrail** trail capturing management + data events `[3]`
- [ ] Replace the wildcard IAM policy with **least-privilege** statements `[4]`
- [ ] **TLS floor** on the API edge (custom domain security policy / min TLS) `[2]`
- [ ] Evidence bucket with **S3 Object Lock** (GOVERNANCE/COMPLIANCE) `[2]`

## 2. OPA / Rego policy suite  `policies/`  [25]

- [ ] ≥5 `.rego` policy files `[6]`
- [ ] ≥8 unit tests (`test_...` rules), all passing `opa test ./policies` `[6]`
- [ ] ≥6 `deny`/`violation` rules `[5]`
- [ ] Policies cite PCI requirement ids in comments/messages `[4]`
- [ ] Every `PV-0x` gap id referenced by a policy/terraform/oscal/writeup `[4]`

Ideas: deny DynamoDB without SSE (PV-03); deny S3 without public-access-block
(PV-04); deny any stored field named `cvv`/`cvc` (PV-02); deny IAM `"*"` actions
(PV-06); deny plaintext secrets in Lambda env (PV-09); deny stages without
access logging (PV-07).

## 3. GitHub Actions GRC gate  `.github/workflows/`  [15]

- [ ] Workflow runs **plan → conftest/opa test → apply** `[6]`
- [ ] **Signs** the plan/artifact with cosign `[4]`
- [ ] **Uploads evidence** (plan, test output, signatures) to the vault `[5]`
- [ ] Show at least one **blocked** PR (policy failed) and one **passed** PR

## 4. OSCAL component  `oscal/`  [20]

- [ ] Valid JSON `component-definition` `[4 + 3]`
- [ ] ≥6 `implemented-requirement`s mapped to **valid PCI control ids** `[8]`
- [ ] Declares PCI DSS 4.0 as the framework `[2]`
- [ ] `oscal/README.md` with your validation command + result `[3]`

## 5. Evidence chain  `scripts/`  [15]

- [ ] `verify-evidence.sh` that recomputes **SHA-256** over evidence `[3+4]`
- [ ] **Verifies signatures** (cosign verify) `[4]`
- [ ] Confirms **Object Lock** immutability on the vault `[4]`
- [ ] Prints a clear final verdict (e.g. `CHAIN INTACT`)

## 6. WRITEUP.md (human-graded, not scored by the script)

- [ ] Primary framework declaration + CDE scope
- [ ] One paragraph per gap: prevention, detection, attestation
- [ ] Any judgement calls (e.g. tokenization vs. encryption for PV-01)

Run `python3 scoring/score.py` after each step and watch the number climb.
