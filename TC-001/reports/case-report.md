# 案例报告 TC-001（run-20261126-02 / offline）

- 运行目录：`<offline_root>/run-20261126-02/TC-001/`（offline_root 由执行者选定并已在总结报告披露）
- 案例隔离：本案例只读取自身输入切片生成的 `index/`，未引用其他案例的消息、数字或结论

## 1. 输入与读取

- 输入记录数：2（来源分布：gitlab 2）
- 实际读取证据：0 条（library/evidence.json；全部来自本案例 index 的 source_key）
- 筛选决策分布：noise 1、template 1

## 2. 缺陷与发生

- 已确认缺陷：0；疑似缺陷：0
- 独立发生：0（无）
- 复发（repeat_after_fix + rollback_regress）：0
- 待复核：0

## 3. actual_counts

| 指标 | 值 |
|---|---|
| confirmed_defects | 0 |
| suspect_defects | 0 |
| evidence_items | 0 |
| fix_actions | 0 |
| independent_occurrences | 0 |
| repeat_unresolved_events | 0 |
| recurrence_events | 0 |
| unresolved_open_bugs | 0 |
| related_cases | 0 |
| bugs_without_occurrence | 0 |
| coverage | 输入 2 条（2 个 GitLab 提交）；时间精度 seconds；无钉钉/禅道记录；未覆盖：无；未知：无 |
| recurrence_by_subtype | {"repeat_after_fix": 0, "rollback_regress": 0} |
| verified_environments | "未知（本案例无已验证环境流转）" |

- bug_ids：无
- evidence_ids：无

## 4. 确定性校验

- `bc_validate.py --case-id TC-001`：fail_count=0，warn_count=0，by_code={}
- 本案例无 WARN。

## 5. 身份与时间

- 无法解析身份记录：0（unresolved_identity_count）
- sender_quality 分布：{"missing": 2}
- 索引注记：{"project_scope_is_repo_name": 2}
- source_time 精度分布：{"seconds": 2}

first_observed_at 溯源：


## 6. 事实锚点

- fact_anchors 总数：0；每条已确认缺陷至少 1 条（疑似缺陷按规则不强制虚构事实锚点）
- 机械校验：quote 为证据原文子串、fact 中数字可在所挂证据中找到支持（ISO-003 fail=0）

## 7. 上下文事件

- context_events：1（background 1）

## 8. 声明

- 本轮未读取 expected-results-V1.4.json（该文件不在离线测试包内，物理上不可读）；本报告不含任何期望值比对结论。
- 以上仅为确定性校验（格式、口径、隔离、锚点）结果，**不代表功能正确性已验证**；语义判定仍需人工复核。
