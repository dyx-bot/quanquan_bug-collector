# 案例报告 TC-005（run-20261126-02 / offline）

- 运行目录：`<offline_root>/run-20261126-02/TC-005/`（offline_root 由执行者选定并已在总结报告披露）
- 案例隔离：本案例只读取自身输入切片生成的 `index/`，未引用其他案例的消息、数字或结论

## 1. 输入与读取

- 输入记录数：5（来源分布：gitlab 4、zentao 1）
- 实际读取证据：5 条（library/evidence.json；全部来自本案例 index 的 source_key）
- 筛选决策分布：candidate 2、evidence_only 3

## 2. 缺陷与发生

- 已确认缺陷：1；疑似缺陷：0
- 独立发生：1（first 1）
- 复发（repeat_after_fix + rollback_regress）：0
- 待复核：1

## 3. actual_counts

| 指标 | 值 |
|---|---|
| confirmed_defects | 1 |
| suspect_defects | 0 |
| evidence_items | 5 |
| fix_actions | 3 |
| independent_occurrences | 1 |
| repeat_unresolved_events | 0 |
| recurrence_events | 0 |
| unresolved_open_bugs | 0 |
| related_cases | 0 |
| bugs_without_occurrence | 0 |
| coverage | 输入 5 条（1 个禅道快照、4 个提交）；时间精度 seconds；未覆盖：部署与现场复测；未知：环境 |
| recurrence_by_subtype | {"repeat_after_fix": 0, "rollback_regress": 0} |
| verified_environments | "未知（本案例无已验证环境流转）" |

- bug_ids：B01
- evidence_ids：EV01、EV02、EV03、EV04、EV05

## 4. 确定性校验

- `bc_validate.py --case-id TC-005`：fail_count=0，warn_count=0，by_code={}
- 本案例无 WARN。

## 5. 身份与时间

- 无法解析身份记录：0（unresolved_identity_count）
- sender_quality 分布：{"missing": 5}
- 索引注记：{"project_scope_is_repo_name": 4}
- source_time 精度分布：{"seconds": 5}

first_observed_at 溯源：

- B01：2026-11-17T16:38:07+08:00（取自 role=report 证据 EV01 的最早 source_time）

occurrence.observed_at 均等于所挂证据的 source_time（逐条与 index 核对）：
- OC01 first → 2026-11-17T16:38:07+08:00（证据 EV01）

## 6. 事实锚点

- fact_anchors 总数：3；每条已确认缺陷至少 1 条（疑似缺陷按规则不强制虚构事实锚点）
- 机械校验：quote 为证据原文子串、fact 中数字可在所挂证据中找到支持（ISO-003 fail=0）

## 7. 上下文事件

- context_events：0（无）

## 8. 声明

- 本轮未读取 expected-results-V1.4.json（该文件不在离线测试包内，物理上不可读）；本报告不含任何期望值比对结论。
- 以上仅为确定性校验（格式、口径、隔离、锚点）结果，**不代表功能正确性已验证**；语义判定仍需人工复核。
