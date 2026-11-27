#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bc_validate.py — Bug Collector 确定性校验（V0.1.5）

把“原始输入”与“实际输出”做确定性比对，专门覆盖首轮离线测试暴露的 P0 问题：
  DEF-001 原始消息身份错误（source_key / message_id 被重写、补造）
  DEF-002 时间错误（来源时间、发生时间、采集/处理时间混用；精度被补造）
  DEF-003 证据归属与跨案例上下文污染（引用其他案例事实、事实挂错证据）
  DEF-004 自检只查输出内部引用，无法发现来源错误
并检查：筛选覆盖、枚举/引用、发生记录、非缺陷事件留痕、actual_counts 统计一致性。

只依赖 Python 标准库。退出码：0 = 无 FAIL（可有 WARN）；2 = 存在 FAIL；1 = 使用错误。

用法：
  python3 bc_validate.py --index <preprocess_out> --runs-root <runs> --out report.json
  python3 bc_validate.py --index <preprocess_out> --run-dir <case_run> --case-id TC-A5 --out r.json

runs-root 约定：<runs-root>/<case_id>/{process,library,reports}
  process/filter_results.jsonl
  process/candidates.jsonl
  process/match_results.json
  process/context_events.jsonl
  library/bugs.json
  library/evidence.json
  library/occurrences.json
  library/transitions.jsonl
  library/review_queue.json
  reports/actual_counts.json
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))

ENUMS = {
    "category": {"defect", "suspect", "requirement_related"},
    "lifecycle": {"open", "fixing", "fixed_unverified", "verified_fixed", "closed", "wont_fix"},
    "filter_decision": {"candidate", "evidence_only", "template", "sync", "noise", "context"},
    "priority": {"high", "mid", "low"},
    "match_result": {"new", "merge_into", "related_to", "duplicate_record", "review"},
    "confidence": {"high", "medium", "low"},
    "evidence_kind": {"message", "bug_record", "commit", "mr", "file", "review_note"},
    "role": {"primary_fix", "related_fix", "background", "status_evidence", "report"},
    "occurrence_kind": {"first", "repeat_unresolved", "repeat_after_fix", "rollback_regress"},
    "related_kind": {"same_incident", "caused_by", "blocked_by", "similar_class", "other"},
    "event_type": {"environment_event", "platform_incident", "evidence_gap", "requirement",
                   "operation_command", "execution_receipt", "performance_issue",
                   "capability_boundary", "reporting_discrepancy", "remediation", "background"},
    "record_type": {"commit_normal", "commit_merge", "mr", "message", "zentao_bug", "file"},
}

STAT_FIELDS = [
    "confirmed_defects", "suspect_defects", "evidence_items", "independent_occurrences",
    "repeat_unresolved_events", "recurrence_events", "unresolved_open_bugs",
    "related_cases", "bugs_without_occurrence", "recurrence_by_subtype",
]
EVENT_PREFIX = {
    "environment_events": "environment_event",
    "platform_incidents": "platform_incident",
    "evidence_gaps": "evidence_gap",
    "performance_issues": "performance_issue",
}


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                rows.append({"__parse_error__": "%s:%d %s" % (path, i, e)})
    return rows


def norm_ws(s):
    if s is None:
        return ""
    return re.sub(r"\s+", "", str(s))


def norm_num(s):
    return str(s).replace(",", "")


def nums_in(text):
    return {norm_num(x) for x in re.findall(r"\d[\d,]*(?:\.\d+)?", str(text or ""))}


QUOTE_SPLIT = re.compile(r"…|\.\.\.|⋯⋯")


def quote_matches(quote, raw_text):
    if not quote or not raw_text:
        return False
    raw = norm_ws(raw_text)
    parts = [p for p in (norm_ws(x) for x in QUOTE_SPLIT.split(quote)) if p]
    if not parts:
        return False
    return all(p in raw for p in parts)


def parse_iso(s):
    if not s:
        return None, "unknown"
    s = str(s).strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2}))?)?(Z|[+-]\d{2}:?\d{2})?$", s)
    if not m:
        return None, "unknown"
    y, mo, d, hh, mm, ss, tz = m.groups()
    if hh is None:
        return datetime(int(y), int(mo), int(d), tzinfo=CST), "date"
    dt = datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss or 0))
    prec = "seconds" if ss is not None else "minutes"
    if tz in (None, ""):
        dt = dt.replace(tzinfo=CST)
    elif tz == "Z":
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        t = tz.replace(":", "")
        sign = 1 if t[0] == "+" else -1
        dt = dt.replace(tzinfo=timezone(timedelta(hours=int(t[1:3]), minutes=int(t[3:5])) * sign))
    return dt.astimezone(CST), prec


def same_time(a, b, prec_a="seconds", prec_b="seconds"):
    da, pa = parse_iso(a)
    db, pb = parse_iso(b)
    if da is None or db is None:
        return False
    if "date" in (prec_a, prec_b, pa, pb):
        return da.date() == db.date()
    return da == db


