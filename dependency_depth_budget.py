#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dependency-depth-budget — declared budget vs measured dependency-tree scan.

Loads a budget declaration (max depth / breadth / total) and a dependency
adjacency tree, measures the real tree, and emits a graded OK/WARN/OVER
report plus cycle detection. Pure stdlib.
"""
import argparse
import json
import sys

METRICS = ("max_depth", "max_breadth", "max_width", "max_total")
DEFAULT_WARN_RATIO = 0.8


class BudgetError(Exception):
    """Recoverable input error surfaced as exit 2."""


# ------------------------------------------------------------------ budget io

def load_budget(path_or_obj):
    if isinstance(path_or_obj, dict):
        data = path_or_obj
    else:
        with open(path_or_obj, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    if not isinstance(data, dict):
        raise BudgetError("budget must be a JSON object")
    out = {}
    for key in METRICS:
        v = data.get(key)
        if v is None:
            continue
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            raise BudgetError("budget.%s must be a non-negative int, got %r" % (key, v))
        out[key] = v
    if not out:
        raise BudgetError("budget declares no limits (need at least one of %s)" % ", ".join(METRICS))
    out["warn_ratio"] = data.get("warn_ratio", DEFAULT_WARN_RATIO)
    if not (0 < out["warn_ratio"] <= 1):
        raise BudgetError("budget.warn_ratio must be in (0, 1]")
    return out


def load_tree(path_or_obj):
    if isinstance(path_or_obj, dict):
        data = path_or_obj
    else:
        with open(path_or_obj, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    if not isinstance(data, dict) or not isinstance(data.get("deps"), dict):
        raise BudgetError("tree must be {\"root\": name, \"deps\": {node: [children]}}")
    deps = {}
    for node, children in data["deps"].items():
        if not isinstance(children, list):
            raise BudgetError("deps[%r] must be a list" % node)
        deps[node] = list(children)
    return {"root": data.get("root"), "deps": deps}


# ------------------------------------------------------------------ measuring

def measure_tree(tree):
    deps = tree["deps"]
    root = tree.get("root")
    nodes = set(deps)
    for children in deps.values():
        nodes.update(children)

    # missing declarations: referenced but never defined
    missing = sorted(n for n in nodes if n not in deps)
    # self loops
    self_loops = sorted(n for n, ch in deps.items() if n in ch)

    # cycle detection: iterative coloring DFS (back edge -> cycle members = gray path)
    color = {}     # 0/absent=white, 1=gray, 2=black
    finish = []    # post-order for depth DP
    cyclic = set()
    for start in deps:
        if color.get(start, 0) != 0:
            continue
        color[start] = 1
        stack = [start]
        iters = [iter(deps[start])]
        while stack:
            node = stack[-1]
            nxt = None
            for ch in iters[-1]:
                c = color.get(ch, 0)
                if c == 0:
                    nxt = ch
                    break
                if c == 1:  # back edge: cycle runs from ch down the gray stack
                    for i in range(len(stack) - 1, -1, -1):
                        cyclic.add(stack[i])
                        if stack[i] == ch:
                            break
            if nxt is not None:
                color[nxt] = 1
                stack.append(nxt)
                iters.append(iter(deps.get(nxt, [])))
            else:
                color[node] = 2
                finish.append(node)
                stack.pop()
                iters.pop()

    # depth DP in post-order (finish): children (finished earlier) first
    depth = {}
    for node in finish:
        if node in cyclic:
            depth[node] = None
            continue
        best = 0
        bad = False
        for ch in deps.get(node, []):
            if ch in cyclic or depth.get(ch) is None and ch in depth:
                bad = True
                break
            best = max(best, depth.get(ch, 0) + 1)  # undeclared leaf = depth 0
        depth[node] = None if bad else best

    root = tree.get("root")
    if root is not None and root in depth:
        max_depth = depth[root]
    else:
        vals = [v for v in depth.values()]
        max_depth = None if (not vals or None in vals) else max(vals)
        if root is not None and root not in depth:
            max_depth = 0 if max_depth is None else max(max_depth, 0)

    max_breadth = max((len(ch) for ch in deps.values()), default=0)

    # width: max nodes per level from root (or the fan-out component)
    max_width = 0
    if root is not None and root in deps:
        level = [root]
        seen = {root}
        while level:
            max_width = max(max_width, len(level))
            nxt = []
            for n in level:
                for ch in deps.get(n, []):
                    if ch not in seen:
                        seen.add(ch)
                        nxt.append(ch)
            level = nxt
        max_width = max(max_width, len(level)) if not level else max_width
    else:
        max_width = len(nodes)

    cycles = []
    if cyclic:
        cycles = sorted(n for n in cyclic)
        max_depth = None  # unmeasurable

    return {
        "nodes_total": len(nodes),
        "max_depth": max_depth,
        "max_breadth": max_breadth,
        "max_width": max_width,
        "missing_declarations": missing,
        "self_loops": self_loops,
        "cycles": cycles,
    }


def grade(metric, actual, budget):
    """Return (status, detail) with status in OK/WARN/OVER/SKIP."""
    limit = budget.get(metric)
    if limit is None:
        return "SKIP", None
    if actual is None:
        return "SKIP", "unmeasurable (cycle)"
    if actual > limit:
        return "OVER", "%s > %s" % (actual, limit)
    if actual > limit * budget.get("warn_ratio", DEFAULT_WARN_RATIO):
        return "WARN", "%s > %.0f%% of %s" % (actual, budget["warn_ratio"] * 100, limit)
    return "OK", "%s <= %s" % (actual, limit)


def run_check(tree, budget):
    m = measure_tree(tree)
    rows = {}
    for metric in METRICS:
        status, detail = grade(metric, m.get(metric) if metric != "max_total" else m["nodes_total"], budget)
        rows[metric] = {"actual": m.get(metric) if metric != "max_total" else m["nodes_total"],
                        "status": status, "detail": detail}
    findings = []
    if m["missing_declarations"]:
        findings.append("missing declarations: %s" % ", ".join(m["missing_declarations"]))
    if m["self_loops"]:
        findings.append("self loops: %s" % ", ".join(m["self_loops"]))
    if m["cycles"]:
        findings.append("dependency cycles detected at: %s" % ", ".join(m["cycles"]))
    worst = "OK"
    for metric in METRICS:
        s = rows[metric]["status"]
        if s == "OVER":
            worst = "OVER"
            break
        if s == "WARN":
            worst = "WARN" if worst != "OVER" else worst
    if m["cycles"]:
        worst = "OVER"
    return {"measured": m, "budget": budget, "grades": rows,
            "findings": findings, "verdict": worst}


# ------------------------------------------------------------------------ CLI

def _cmd_check(args):
    budget = load_budget(args.budget)
    tree = load_tree(args.tree)
    report = run_check(tree, budget)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verdict: %s" % report["verdict"])
        for metric, row in report["grades"].items():
            if row["status"] != "SKIP":
                print("  %-12s %-4s (%s)" % (metric, row["status"], row["detail"]))
        for f in report["findings"]:
            print("  finding: %s" % f)
    return 1 if report["verdict"] == "OVER" else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="dependency-depth-budget",
        description="Compare a declared dependency budget (depth/breadth/width/total) "
                    "against a measured dependency tree.")
    sub = parser.add_subparsers(dest="cmd")
    p = sub.add_parser("check", help="check tree against budget")
    p.add_argument("--budget", required=True, help="budget JSON file")
    p.add_argument("--tree", required=True, help="tree JSON file ({root, deps})")
    p.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd != "check":
        parser.print_help()
        return 2
    try:
        return _cmd_check(args)
    except (BudgetError, OSError, json.JSONDecodeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
