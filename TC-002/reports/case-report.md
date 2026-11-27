# 案例报告 TC-002（run-20261126-02 / offline）

- 运行目录：`<offline_root>/run-20261126-02/TC-002/`（offline_root 由执行者选定并已在总结报告披露）
- 案例隔离：本案例只读取自身输入切片生成的 `index/`，未引用其他案例的消息、数字或结论

## 1. 输入与读取

- 输入记录数：1（来源分布：gitlab 1）
- 实际读取证据：1 条（library/evidence.json；全部来自本案例 index 的 source_key）
- 筛选决策分布：candidate 1

## 2. 缺陷与发生

- 已确认缺陷：1；疑似缺陷：0
- 独立发生：0（无）
- 复发（repeat_after_fix + rollback_regress）：0
- 待复核：1

## 3. actual_counts

| 指标 | 值 |
|---|---|
| confirmed_defects | 1 |
| suspect_defects | 0 |
| evidence_items | 1 |
| fix_actions | 1 |
| independent_occurrences | 0 |
| repeat_unresolved_events | 0 |
| recurrence_events | 0 |
| unresolved_open_bugs | 0 |
| related_cases | 0 |
| bugs_without_occurrence | 1 |
| coverage | 输入 1 条（1 个 Merge 提交）；时间精度 seconds；未覆盖：部署与复测记录；未知：环境 |
| recurrence_by_subtype | {"repeat_after_fix": 0, "rollback_regress": 0} |
| verified_environments | "未知（本案例无已验证环境流转）" |

- bug_ids：B01
- evidence_ids：EV01

## 4. 确定性校验

- `bc_validate.py --case-id TC-002`：fail_count=0，warn_count=1，by_code={"TIME-005:WARN": 1}
- TIME-005:WARN：该缺陷在当前案例输入中没有 role=report 的现象报告证据，first_observed_at 只能回退取最早关联证据的 source_time；这是推断时间，不是用户报告时间，需人工补证。

## 5. 身份与时间

- 无法解析身份记录：0（unresolved_identity_count）
- sender_quality 分布：{"missing": 1}
- 索引注记：{"project_scope_is_repo_name": 1}
- source_time 精度分布：{"seconds": 1}

first_observed_at 溯源：

- B01：2026-11-24T09:59:19+08:00（无 role=report 证据，回退取最早关联证据的 source_time（TIME-005））

## 6. 事实锚点

- fact_anchors 总数：1；每条已确认缺陷至少 1 条（疑似缺陷按规则不强制虚构事实锚点）
- 机械校验：quote 为证据原文子串、fact 中数字可在所挂证据中找到支持（ISO-003 fail=0）

## 7. 上下文事件

- context_events：0（无）

## 8. 声明

- 本轮未读取 expected-results-V1.4.json（该文件不在离线测试包内，物理上不可读）；本报告不含任何期望值比对结论。
- 以上仅为确定性校验（格式、口径、隔离、锚点）结果，**不代表功能正确性已验证**；语义判定仍需人工复核。
