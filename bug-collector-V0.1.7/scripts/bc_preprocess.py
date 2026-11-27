#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bc_preprocess.py — Bug Collector 确定性预处理（V0.1.6；V0.1.5 逻辑不变，仅版本对齐）

用途：在语义处理之前，把原始输入中的“来源身份 / 时间 / 正文 / 内容哈希”确定性抽取为
records_index.jsonl。后续筛选、证据、缺陷、发生记录中的 source_key、source_time、
quote 必须从本索引复制，禁止由 Agent 重写、补造或推测。

只依赖 Python 标准库。单次运行在毫秒级完成。

支持输入：
  1) --test-inputs test-inputs-V1.4.json [--casebook candidate-cases-V1.4.json]
  2) --records records.json      # {"records":[{...}]}

输出（--out 目录）：
  records_index.jsonl  一行一条原始记录（同一 source_key 多案例合并，cases 列出全部）
  case_scopes.json     case_id -> [source_key]
  summary.json         统计、无法解析身份的记录、发送人字段异常等

source_key 口径（collection-rules §6.1）：
  钉钉        dingtalk:<conversationId>:<messageId>
  禅道        zentao:<实例标识>:<bugId>
  GitLab      gitlab:<项目ID>:<SHA>
  GitLab MR   gitlab:<项目ID>:mr:<iid>
  构造事件    synthetic:<case_id>:<ref>       （仅离线测试，verifiable=false）
  其他文件    file:<case_id>:<ref>            （仅离线测试，verifiable=false）

时间语义（V0.1.5）：
  source_time_raw / source_time_iso / time_precision / time_source_field
  source_time_iso 统一为 Asia/Shanghai（+08:00）；原始精度保留：
    seconds / minutes / date / unknown
  不补造时分秒；原文只有日期时 precision=date。
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))

# V1.4 案例集里唯一登记的群：数据小队。允许 --conversation-map 覆盖。
DEFAULT_CONVERSATION_MAP = {"数据小队": "cidxs5TpPs34DWnKqMsf+WrEw=="}

TIME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?")
ISO_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-]\d{2}:?\d{2})$")
# V0.1.7：附件引用识别（mediaId / fileId 等显式标识；只证明"存在引用"，不证明获取了附件内容）
ATTACH_REF_RE = re.compile(r"(media[_ ]?id|file[_ ]?id|resource[_ ]?refs)\s*[=:：]\s*[\w+/=\-]{4,}", re.I)


def norm_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_time(raw):
    """返回 (iso, precision, error). iso 带 +08:00；无法解析返回 (None, 'unknown', reason)。"""
    if raw is None:
        return None, "unknown", "missing"
    s = str(raw).strip()
    if not s:
        return None, "unknown", "empty"
    m = ISO_RE.match(s)
    if m:
        y, mo, d, hh, mm, ss, tz = m.groups()
        dt = datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss))
        if tz == "Z":
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            sign = 1 if tz[0] == "+" else -1
            tz = tz.replace(":", "")
            off = timedelta(hours=int(tz[1:3]), minutes=int(tz[3:5])) * sign
            dt = dt.replace(tzinfo=timezone(off))
        return dt.astimezone(CST).isoformat(), "seconds", None
    m = TIME_RE.match(s)
    if m:
        y, mo, d, hh, mm, ss = m.groups()
        if ss is not None:
            dt = datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss), tzinfo=CST)
            return dt.isoformat(), "seconds", None
        if hh is not None:
            dt = datetime(int(y), int(mo), int(d), int(hh), int(mm), tzinfo=CST)
            return dt.isoformat(), "minutes", None
        dt = datetime(int(y), int(mo), int(d), tzinfo=CST)
        return dt.isoformat(), "date", None
    # 只有日期片段（如 2026-11-25）也被 TIME_RE 覆盖；其余无法确定性解析
    return None, "unknown", "unparsed_time:%s" % s[:40]


def extract_sender(raw_sender, time_raw):
    """发送人只从显式姓名或 time 尾部的姓名读取；sender 等于 messageId 时标记 invalid。"""
    sender = None
    quality = "missing"
    if isinstance(raw_sender, str) and raw_sender.strip():
        sender = raw_sender.strip()
        quality = "declared"
    # time 形如 "2026-11-18 10:46:25 陈昔"
    if isinstance(time_raw, str):
        m = re.search(r"\d{2}:\d{2}(?::\d{2})?\s+([^\s]+)\s*$", time_raw)
        if m:
            tail = m.group(1).strip()
            if tail and not tail.startswith("msg") and tail not in ("(北京时间)",):
                if sender is None:
                    sender = tail
                    quality = "parsed_from_time"
    return sender, quality


