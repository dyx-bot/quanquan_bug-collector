#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bc_run_summary.py — Bug Collector 跨案例汇总视图生成器（V0.1.7）

用途：一次 offline 运行会有「案例数 × 十几张表」的产物，逐案例可追溯但缺少一眼看完的视图。
本脚本把各案例折叠成 `reports/run-summary.md`：一行一案例的总表 + 合计行 + WARN 聚类 + 口径异常。

边界（重要）：
  * 只读派生视图：只读各案例的 reports/actual_counts.json、library/*.json、reports/validate-report.json
    （或运行级 reports/validate-all.json），**只写 run-summary.md**，不改动任何案例文件、不改契约字段。
  * 数字一律取自实际文件；取不到就写「—」并在「口径异常」说明，不得手填、不得估算。
  * 视图存在不等于案例通过：结论仍以 actual_counts + bc_validate.py 报告为准。

只依赖 Python 标准库。

用法：
  python3 -I scripts/bc_run_summary.py --run-dir <运行根> [--out <运行根>/reports/run-summary.md]
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
DASH = "—"


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def load_jsonl(path):
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    out.append({"__parse_error__": line[:200]})
    except Exception:
        return []
    return out


def is_case_dir(p):
    return os.path.isdir(p) and (
        os.path.exists(os.path.join(p, "library", "bugs.json"))
        or os.path.exists(os.path.join(p, "reports", "actual_counts.json")))


def discover_cases(run_dir):
    cases = {}
    for name in sorted(os.listdir(run_dir)):
        p = os.path.join(run_dir, name)
        if name in ("reports", "runs", "process", "library") or name.startswith("."):
            continue
        if is_case_dir(p):
            cases[name] = p
    if not cases:
        # 兼容 <run_id>/<case> 或 cases/<case> 一层嵌套
        for name in sorted(os.listdir(run_dir)):
            p = os.path.join(run_dir, name)
            if not os.path.isdir(p):
                continue
            for sub in sorted(os.listdir(p)):
                q = os.path.join(p, sub)
                if is_case_dir(q):
                    cases[sub] = q
    return cases


def counts_of(ac, case):
    if not isinstance(ac, dict):
        return {}
    cases = ac.get("cases")
    if isinstance(cases, dict) and isinstance(cases.get(case), dict):
        return cases[case].get("counts") or {}
    if isinstance(ac.get("counts"), dict):
        return ac["counts"]
    return {}


def validate_report(case_root, run_dir, case):
    """返回 (fail, warn, [codes])；优先案例级报告，其次运行级 validate-all。"""
    rep = load_json(os.path.join(case_root, "reports", "validate-report.json"))
    if isinstance(rep, dict):
        s = rep.get("summary") or {}
        codes = [c.get("code") for c in (rep.get("checks") or []) if c.get("severity") == "WARN"]
        return s.get("fail_count"), s.get("warn_count"), codes
    allrep = load_json(os.path.join(run_dir, "reports", "validate-all.json"))
    if isinstance(allrep, dict):
        for key in ("cases", "case_reports", "results"):
            block = allrep.get(key)
            if isinstance(block, dict) and case in block:
                item = block[case] or {}
                s = item.get("summary") or item
                codes = [c.get("code") for c in (item.get("checks") or []) if c.get("severity") == "WARN"]
                return s.get("fail_count"), s.get("warn_count"), codes
        s = allrep.get("summary") or {}
        if s and len(discover_cases(run_dir)) <= 1:
            codes = [c.get("code") for c in (allrep.get("checks") or []) if c.get("severity") == "WARN"]
            return s.get("fail_count"), s.get("warn_count"), codes
    return None, None, []


def num(v):
    if v is None or v == "":
        return DASH
    return str(v)


def build(run_dir, out_path):
    cases = discover_cases(run_dir)
    rows = []
    anomalies = []
    warn_codes = {}
    run_ids = set()
    modes = set()
    total = {"records": 0, "confirmed": 0, "suspect": 0, "evidence": 0,
             "occurrences": 0, "recurrence": 0, "fix": 0, "fail": 0, "warn": 0}
    numeric_any = False

    for case in sorted(cases):
        root = cases[case]
        ac = load_json(os.path.join(root, "reports", "actual_counts.json"), {}) or {}
        if isinstance(ac, dict):
            for k in ("run_id", "runId"):
                if ac.get(k):
                    run_ids.add(str(ac[k]))
            if ac.get("mode"):
                modes.add(str(ac["mode"]))
        counts = counts_of(ac, case)
        bugs = load_json(os.path.join(root, "library", "bugs.json"), []) or []
        evidence = load_json(os.path.join(root, "library", "evidence.json"), []) or []
        filters = load_jsonl(os.path.join(root, "process", "filter_results.jsonl"))
        records = len({r.get("source_key") for r in filters if r.get("source_key")})

        confirmed = counts.get("confirmed_defects")
        suspect = counts.get("suspect_defects")
        if confirmed is None and isinstance(bugs, list) and bugs:
            confirmed = len([b for b in bugs if b.get("category") == "defect"
                             and not (b.get("merge") or {}).get("merged_into")])
        if suspect is None and isinstance(bugs, list) and bugs:
            suspect = len([b for b in bugs if b.get("category") == "suspect"])
        ev_items = counts.get("evidence_items")
        if ev_items is None and isinstance(evidence, list):
            ev_items = len(evidence)
        occ = counts.get("independent_occurrences")
        rec = counts.get("recurrence_events")
        fix = counts.get("fix_actions")
        fix_note = counts.get("fix_actions_note")
        fail, warn, codes = validate_report(root, run_dir, case)

        for c in codes:
            if c:
                warn_codes[c] = warn_codes.get(c, 0) + 1

        if not counts:
            anomalies.append("%s：缺少可解析的 reports/actual_counts.json（计数列不可采信）" % case)
        if fix is None and not fix_note:
            anomalies.append("%s：fix_actions=null 但无 fix_actions_note" % case)
        if fail is None and warn is None:
            anomalies.append("%s：无校验报告（fail/warn 未判定）" % case)
        elif (fail or 0) > 0:
            anomalies.append("%s：校验 FAIL=%s，结论不可采信（先修输出）" % (case, fail))

        rows.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            case, records if records else DASH, num(confirmed), num(suspect), num(ev_items),
            num(occ), num(rec), num(fix), num(fail), num(warn)))

        for key, val in (("records", records), ("confirmed", confirmed), ("suspect", suspect),
                         ("evidence", ev_items), ("occurrences", occ), ("recurrence", rec),
                         ("fix", fix), ("fail", fail), ("warn", warn)):
            if isinstance(val, int):
                total[key] += val
                if key != "records":
                    numeric_any = True

    run_id = sorted(run_ids)[0] if run_ids else os.path.basename(os.path.normpath(run_dir))
    now = datetime.now(CST).isoformat(timespec="seconds")

    lines = []
    lines.append("# 运行汇总 · %s" % run_id)
    lines.append("")
    lines.append("> 生成方式：`python3 -I scripts/bc_run_summary.py --run-dir <运行根>`（V0.1.7 只读派生视图）")
    lines.append("> 生成时间：%s；案例数：%d；模式：%s" % (now, len(cases), "、".join(sorted(modes)) if modes else DASH))
    lines.append("> 口径：数字取自各案例 `reports/actual_counts.json`（缺值回落实际记录并标注）；"
                 "校验列取自 `reports/validate-report.json` 或运行级 `validate-all.json`。")
    lines.append("> 注意：本视图存在与数字一致**不等于**案例通过；结论以各案例 `actual_counts` + 校验报告为准。")
    lines.append("")
    lines.append("## 一、案例总表")
    lines.append("")
    lines.append("| 案例 | 输入记录 | 确认缺陷 | 疑似缺陷 | 证据 | 独立发生 | 复发 | fix_actions | 校验 FAIL | 校验 WARN |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    lines.extend(rows if rows else ["| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % ((DASH,) * 10)])
    lines.append("| **合计** | %d | %s | %s | %s | %s | %s | %s | %d | %d |" % (
        total["records"], total["confirmed"], total["suspect"], total["evidence"],
        total["occurrences"], total["recurrence"], total["fix"], total["fail"], total["warn"]))
    lines.append("")
    lines.append("- 合计列对 `null`/未知值不计入（不把未知当 0）；`—` 表示该案例取不到对应值。")
    lines.append("")
    lines.append("## 二、WARN 聚类")
    lines.append("")
    if warn_codes:
        lines.append("| 校验码 | 条数 |")
        lines.append("|---|---|")
        for code in sorted(warn_codes):
            lines.append("| %s | %d |" % (code, warn_codes[code]))
        lines.append("")
        lines.append("- WARN 说明输入或口径不完整，不等于 FAIL；不得为消除 WARN 而补造证据。")
    else:
        lines.append("无 WARN（或未提供可解析的校验报告，见「口径异常」）。")
    lines.append("")
    lines.append("## 三、口径异常")
    lines.append("")
    if anomalies:
        for a in anomalies:
            lines.append("- %s" % a)
    else:
        lines.append("无。")
    lines.append("")
    lines.append("## 四、视图自检")
    lines.append("")
    lines.append("- 行数：%d（案例目录 %d 个）%s" % (len(rows), len(cases), "，一致" if len(rows) == len(cases) else "，**不一致**"))
    lines.append("- 只读校验：本文件不写回 `actual_counts.json` / `library/`，不新增契约字段。")
    lines.append("")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return {"ok": len(rows) == len(cases), "cases": len(cases), "out": out_path,
            "run_id": run_id, "warn_codes": warn_codes, "anomalies": len(anomalies)}


def main():
    ap = argparse.ArgumentParser(description="Bug Collector 跨案例汇总视图（V0.1.7）")
    ap.add_argument("--run-dir", required=True, help="本轮运行根目录（含各案例目录）")
    ap.add_argument("--out", default=None, help="输出路径，默认 <run-dir>/reports/run-summary.md")
    args = ap.parse_args()
    run_dir = os.path.abspath(args.run_dir)
    if not os.path.isdir(run_dir):
        print(json.dumps({"ok": False, "error": "run-dir 不存在: %s" % run_dir}, ensure_ascii=False))
        return 1
    out = args.out or os.path.join(run_dir, "reports", "run-summary.md")
    res = build(run_dir, out)
    print(json.dumps(res, ensure_ascii=False))
    return 0 if res["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
