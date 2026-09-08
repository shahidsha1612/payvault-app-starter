#!/usr/bin/env python3
"""
Deterministic self-evaluation scorer for GRC-Eng starter capstones.

Design goals
------------
1. DETERMINISTIC: the same repository state always produces the same score,
   on any machine, with no network access, no clocks, and no randomness.
   Only the Python standard library is used. No external tools (terraform,
   opa, cosign) are invoked as part of the score, because their presence and
   version would make results machine-dependent. (An optional --advisory pass
   can run those tools for your own benefit, but it never affects the score.)

2. PORTABLE: `python3 scoring/score.py` from the repo root is all it takes.

3. FAIR & PER-PERSON: the score is a pure function of the files in *this*
   checkout. Fork it, do the work, and your score reflects exactly what you
   built. Two different people => two different repo states => two scores.

The rubric lives in scoring/rubric.json (the "what"); this file is the engine
(the "how"). Keeping them separate lets the same engine grade every workload.

Usage
-----
    python3 scoring/score.py            # human-readable report + writes report json
    python3 scoring/score.py --json     # machine-readable JSON only
    python3 scoring/score.py --quiet    # just the final line
    python3 scoring/score.py --no-write # do not write scoring/score-report.json
    python3 scoring/score.py --advisory # ALSO run opa/terraform if installed (not scored)

Exit code is 0 on success (any score), 2 if the rubric is missing/invalid.
"""

import argparse
import hashlib
import json
import math
import os
import re
import sys

# Repo root is the parent of the scoring/ directory this file lives in.
SCORING_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCORING_DIR)


# --------------------------------------------------------------------------- #
# Deterministic filesystem helpers
# --------------------------------------------------------------------------- #
def _iter_glob(pattern):
    """Return a SORTED list of repo-relative paths matching a glob pattern.

    Sorting guarantees identical iteration order everywhere, which is a
    prerequisite for a reproducible score.
    """
    import pathlib

    root = pathlib.Path(REPO_ROOT)
    matches = [p for p in root.glob(pattern) if p.is_file()]
    rels = sorted(str(p.relative_to(root)).replace(os.sep, "/") for p in matches)
    return rels


