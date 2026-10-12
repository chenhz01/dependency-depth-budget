# -*- coding: utf-8 -*-
"""self_test for dependency-depth-budget — inherits scaffold-v2 defenses D1-D4."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")  # D3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dependency_depth_budget as mod  # noqa: E402


def run_cli(argv):  # D1
    buf_out, buf_err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            rc = mod.main(argv)
            code = 0 if rc is None else rc
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception as e:  # noqa: BLE001
        code = 1
        buf_err.write(repr(e))
    return code, buf_out.getvalue(), buf_err.getvalue()


CASES = []


def case(name, cat):
    def deco(fn):
        CASES.append((name, cat, fn))
        return fn
    return deco


TMP = tempfile.mkdtemp(prefix="ddb_selftest_")


def write_json(name, obj):
    p = os.path.join(TMP, name)
    with open(p, "w", encoding="utf-8", newline="") as fh:  # D3
        json.dump(obj, fh, ensure_ascii=False)
    return p


BUDGET = {"max_depth": 5, "max_breadth": 3, "max_total": 10}
TREE = {"root": "app", "deps": {"app": ["a", "b"], "a": ["c"], "b": [], "c": []}}

# ------------------------------------------------------------------ [A] functional

@case("A01_measure_simple_tree", "A")
def t():
    m = mod.measure_tree({"root": "app", "deps": {"app": ["a"], "a": []}})
    assert m["max_depth"] == 1 and m["nodes_total"] == 2

@case("A02_depth_chain", "A")
def t():
    deps = {"n%d" % i: ["n%d" % (i + 1)] for i in range(5)}
    m = mod.measure_tree({"root": "n0", "deps": deps})
    assert m["max_depth"] == 5

@case("A03_breadth_fanout", "A")
def t():
    deps = {"app": ["a", "b", "c", "d"]}
    m = mod.measure_tree({"root": "app", "deps": deps})
    assert m["max_breadth"] == 4

@case("A04_width_from_root", "A")
def t():
    deps = {"app": ["a", "b"], "a": ["x", "y"], "b": ["z"]}
    m = mod.measure_tree({"root": "app", "deps": deps})
    assert m["max_width"] == 3  # leaf level (3 refs) is the widest

@case("A05_total_nodes_counts_refs", "A")
def t():
    m = mod.measure_tree(TREE)
    assert m["nodes_total"] == 4

@case("A06_missing_declarations_listed", "A")
def t():
    m = mod.measure_tree({"root": "app", "deps": {"app": ["ghost"]}})
    assert m["missing_declarations"] == ["ghost"]

@case("A07_self_loop_detected", "A")
def t():
    m = mod.measure_tree({"root": "a", "deps": {"a": ["a"]}})
    assert m["self_loops"] == ["a"]

@case("A08_cycle_detected", "A")
def t():
    m = mod.measure_tree({"root": "a", "deps": {"a": ["b"], "b": ["c"], "c": ["a"]}})
    assert m["cycles"] == ["a", "b", "c"] and m["max_depth"] is None

@case("A09_cycle_elsewhere_not_from_root", "A")
def t():
    m = mod.measure_tree({"root": "app", "deps": {"app": [], "x": ["y"], "y": ["x"]}})
    assert m["cycles"] and m["max_depth"] is None

@case("A10_grade_ok", "A")
def t():
    s, _ = mod.grade("max_depth", 3, BUDGET)
    assert s == "OK"

@case("A11_grade_warn_ratio", "A")
def t():
    s, _ = mod.grade("max_depth", 4, dict(BUDGET, warn_ratio=0.7))
    assert s == "WARN"

@case("A12_grade_over", "A")
def t():
    s, _ = mod.grade("max_depth", 7, BUDGET)
    assert s == "OVER"

@case("A13_grade_skip_when_no_limit", "A")
def t():
    s, _ = mod.grade("max_width", 100, BUDGET)
    assert s == "SKIP"

@case("A14_load_budget_defaults", "A")
def t():
    b = mod.load_budget({"max_depth": 3})
    assert b["warn_ratio"] == 0.8

@case("A15_load_budget_custom_ratio", "A")
def t():
    b = mod.load_budget({"max_depth": 3, "warn_ratio": 0.5})
    assert b["warn_ratio"] == 0.5

@case("A16_load_tree_ok", "A")
def t():
    tr = mod.load_tree({"root": "r", "deps": {"r": []}})
    assert tr["root"] == "r"

@case("A17_verdict_ok_tree", "A")
def t():
    r = mod.run_check(TREE, mod.load_budget(BUDGET))
    assert r["verdict"] in ("OK", "WARN")

@case("A18_verdict_over_depth", "A")
def t():
    r = mod.run_check(TREE, mod.load_budget({"max_depth": 0}))
    assert r["verdict"] == "OVER"

@case("A19_verdict_over_breadth", "A")
def t():
    r = mod.run_check(TREE, mod.load_budget({"max_breadth": 1}))
    assert r["verdict"] == "OVER"

@case("A20_verdict_over_total", "A")
def t():
    r = mod.run_check(TREE, mod.load_budget({"max_total": 2}))
    assert r["verdict"] == "OVER"

@case("A21_findings_report_missing", "A")
def t():
    r = mod.run_check({"root": "app", "deps": {"app": ["ghost"]}}, mod.load_budget(BUDGET))
    assert any("missing" in f for f in r["findings"])

@case("A22_cli_clean_exit0", "A")
def t():
    bp = write_json("b.json", BUDGET)
    tp = write_json("t.json", TREE)
    code, out, _ = run_cli(["check", "--budget", bp, "--tree", tp])
    assert code == 0 and "verdict" in out

@case("A23_cli_over_exit1", "A")
def t():
    bp = write_json("b2.json", {"max_depth": 0})
    tp = write_json("t2.json", TREE)
    code, out, _ = run_cli(["check", "--budget", bp, "--tree", tp])
    assert code == 1

@case("A24_cli_json_grades", "A")
def t():
    bp = write_json("b3.json", BUDGET)
    tp = write_json("t3.json", TREE)
    code, out, _ = run_cli(["check", "--budget", bp, "--tree", tp, "--json"])
    data = json.loads(out)
    assert set(data["grades"]) == set(mod.METRICS)

# ------------------------------------------------------------------ [B] exception / CLI contract

@case("B01_cli_no_subcommand_exit2", "B")
def t():
    assert run_cli([])[0] == 2

@case("B02_cli_unknown_subcommand_exit2", "B")
def t():
    assert run_cli(["scan"])[0] == 2

@case("B03_missing_budget_file_exit2", "B")
def t():
    tp = write_json("t5.json", TREE)
    code, _, err = run_cli(["check", "--budget", "ghost.json", "--tree", tp])
    assert code == 2 and "error" in err

@case("B04_missing_tree_file_exit2", "B")
def t():
    bp = write_json("b6.json", BUDGET)
    assert run_cli(["check", "--budget", bp, "--tree", "ghost.json"])[0] == 2

@case("B05_budget_not_object_exit2", "B")
def t():
    bp = write_json("b7.json", [1])
    tp = write_json("t7.json", TREE)
    assert run_cli(["check", "--budget", bp, "--tree", tp])[0] == 2

@case("B06_budget_negative_limit_exit2", "B")
def t():
    bp = write_json("b8.json", {"max_depth": -1})
    tp = write_json("t8.json", TREE)
    code, _, err = run_cli(["check", "--budget", bp, "--tree", tp])
    assert code == 2 and "non-negative" in err

@case("B07_budget_bool_limit_exit2", "B")
def t():
    bp = write_json("b9.json", {"max_depth": True})
    tp = write_json("t9.json", TREE)
    assert run_cli(["check", "--budget", bp, "--tree", tp])[0] == 2

@case("B08_budget_empty_exit2", "B")
def t():
    bp = write_json("b10.json", {})
    tp = write_json("t10.json", TREE)
    code, _, err = run_cli(["check", "--budget", bp, "--tree", tp])
    assert code == 2 and "no limits" in err

@case("B09_bad_warn_ratio_exit2", "B")
def t():
    bp = write_json("b11.json", {"max_depth": 1, "warn_ratio": 1.5})
    tp = write_json("t11.json", TREE)
    assert run_cli(["check", "--budget", bp, "--tree", tp])[0] == 2

@case("B10_tree_missing_deps_exit2", "B")
def t():
    bp = write_json("b12.json", BUDGET)
    tp = write_json("t12.json", {"root": "app"})
    code, _, err = run_cli(["check", "--budget", bp, "--tree", tp])
    assert code == 2 and "deps" in err

@case("B11_tree_children_not_list_exit2", "B")
def t():
    bp = write_json("b13.json", BUDGET)
    tp = write_json("t13.json", {"deps": {"a": "b"}})
    assert run_cli(["check", "--budget", bp, "--tree", tp])[0] == 2

@case("B12_bad_json_budget_exit2", "B")
def t():
    bp = os.path.join(TMP, "bad.json")
    with open(bp, "w", encoding="utf-8", newline="") as fh:
        fh.write("{oops")
    tp = write_json("t14.json", TREE)
    assert run_cli(["check", "--budget", bp, "--tree", tp])[0] == 2

@case("B13_root_absent_uses_max_all", "B")
def t():
    m = mod.measure_tree({"deps": {"a": ["b"], "b": []}})
    assert m["max_depth"] == 1

@case("B14_root_not_in_deps", "B")
def t():
    m = mod.measure_tree({"root": "zz", "deps": {"a": []}})
    assert m["nodes_total"] == 1

@case("B15_grade_unmeasurable_skip", "B")
def t():
    s, d = mod.grade("max_depth", None, BUDGET)
    assert s == "SKIP" and "cycle" in d

@case("B16_verdict_cycle_forces_over", "B")
def t():
    r = mod.run_check({"root": "a", "deps": {"a": ["a"]}}, mod.load_budget({"max_depth": 100}))
    assert r["verdict"] == "OVER"

@case("B17_verdict_warn_not_over", "B")
def t():
    r = mod.run_check(TREE, mod.load_budget({"max_depth": 3, "warn_ratio": 0.5}))
    assert r["verdict"] == "WARN"

@case("B18_cli_help_mentions_budget", "B")
def t():
    code, out, _ = run_cli(["--help"])
    assert code == 0 and "budget" in out

@case("B19_load_budget_from_dict_no_file", "B")
def t():
    assert mod.load_budget({"max_total": 1})["max_total"] == 1

@case("B20_unicode_node_names", "B")
def t():
    m = mod.measure_tree({"root": "应用", "deps": {"应用": ["模块一"], "模块一": []}})
    assert m["max_depth"] == 1 and m["missing_declarations"] == []

# ------------------------------------------------------------------ [C] extreme edge

@case("C01_empty_deps", "C")
def t():
    m = mod.measure_tree({"deps": {}})
    assert m["nodes_total"] == 0 and m["max_depth"] in (0, None)

@case("C02_leaf_only_nodes", "C")
def t():
    m = mod.measure_tree({"deps": {"a": [], "b": []}})
    assert m["max_depth"] == 0 and m["max_breadth"] == 0

@case("C03_deep_chain_5000_no_recursion_crash", "C")
def t():
    deps = {"n%d" % i: ["n%d" % (i + 1)] for i in range(4999)}
    import time
    t0 = __import__("time").perf_counter()
    m = mod.measure_tree({"root": "n0", "deps": deps})
    assert __import__("time").perf_counter() - t0 < 5
    assert m["max_depth"] == 4999

@case("C04_wide_fanout_1000", "C")
def t():
    deps = {"root": ["c%d" % i for i in range(1000)]}
    m = mod.measure_tree({"root": "root", "deps": deps})
    assert m["max_breadth"] == 1000 and m["max_width"] == 1000

@case("C05_diamond_no_false_cycle", "C")
def t():
    m = mod.measure_tree({"root": "r", "deps": {"r": ["a", "b"], "a": ["c"], "b": ["c"], "c": []}})
    assert m["cycles"] == [] and m["max_depth"] == 2

@case("C06_two_disjoint_cycles", "C")
def t():
    m = mod.measure_tree({"deps": {"a": ["b"], "b": ["a"], "x": ["y"], "y": ["x"]}})
    assert m["cycles"] == ["a", "b", "x", "y"]

@case("C07_cycle_plus_tail_depth_none", "C")
def t():
    m = mod.measure_tree({"root": "s", "deps": {"s": ["a"], "a": ["b"], "b": ["a"]}})
    assert m["max_depth"] is None

@case("C08_unicode_children_cjk", "C")
def t():
    m = mod.measure_tree({"root": "r", "deps": {"r": ["中文依赖"], "中文依赖": []}})
    assert m["max_depth"] == 1

@case("C09_emoji_node_names", "C")
def t():
    m = mod.measure_tree({"root": "🚀", "deps": {"🚀": ["🔥"], "🔥": []}})
    assert m["nodes_total"] == 2

@case("C10_self_loop_in_wide_fanout", "C")
def t():
    m = mod.measure_tree({"root": "r", "deps": {"r": ["r", "a"], "a": []}})
    assert m["self_loops"] == ["r"]

@case("C11_budget_exact_boundary_ok", "C")
def t():
    r = mod.run_check(TREE, mod.load_budget({"max_depth": 2, "warn_ratio": 1}))
    assert r["grades"]["max_depth"]["status"] == "OK"

@case("C12_budget_one_over_boundary_over", "C")
def t():
    r = mod.run_check(TREE, mod.load_budget({"max_depth": 1}))
    assert r["grades"]["max_depth"]["status"] == "OVER"

@case("C13_warn_ratio_1_never_warns", "C")
def t():
    r = mod.run_check(TREE, mod.load_budget({"max_depth": 2, "warn_ratio": 1}))
    assert r["grades"]["max_depth"]["status"] == "OK"

@case("C14_missing_node_counts_in_total", "C")
def t():
    m = mod.measure_tree({"deps": {"a": ["ghost"]}})
    assert m["nodes_total"] == 2

@case("C15_crlf_json_files_cli", "C")
def t():
    bp = os.path.join(TMP, "cb.json")
    tp = os.path.join(TMP, "ct.json")
    for path, obj in ((bp, BUDGET), (tp, TREE)):
        with open(path, "w", encoding="utf-8", newline="\r\n") as fh:
            json.dump(obj, fh)
    assert run_cli(["check", "--budget", bp, "--tree", tp])[0] == 0

@case("C16_bom_budget_file", "C")
def t():
    bp = os.path.join(TMP, "bom.json")
    with open(bp, "w", encoding="utf-8-sig", newline="") as fh:
        json.dump(BUDGET, fh)
    tp = write_json("tb.json", TREE)
    code, _, err = run_cli(["check", "--budget", bp, "--tree", tp])
    assert code in (0, 2)  # tolerated, must not crash

@case("C17_large_diamond_graph_perf", "C")
def t():
    deps = {}
    for i in range(500):
        deps["l%d" % i] = ["m%d" % i, "m%d" % ((i + 1) % 500)]
    deps["root"] = ["l0"]
    import time
    t0 = __import__("time").perf_counter()
    m = mod.measure_tree({"root": "root", "deps": deps})
    assert __import__("time").perf_counter() - t0 < 5

@case("C18_json_mode_unicode_names", "C")
def t():
    bp = write_json("c18b.json", {"max_depth": 1})
    tp = write_json("c18t.json", {"root": "应用", "deps": {"应用": ["模块一"]}})
    code, out, _ = run_cli(["check", "--budget", bp, "--tree", tp, "--json"])
    data = json.loads(out)
    assert code == 0 and "模块一" in json.dumps(data, ensure_ascii=False)

@case("C19_zero_budget_all_nodes_over", "C")
def t():
    r = mod.run_check(TREE, mod.load_budget({"max_total": 0, "max_breadth": 0, "max_depth": 0}))
    assert r["verdict"] == "OVER"

@case("C20_grade_detail_strings", "C")
def t():
    _, d_ok = mod.grade("max_depth", 2, BUDGET)
    _, d_over = mod.grade("max_depth", 9, BUDGET)
    assert "<=" in d_ok and ">" in d_over

class TestAll(unittest.TestCase):
    pass


def _build():
    for i, (name, cat, fn) in enumerate(CASES):
        def make(f):
            def m(self):
                f()
            return m
        slug = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in name)
        setattr(TestAll, "test_%s_%03d_%s" % (cat, i, slug), make(fn))
_build()


class TestMeta(unittest.TestCase):
    def test_case_count_ge_60(self):
        self.assertGreaterEqual(len(CASES), 60)

    def test_categories_present(self):
        self.assertEqual({c for _, c, _ in CASES}, {"A", "B", "C"})


if __name__ == "__main__":
    r = unittest.TextTestRunner(verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules["__main__"]))
    total, fails = r.testsRun, len(r.failures) + len(r.errors)
    print("SUMMARY: PASS %d/%d" % (total - fails, total))  # D4
    sys.exit(0 if fails == 0 else 1)