class Checker:
    def __init__(self, index_dir, raw_root=None, contamination_min_len=10):
        self.index_dir = index_dir
        self.index_path = index_dir if index_dir.endswith(".jsonl") else os.path.join(index_dir, "records_index.jsonl")
        self.records = load_jsonl(self.index_path)
        self.by_key = {}
        self.duplicate_keys = []
        for r in self.records:
            k = r.get("source_key")
            if not k:
                continue
            if k in self.by_key:
                self.duplicate_keys.append(k)
            else:
                self.by_key[k] = r
        scopes_path = os.path.join(os.path.dirname(self.index_path), "case_scopes.json")
        self.scopes = load_json(scopes_path, {}) or {}
        self.raw_root = raw_root or os.path.dirname(os.path.abspath(self.index_path))
        self.contamination_min_len = contamination_min_len
        self.results = []

    # ---------- 基础 ----------
    def add(self, case, code, severity, message, detail=None):
        self.results.append({
            "case": case, "code": code, "severity": severity,
            "message": message, "detail": detail,
        })

    def fail(self, case, code, msg, detail=None):
        self.add(case, code, "FAIL", msg, detail)

    def warn(self, case, code, msg, detail=None):
        self.add(case, code, "WARN", msg, detail)

    # ---------- 索引自检 ----------
    def check_index(self):
        case = "*"
        for k in sorted(set(self.duplicate_keys)):
            self.fail(case, "IDX-002", "records_index 中 source_key 重复", {"source_key": k})
        for r in self.records:
            sk = r.get("source_key") or r.get("unresolved_key")
            if not sk:
                self.fail(case, "IDX-001", "记录缺少 source_key 且无法生成临时键", {"refs": r.get("refs")})
                continue
            recomputed = self.recompute_key(r)
            if recomputed is not None and recomputed != sk:
                self.fail(case, "IDX-001", "source_key 不能由原始身份字段重算", {
                    "source_key": sk, "recomputed": recomputed, "identity": r.get("identity")})
            if not r.get("source_time_iso") and r.get("source") in ("dingtalk", "gitlab", "zentao"):
                self.warn(case, "IDX-003", "来源时间无法确定性解析", {"source_key": sk, "raw": r.get("source_time_raw")})
        mapped = [r for r in self.records if "conversation_id_from_mapping" in (r.get("notes") or [])]
        if mapped:
            self.warn(case, "IDX-005", "conversationId 来自显式映射而非原始输入字段；必须披露，不得当作输入自带身份",
                      {"count": len(mapped), "samples": [r.get("source_key") for r in mapped[:3]]})
        sender_bad = [r for r in self.records if "sender_equals_message_id" in (r.get("notes") or [])]
        if sender_bad:
            self.warn(case, "IDX-004", "输入 sender 字段等于 messageId，已按无效发送人处理（不得作为身份）",
                      {"count": len(sender_bad), "samples": [r.get("source_key") for r in sender_bad[:5]]})

    @staticmethod
    def recompute_key(r):
        src = r.get("source")
        ident = r.get("identity") or {}
        if src == "dingtalk":
            cid, mid = ident.get("conversation_id"), ident.get("message_id")
            return "dingtalk:%s:%s" % (cid, mid) if cid and mid else None
        if src == "zentao":
            inst, bid = ident.get("instance"), ident.get("bug_id")
            return "zentao:%s:%s" % (inst, bid) if inst and bid is not None else None
        if src == "gitlab":
            proj, sha, iid = ident.get("project"), ident.get("sha"), ident.get("iid")
            if iid is not None:
                return "gitlab:%s:mr:%s" % (proj, iid) if proj else None
            return "gitlab:%s:%s" % (proj, sha) if proj and sha else None
        if src == "synthetic":
            return "synthetic:%s:%s" % (ident.get("case_id"), ident.get("ref"))
        if src == "file":
            return "file:%s:%s" % (ident.get("case_id"), ident.get("ref"))
        return None

    # ---------- 案例数据 ----------
    def load_case(self, case_id, root):
        lib = os.path.join(root, "library")
        proc = os.path.join(root, "process")
        rep = os.path.join(root, "reports")
        data = {
            "case_id": case_id, "root": root,
            "filters": load_jsonl(os.path.join(proc, "filter_results.jsonl")),
            "candidates": load_jsonl(os.path.join(proc, "candidates.jsonl")),
            "match_results": load_json(os.path.join(proc, "match_results.json"), {}) or {},
            "context_events": load_jsonl(os.path.join(proc, "context_events.jsonl")),
            "bugs": load_json(os.path.join(lib, "bugs.json"), []) or [],
            "evidence": load_json(os.path.join(lib, "evidence.json"), []) or [],
            "occurrences": load_json(os.path.join(lib, "occurrences.json"), []) or [],
            "transitions": load_jsonl(os.path.join(lib, "transitions.jsonl")),
            "review": load_json(os.path.join(lib, "review_queue.json"), []) or [],
            "actual_counts": load_json(os.path.join(rep, "actual_counts.json"), {}) or {},
        }
        data["missing"] = [p for p in [
            os.path.join(proc, "filter_results.jsonl"), os.path.join(lib, "bugs.json"),
            os.path.join(lib, "evidence.json"), os.path.join(lib, "occurrences.json"),
            os.path.join(rep, "actual_counts.json")] if not os.path.exists(p)]
        data["evidence_by_id"] = {e.get("evidence_id"): e for e in data["evidence"] if e.get("evidence_id")}
        data["bug_by_id"] = {b.get("bug_id"): b for b in data["bugs"] if b.get("bug_id")}
        data["occ_by_id"] = {o.get("occurrence_id"): o for o in data["occurrences"] if o.get("occurrence_id")}
        return data

    # ---------- 单个案例 ----------
    def check_case(self, d):
        case = d["case_id"]
        for p in d["missing"]:
            self.fail(case, "LIB-000", "缺少必需输出文件", {"path": p})
        scope = set(self.scopes.get(case, []))

        # 筛选覆盖与身份
        seen = {}
        candidate_ids_in_filters = set()
        for line in d["filters"]:
            if "__parse_error__" in line:
                self.fail(case, "JSON-000", "filter_results 行无法解析", line["__parse_error__"])
                continue
            sk = line.get("source_key")
            if not sk:
                self.fail(case, "ID-001", "筛选记录缺少 source_key", {"line": line})
                continue
            seen[sk] = seen.get(sk, 0) + 1
            if sk not in self.by_key:
                self.fail(case, "ID-001", "筛选记录的 source_key 不在原始输入中（疑似补造/改写）", {"source_key": sk})
            if scope and sk not in scope:
                self.fail(case, "ISO-001", "筛选记录不属于本案例输入范围（跨案例上下文污染）", {"source_key": sk})
            self.check_enum(case, "filter_decision", line.get("filter_decision"), "filter_results", sk)
            self.check_enum(case, "priority", line.get("priority"), "filter_results", sk)
            if not line.get("triage_reason") or not line.get("reason"):
                self.fail(case, "FIL-001", "筛选记录缺少 triage_reason/reason", {"source_key": sk})
            for cid in line.get("candidate_ids") or []:
                candidate_ids_in_filters.add(cid)
            # 非缺陷事件留痕
            dec = line.get("filter_decision")
            if dec in ("template", "sync", "noise", "context"):
                has_ctx = any(e.get("source_key") == sk for e in d["context_events"])
                confirmed_noise = dec == "noise" and line.get("noise_scope") == "confirmed_irrelevant" and line.get("reason")
                if not has_ctx and not confirmed_noise:
                    self.fail(case, "CTX-001", "非候选记录未在 context_events 中结构化保留", {"source_key": sk, "decision": dec})

        if scope:
            for sk in sorted(scope - set(seen)):
                self.fail(case, "COV-001", "原始输入记录没有对应的筛选结论", {"source_key": sk})
        if not d["filters"]:
            self.fail(case, "COV-000", "filter_results.jsonl 为空或缺失")

        cand_by_id = {}
        for c in d["candidates"]:
            cid = c.get("candidate_id")
            if not cid:
                self.fail(case, "CAND-001", "候选缺少 candidate_id", {"candidate": c})
                continue
            cand_by_id[cid] = c
            for sk in c.get("source_refs") or []:
                if sk not in self.by_key:
                    self.fail(case, "CAND-002", "候选 source_refs 指向不存在的原始记录", {"candidate_id": cid, "source_key": sk})
                if scope and sk not in scope:
                    self.fail(case, "ISO-001", "候选引用了本案例之外的原始记录", {"candidate_id": cid, "source_key": sk})
        for cid in candidate_ids_in_filters - set(cand_by_id):
            self.fail(case, "CAND-003", "筛选记录引用的候选不存在", {"candidate_id": cid})
        for cid in cand_by_id:
            if cid not in set(l.get("candidate_id") for l in d["match_results"].get("items", []) if isinstance(l, dict)):
                self.fail(case, "CAND-004", "候选没有匹配结果（unknown 状态不得静默丢弃）", {"candidate_id": cid})

        # 证据
        for e in d["evidence"]:
            self.check_evidence(case, e, scope)

        # 缺陷与事实锚点
        for b in d["bugs"]:
            self.check_bug(case, b, d, scope)

        # 发生记录
        for o in d["occurrences"]:
            self.check_occurrence(case, o, d)

        # 上下文事件
        for ev in d["context_events"]:
            self.check_context_event(case, ev, scope)

        # 引用完整性 / 枚举 / 归并
        self.check_refs(case, d)

        # 统计
        self.check_stats(case, d)

        # 跨案例短语污染
        self.check_contamination(case, d)

    def check_enum(self, case, enum_name, value, where, sk):
        allowed = ENUMS.get(enum_name)
        if allowed and value not in allowed:
            self.fail(case, "ENUM-001", "非法枚举值", {"field": enum_name, "value": value, "where": where, "source_key": sk})

    def check_evidence(self, case, e, scope):
        eid = e.get("evidence_id") or "<no-id>"
        sk = e.get("source_key")
        if not sk:
            self.fail(case, "ID-002", "证据缺少 source_key", {"evidence_id": eid})
            return
        rec = self.by_key.get(sk)
        if rec is None:
            self.fail(case, "ID-002", "证据 source_key 不在原始输入中（疑似补造 message_id/SHA/禅道号）",
                      {"evidence_id": eid, "source_key": sk})
            return
        if scope and sk not in scope:
            self.fail(case, "ISO-001", "证据引用了本案例之外的原始记录", {"evidence_id": eid, "source_key": sk})
        self.check_enum(case, "evidence_kind", e.get("kind"), "evidence", sk)
        # 身份字段逐项比对
        ident = rec.get("identity") or {}
        for field in ("message_id", "bug_id", "sha", "iid"):
            if field in e and e.get(field) is not None and ident.get(field) is not None:
                if str(e.get(field)) != str(ident.get(field)):
                    self.fail(case, "ID-003", "证据身份字段与原始输入不一致", {
                        "evidence_id": eid, "field": field, "evidence": e.get(field), "raw": ident.get(field)})
        # 时间：来源记录时间
        st = e.get("source_time") or e.get("source_record_time")
        if st is None:
            self.warn(case, "TIME-004", "证据缺少 source_time，无法确定性核对来源时间（不得因此标 PASS）",
                      {"evidence_id": eid})
        elif rec.get("source_time_iso"):
            rp = rec.get("time_precision")
            if rp == "date":
                if not same_time(st, rec["source_time_iso"], "date", "date"):
                    self.fail(case, "TIME-003", "来源仅日期精度，证据时间不匹配", {"evidence_id": eid, "evidence": st, "raw": rec["source_time_iso"]})
            elif not same_time(st, rec["source_time_iso"], "seconds", rp):
                self.fail(case, "TIME-001", "证据时间与原始来源时间不一致", {
                    "evidence_id": eid, "evidence": st, "raw": rec["source_time_iso"]})
        # 内容哈希
        if e.get("content_sha256") and rec.get("content_sha256") and e["content_sha256"] != rec["content_sha256"]:
            self.fail(case, "ID-005", "证据内容哈希与原始输入不一致", {"evidence_id": eid})
        # quote
        if e.get("quote"):
            if rec.get("verifiable") is False:
                self.warn(case, "EV-001", "构造输入无法校验 quote（只作离线夹具）", {"evidence_id": eid})
            elif not quote_matches(e["quote"], rec.get("text")):
                self.fail(case, "EV-001", "证据 quote 与原始内容不符", {
                    "evidence_id": eid, "quote": str(e["quote"])[:120]})
        else:
            self.warn(case, "EV-004", "证据缺少 quote", {"evidence_id": eid})
        # raw_pointer
        self.check_raw_pointer(case, e, rec)
        # bug_links
        for link in e.get("bug_links") or []:
            if not link.get("bug_id"):
                self.fail(case, "REF-001", "证据 bug_links 缺少 bug_id", {"evidence_id": eid})
            self.check_enum(case, "role", link.get("role"), "evidence.bug_links", sk)
        # 更正链
        for field in ("supersedes", "superseded_by"):
            if e.get(field):
                if not isinstance(e[field], str):
                    self.fail(case, "EV-005", "%s 应为 evidence_id 字符串" % field, {"evidence_id": eid})
        # 传播证据不能直接当状态证据等语义项由 QC 语义复核；脚本只查引用存在

    def check_raw_pointer(self, case, e, rec):
        p = e.get("raw_pointer")
        eid = e.get("evidence_id") or "<no-id>"
        if not p:
            self.fail(case, "EV-002", "证据缺少 raw_pointer", {"evidence_id": eid})
            return
        if isinstance(p, str):
            ok = (e.get("source_key") or "") in p or (rec.get("refs") or [""])[0] in p
            if not ok:
                self.fail(case, "EV-002", "raw_pointer 无法解析到原始输入", {"evidence_id": eid, "raw_pointer": p})
            return
        if not isinstance(p, dict):
            self.fail(case, "EV-002", "raw_pointer 结构非法", {"evidence_id": eid})
            return
        psk = p.get("source_key")
        if psk and psk != e.get("source_key"):
            self.fail(case, "EV-002", "raw_pointer.source_key 与证据不一致", {"evidence_id": eid, "pointer": psk, "evidence": e.get("source_key")})
            return
        if psk and psk in self.by_key:
            return
        path = p.get("path")
        if path:
            full = path if os.path.isabs(path) else os.path.join(self.raw_root, path)
            if os.path.exists(full):
                if full.endswith(".json"):
                    try:
                        obj = load_json(full)
                        loc = p.get("locator")
                        if isinstance(loc, str) and loc.startswith("/"):
                            cur = obj
                            for part in [x for x in loc.split("/") if x]:
                                cur = cur[int(part)] if isinstance(cur, list) else cur[part]
                            if isinstance(cur, dict) and cur.get("source_key") in (None, e.get("source_key")):
                                return
                    except Exception:
                        pass
                return
            if psk:
                # 原始快照文件不在本机时，允许以索引作为可回查代理
                self.warn(case, "EV-002", "raw_pointer.path 不存在，已用 records_index 代理核对", {"evidence_id": eid, "path": path})
                return
        self.fail(case, "EV-002", "raw_pointer 无法解析到真实输入", {"evidence_id": eid, "raw_pointer": p})

    def check_bug(self, case, b, d, scope):
        bid = b.get("bug_id") or "<no-id>"
        self.check_enum(case, "category", b.get("category"), "bugs", bid)
        self.check_enum(case, "lifecycle", b.get("lifecycle"), "bugs", bid)
        ev_ids = b.get("evidence_ids") or []
        if not ev_ids:
            self.fail(case, "BUG-001", "缺陷没有任何证据", {"bug_id": bid})
        ev_texts = {}
        report_times = []
        for eid in ev_ids:
            e = d["evidence_by_id"].get(eid)
            if not e:
                self.fail(case, "REF-001", "缺陷 evidence_ids 指向不存在的证据", {"bug_id": bid, "evidence_id": eid})
                continue
            rec = self.by_key.get(e.get("source_key"))
            if rec:
                ev_texts[eid] = rec.get("text") or ""
            role = None
            for link in e.get("bug_links") or []:
                if link.get("bug_id") == bid:
                    role = link.get("role")
            if role == "report" and rec and rec.get("source_time_iso"):
                report_times.append(rec["source_time_iso"])
        # first_observed_at 必须来自来源时间
        if b.get("first_observed_at"):
            expected = min(report_times) if report_times else None
            if expected:
                # 精度按来源
                prec = "seconds"
                for eid in ev_ids:
                    e = d["evidence_by_id"].get(eid)
                    rec = self.by_key.get((e or {}).get("source_key"))
                    if rec and rec.get("time_precision") == "date":
                        prec = "date"
                        break
                if not same_time(b["first_observed_at"], expected, "seconds", prec):
                    self.fail(case, "TIME-001", "缺陷 first_observed_at 与来源记录时间不一致", {
                        "bug_id": bid, "bug": b["first_observed_at"], "expected": expected})
            else:
                self.warn(case, "TIME-005", "无法从证据来源时间核对 first_observed_at", {"bug_id": bid})
        else:
            self.fail(case, "TIME-006", "缺陷缺少 first_observed_at", {"bug_id": bid})
        # 事实锚点
        anchors = b.get("fact_anchors") or []
        if b.get("category") == "defect" and not anchors:
            self.fail(case, "ISO-003", "缺陷缺少 fact_anchors，事实无法逐条落到自身证据", {"bug_id": bid})
        for a in anchors:
            eid = a.get("evidence_id")
            fact = a.get("fact") or ""
            quote = a.get("quote") or ""
            if eid not in ev_ids:
                self.fail(case, "ISO-003", "事实锚点指向未关联证据", {"bug_id": bid, "evidence_id": eid})
                continue
            txt = ev_texts.get(eid, "")
            if not txt:
                self.warn(case, "ISO-003", "事实锚点证据为构造/不可校验输入", {"bug_id": bid, "evidence_id": eid})
                continue
            if quote and not quote_matches(quote, txt):
                self.fail(case, "ISO-003", "事实锚点 quote 不在所挂证据中", {"bug_id": bid, "evidence_id": eid, "quote": quote[:80]})
            missing = nums_in(fact) - (nums_in(txt) | nums_in(quote))
            if missing:
                self.fail(case, "ISO-003", "事实中的数字在所挂证据中找不到支持（疑似挂错证据）", {
                    "bug_id": bid, "evidence_id": eid, "fact": fact[:100], "missing": sorted(missing)[:10]})
        # 关联
        for rel in b.get("related") or []:
            self.check_enum(case, "related_kind", rel.get("kind"), "bugs.related", bid)
            if rel.get("bug_id") and rel.get("bug_id") not in d["bug_by_id"]:
                self.fail(case, "REF-001", "related.bug_id 不存在", {"bug_id": bid, "target": rel.get("bug_id")})
        # 归并别名不得重复计入统计（统计阶段处理）

    def check_occurrence(self, case, o, d):
        oid = o.get("occurrence_id") or "<no-id>"
        self.check_enum(case, "occurrence_kind", o.get("kind"), "occurrences", oid)
        bid = o.get("bug_id")
        if bid not in d["bug_by_id"]:
            self.fail(case, "OCC-004", "发生记录指向不存在的缺陷", {"occurrence_id": oid, "bug_id": bid})
            return
        ev_ids = o.get("evidence_ids") or []
        if not ev_ids:
            self.fail(case, "OCC-001", "发生记录没有证据（虚构 occurrence）", {"occurrence_id": oid, "bug_id": bid})
            return
        times = []
        for eid in ev_ids:
            e = d["evidence_by_id"].get(eid)
            if not e:
                self.fail(case, "OCC-005", "发生记录的 evidence_ids 不存在", {"occurrence_id": oid, "evidence_id": eid})
                continue
            if eid not in (d["bug_by_id"][bid].get("evidence_ids") or []):
                self.fail(case, "OCC-005", "发生记录引用的证据未关联到该缺陷", {"occurrence_id": oid, "evidence_id": eid})
            rec = self.by_key.get(e.get("source_key"))
            if rec and rec.get("source_time_iso"):
                times.append(rec["source_time_iso"])
        if o.get("observed_at") and times:
            if not any(same_time(o["observed_at"], t) for t in times):
                self.fail(case, "TIME-002", "发生时间与所引证据的来源时间不一致（不得借用其他消息时间）", {
                    "occurrence_id": oid, "observed_at": o["observed_at"], "evidence_times": times})
        elif not o.get("observed_at"):
            self.fail(case, "TIME-006", "发生记录缺少 observed_at", {"occurrence_id": oid})
        env = o.get("environment")
        if isinstance(env, dict) and not any(v for v in env.values()):
            self.fail(case, "ENV-001", "environment 为全空对象，应写 null", {"occurrence_id": oid})

    def check_context_event(self, case, ev, scope):
        eid = ev.get("event_id") or "<no-id>"
        self.check_enum(case, "event_type", ev.get("event_type"), "context_events", eid)
        sk = ev.get("source_key")
        if not sk or sk not in self.by_key:
            self.fail(case, "CTX-002", "非缺陷事件 source_key 不在原始输入中", {"event_id": eid, "source_key": sk})
        if scope and sk and sk not in scope:
            self.fail(case, "CTX-003", "非缺陷事件引用本案例之外的记录", {"event_id": eid, "source_key": sk})
        if not ev.get("summary") or not ev.get("reason"):
            self.fail(case, "CTX-002", "非缺陷事件缺少 summary/reason", {"event_id": eid})

    def check_refs(self, case, d):
        # 证据 -> 缺陷引用
        for e in d["evidence"]:
            for link in e.get("bug_links") or []:
                if link.get("bug_id") not in d["bug_by_id"]:
                    self.fail(case, "REF-001", "证据关联的缺陷不存在", {"evidence_id": e.get("evidence_id"), "bug_id": link.get("bug_id")})
        # 归并无环
        graph = {b.get("bug_id"): (b.get("merge") or {}).get("merged_into") for b in d["bugs"]}
        for start in graph:
            seen = set()
            cur = start
            while cur and cur in graph:
                if cur in seen:
                    self.fail(case, "REF-002", "merge.merged_into 成环", {"bug_id": start})
                    break
                seen.add(cur)
                cur = graph.get(cur)
        # 主键唯一
        for name, items, key in (("bugs", d["bugs"], "bug_id"), ("evidence", d["evidence"], "evidence_id"),
                                 ("occurrences", d["occurrences"], "occurrence_id")):
            ids = [x.get(key) for x in items if x.get(key)]
            if len(ids) != len(set(ids)):
                self.fail(case, "REF-003", "%s 主键重复" % name)
        # 更正链引用
        for e in d["evidence"]:
            for field in ("supersedes", "superseded_by"):
                tgt = e.get(field)
                if tgt and tgt not in d["evidence_by_id"]:
                    self.fail(case, "EV-005", "%s 指向不存在的证据" % field, {"evidence_id": e.get("evidence_id"), "target": tgt})
        # 去重事件提醒
        deduped = self.deduped_occurrences(d)
        if len(deduped) < len([o for o in d["occurrences"] if o.get("kind") in ENUMS["occurrence_kind"]]):
            self.warn(case, "OCC-003", "存在同缺陷同一事件的重复 occurrence 记录；统计已按 §3.8 去重，原始记录保留", {
                "raw": len(d["occurrences"]), "deduped": len(deduped)})

    def deduped_occurrences(self, d):
        occs = [o for o in d["occurrences"] if o.get("kind") in ENUMS["occurrence_kind"]]
        by_bug = {}
        for o in occs:
            by_bug.setdefault(o.get("bug_id"), []).append(o)
        kept_all = []
        for bid, group in by_bug.items():
            kept = []
            for o in sorted(group, key=lambda x: str(x.get("observed_at") or "")):
                dup = False
                for k in kept:
                    if same_time(o.get("observed_at"), k.get("observed_at")):
                        inter = set(o.get("evidence_ids") or []) & set(k.get("evidence_ids") or [])
                        report = {eid for eid in inter if self.role_of(d, eid, bid) == "report"}
                        if report and not o.get("independent_evidence") and not k.get("independent_evidence"):
                            dup = True
                            break
                if not dup:
                    kept.append(o)
            kept_all.extend(kept)
        return kept_all

    @staticmethod
    def role_of(d, eid, bid):
        e = d["evidence_by_id"].get(eid) or {}
        for link in e.get("bug_links") or []:
            if link.get("bug_id") == bid:
                return link.get("role")
        return None

    # ---------- 统计 ----------
    def case_counts(self, d, entry):
        case = d["case_id"]
        bugs = []
        bug_ids = entry.get("bug_ids")
        if bug_ids is None:
            # 退化：按案例 scope 证据反查缺陷
            scope = set(self.scopes.get(case, []))
            bug_ids = [b.get("bug_id") for b in d["bugs"]
                       if any((d["evidence_by_id"].get(eid) or {}).get("source_key") in scope for eid in (b.get("evidence_ids") or []))]
        for bid in bug_ids:
            b = d["bug_by_id"].get(bid)
            if b:
                bugs.append(b)
            else:
                self.fail(case, "REF-001", "actual_counts.bug_ids 指向不存在的缺陷", {"bug_id": bid})
        main_bugs = [b for b in bugs if not (b.get("merge") or {}).get("merged_into")]
        confirmed = sum(1 for b in main_bugs if b.get("category") == "defect")
        suspect = sum(1 for b in main_bugs if b.get("category") == "suspect")
        ev_ids = entry.get("evidence_ids")
        if ev_ids is None:
            ev_ids = sorted({eid for b in bugs for eid in (b.get("evidence_ids") or [])})
        for eid in ev_ids:
            if eid not in d["evidence_by_id"]:
                self.fail(case, "STAT-005", "actual_counts.evidence_ids 指向不存在的证据", {"evidence_id": eid})
        deduped = [o for o in self.deduped_occurrences(d) if o.get("bug_id") in {b.get("bug_id") for b in bugs}]
        by_kind = {}
        for o in deduped:
            by_kind[o.get("kind")] = by_kind.get(o.get("kind"), 0) + 1
        related = sum(1 for b in main_bugs for r in (b.get("related") or []) if r.get("kind") == "similar_class")
        open_bugs = sum(1 for b in main_bugs if b.get("lifecycle") in ("open", "fixing"))
        without_occ = 0
        for b in main_bugs:
            if not any(o.get("bug_id") == b.get("bug_id") for o in deduped):
                without_occ += 1
        verified = set()
        for t in d["transitions"]:
            if t.get("field") == "lifecycle" and t.get("to") in ("verified_fixed", "closed"):
                env = t.get("environment")
                if isinstance(env, dict) and env.get("canonical_name"):
                    verified.add(env["canonical_name"])
                elif isinstance(env, str) and env:
                    verified.add(env)
        ctx = {}
        for ev in d["context_events"]:
            ctx[ev.get("event_type")] = ctx.get(ev.get("event_type"), 0) + 1
        return {
            "confirmed_defects": confirmed,
            "suspect_defects": suspect,
            "evidence_items": len(set(ev_ids)),
            "independent_occurrences": len(deduped),
            "repeat_unresolved_events": by_kind.get("repeat_unresolved", 0),
            "recurrence_events": by_kind.get("repeat_after_fix", 0) + by_kind.get("rollback_regress", 0),
            "unresolved_open_bugs": open_bugs,
            "related_cases": related,
            "bugs_without_occurrence": without_occ,
            "recurrence_by_subtype": {
                "repeat_after_fix": by_kind.get("repeat_after_fix", 0),
                "rollback_regress": by_kind.get("rollback_regress", 0),
            },
            "_verified_environments": sorted(verified),
            "_event_counts": ctx,
        }

    def check_stats(self, case, d):
        ac = d["actual_counts"]
        entry = None
        if isinstance(ac, dict):
            if "cases" in ac:
                cases = ac["cases"]
                if isinstance(cases, dict):
                    entry = cases.get(case)
                elif isinstance(cases, list):
                    entry = next((x for x in cases if x.get("case_id") == case), None)
            if entry is None and ac.get("case_id") == case:
                entry = ac
        if entry is None:
            self.fail(case, "STAT-001", "缺少本案例 actual_counts", {"path": os.path.join(d["root"], "reports/actual_counts.json")})
            return
        declared = entry.get("counts") or entry.get("actual_counts") or {}
        computed = self.case_counts(d, entry)
        for f in STAT_FIELDS:
            if f == "recurrence_by_subtype":
                continue
            if f not in declared:
                self.fail(case, "STAT-001", "actual_counts 缺少字段", {"field": f})
                continue
            if declared.get(f) is None:
                if f in ("suspect_defects", "independent_occurrences"):
                    continue  # 允许 undetermined
                self.fail(case, "STAT-002", "actual_counts 字段为 null 但该指标不允许缺省", {"field": f})
                continue
            if declared.get(f) != computed[f]:
                self.fail(case, "STAT-002", "actual_counts 与输出记录重算不一致", {
                    "field": f, "declared": declared.get(f), "computed": computed[f]})
        sub = declared.get("recurrence_by_subtype")
        if sub is None:
            self.fail(case, "STAT-003", "缺少 recurrence_by_subtype", {})
        else:
            if sub != computed["recurrence_by_subtype"]:
                self.fail(case, "STAT-003", "复发子类型分布与重算不一致", {"declared": sub, "computed": computed["recurrence_by_subtype"]})
            if sum(v for v in sub.values() if isinstance(v, int)) != computed["recurrence_events"]:
                self.fail(case, "STAT-003", "复发子类型合计不等于 recurrence_events", {"subtype": sub, "computed": computed["recurrence_events"]})
        # verified_environments
        if "verified_environments" in declared:
            dv = declared["verified_environments"]
            if computed["_verified_environments"]:
                if isinstance(dv, str) or set(dv or []) != set(computed["_verified_environments"]):
                    self.fail(case, "STAT-006", "verified_environments 与流转记录不一致", {
                        "declared": dv, "computed": computed["_verified_environments"]})
            else:
                if not (isinstance(dv, str) and ("未知" in dv or "unknown" in dv.lower())):
                    self.fail(case, "STAT-006", "无可归一环境时必须报未知，不得写 0 或空", {"declared": dv})
        # coverage
        if not declared.get("coverage"):
            self.fail(case, "STAT-004", "actual_counts 缺少 coverage", {})
        # 非缺陷事件计数
        for field, etype in EVENT_PREFIX.items():
            if field in declared and declared[field] != computed["_event_counts"].get(etype, 0):
                self.fail(case, "STAT-002", "非缺陷事件计数与 context_events 不一致", {
                    "field": field, "declared": declared[field], "computed": computed["_event_counts"].get(etype, 0)})
        # fix_actions 可选：只做类型检查
        fa = declared.get("fix_actions")
        if fa is not None and not isinstance(fa, int):
            self.fail(case, "STAT-007", "fix_actions 只能是整数或 null", {"declared": fa})

    # ---------- 跨案例污染 ----------
    def shingles(self, text, n):
        s = norm_ws(text)
        out = set()
        for i in range(0, max(0, len(s) - n + 1)):
            piece = s[i:i + n]
            cjk = sum(1 for ch in piece if "一" <= ch <= "鿿")
            if cjk >= max(4, n - 2):
                out.add(piece)
        return out

    def check_contamination(self, case, d):
        n = self.contamination_min_len
        own_text = "\n".join((self.by_key.get(sk, {}) or {}).get("text") or "" for sk in self.scopes.get(case, []))
        own = self.shingles(own_text, n)
        foreign = set()
        for other, keys in self.scopes.items():
            if other == case:
                continue
            for sk in keys:
                foreign |= self.shingles((self.by_key.get(sk, {}) or {}).get("text") or "", n)
        foreign -= own
        if not foreign:
            return
        bug_text = "\n".join(str(b.get(k) or "") for b in d["bugs"]
                             for k in ("title", "actual_behavior", "expected_behavior", "trigger_conditions", "impact"))
        hits = sorted(self.shingles(bug_text, n) & foreign)
        if hits:
            self.fail(case, "ISO-002", "缺陷描述包含仅出现在其他案例输入中的原文片段（跨案例上下文污染）", {
                "hits": hits[:8], "count": len(hits)})

    # ---------- 入口 ----------
    def run(self, runs_root, only_cases=None, single=None):
        self.check_index()
        case_roots = {}
        if single:
            case_roots[single[0]] = single[1]
        else:
            for name in sorted(os.listdir(runs_root)):
                root = os.path.join(runs_root, name)
                if os.path.isdir(root):
                    case_roots[name] = root
        if only_cases:
            case_roots = {k: v for k, v in case_roots.items() if k in set(only_cases)}
        for case_id, root in case_roots.items():
            d = self.load_case(case_id, root)
            self.check_case(d)
        fails = [r for r in self.results if r["severity"] == "FAIL"]
        warns = [r for r in self.results if r["severity"] == "WARN"]
        summary = {
            "ok": len(fails) == 0,
            "cases": sorted(case_roots),
            "fail_count": len(fails),
            "warn_count": len(warns),
            "by_code": {},
        }
        for r in self.results:
            key = r["code"] + ":" + r["severity"]
            summary["by_code"][key] = summary["by_code"].get(key, 0) + 1
        return {"summary": summary, "checks": self.results}


def main():
    ap = argparse.ArgumentParser(description="Bug Collector 确定性校验")
    ap.add_argument("--index", required=True, help="bc_preprocess.py 输出目录或 records_index.jsonl")
    ap.add_argument("--runs-root", help="案例运行根目录（每个子目录一个 case_id）")
    ap.add_argument("--run-dir", help="单个案例运行目录")
    ap.add_argument("--case-id", help="配合 --run-dir 的案例 ID")
    ap.add_argument("--only", nargs="*", help="只校验指定案例")
    ap.add_argument("--raw-root", help="raw_pointer.path 的解析根目录")
    ap.add_argument("--contamination-min-len", type=int, default=10)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if not args.runs_root and not (args.run_dir and args.case_id):
        ap.error("必须提供 --runs-root 或 --run-dir + --case-id")
    ck = Checker(args.index, args.raw_root, args.contamination_min_len)
    result = ck.run(args.runs_root, args.only, (args.case_id, args.run_dir) if args.run_dir else None)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps(result["summary"], ensure_ascii=False))
    return 0 if result["summary"]["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
