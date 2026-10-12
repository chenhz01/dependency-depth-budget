# dependency-depth-budget

Declare a budget for your dependency tree — depth, breadth and total nodes — and let a scanner measure the real tree against it. Overruns get graded OK / WARN / OVER with a non-zero exit for CI; cycles are reported instead of exploding the analysis. Budgets turn a heavy graph into a number that only moves on purpose.

As of 2026-10-13, no direct equivalent found as of 2026-10-13: dependency audit tools check *versions and vulnerabilities*; searches across GitHub (194 queries) and the web found no standalone shape-budget (depth/breadth/width/total) checker.

## Problem

Dependency trees grow one "small helper" at a time. Transitive chains deepen until upgrade debugging means spelunking ten levels of indirection, and fan-out widens until one package pin breaks thirty builds. Vulnerability scanners tell you a version is bad; nothing tells you the tree's *shape* is past the point where a human can reason about it. There is no budget, so there is no breach.

## How it works

1. **Budget declaration.** A JSON file with any of `max_depth`, `max_breadth`, `max_width`, `max_total` plus a `warn_ratio` (default 0.8) — metrics without limits are skipped.
2. **Tree input.** An adjacency map `{"root": "app", "deps": {node: [children]}}`; nodes referenced but never declared are listed as `missing_declarations` (leaf semantics, depth 0).
3. **Measurement.** Iterative colouring DFS finds cycles via back edges (no recursion limit issues, verified on a 5,000-node chain); longest-path depth runs as post-order DP; `max_breadth` = largest single fan-out; `max_width` = largest level population from the root.
4. **Grading.** Each metric → `OK` (≤ warn ratio × limit), `WARN`, or `OVER` (exit 1). Cycles force `OVER` because depth is unmeasurable — the report names the cycle members.

## Quickstart

Requires Python 3.8+. No dependencies. A 5,000-node chain measures in ~0.011 s [Measured].

```bash
python dependency_depth_budget.py check --budget budget.json --tree tree.json
python dependency_depth_budget.py check --budget budget.json --tree tree.json --json
```

`budget.json`: `{"max_depth": 8, "max_breadth": 50, "max_total": 300}` — `tree.json`: `{"root": "app", "deps": {"app": ["a", "b"], "a": ["c"], "b": [], "c": []}}`.

## Why not X

- **`npm ls` / `pipdeptree` / `mvn dependency:tree`**: they *print* the real tree from installed packages but have no declared budget, no grading, and no cycle-safe depth number. No direct equivalent found as of 2026-10-13 for budget-vs-measured grading.
- **Dependabot / Renovate**: automate version bumps; orthogonal to shape — a fully patched tree can still be 15 levels deep.
- **Vulnerability scanners** (`npm audit`, `pip-audit`): measure risk per package, not structural complexity.
- **Bundle analysers**: size-oriented (bytes), not graph-oriented (levels/fan-out).

## Performance

Measured on Windows 10, Python 3.13, single core:

| Tree | Time | Reproduce |
|---|---|---|
| 5,000-node chain (worst-case depth) [Measured] | 0.011 s | `python -c "import time,dependency_depth_budget as d; t={'root':'n0','deps':{'n%d'%i:['n%d'%(i+1)] for i in range(4999)}}; s=time.perf_counter(); d.measure_tree(t); print('%.4fs'%(time.perf_counter()-s))"` |
| small project tree check [Measured] | < 0.05 s | `python dependency_depth_budget.py check --budget budget.json --tree tree.json` |

## Minimal Fallback

No Python? For a small tree, draw it and count: the deepest path is your depth, the node with the most arrows-out is your breadth. The CLI exists to make that count mechanical, repeatable and gated — a whiteboard photo does not fail CI.

## Design Trade-offs

- **Adjacency JSON, not lockfile parsing.** Ecosystem-agnostic (works for pip, npm, cargo, or your own modules); extracting the map from a lockfile is a separate, per-ecosystem concern.
- **Cycles → OVER, not a partial answer.** A cycle means the "depth" question is malformed; pretending otherwise hides the problem.
- **Width counts undeclared leaves.** References without a `deps` entry still populate levels — they are real dependencies even if undeclared.
- **WARN band is proportional (default 80%).** One number to tune; absolute-offset bands would need four more config knobs.

## Limits & Second-order Effects

- If the adjacency map is hand-maintained it can drift from reality; generate it from your package manager for honest numbers.
- A depth budget can push teams to flatten trees by inlining dependencies — moving complexity, not removing it.
- `max_total` ignores duplicate names across namespaces; two `utils` packages count as two nodes.
- Over-strict budgets get bypassed via config edits with no review; treat budget changes like code changes.

## FAQ

**When NOT to use this?** Not as a security tool (use an advisory scanner), not for runtime import-graph analysis (use import-linter-style tooling), and not for trees you cannot extract into JSON.

**Why does a cycle fail the whole check?** Longest-path depth is undefined on cycles; reporting OVER plus the member list is the honest answer.

**What's the difference between breadth and width?** Breadth = most children of any single node; width = most nodes on any single level from the root.

**Can I budget only some metrics?** Yes — undeclared metrics are reported as `SKIP` and never affect the verdict.

## [Core Assumptions]

- **Tree shape correlates with maintainability cost.** Confidence: medium-high — deep/wide graphs are consistently harder to reason about.
- **A declared budget gets updated deliberately.** Confidence: medium — process, not tooling, enforces this.
- **Adjacency snapshots represent the real graph.** Confidence: medium — depends on generation hygiene.
- **Cycles are defects in dependency graphs.** Confidence: high for package graphs, medium for call graphs.

As of 2026-10-13.

---

Part of the [zhengming-toolbox](https://github.com/chenhz01/zhengming-toolbox) — 105 purpose-built AI-engineering tools across neglected niches.

Related tools: [math-render-precheck](https://github.com/chenhz01/math-render-precheck) · [postmortem-template-lint](https://github.com/chenhz01/postmortem-template-lint) · [deprecation-timeline-audit](https://github.com/chenhz01/deprecation-timeline-audit)
