# Changelog

All notable changes to this project are documented here.
Format based on Keep a Changelog; versioning: SemVer.

## [0.1.1] - 2026-10-13

### Fixed / Revised (round-2 iteration)
- replaced recursive depth_of with iterative colouring DFS - RecursionError on a 5,000-node chain (found during measured perf run)
- fixed depth DP direction: process post-order finish list forward (children first); reverse order computed parents before children
- undeclared leaf references now score depth 0 instead of poisoning parents to None; grade() defaults warn_ratio when budget dict passed raw
- cycle detection reports back-edge members instead of a blanket failure

### Verification
- self_test re-run green after revisions: SUMMARY: PASS 66/66 (64 cases + 2 meta; >=60 gate met)
- CLI error contract re-verified (exit 0/1/2); four scaffold-v2 defenses inherited.

## [0.1.0] - 2026-10-13

### Added
- Core module `dependency_depth_budget.py`: check (--budget budget.json --tree tree.json, --json), pure standard library.
- argparse CLI with `--json` machine output and 0/1/2 exit-code contract.
- `self_test.py` inheriting scaffold-v2 defenses: SystemExit capture, unicode-safe
  regexes, `newline=""` fixtures, and the `SUMMARY: PASS n/n` last-line contract.
- README (Performance section with [Measured] numbers and in-repo repro commands),
  MIT LICENSE, ALIGNMENT.md (16-item rubric).
