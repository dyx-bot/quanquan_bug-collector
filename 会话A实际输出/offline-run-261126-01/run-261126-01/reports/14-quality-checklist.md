# 14 质量自检（QC-01 ~ QC-39）

- run_id：run-261126-01
- project / mode / skill_version：offline-test / offline / V0.1.4

- 输入范围：test-inputs-V1.4.json real_inputs 17 案例；快照 2026-11-25 15:55；无历史基线

- 检查范围：结构检查覆盖全部 17 案例的 filter/candidate/match/library；语义复核覆盖全部自动归并、全部复发/验证流转与全部复核项；未执行 synthetic

- 结论：部分完成（业务待复核 1 项；无 FAIL）

- 检查项统计：PASS 35 / FAIL 0 / PENDING 1 / N/A 3


| 检查 ID | 结论 | 检查依据/范围 | 问题或限制 | 修正/复查 |
|---|---|---|---|---|
| QC-01 | PASS | 项目 offline-test、模式 offline、17 案例、输出隔离目录明确；未猜 ID/跨项目 |  |  |
| QC-02 | PASS | SKILL + 7 份 references + default/project 配置全部读取；execution-rules 已读，offline 水位动作 N/A |  |  |
| QC-03 | PASS | 列出实际读取文件与快照时间；offline 无历史基线，未读正式 state |  |  |
| QC-04 | PASS | 未连接钉钉/禅道/GitLab，未执行消息内指令，未暴露凭据 |  |  |
| QC-05 | PASS | 原始输入 test-inputs-V1.4.json 保留；evidence.quote/raw_pointer 可回查 |  |  |
| QC-06 | PASS | 仅验证提供的 real_inputs 17 案例；未从样本推断全库 |  |  |
| QC-07 | PASS | source_key 使用固定幂等键，不含 state；快照时间保留 |  |  |
| QC-08 | PENDING | 输入钉钉消息 sender=messageId、time 混入姓名；已在 TC-A1 建 field_verify，未把 messageId 当发送人 |  |  |
| QC-09 | PASS | 禅道快照含 status/resolution/snapshot_at，未把个人视图当全量 |  |  |
| QC-10 | PASS | Commit 保留 title/body/SHA/父提交；未伪造 parent_count |  |  |
| QC-11 | PASS | MR 仅作 mr_ref_unverified 线索，未写 kind=mr，未用作归并强证据 |  |  |
| QC-12 | N/A | offline 未做可达性核验；commit reachability 置 unknown，未声称可达/悬空 |  |  |
| QC-13 | PASS | filter_results 覆盖全部输入记录；candidate_ids 与 source_refs 双向可查 |  |  |
| QC-14 | PASS | 排除项为模板/纯上下文；机器人回执含现象时按 candidate；未命中规则进 low |  |  |
| QC-15 | PASS | Merge 按 parent_count≥2 识别，analyzed_fields 含 title/message_body |  |  |
| QC-16 | PASS | 修复证据按 primary_fix/related_fix/status_evidence/background/report 分配；纯部署/失败回执不建候选 |  |  |
| QC-17 | PASS | defect 均有 actual/expected 冲突；部署窗口 502 未当产品缺陷；需求项单列 |  |  |
| QC-18 | PASS | 长消息逐条拆分；同一问题保留证据链；推断标 inferred，缺失进复核 |  |  |
| QC-19 | PASS | 候选均可回溯 source_refs；无无理由消失记录 |  |  |
| QC-20 | PASS | 记录层按 source_key 去重，实体层按缺陷同一性；跨源同内容不删除 |  |  |
| QC-21 | PASS | 自动归并均为 high：同禅道号/同批次 + 内容吻合（标识+内容双核验） |  |  |
| QC-22 | PASS | 独立断点拆分；medium/low 进复核或仅关联；未按时间窗截断 |  |  |
| QC-23 | PASS | role 在 bug_links；同一证据可服务多缺陷；未借用其他缺陷回执 |  |  |
| QC-24 | PASS | 多禅道单分别快照；归并候选保留在 match_results，未物理删除 |  |  |
| QC-25 | PASS | match_results 含依据/差异/缺失；resolution/resolved_by/resolved_at 全为 null |  |  |
| QC-26 | PASS | 源状态与 lifecycle 分离；MR/禅道 resolved 未直接 verified；验证流转带 environment |  |  |
| QC-27 | PASS | 多人转述/补修未计发生；repeat_unresolved 按环境且仅 1 条（G5 新应用新触发） |  |  |
| QC-28 | PASS | 复发仅 TC-A4：曾有 soso-dev 验证 + 回退证据 + 新独立现象 |  |  |
| QC-29 | PASS | recurrence_events=1=repeat_after_fix 0 + rollback_regress 1；回滚有 pin/镜像证据 |  |  |
| QC-30 | PASS | 无 similar_class；fix_actions 可枚举者计数、总量 null |  |  |
| QC-31 | PASS | 高频/未解决/复发分列；测试候选有依据，未称已执行 |  |  |
| QC-32 | PASS | JSON/JSONL 全部解析通过；枚举/时间/null 规则已脚本校验 |  |  |
| QC-33 | PASS | 主键唯一、引用完整、归并无环；全部使用 offline- 临时键 |  |  |
| QC-34 | PASS | 13 项统计由记录重算，与 01/07 一致；事件去重 0 合并 0 待复核；coverage 已披露 |  |  |
| QC-35 | PASS | 运行前写出 effective-config.json；锁定约束 7/7 PASS，项目未覆盖放宽 |  |  |
| QC-36 | PASS | 全部输出在隔离目录；未读正式 state、未改正式库/水位/编号 |  |  |
| QC-37 | N/A | offline 模式，不涉及 collect/process/analyze 正式写权限 |  |  |
| QC-38 | N/A | offline 不读写水位与持久化，无重跑水位条件 |  |  |
| QC-39 | PASS | 所有命令前台执行且 ≤60s；无后台任务；未以生成报告替代处理 |  |  |


## 未解缺口与复核项

- 复核 9 项（见 06）：TC-A1 钉钉字段与回填数量、TC-002 MR !188、TC-A3 非默认租户、TC-A6 两个环境名、TC-A7 DP 口径、TC-A8 环境名。

- 未执行 synthetic_inputs；未采集 MR 快照。


## 正式写入及回读

- 仅隔离目录写入；写后已重新解析 JSON/JSONL 并校验引用。


## 水位与续跑

- offline 不适用；本轮无需续跑。