def build_record(case_id, item, conversation_map):
    kind = item.get("kind") or item.get("source") or "unknown"
    ref = str(item.get("ref") or item.get("id") or "")
    source = "unknown"
    identity = {}
    text = ""
    time_raw = None
    time_field = None
    verifiable = True
    notes = []

    if kind in ("dingtalk_message", "message", "dingtalk"):
        source = "dingtalk"
        mid = item.get("message_id") or item.get("messageId") or item.get("msg_id")
        group = item.get("group") or item.get("conversation_name") or ""
        cid = item.get("conversation_id") or item.get("conversationId")
        if cid:
            notes.append("conversation_id_from_input")
        elif conversation_map.get(group):
            cid = conversation_map.get(group)
            notes.append("conversation_id_from_mapping")
        text = norm_text(item.get("text") or item.get("content") or item.get("full_text"))
        time_raw = item.get("time") or item.get("send_time") or item.get("create_time")
        time_field = "time"
        identity = {"conversation_id": cid, "message_id": mid, "group": group}
        if not mid:
            notes.append("missing_message_id")
        if not cid:
            notes.append("missing_conversation_id")
        if mid and isinstance(item.get("sender"), str) and item.get("sender") == mid:
            notes.append("sender_equals_message_id")
        source_key = "dingtalk:%s:%s" % (cid, mid) if (cid and mid) else None

    elif kind in ("git_commit", "commit"):
        source = "gitlab"
        sha = item.get("sha") or item.get("id")
        project = item.get("project_id") or item.get("repo") or item.get("project")
        text = "\n".join([norm_text(item.get("subject")), norm_text(item.get("body"))]).strip()
        time_raw = item.get("CommitDate") or item.get("committed_date") or item.get("time")
        time_field = "CommitDate"
        identity = {"project": project, "sha": sha, "parents": item.get("parents") or []}
        if not sha:
            notes.append("missing_sha")
        if item.get("project_id") is None:
            notes.append("project_scope_is_repo_name")
        source_key = "gitlab:%s:%s" % (project, sha) if (project and sha) else None

    elif kind in ("git_mr", "mr", "merge_request"):
        source = "gitlab"
        iid = item.get("iid") or item.get("mr_iid")
        project = item.get("project_id") or item.get("repo") or item.get("project")
        text = "\n".join([norm_text(item.get("title")), norm_text(item.get("description") or item.get("body"))]).strip()
        time_raw = item.get("created_at") or item.get("time")
        time_field = "created_at"
        identity = {"project": project, "iid": iid}
        source_key = "gitlab:%s:mr:%s" % (project, iid) if (project and iid) else None

    elif kind in ("zentao_bug", "zentao"):
        source = "zentao"
        bug_id = item.get("bug_id") or item.get("id")
        instance = item.get("instance") or "zentao-main"
        snapshot = item.get("snapshot") or {}
        text = norm_text(snapshot) if snapshot else norm_text(item.get("title") or item.get("steps"))
        time_raw = snapshot.get("openedDate") or item.get("opened_at") or item.get("time")
        time_field = "snapshot.openedDate"
        identity = {"instance": instance, "bug_id": str(bug_id) if bug_id is not None else None}
        if not bug_id:
            notes.append("missing_bug_id")
        source_key = "zentao:%s:%s" % (instance, bug_id) if bug_id is not None else None

    elif kind == "synthetic_event":
        source = "synthetic"
        text = norm_text(item.get("content"))
        time_raw = item.get("time")
        time_field = "time"
        identity = {"case_id": case_id, "ref": ref}
        verifiable = False
        source_key = "synthetic:%s:%s" % (case_id, ref)

    else:
        source = "file"
        text = norm_text(item.get("text") or item.get("content") or item)
        time_raw = item.get("time")
        time_field = "time"
        identity = {"case_id": case_id, "ref": ref}
        verifiable = False
        source_key = "file:%s:%s" % (case_id, ref)

    iso, precision, terr = parse_time(time_raw)
    if terr:
        notes.append(terr)
    sender, sender_quality = extract_sender(item.get("sender"), time_raw)
    if sender_quality == "declared" and identity.get("message_id") and sender == identity.get("message_id"):
        sender_quality = "invalid_equals_message_id"

    # V0.1.7：附件引用原样保留（resource_refs），不推断、不补造附件内容
    resource_refs = item.get("resource_refs")
    if resource_refs is None:
        resource_refs = item.get("resourceRefs")
    if resource_refs is None:
        resource_refs = []
    if not isinstance(resource_refs, list):
        resource_refs = [resource_refs]
    if resource_refs:
        notes.append("attachment_refs_present")
    if ATTACH_REF_RE.search(text):
        notes.append("attachment_ref_in_text")

    return {
        "case_ids": [case_id],
        "refs": [ref],
        "source": source,
        "source_key": source_key,
        "identity": identity,
        "text": text,
        "content_sha256": sha256_text(text),
        "source_time_raw": time_raw,
        "source_time_iso": iso,
        "time_precision": precision,
        "time_source_field": time_field,
        "sender": sender,
        "sender_quality": sender_quality,
        "resource_refs": resource_refs,
        "verifiable": verifiable,
        "notes": sorted(set(notes)),
    }


