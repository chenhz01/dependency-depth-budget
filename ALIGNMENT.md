# ALIGNMENT — dependency-depth-budget

Round R14, rubric v4.0 (E/F graded). Local-only draft: no git remote, no push, no repo creation.
Date: 2026-10-13.

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | Runnable Python, pure stdlib | PASS | dependency_depth_budget.py imports only argparse/json/sys + io/contextlib/unittest/tempfile (self_test); `python dependency_depth_budget.py --help` runs |
| 2 | argparse CLI | PASS | subcommands: check (--budget budget.json --tree tree.json, --json); usage errors exit 2 |
| 3 | self_test inherits scaffold-v2 four defenses | PASS | D1 SystemExit caught in run_cli (tested); D2 unicode-aware regexes + CJK/emoji fixtures (tested); D3 fixtures written with newline="" (tested); D4 last line `SUMMARY: PASS n/n` |
| 4 | E gate >=60 cases, 3 categories | PASS | SUMMARY: PASS 66/66 (64 cases + 2 meta; >=60 gate met) — sections [A] functional / [B] exception / [C] extreme edge, incl. empty/oversized/unicode/CRLF inputs |
| 5 | SUMMARY last-line contract | PASS | `python self_test.py` prints `SUMMARY: PASS 66/66 (64 cases + 2 meta; >=60 gate met)` as its final line; meta-case asserts len(CASES)>=60 |
| 6 | README English, <=60-word lead | PASS | README.md opening paragraph is English and <=60 words |
| 7 | README Problem section | PASS | README.md '## Problem' |
| 8 | README How-it-works | PASS | README.md '## How it works' |
| 9 | README Quickstart with timing | PASS | README.md '## Quickstart' cites the [Measured] run time |
| 10 | why-not-X >=3 alternatives | PASS | README.md '## Why not X' — 4 adjacent solutions listed (npm ls/pipdeptree/mvn dependency:tree, Dependabot/Renovate, vulnerability scanners, bundle analysers); sim=none per _r14_design.json; no direct equivalent found as of 2026-10-13 |
| 11 | Performance [Measured] + repro command | PASS | README.md '## Performance': 5,000-node chain measured in 0.011 s -- python -c repro in README Performance [Measured] |
| 12 | Minimal Fallback | PASS | README.md '## Minimal Fallback' (spreadsheet/manual equivalents) |
| 13 | Design Trade-offs | PASS | README.md '## Design Trade-offs' (4 entries) |
| 14 | Limits & Second-order Effects | PASS | README.md '## Limits & Second-order Effects' (4 entries) |
| 15 | FAQ incl When NOT to use | PASS | README.md '## FAQ' first item is 'When NOT to use this?' |
| 16 | Core Assumptions >=3 + confidence + as-of + hygiene | PASS | README.md '[Core Assumptions]' lists 4 assumptions with confidence line and 'As of 2026-10-13'; MIT LICENSE (zhengming contributors); CHANGELOG.md v0.1.0 -> v0.1.1; no secrets, no real names, contact limited to hcac4735@agent.qq.com |

Round-2 iterations: replaced recursive depth_of with iterative colouring DFS - RecursionError on a 5,000-node chain (found during measured perf run); fixed depth DP direction: process post-order finish list forward (children first); reverse order computed parents before children; undeclared leaf references now score depth 0 instead of poisoning parents to None; grade() defaults warn_ratio when budget dict passed raw; cycle detection reports back-edge members instead of a blanket failure
All suites re-run green after revisions before hand-off.