def _read(path):
    full = os.path.join(REPO_ROOT, path)
    try:
        with open(full, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except (OSError, IOError):
        return ""


def _concat(glob_pattern):
    """Concatenated text of every file matching a glob (sorted, deterministic)."""
    return "\n".join(_read(p) for p in _iter_glob(glob_pattern))


def _exists(glob_pattern):
    return len(_iter_glob(glob_pattern)) > 0


def _award(points, ratio):
    """Deterministic partial credit: floor so the max is only reached at ratio>=1."""
    ratio = max(0.0, min(1.0, ratio))
    return int(math.floor(points * ratio + 1e-9))


# --------------------------------------------------------------------------- #
# Check implementations. Each returns (awarded:int, detail:str).
# All are pure functions of the on-disk repo state.
# --------------------------------------------------------------------------- #
def check_exists(chk):
    ok = _exists(chk["glob"])
    return (chk["points"] if ok else 0, "found" if ok else "missing")


def check_absent(chk):
    ok = not _exists(chk["glob"])
    return (chk["points"] if ok else 0, "clean" if ok else "still present")


def check_contains_all(chk):
    text = _concat(chk["glob"])
    if not text:
        return (0, "no matching files")
    missing = [p for p in chk["patterns"] if not re.search(p, text, re.IGNORECASE | re.MULTILINE)]
    if not missing:
        return (chk["points"], "all patterns present")
    return (0, "missing: " + ", ".join(missing[:3]))


def check_contains_any(chk):
    text = _concat(chk["glob"])
    if not text:
        return (0, "no matching files")
    for p in chk["patterns"]:
        if re.search(p, text, re.IGNORECASE | re.MULTILINE):
            return (chk["points"], "matched: " + p)
    return (0, "none of the patterns present")


def check_not_contains(chk):
    """Award points only when at least one target file exists AND none of the
    anti-patterns appear. Used to reward removing an insecure default."""
    files = _iter_glob(chk["glob"])
    if not files:
        return (0, "no matching files to clear")
    text = _concat(chk["glob"])
    hits = [p for p in chk["patterns"] if re.search(p, text, re.IGNORECASE | re.MULTILINE)]
    if hits:
        return (0, "anti-pattern present: " + hits[0])
    return (chk["points"], "no anti-patterns found")


def check_glob_min(chk):
    n = len(_iter_glob(chk["glob"]))
    need = chk["min"]
    return (_award(chk["points"], n / need if need else 1.0), f"{n}/{need} files")


def _count_regex(glob_pattern, pattern):
    return len(re.findall(pattern, _concat(glob_pattern), re.MULTILINE))


def check_rego_rules_min(chk):
    # Count policy rules that express a decision: deny / violation / warn heads.
    cnt = _count_regex(chk.get("glob", "policies/**/*.rego"),
                       r"^\s*(deny|violation|warn)\b")
    need = chk["min"]
    return (_award(chk["points"], cnt / need if need else 1.0), f"{cnt}/{need} rules")


def check_rego_tests_min(chk):
    cnt = _count_regex(chk.get("glob", "policies/**/*.rego"), r"^\s*test_[A-Za-z0-9_]+\b")
    need = chk["min"]
    return (_award(chk["points"], cnt / need if need else 1.0), f"{cnt}/{need} tests")


def check_json_valid(chk):
    files = _iter_glob(chk["glob"])
    if not files:
        return (0, "no file")
    try:
        json.loads(_read(files[0]))
        return (chk["points"], "valid JSON")
    except (ValueError, TypeError) as exc:
        return (0, f"invalid JSON: {exc}".split("\n")[0])


def _walk_collect(node, key):
    """Yield every value stored under `key` anywhere in a nested dict/list."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key and isinstance(v, str):
                yield v
            yield from _walk_collect(v, key)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_collect(item, key)


def check_oscal_controls(chk):
    """Parse an OSCAL component-definition and reward mapped, *valid* controls.

    Valid == the control id appears in scoring/controls.json for this framework.
    This stops someone scoring by inventing control ids that don't exist.
    """
    files = _iter_glob(chk["glob"])
    if not files:
        return (0, "no OSCAL file")
    try:
        doc = json.loads(_read(files[0]))
    except (ValueError, TypeError):
        return (0, "OSCAL file is not valid JSON")

    catalog = set()
    try:
        catalog = set(json.loads(_read("scoring/controls.json")).get("control_ids", []))
    except (ValueError, TypeError):
        catalog = set()

    found = set()
    for props in _walk_collect(doc, "control-id"):
        found.add(props.strip())
    # OSCAL also allows control ids as props/params; accept a "control_id" fallback.
    for props in _walk_collect(doc, "control_id"):
        found.add(props.strip())

    valid = sorted(c for c in found if (not catalog or c in catalog))
    need = chk["min"]
    ratio = len(valid) / need if need else 1.0
    detail = f"{len(valid)}/{need} valid controls mapped"
    if found and not valid and catalog:
        detail += " (mapped ids not in framework catalog)"
    return (_award(chk["points"], ratio), detail)


def check_gap_coverage(chk):
    """For every gap id documented in GAPS.md, check it is referenced by an
    artifact (policy, OSCAL, terraform, or writeup). Proportional credit.
    This is the check that ties your score to actually *closing the gaps*."""
    gaps_text = _read(chk.get("gaps_file", "GAPS.md"))
    gap_ids = sorted(set(re.findall(chk.get("gap_id_pattern", r"\b[A-Z]{2}-\d{2}\b"), gaps_text)))
    if not gap_ids:
        return (0, "no gap ids found in GAPS.md")
    globs = chk.get("coverage_globs") or [chk["coverage_glob"]]
    coverage_text = "\n".join(_concat(g) for g in globs)
    covered = [g for g in gap_ids if g in coverage_text]
    ratio = len(covered) / len(gap_ids)
    return (_award(chk["points"], ratio), f"{len(covered)}/{len(gap_ids)} gaps referenced")


CHECK_DISPATCH = {
    "exists": check_exists,
    "absent": check_absent,
    "contains_all": check_contains_all,
    "contains_any": check_contains_any,
    "not_contains": check_not_contains,
    "glob_min": check_glob_min,
    "rego_rules_min": check_rego_rules_min,
    "rego_tests_min": check_rego_tests_min,
    "json_valid": check_json_valid,
    "oscal_controls": check_oscal_controls,
    "gap_coverage": check_gap_coverage,
}


# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #
def load_rubric():
    path = os.path.join(SCORING_DIR, "rubric.json")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def run(rubric):
    categories_out = []
    total_awarded = 0
    total_possible = 0
    for cat in rubric["categories"]:
        checks_out = []
        cat_awarded = 0
        cat_possible = 0
        for chk in cat["checks"]:
            fn = CHECK_DISPATCH.get(chk["type"])
            if fn is None:
                awarded, detail = 0, f"unknown check type '{chk['type']}'"
            else:
                awarded, detail = fn(chk)
            awarded = max(0, min(awarded, chk["points"]))
            cat_awarded += awarded
            cat_possible += chk["points"]
            checks_out.append({
                "id": chk["id"],
                "desc": chk["desc"],
                "points": chk["points"],
                "awarded": awarded,
                "detail": detail,
            })
        categories_out.append({
            "id": cat["id"],
            "title": cat["title"],
            "awarded": cat_awarded,
            "possible": cat_possible,
            "checks": checks_out,
        })
        total_awarded += cat_awarded
        total_possible += cat_possible

    report = {
        "workload": rubric.get("workload", "unknown"),
        "framework": rubric.get("framework", "unknown"),
        "rubric_version": rubric.get("version", "0"),
        "score": total_awarded,
        "possible": total_possible,
        "categories": categories_out,
    }
    # Reproducibility receipt: a hash over the canonical report. No timestamps,
    # so re-running on an unchanged repo yields an identical receipt everywhere.
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["receipt_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return report


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
BAR = "=" * 66


def render(report):
    lines = []
    lines.append(BAR)
    lines.append(f"  {report['workload']}  —  self-evaluation")
    lines.append(f"  Framework: {report['framework']}   Rubric v{report['rubric_version']}")
    lines.append(BAR)
    for cat in report["categories"]:
        lines.append("")
        lines.append(f"[{cat['awarded']:>3}/{cat['possible']:<3}]  {cat['title']}")
        for chk in cat["checks"]:
            if chk["awarded"] == chk["points"]:
                mark = "PASS "
            elif chk["awarded"] == 0:
                mark = "MISS "
            else:
                mark = "PART "
            lines.append(f"    {mark} {chk['awarded']:>2}/{chk['points']:<2}  "
                         f"{chk['desc']}  ({chk['detail']})")
    lines.append("")
    lines.append(BAR)
    pct = (100.0 * report["score"] / report["possible"]) if report["possible"] else 0.0
    grade = grade_for(pct)
    lines.append(f"  SCORE: {report['score']}/{report['possible']}  ({pct:.1f}%)   Grade: {grade}")
    lines.append(f"  Receipt: {report['receipt_sha256']}")
    lines.append(BAR)
    return "\n".join(lines)


def grade_for(pct):
    for threshold, label in ((90, "A — audit-ready"), (80, "B — strong"),
                             (70, "C — passing"), (50, "D — in progress")):
        if pct >= threshold:
            return label
    return "F — starter (no remediation yet)"


# --------------------------------------------------------------------------- #
# Optional advisory pass (NEVER affects the score)
# --------------------------------------------------------------------------- #
def advisory():
    import shutil
    import subprocess

    print("\n--- advisory (informational only, NOT part of your score) ---")
    for tool, args, cwd in (
        ("opa", ["opa", "test", "./policies", "-v"], REPO_ROOT),
        ("terraform", ["terraform", "fmt", "-check", "-recursive", "terraform"], REPO_ROOT),
    ):
        if shutil.which(tool) is None:
            print(f"  [skip] {tool} not installed")
            continue
        try:
            res = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=120)
            head = (res.stdout or res.stderr).strip().splitlines()
            print(f"  [{tool}] exit={res.returncode}")
            for ln in head[-8:]:
                print(f"      {ln}")
        except Exception as exc:  # noqa: BLE001 - advisory only
            print(f"  [{tool}] could not run: {exc}")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv=None):
    parser = argparse.ArgumentParser(description="Deterministic GRC capstone scorer")
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    parser.add_argument("--quiet", action="store_true", help="print only the final score line")
    parser.add_argument("--no-write", action="store_true", help="do not write score-report.json")
    parser.add_argument("--advisory", action="store_true",
                        help="also run opa/terraform if installed (never scored)")
    args = parser.parse_args(argv)

    try:
        rubric = load_rubric()
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"error: cannot load scoring/rubric.json: {exc}\n")
        return 2

    report = run(rubric)

    if not args.no_write:
        out = os.path.join(SCORING_DIR, "score-report.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
            fh.write("\n")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.quiet:
        pct = (100.0 * report["score"] / report["possible"]) if report["possible"] else 0.0
        print(f"SCORE: {report['score']}/{report['possible']} ({pct:.1f}%)  "
              f"receipt={report['receipt_sha256'][:12]}")
    else:
        print(render(report))

    if args.advisory:
        advisory()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