def load_records(args, conversation_map):
    records = []
    if args.test_inputs:
        with open(args.test_inputs, encoding="utf-8") as f:
            data = json.load(f)
        for section in ("real_inputs", "synthetic_inputs"):
            for case in data.get(section, []) or []:
                case_id = case.get("case_id")
                for item in case.get("inputs", []) or []:
                    records.append(build_record(case_id, item, conversation_map))
        return records
    with open(args.records, encoding="utf-8") as f:
        data = json.load(f)
    for item in data.get("records", []) or []:
        case_id = item.get("case_id")
        records.append(build_record(case_id, item, conversation_map))
    return records


def merge_by_source_key(records):
    merged = {}
    order = []
    for r in records:
        sk = r.get("source_key")
        if not sk:
            key = "UNRESOLVED:%s:%s" % (r["case_ids"][0], r["refs"][0])
            r["unresolved_key"] = key
            merged[key] = r
            order.append(key)
            continue
        if sk in merged:
            m = merged[sk]
            for c in r["case_ids"]:
                if c not in m["case_ids"]:
                    m["case_ids"].append(c)
            for ref in r["refs"]:
                if ref not in m["refs"]:
                    m["refs"].append(ref)
            m["notes"] = sorted(set(m["notes"]) | set(r["notes"]))
        else:
            merged[sk] = r
            order.append(sk)
    return [merged[k] for k in order]


def main():
    ap = argparse.ArgumentParser(description="Bug Collector 确定性预处理")
    ap.add_argument("--test-inputs", help="test-inputs-V1.4.json")
    ap.add_argument("--records", help="通用 records.json")
    ap.add_argument("--casebook", help="candidate-cases-V1.4.json（可选，仅用于补充群映射）")
    ap.add_argument("--conversation-map", help='JSON 文件或内联，如 {"数据小队":"cid..."}')
    ap.add_argument("--out", required=True, help="输出目录")
    args = ap.parse_args()
    if not args.test_inputs and not args.records:
        ap.error("必须提供 --test-inputs 或 --records")

    conversation_map = dict(DEFAULT_CONVERSATION_MAP)
    if args.conversation_map:
        raw = args.conversation_map
        if os.path.exists(raw):
            with open(raw, encoding="utf-8") as f:
                conversation_map.update(json.load(f))
        else:
            conversation_map.update(json.loads(raw))

    os.makedirs(args.out, exist_ok=True)
    records = merge_by_source_key(load_records(args, conversation_map))

    scopes = {}
    unresolved = []
    with open(os.path.join(args.out, "records_index.jsonl"), "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
            for c in r["case_ids"]:
                scopes.setdefault(c, []).append(r.get("source_key") or r.get("unresolved_key"))
            if r.get("unresolved_key"):
                unresolved.append(r["unresolved_key"])

    with open(os.path.join(args.out, "case_scopes.json"), "w", encoding="utf-8") as f:
        json.dump(scopes, f, ensure_ascii=False, indent=2, sort_keys=True)

    summary = {
        "generated_at": datetime.now(CST).isoformat(),
        "record_count": len(records),
        "case_count": len(scopes),
        "unresolved_identity_count": len(unresolved),
        "unresolved_keys": unresolved,
        "by_source": {},
        "by_precision": {},
        "sender_quality": {},
        "notes": {},
    }
    for r in records:
        summary["by_source"][r["source"]] = summary["by_source"].get(r["source"], 0) + 1
        summary["by_precision"][r["time_precision"]] = summary["by_precision"].get(r["time_precision"], 0) + 1
        summary["sender_quality"][r["sender_quality"]] = summary["sender_quality"].get(r["sender_quality"], 0) + 1
        for n in r["notes"]:
            summary["notes"][n] = summary["notes"].get(n, 0) + 1
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, sort_keys=True)

    print(json.dumps({"ok": True, "records": len(records), "cases": len(scopes),
                      "unresolved": len(unresolved), "out": os.path.abspath(args.out)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
