# Bug Collector Skill 测试案例集（候选）V1.4

> 版本：V1.4 候选稿（2026-11-26）　模式：offline（不写正式案例库/水位/永久编号）
> 基线：candidate-cases-V1.3.json（真实证据与案例编号原样保留）
> 依据：Bug Collector Skill V0.1.3 七份核心规则 + references/execution-rules.md + config/default.json + CHANGELOG-V0.1.3 + 一致性检查结果-V0.1.3 + 测试案例同步建议-V0.1.3 + 测试案例同步修改清单-V0.1.2

**本文件是候选案例集，不是已执行、已人工核实的参考答案。** 原始输入为真实、可回查的证据（synthetic 案例除外），但“预期结果”各项是按规则推导的候选参考答案，需人工确认后才能作为判分基准；“实际输出/测试结果/失败原因”本轮未执行，统一标为“待执行”。

## 1. 本版改了什么（摘要）

1. 补齐 V1.3 未执行的 V0.1.2 同步项：`filter_decision=excluded` → `template/sync`；`repeat_unresolved_events` 1→0（TC-008 不建 occurrence）；`reopen_recurrence`/`fix_not_live`/`deployment_drift`/`similar_but_distinct` 退出 `occurrence.kind`；`role` 归一为五值。
2. 按 V0.1.3 新增断言：分环境验证与 canonical_name 归一（§2.6/§10.5）、同分类不同环境独立性（TC-R4）、事件去重（§3.8，TC-R6）、归并 occurrence 只迁移不重判（dedup §4.3，TC-R7）、回滚重现（§2.4，TC-R5）、修复未生效/已部署未验证分支（TC-A3/A4/R2）、offline 隔离与临时编号（TC-R8）。
3. 每个案例新增 `rule_refs`；每条新增/修改断言新增 `rule`（规则文件+章节）；新增 12 条全局断言 G-01~G-12。
4. `expected_counts` 按 §3.7 补齐十项指标：confirmed/suspect/evidence/fix_actions/independent_occurrences/repeat_unresolved_events/unresolved_open_bugs/recurrence_events/recurrence_by_subtype/related_cases/bugs_without_occurrence/verified_environments/coverage。
5. 新增 5 条 synthetic：TC-R4~R8；真实案例与证据引用保持不变（real_inputs 与 V1.3 逐条一致）。
6. 规则本身的矛盾与无法形成确定预期的点，另见《规则问题与待确认清单-V1.4-20261126.md》。

## 2. 判分口径

- 判分以 `assertions` 为最小单元（pass / fail / na）；`meta.global_assertions` 对所有案例共同生效，不重复计入各案例断言数。
- `expected_*` 是整体参考，不是唯一答案；`expected_counts` 十项指标必须分列，不得互相替代。
- 未标注 `rule` 的断言沿用其原有依据（V1.4 未改动）；新增/修改断言均标 `rule`。

## 3. 计数指标字典（recurrence-rules §3.7）

| 字段 | 名称 | 口径 |
|---|---|---|
| `confirmed_defects` | 已确认缺陷数量 | 有缺陷记录锚点（禅道单/群内明确报告含预期偏差）且证据充分的缺陷条数 |
| `suspect_defects` | 疑似缺陷数量 | 现象存在但证据不足以确认的候选条数；不得计入 confirmed；可为 null（未定性） |
| `evidence_items` | 证据数量 | 本案例输入证据的条数（按 ref 计；一条消息/一次提交/一张快照各记 1） |
| `fix_actions` | 修复动作次数（可选指标） | 可逐条枚举的独立处置次数；同一动作的多轮提交算 1；同一 MR 修多缺陷各记 1；无法确认写 null 并注明；不得用轮数/MR 数/Commit 数推算（recurrence-rules §3.6） |
| `independent_occurrences` | 独立发生次数 | first + repeat_unresolved + repeat_after_fix + rollback_regress 的有效 occurrence 记录数（事件去重后，recurrence-rules §3.1） |
| `repeat_unresolved_events` | 持续未解决期间的再次发生事件数 | kind=repeat_unresolved 的记录数；仅在未解决期间出现新的独立触发/异常证据时登记，不按缺陷固定计 1（§2.2/§3.3） |
| `unresolved_open_bugs` | 未解决状态缺陷数 | lifecycle 为 open/fixing 的缺陷数，用于表达持续未解决（§3.7） |
| `recurrence_events` | 广义复发次数 | repeat_after_fix 条数 + rollback_regress 条数（§3.2） |
| `recurrence_by_subtype` | 复发子类型分布 | {repeat_after_fix, rollback_regress} 分项计数，必须与总数同时给出（§3.2） |
| `related_cases` | 同类关联数 | bugs.related[].kind=similar_class 的条数；same_incident/caused_by 不计入本指标，也不计复发（§3.4/§3.7） |
| `bugs_without_occurrence` | 无发生记录缺陷数 | 有缺陷主记录但无有效 occurrence 的缺陷数；不得用缺陷数反推发生数（§3.1） |
| `verified_environments` | 验证适用环境 | 由 verified_fixed/closed 流转行及其证据可确认的 canonical_name 去重集合；全无可归一环境时报『未知/未披露』，不得写 0（§2.6/§3.7） |
| `coverage` | 统计覆盖范围 | 时间窗、来源、批次、时间精度覆盖、未覆盖部分与未知数量（§3.7/§3.8） |

## 4. 全局断言（所有案例共同适用）

| ID | 阶段 | 检查项 | 规则 |
|---|---|---|---|
| G-01 | schema | 所有 occurrence.kind ∈ {first, repeat_unresolved, repeat_after_fix, rollback_regress}；无 reopen_recurrence / fix_not_live / deployment_drift / similar_but_distinct / related_case | output-schema §10.2；recurrence-rules §2 |
| G-02 | schema | 所有 filter_decision ∈ {candidate, evidence_only, template, sync, noise}；不使用 excluded | output-schema §10.2；filtering-rules §3.1 |
| G-03 | schema | 所有 bug_links.role ∈ {primary_fix, related_fix, background, status_evidence, report}；旧词（related/root_cause/failed_delivery/second_fix/origin）不得作 role | output-schema §4、§10.2 |
| G-04 | schema | 描述标签（fix_not_live / fix_not_effective / deployment_drift / mr_ref_unverified / context_only）只出现在 reason/basis/review.reason/报告，不写入枚举字段 | output-schema §10.2.1 |
| G-05 | count | 每个案例的 expected_counts 十项指标齐全；null/未知已注明原因，未用 0 冒充未知 | recurrence-rules §3.7；output-schema §9 第 13 项 |
| G-06 | count | recurrence_events 与 recurrence_by_subtype 同时给出，且总数 == 两子类型之和 | recurrence-rules §3.2 |
| G-07 | integrity | verified_environments 只统计可归一 canonical_name；无从归一时报『未知/未披露』，不写 0、不外推同分类其他环境 | recurrence-rules §2.6/§3.7；output-schema §10.5 |
| G-08 | integrity | 报告同时披露 coverage（时间窗/来源/时间精度/未覆盖/未知数量）与事件去重已合并组数、待复核数 | recurrence-rules §3.8；output-schema §9 |
| G-09 | integrity | 派生统计可由 occurrences/bugs/transitions 重算并与运行概览逐项对上；不只给结论数字 | output-schema §9；execution-rules §8 |
| G-10 | integrity | offline 运行不写正式 data/<project>/、不改水位、不分配 DC-/EV-/OC-/RV-/TR- 正式编号，使用 offline-<run_id>- 临时键 | output-schema §1.2/§1.3；execution-rules §5/§9 |
| G-11 | filter | 未核实的 MR 引用只作待核查线索（mr_ref_unverified），不写成 kind=mr 证据、不作归并强证据 | output-schema §4、§10.2.1 |
| G-12 | integrity | 运行声明的 skill_version 与规则文件版本头一致（V0.1.3）；项目配置含 __TBD__ 时按不完整配置处理，不把占位当真实参数 | SKILL.md §2；config/default.json meta；execution-rules §4 |

## 5. 合成案例策略

TC-R1/R2/R3 为构造边界案例（synthetic=true），存放于 cases_synthetic 与 test-inputs.synthetic_inputs，不得与真实案例混评。

## 6. 真实案例（17 条）

### TC-001　数据清洗

- **类型**：real（真实证据）
- **输入摘要**：E1 d631b389「test commit dc-api」（body 空）；E2 84cf120b「调整 runtime/storage 的插入位置，保证与 develop@122e700 可无冲突合并」（body 明示『文件内容与上一提交一致，只调整了 diff 落点』）。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证『纯同步/合并落点调整/空 body 测试提交』不被计为缺陷，且排除理由可回查。 |
| 预期缺陷数 | 0 |
| 预期筛选 | 两条均按非候选处理：E1 filter_decision=template（triage_reason=template_noise），E2 filter_decision=sync（triage_reason=context_only，合并落点准备）；保留排除理由，可重查，不得使用 excluded。 |
| 预期归并 | 无（不进入缺陷库）。 |
| 预期证据归属 | 不作为任何缺陷的证据。 |
| 预期复发定性 | 无。 |
| 判定依据 | 两条都没有『实际现象 vs 预期』的不一致：E1 body 为空且是测试提交；E2 自述内容与上一提交一致、仅调整 diff 落点，不产生新行为。 |
| 否定项 | 不得把 E2 的『合并』字样误判为 Merge 缺陷；不得因 E1 无内容就臆造缺陷；纯噪声也要写排除理由而非静默丢弃。 |
| 计数（十项） | {"confirmed_defects": 0, "suspect_defects": 0, "evidence_items": 2, "fix_actions": 0, "independent_occurrences": 0, "recurrence_events": 0, "repeat_unresolved_events": 0, "unresolved_open_bugs": 0, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-11-13~11-18；来源 gitlab（2 条提交）；时间精度：秒级；未覆盖：无（纯排除案例）；未知：无", "non_candidate_records": 2} |
| 规则引用 | references/filtering-rules.md §3.1；references/output-schema.md §10.2/§10.2.1 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-001-1 | filter | 两条输入的 filter_decision 分别取 template（E1）/ sync（E2），均不得使用 excluded | true | output-schema §10.2；filtering-rules §3.1；V0.1.2 同步清单 G-5 |
| TC-001-2 | filter | E1 triage_reason == template_noise | true | output-schema §10.2.1 |
| TC-001-3 | filter | E2 triage_reason == context_only（合并落点准备，作上下文保留） | true | output-schema §10.2.1 |
| TC-001-4 | count | confirmed_defects == 0 且 suspect_defects == 0 | true |  |
| TC-001-5 | integrity | 每条排除记录都带 triage_reason（无静默丢弃） | true |  |
| TC-001-6 | negative | E2 的『合并』字样未被误读为 Merge commit 缺陷 | true |  |
| TC-001-7 | schema | occurrence.kind 为空（0 缺陷）；expected_counts 十项指标齐全并把不适用项标 0/— | true | output-schema §10.2；recurrence-rules §3.7 |

### TC-002　Commit 筛选

- **类型**：real（真实证据）
- **输入摘要**：E3 27da39f3，父提交=2；subject=「Merge branch 'fix/dc-onto-token-refresh-20261124' into 'develop'」；body 首行=「fix(dc): 本体 token 过期自动重登，修复 /api/dc/onto/scenes 502（HTTP 401）」+「See merge request …!188」。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证 Merge commit（subject 是纯合并模板）正文里的独有 Bug 信息被提取，不被当纯合并排除。 |
| 预期缺陷数 | 1（本体 token 过期未自动重登导致 scenes 接口 502/401 的缺陷） |
| 预期筛选 | 不因 subject 是纯 Merge 直接排除；识别父提交=2 为 Merge；提取 body 中的 fix 描述进入语义分析；不因『已 merge』直接判『已修复上线』。 |
| 预期归并 | 若禅道/群聊有同现象记录应归并（本轮该缺陷仅此 GitLab 证据）。 |
| 预期证据归属 | 27da39f3 与该 MR!188 均作为该缺陷的 primary_fix 证据（同一修复的两条来源，记录层不重复建号）。 |
| 预期复发定性 | 无。 |
| 判定依据 | 父提交数量=2 即 Merge；body 含『token 过期/502/401』独有业务描述，区别于纯合并同步。 |
| 否定项 | ①是否直接排除 Merge=否；②是否提取正文=是；③是否直接认定已修复上线=否（合并≠部署复验）；④是否编造具体异常=否。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 1, "fix_actions": 1, "independent_occurrences": 1, "recurrence_events": 0, "repeat_unresolved_events": 0, "unresolved_open_bugs": 0, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-11-20~11-24；来源 gitlab+zentao；时间精度：秒级；未覆盖：部署与复验证据；未知：环境身份"} |
| 规则引用 | references/recurrence-rules.md §2.1；references/output-schema.md §4/§8 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-002-1 | filter | 27da39f3 被识别为 Merge commit（parent_count >= 2） | true |  |
| TC-002-2 | filter | body 缺陷描述（token 过期未自动重登 → /api/dc/onto/scenes 502 HTTP 401）被提取为缺陷候选，未因『纯合并』排除 | true |  |
| TC-002-3 | count | confirmed_defects == 1 | true |  |
| TC-002-4 | integrity | 输出缺陷的现象集合仅包含 body 原文所列内容（无编造细节） | true |  |
| TC-002-5 | attribution | 27da39f3 与 MR !188 均挂到同一缺陷上（bug_links 2 条，记录层不重复建号） | true |  |
| TC-002-6 | recurrence | 『已修复上线』判定 == false（无部署/复验证据） | true |  |
| TC-002-7 | negative | 『已 merge』未被直接当作『已修复且已上线』 | true |  |
| TC-002-8 | recurrence | 输出 occurrence.kind == first（本缺陷唯一一次可核验发生） | true | recurrence-rules §2.1 |
| TC-002-9 | schema | bug_links.role 只取 primary_fix / status_evidence；不得用 root_cause、failed_delivery 等旧词 | true | output-schema §4/§10.2 |

### TC-003　Commit 筛选

- **类型**：real（真实证据）
- **输入摘要**：E4 da00120f，subject=「feat(dc): 全站视觉美化·澄蓝精工方向（方向A选定…）」；body 第 2 条=「修复存量 bug：--muted-foreground 原为 18% 深灰（近黑），改回 46%」。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证以 feat 前缀提交中隐藏的『修复存量 bug』子句被单独识别为缺陷候选，不被 feat 语义吞掉。 |
| 预期缺陷数 | 1（前景色 token 过暗导致对比度/可读性不足的缺陷） |
| 预期筛选 | 不从 feat 前缀直接判为非缺陷而跳过；从 body 抽出『修复存量 bug』子句作为独立缺陷候选；视觉美化主体与新缺陷分离，不把整站改版算缺陷。 |
| 预期归并 | 无（独立小缺陷）。 |
| 预期证据归属 | da00120f 对该缺陷 role=primary_fix；视觉美化其余内容为背景，不并入缺陷。 |
| 预期复发定性 | 无。 |
| 判定依据 | body 显式写明『修复存量 bug』并给出原值 18%/目标 46%，是现象+预期可判定的修复。 |
| 否定项 | 不得把整个 feat 当缺陷；不得漏掉隐藏修复；不得把『方向A选定』等设计决策当 Bug。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 1, "fix_actions": 1, "independent_occurrences": 1, "recurrence_events": 0, "repeat_unresolved_events": 0, "unresolved_open_bugs": 0, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-11-19~11-24；来源 gitlab；时间精度：秒级；未覆盖：部署与复验证据；未知：环境身份"} |
| 规则引用 | references/recurrence-rules.md §2.1；references/filtering-rules.md §3.1 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-003-1 | filter | feat 前缀未导致提交被跳过 | true |  |
| TC-003-2 | filter | 『修复存量 bug：--muted-foreground 18%→46%』子句被识别为独立缺陷候选 | true |  |
| TC-003-3 | count | confirmed_defects == 1 | true |  |
| TC-003-4 | filter | 视觉美化主体未被计为缺陷（background） | true |  |
| TC-003-5 | attribution | da00120f 对该缺陷 role == primary_fix | true |  |
| TC-003-6 | negative | 隐藏修复未被漏报（输出缺陷数 >= 1） | true |  |
| TC-003-7 | recurrence | occurrence.kind == first；『隐藏修复』仍按首次发生登记 | true | recurrence-rules §2.1 |

### TC-004　Commit 筛选

- **类型**：real（真实证据）
- **输入摘要**：E5 2c70dbdb，title=「表格切片修复：分隔行识别、真实表头继承、空壳行与<br>清理、禁表格上下文拼接（禅道 #14686）」，单父提交，无常规前缀；对应 Z-14686（resolved/fixed）。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证无 feat/fix 前缀的中文描述型修复提交被识别为修复，并据禅道编号与内容与既有缺陷归并。 |
| 预期缺陷数 | 1 |
| 预期筛选 | 不因无 feat/fix 前缀当作无关/需求；标题含『修复』+ 现象清单 +『禅道 #14686』→ 识别为缺陷修复。 |
| 预期归并 | 与禅道 #14686 归并为同一缺陷（high：编号锚定 + 内容吻合『表格切片/多余信息』）。 |
| 预期证据归属 | 2c70dbdb role=primary_fix；#14686 作为 source_status.zentao 快照（resolved/fixed）。 |
| 预期复发定性 | 无。 |
| 判定依据 | 标题显式『修复』『禅道 #14686』，正文逐条对应现象；禅道 #14686 标题与现象一致。 |
| 否定项 | 不得因无前缀漏提；不得新建与 #14686 重复的『独立表格缺陷』；归并须编号+内容双核验。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 2, "fix_actions": 1, "independent_occurrences": 1, "recurrence_events": 0, "repeat_unresolved_events": 0, "unresolved_open_bugs": 0, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-11-18~11-25；来源 gitlab+zentao（#14686 resolved 快照）；时间精度：秒级；未覆盖：复验记录；未知：环境身份"} |
| 规则引用 | references/output-schema.md §4/§8；references/recurrence-rules.md §2.1 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-004-1 | filter | 无 feat/fix 前缀的中文修复标题被识别为修复（非无关/需求） | true |  |
| TC-004-2 | merge | 归并到禅道 #14686，merge_confidence == high（编号+内容双核验） | true |  |
| TC-004-3 | count | confirmed_defects == 1 且 duplicate_candidates == 0 | true |  |
| TC-004-4 | attribution | 2c70dbdb role == primary_fix；证据带 #14686 状态快照（resolved/fixed） | true |  |
| TC-004-5 | negative | 未新建与 #14686 重复的『独立表格缺陷』 | true |  |
| TC-004-6 | recurrence | occurrence.kind == first；禅道 resolved 只更新 source_status，不推进 lifecycle/不产生第二次发生 | true | output-schema §8；recurrence-rules §2.1 |
| TC-004-7 | attribution | #14686 的状态快照在 bug_links 上 role=status_evidence（不得当作 verified_fixed 的验证证据） | true | output-schema §4/§8 |

### TC-005　跨源去重

- **类型**：real（真实证据）
- **输入摘要**：Z-14686（resolved/fixed，activatedCount=0）＋4 条提交：E5 2c70dbdb（主修）、E6 1388d78（补回归测试）、E7 fd01100（复测反馈：表头继承被非表格块打断时重置）、E8 2ac5f64（naive/md/table/image 多切片器补修）。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证一个缺陷对应多条提交时的正确归并与证据角色分配，且『复测反馈补修』不被误判为复发。 |
| 预期缺陷数 | 1（同一条 #14686） |
| 预期筛选 | 4 条提交全部保留；E6 测试提交 role=status_evidence（回归证据），不作为独立缺陷。 |
| 预期归并 | 全部归并到 #14686；不得因 4 条提交产生 4 个缺陷；不得把『复测反馈』另立新缺陷。 |
| 预期证据归属 | E5=primary_fix；E7、E8=related_fix（复测补修）；E6=related（测试）。同一缺陷多证据、role 记在关联上。 |
| 预期复发定性 | 属同一发生的后续补修，非复发：禅道 activatedCount=0、直接 resolved，无 resolved→reopen 轨迹。 |
| 判定依据 | E5-E8 正文均含 #14686；禅道状态直接 fixed 而非重新激活。 |
| 否定项 | 错并/错拆=否；不得把复测补修当『复发新发生』；不得把回归测试提交当缺陷。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 5, "fix_actions": 4, "independent_occurrences": 1, "recurrence_events": 0, "repeat_unresolved_events": 0, "unresolved_open_bugs": 0, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-11-17~11-25；来源 gitlab（4 条提交）+zentao；时间精度：秒级；未覆盖：复验记录；未知：环境身份", "reason_tag": "followup_unresolved（描述标签，不在枚举字段）"} |
| 规则引用 | references/dedup-rules.md §4.3；references/output-schema.md §4；references/recurrence-rules.md §3/§3.6 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-005-1 | count | confirmed_defects == 1（同一条 #14686） | true |  |
| TC-005-2 | merge | 4 条提交全部归并至 #14686；输出缺陷条数 == 1 | true |  |
| TC-005-3 | count | fix_actions == 4（主修/回归/复测反馈补修/多切片器补修） | 4 |  |
| TC-005-4 | attribution | E5=primary_fix、E6=status_evidence（回归测试提交）、E7=related_fix、E8=related_fix | true | output-schema §4（role 枚举与选择口径） |
| TC-005-5 | count | independent_occurrences == 1（复测反馈不构成新发生） | 1 |  |
| TC-005-6 | recurrence | recurrence_events == 0 且 occurrence.kind 中无 repeat_after_fix / rollback_regress | true | recurrence-rules §2/§3.2 |
| TC-005-7 | negative | 回归测试提交（E6）未被计为缺陷 | true |  |
| TC-005-8 | count | fix_actions == 4 且四条独立处置可逐条枚举；若无法逐条枚举则输出 null 并注明，不得由提交条数推算 | true | recurrence-rules §3.6 |
| TC-005-9 | merge | 归并动作没有顺带改判 kind 或补记复发：4 条证据归并后 occurrence 仍为 1 条 first | true | dedup-rules §4.3 |
| TC-005-10 | count | 统计按主记录聚合，别名不重复计数（confirmed == 1，不是 4） | true | dedup-rules §4.3；recurrence-rules §3 |

### TC-006　问题链拆分

- **类型**：real（真实证据）
- **输入摘要**：三条同处解析流程、均 active 的独立缺陷：Z-15030（乱码探测整份走 DP 无产出、覆盖率虚报 1.0，对应 E9/MR!167『四条修法+覆盖率分母』）、Z-15032（全量重解析沿用旧切片策略，对应 E10/db52528）、Z-15036（容器 OOM P1，对应 E11 三条 feat + d988394）。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证同一业务流程（解析/重解析）中根因不同的多个缺陷被拆分为独立缺陷，而不是按时间/位置批量并为一条。 |
| 预期缺陷数 | 3（各自独立） |
| 预期筛选 | 三条均保留为独立 candidate；不因『都在解析流程/同一天』合并。 |
| 预期归并 | 不合并：现象（乱码误判/切片策略/OOM）、根因、修复 MR 均不同。 |
| 预期证据归属 | Z-15030←E9；Z-15032←E10；Z-15036←E11（多提交=同一缺陷证据链）。 |
| 预期复发定性 | 无（均为首次登记）。 |
| 判定依据 | 三缺陷现象与根因互不相同，仅共享『解析』业务域；各自有独立禅道号与修复分支。 |
| 否定项 | 不得把『解析一波问题』归为 1 个；也不得把同一缺陷的多条修复拆成多缺陷（与 TC-007 反向校验）。 |
| 计数（十项） | {"confirmed_defects": 3, "suspect_defects": 0, "evidence_items": 6, "fix_actions": 3, "independent_occurrences": 3, "recurrence_events": 0, "repeat_unresolved_events": 0, "unresolved_open_bugs": 3, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-11-20~11-25；来源 gitlab+zentao（3 张 active 快照）；时间精度：秒级；未覆盖：闭环状态与复验；未知：环境身份"} |
| 规则引用 | references/recurrence-rules.md §2.1/§3.4/§3.7；references/dedup-rules.md §5 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-006-1 | count | confirmed_defects == 3 | 3 |  |
| TC-006-2 | merge | merge_groups == 3（三缺陷互不归并） | 3 |  |
| TC-006-3 | attribution | E9→#15030、E10→#15032、E11→#15036 映射正确 | true |  |
| TC-006-4 | filter | 三条缺陷候选均保留（无被过滤丢弃） | true |  |
| TC-006-5 | negative | 未按『同在解析流程/同一天』批量归并为 1 条 | true |  |
| TC-006-6 | recurrence | 三条 occurrence.kind 均为 first；互不生成对方 occurrence、互不增加 recurrence_events | true | recurrence-rules §2.1/§3.4 |
| TC-006-7 | count | same_incident/caused_by 关联不计入 related_cases（该指标只统计 similar_class） | true | recurrence-rules §3.4/§3.7 |

### TC-007　证据归属

- **类型**：real（真实证据）
- **输入摘要**：E12 71bc6835 / MR!163 body=「解析路由质检整改一批（文本层兜底/乱码探测/表格结构/切片页码/入库拆账）」（列明 5 类问题域）；对照 E9 534ac0c / MR!167 body=「15030 乱码误判四条修法 + 覆盖率分母」（同一 #15030 的四条修法）。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证『一个 MR 覆盖多类问题』与『一个缺陷多条修法』两种情形的证据归属区分，role 定义在缺陷⇄证据关联上。 |
| 预期缺陷数 | MR!167：1（#15030，MR 正文编号锚定）。MR!163：不强制规定缺陷数量——正文虽列 5 个问题域（文本层兜底/乱码探测/表格结构/切片页码/入库拆账），但输入没有各域的独立现象证据；正确输出是把 5 个域各登记为候选域且互不自动归并、互不自动确认，缺陷数量字段输出 undetermined（或各域标 unconfirmed）；已带锚点的域（如乱码探测域与 #15030 对账）可确认归并或保留独立，歧义进人工复核。 |
| 预期筛选 | 均保留；不把一批整改整体当单一缺陷，也不把同一缺陷的多条修法拆成多缺陷；MR!163 的 5 问题域各自成候选（unconfirmed），证据不足的域不强制确认数量。 |
| 预期归并 | MR!163 与多个缺陷多对多关联；MR!167 仅关联 #15030。 |
| 预期证据归属 | 同一 MR 对不同缺陷可承担不同 role（如对乱码探测=primary_fix，对表格结构=related_fix）；role 记在 bug_links 而非证据本体。 |
| 预期复发定性 | 无。 |
| 判定依据 | MR!163 标题并列 5 个不同问题域（非同一现象的四条修法）；MR!167 四条修法同属 #15030。 |
| 否定项 | 不得『一 MR 只登记 1 缺陷』漏提；不得把同 bug 的多条修法拆成多 bug（错拆）；role 不得写成证据固有属性。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": null, "evidence_items": 2, "fix_actions": 2, "independent_occurrences": null, "recurrence_events": 0, "suspect_range": [1, 4], "quantity_policy": "undetermined_until_evidence", "repeat_unresolved_events": 0, "unresolved_open_bugs": 1, "related_cases": 0, "bugs_without_occurrence": 1, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-11-20~11-25；来源 gitlab（MR!167/!163 正文）；时间精度：秒级；未覆盖：5 个问题域各自的独立现象证据；未知：域数量（1~4 待定）"} |
| 规则引用 | references/recurrence-rules.md §2.2/§3.1；references/output-schema.md §10.2.2 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-007-1 | count | MR!167 关联 #15030 → confirmed_defects == 1 | true |  |
| TC-007-2 | count | MR!163 域数量字段为 undetermined 或各域 unconfirmed（未输出 2~5 的确定条数） | true |  |
| TC-007-3 | filter | MR!163 的 5 个问题域各自登记为候选（既未并为 1 条缺陷、也未漏域） | true |  |
| TC-007-4 | count | 无锚点域的 confirmed 计数 == 0（证据不足不确认） | 0 |  |
| TC-007-5 | attribution | role 记在 bug_links（缺陷⇄证据关联）上，同一 MR 对不同缺陷可承担不同 role | true |  |
| TC-007-6 | merge | MR!167 仅关联 #15030 | true |  |
| TC-007-7 | negative | #15030 的四条修法未被拆成 4 个缺陷 | true |  |
| TC-007-8 | recurrence | 无锚定的问题域不生成 occurrence；bugs_without_occurrence ≥ 1 或按域标注未确认，不虚构发生 | true | recurrence-rules §2.2/§3.1 |
| TC-007-9 | schema | match_result 与 category 分列输出，不把筛选/匹配/语义分类的阶段枚举互相顶替 | true | output-schema §10.2.2 |

### TC-008　复发识别

- **类型**：real（真实证据）
- **输入摘要**：Z-15048（active，pri1，opened 温晓宇 2026-11-23 15:40，activatedCount=0，从未 resolved）＋E13：MR!185「标题噪声收紧…（#15048 跟进）」、MR!186「标题噪声收紧二轮…（#15048 跟进）」。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证『原缺陷一直未解决/反复跟进补修』不被判为『已修复后再次发生的复发』，未 resolved 不得报已解决。 |
| 预期缺陷数 | 1（#15048） |
| 预期筛选 | 保留；MR!185/!186 标 related_fix（跟进补修）。 |
| 预期归并 | 并入 #15048。 |
| 预期证据归属 | MR!185/!186 对 #15048 role=related_fix；两轮跟进均属同一缺陷的持续处理；独立发生次数保持 1。 |
| 预期复发定性 | 定性为『原缺陷一直未彻底解决、反复补修』（lifecycle=open，未到 verified_fixed）：未解决期间没有出现新的独立触发/异常证据（只有两轮跟进 MR），因此不登记 occurrence、repeat_unresolved_events=0；该状态由 lifecycle 与流转记录表达。“fix_not_live”“持续未解决”只作描述，不写进 occurrence.kind。未来若 reopened 且有新现象/时间/环境证据，才可按 §2.2 判 repeat_unresolved。 |
| 判定依据 | 禅道 status=active、从未 resolved、activatedCount=0；两条 MR 标题均为『跟进』，缺部署/复验证据。 |
| 否定项 | 不得因『修了两次』就报『复发新发生』；不得因 MR 合并就判『已修复上线』；不得把两轮跟进当两个独立缺陷。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 3, "fix_actions": null, "independent_occurrences": 1, "recurrence_events": 0, "repeat_unresolved_events": 0, "unresolved_open_bugs": 1, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-11-23~11-25；来源 zentao（active，activatedCount=0）+gitlab（MR!185/!186）；时间精度：秒级；未覆盖：部署与复验证据；未知：无"} |
| 规则引用 | references/recurrence-rules.md §2.2/§3.3/§3.6；references/output-schema.md §10.2.1 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-008-1 | count | confirmed_defects == 1 且 evidence_items == 3 | true |  |
| TC-008-2 | count | fix_actions 为 null 或 2（2 须逐条说明独立处置）；不得由两轮 MR 数直接推算 | "null 或 2（2 须逐条给依据）" | recurrence-rules §3.6 |
| TC-008-3 | count | recurrence_events == 0 且 repeat_unresolved_events == 0 且 unresolved_open_bugs == 1 | true | recurrence-rules §2.2/§3.3/§3.7 |
| TC-008-4 | recurrence | occurrence.kind 中不含 repeat_unresolved（无新独立证据不建发生） | true | recurrence-rules §2.2 |
| TC-008-5 | recurrence | 『已解决』判定 == false（禅道快照 status == active） | true |  |
| TC-008-6 | attribution | MR!185/!186 对 #15048 role 均为 related_fix | true |  |
| TC-008-7 | negative | 未据两轮 MR 生成 2 条 repeat_unresolved/复发事件；MR 合并未被判『已修复上线』 | true |  |
| TC-008-8 | integrity | coverage 写明时间精度（禅道快照/提交为秒级）与未覆盖项（部署与复验证据缺失）；不得把未解决写成已解决 | true | recurrence-rules §3.7/§3.8 |

### TC-009　信息完整性

- **类型**：real（真实证据）
- **输入摘要**：E14 8e05cad，subject=「feat(dc): 云端解析接入（华为 Aura sidecar）——独立分支，默认不启用」；body 明示『明确未验证：Aura 真机端点（无凭证）、OCR（交付包目录缺失）』。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证证据不足/状态不明时进入低优先级待复核、不臆造缺陷与验证结论。 |
| 预期缺陷数 | 0（或至多 1 条 suspect，且不确认） |
| 预期筛选 | 标 candidate + priority=low / triage_reason=insufficient_evidence，或归入『需求/变更』类而非缺陷；状态字段标 unknown 并进 review.fields_unverified。 |
| 预期归并 | 无。 |
| 预期证据归属 | 8e05cad 仅作 background，不升级为已确认缺陷证据。 |
| 预期复发定性 | 无。 |
| 判定依据 | body 明示『默认不启用』『明确未验证 Aura 真机/OCR』，无『实际现象 vs 预期』的不一致，也无复现证据；不足以判缺陷。 |
| 否定项 | 不得把『未验证』当『已知问题』；不得编造验证结果或附件；缺陷数量与状态不得硬填确定值。 |
| 计数（十项） | {"confirmed_defects": 0, "suspect_defects": null, "evidence_items": 1, "fix_actions": 0, "independent_occurrences": 0, "recurrence_events": 0, "suspect_max": 1, "repeat_unresolved_events": 0, "unresolved_open_bugs": 0, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-11-24~11-25；来源 gitlab（1 条提交）；时间精度：秒级；未覆盖：真机端点与 OCR 交付包；未知：是否成立（0~1 suspect）"} |
| 规则引用 | references/recurrence-rules.md §3.1/§3.7；references/filtering-rules.md §3.1 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-009-1 | count | confirmed_defects == 0 | 0 |  |
| TC-009-2 | count | suspect 输出 ≤ 1 且状态 unconfirmed（0~1 区间，禁止 confirmed） | true |  |
| TC-009-3 | filter | triage_reason == insufficient_evidence（或归类为需求/变更而非缺陷） | true |  |
| TC-009-4 | filter | priority == low（或进入未确认复核池） | true |  |
| TC-009-5 | integrity | 『未验证』项登记到 fields_unverified，条目 == 2（Aura 真机端点、OCR 交付包目录） | 2 |  |
| TC-009-6 | negative | 未编造验证结果；缺失附件/资料未被补造 | true |  |
| TC-009-7 | integrity | 未确认候选不建 occurrence；coverage 指明证据缺口，不把 0 发生写成不存在 | true | recurrence-rules §3.1/§3.7 |

### TC-A1　群聊提取

- **类型**：real（真实证据）
- **输入摘要**：「数据小队」群（cidxs5TpPs34DWnKqMsf+WrEw==）2026-11-19 09:16–17:45：G12 陈昔报「原文有标题，切片无章节标题」+图片 → G13 小圈圈初判（table 切片器未写 title，server.py:6306/6353）→ G14/G15 Audrey「我在改 es，稍等」→「改完了」 → G16 陈昔「重新基于环境现在的情况，排查一下原因」 → G17 小圈圈「环境确实变了，旧结论不能直接搬…dc_server 现为 dev_20261119_filechain2（15:13 由其他会话部署）…旧文档 doc_c9991f55a0ea 已不存在…同一现象是两个不同原因，按切片器区分」 → G18 Audrey「回填+修代码」 → G19 回填 483 片 0 失败、3 篇 align_skipped → G20 陈昔「合并部署」 → G21 !128 合并 a1841997、部署 dev_20261119_filechain2_title128。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证同一现象跨 8 条群消息（含他人改环境、另一会话换镜像）时归并为 1 个缺陷，且旧根因被环境变化推翻后要按切片器拆成两个原因、不当作新缺陷或复发。 |
| 预期缺陷数 | 1（切片标题字段未覆盖 table/image 切片器；按切片器拆为两条修法，仍属同一缺陷） |
| 预期筛选 | 全部消息保留入库；G14/G15/G16/G18/G20 为非候选记录（filter_decision 取 template/sync/evidence_only 之一，triage_reason=context_only），不进缺陷库；G13 的结论标记 superseded_by=G17 保留版本链。 |
| 预期归并 | 按 群ID+messageId 幂等合并为 1 缺陷；G13 初判与 G17 重判是同缺陷的两个诊断版本，不建第二条缺陷；483 片回填记为 remediation 证据，不是独立缺陷。 |
| 预期证据归属 | G12 role=report；G13 role=diagnosis(v1, superseded)；G17 role=diagnosis(v2, 权威)；!128 + G21 role=primary_fix；G19 role=remediation；3 篇 align_skipped 记为 known_limitation（有护栏理由，不记漏修）。 |
| 预期复发定性 | 不是复发：中途 ES 被他人改动、另一会话部署了新镜像、原样本文档已被删除，属环境漂移；无代码回退证据。 |
| 判定依据 | 同一现象（切片无章节标题）在 09:16 与 16:48 指向同一类字段缺失；环境变更由 G14/G15/G17 明确记录；修复与上线在 G21 可回读。 |
| 否定项 | ①不得把 G16「重新排查」当新缺陷；②不得把「改完 ES 后仍复现」判为复发；③不得只用 G13 的单一根因（table）而漏掉 image 切片器一路；④不得把 3 篇 align_skipped 记成漏修 Bug；⑤不得把 G14/G18/G20 等操作与指令当缺陷。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 10, "fix_actions": 1, "independent_occurrences": 1, "recurrence_events": 0, "known_limitations": 1, "repeat_unresolved_events": 0, "unresolved_open_bugs": 0, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-11-19（当日）；来源 dingtalk（G12~G21，10 条消息）；时间精度：秒级；未覆盖：ES 配置变更与复验证据；未知：环境身份（仅 raw_text）", "context_only_records": 5} |
| 规则引用 | references/output-schema.md §4/§10.2.1/§10.5；references/recurrence-rules.md §2.5 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-A1-1 | intake | 输入 10 条消息（G12~G21）全部读取；group == 数据小队；partial == false | true |  |
| TC-A1-2 | filter | 非候选记录计数 == 5（G14/G15/G16/G18/G20），filter_decision 取 template/sync/evidence_only 之一且 triage_reason=context_only；不得用 excluded | true | output-schema §10.2/§10.2.1；filtering-rules §3.1 |
| TC-A1-3 | integrity | G13 标 superseded_by == G17 且两条消息均保留（版本链完整） | true |  |
| TC-A1-4 | count | confirmed_defects == 1 | 1 |  |
| TC-A1-5 | merge | 输出缺陷条数 == 1（两个切片器是两条修法，不是两个缺陷） | true |  |
| TC-A1-6 | attribution | G12=report；G13=report（v1，superseded）；G17=report（v2，权威）；!128+G21=primary_fix；G19=status_evidence | true | output-schema §4 |
| TC-A1-7 | recurrence | recurrence_events == 0（ES 改动/换镜像属环境漂移） | true |  |
| TC-A1-8 | integrity | 3 篇 align_skipped 记为 known_limitation 而非漏修 | true |  |
| TC-A1-9 | negative | 『重新排查』指令未被登记为新缺陷 | true |  |
| TC-A1-10 | recurrence | environment 只按 raw_text 保留（ES 改动/换镜像），不编造 canonical_name，也不据此判复发 | true | output-schema §10.5；recurrence-rules §2.5 |

### TC-A2　群聊提取

- **类型**：real（真实证据）
- **输入摘要**：G22 2026-11-22 16:18:55 Audrey（1,941 字）：【我独立取的现状】1) 原素材 87 个任务，失败里「音视频 4 个全是 ASR 超时」「大 PDF 写 ES 断管 2 个（2740 条和 5741 条切片全丢）」「1779 页超限 1 个」「不支持格式 11 个」，且「你之前报的 93 个文件、89 个任务、7 个重复，和 87 对不上」；2) 「排队第 50 位已等 5100 秒，预计等待却显示 1600 秒」；3) 「81 的 dc_server 只用 0.22 核（限额 8 核）」「51 的 GPU6 利用率 98%，GPU0 到 GPU5 全是 0%」；4) 「21 个失败任务的文案还停在『重新排队、排队中、解析中』；任务列表接口写死只回 200 行，分页参数无效」；另附【五个目标】验收口径与【四件事】追问。另 G25 2026-11-23 03:51 同类结构：通过 4 项 + 不通过 4 类（多级表头错位 9 页 / 表格结构被打散 4 页 / 页眉页脚未去 / 薄页）+ 否决 2 项。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证一条长消息内并列的多个独立缺陷被按粒度拆分，且『性能问题/能力边界/执行问题/统计口径差异/验收目标/追问』各走各的计数口径，不混入已确认缺陷数量。 |
| 预期缺陷数 | 整体（本案例自身证据簇内）：已确认缺陷 8 条 = G22 侧 4 条（①写 ES 断管致 2740/5741 条切片全丢 ③队列预计等待时间与实际严重不符 ⑤失败任务状态文案卡死 ⑥任务列表接口写死 200 行、分页失效）+ G25 侧 4 类不通过（多级表头错位 9 页、表格结构被打散 4 页、页眉页脚未去、薄文本层页）；疑似缺陷 1 条 =「1779 页超限 1 个」（是产品页数上限的设计边界还是缺陷，证据不足，须人工定性，不得计 confirmed）；性能问题 1 项（GPU0–5 全 0/GPU6 98%、81 CPU 0.22 核 vs 限额 8 核）→ 登记 performance_issue 待人工定级，不计入 confirmed；执行问题 1 类（ASR 超时 4 个任务）→ 标 need_verify；能力边界 1 类（不支持格式 11 个）→ 不计缺陷；统计口径差异 1 项（93/89/7 与 87 对不上）→ reporting_discrepancy 不建号。 |
| 预期筛选 | G22 逐条拆分为独立候选：①③⑤⑥=defect(confirmed)；②=need_verify(定性待人工)；④=performance_issue；ASR 超时=execution_issue(need_verify)；不支持格式=capability_boundary；93/89/7 对不上=reporting_discrepancy；【五个目标】【四件事】不进缺陷库。G25：通过 4 项=background；不通过 4 类=defect(confirmed)；否决 2 项（薄页先走 OXR、抽样 15 页不合格）=技术路线决策，background。 |
| 预期归并 | ①②同属解析完整性但对象不同（写 ES 断管 vs 页数上限），不互相归并；③④⑤⑥互不归并；G25 的 4 类结构问题与 G22 的 6 条不归并（不同批次、不同现象）。 |
| 预期证据归属 | G22 同一 messageId下对不同缺陷 role 均为 report；G25 同理；性能/边界/执行问题各自的记录条目与缺陷记录分开存放，不共享缺陷编号。 |
| 预期复发定性 | 无（本批均为首次登记）。 |
| 判定依据 | 每条现象都有独立对象与失败模式，可分别复现；「通过/不通过」在同条消息里显式标注。 |
| 否定项 | ①不得整条只登记 1 个缺陷；②不得把【五个目标】的验收口径当缺陷；③不得把「不支持格式 11 个」当缺陷；④不得把 ASR 超时直接判为外部原因排除（须标待核）；⑤不得把「薄页先走 OXR 不同意」这类技术路线否决当缺陷；⑥不得把同一根因的连锁现象硬拆（如把「写 ES 断管」再拆成 2740 与 5741 两条）。 |
| 计数（十项） | {"confirmed_defects": 8, "suspect_defects": 1, "evidence_items": 2, "fix_actions": 0, "independent_occurrences": 8, "recurrence_events": 0, "performance_issues": 1, "execution_issues": 1, "capability_boundaries": 1, "reporting_discrepancies": 1, "repeat_unresolved_events": 0, "unresolved_open_bugs": 8, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-11-22~11-23；来源 dingtalk（G22、G25）；时间精度：秒级；未覆盖：8 条缺陷的当前闭环状态与复验；未知：1779 页定性、性能定级"} |
| 规则引用 | references/recurrence-rules.md §2.1/§3.8；references/output-schema.md §9 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-A2-1 | count | confirmed_defects == 8（G22 4 条 + G25 4 类） | 8 |  |
| TC-A2-2 | count | suspect_defects == 1（1779 页超限，定性待人工，不得计入 confirmed） | 1 |  |
| TC-A2-3 | count | performance_issue 登记数 == 1（GPU/CPU 调度），未计入 confirmed 也未被丢弃 | true |  |
| TC-A2-4 | count | execution_issue（ASR 超时 4 任务）== 1 类、标 need_verify；capability_boundary（不支持格式 11 个）未计缺陷；reporting_discrepancy（93/89/7）未建缺陷号 | true |  |
| TC-A2-5 | count | 『写 ES 断管』未被拆成 2740 / 5741 两条（同一根因连锁现象 1 条） | true |  |
| TC-A2-6 | filter | 通过项与被否决项（薄页先走 OXR、抽样 15 页不合格）未登记为缺陷 | true |  |
| TC-A2-7 | merge | G22 与 G25 的缺陷互不归并（不同批次、不同现象） | true |  |
| TC-A2-8 | negative | 【五个目标】与【四件事】未进入缺陷库 | true |  |
| TC-A2-9 | recurrence | 8 条 confirmed 的 occurrence.kind 全为 first；无 repeat_unresolved | true | recurrence-rules §2.1 |
| TC-A2-10 | integrity | 报告同时给出事件去重已合并组数、待复核数与 coverage（含时间精度与未覆盖项） | true | recurrence-rules §3.8 |

### TC-A3　群聊提取

- **类型**：real（真实证据）
- **输入摘要**：G1 2026-11-17 09:16 陈昔「新建的应用，需要有默认的内置类目、字段、索引、词典」（需求） → G2 10:05 小圈圈 MR !105 已提、类目播种走 !104 → G3 11:25 陈昔「合并 MR !104、MR !105，然后部署」 → G4 11:42 !104（e4f28f1）、!105（8ebc493）已合并并部署 → G5 15:44 陈昔「我刚刚创建了一个应用 ai_jian_zheng_quan，这个应用依旧没有内置的类目、字段、索引、词典」；旁支：10:38 陈昔另要求为 soso_guanyutest/testcx1/zhi_de_qian_fan/guo_dian_tou 四个存量应用按历史数据补齐。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证『需求 → 修复合并部署 → 仍复现』链条中：需求条目不计为缺陷，二次反馈是缺陷（修复未生效），且不与历史应用的一次性数据补齐混为一谈。 |
| 预期缺陷数 | 1（新建应用未自动播种内置类目/字段/索引/词典；!104 的通用播种未覆盖该创建路径） |
| 预期筛选 | G1 = requirement（不进缺陷库）；G3 = operation_command；G2/G4 = execution_receipt；G5 = defect_report（含『依旧』= 修复未生效线索）；四个存量应用补齐 = remediation_request（一次性数据处理，不并入该缺陷）。 |
| 预期归并 | G5 与 G1 同一主题但不是同一条目：缺陷由需求派生，记 derived_from=G1；不与存量应用补齐合并。 |
| 预期证据归属 | G1=background（需求背景，候选 category=requirement_related）；G5=report；!104=primary_fix（未覆盖该路径）；后续修复=related_fix；存量补齐=background（另一对象）。 |
| 预期复发定性 | 属「修复未生效」而非复发：无 resolved→reopen 记录，且 !104 的通用逻辑与四应用的既有别名口径不一致（G 系列回执已说明）。 |
| 判定依据 | 「依旧没有」直接指向此前已部署的播种逻辑未覆盖新建路径；G4 可回读合并提交；G5 时间在新应用创建之后。 |
| 否定项 | ①不得把 G1 直接记成 Bug；②不得把 G5 当新需求（『再加个功能』）；③不得因 !104 已合并就判已修复；④不得把四个存量应用的手工补齐当同一缺陷的证据主体；⑤不得把 G3「然后部署」当缺陷描述。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 5, "fix_actions": 1, "independent_occurrences": 1, "recurrence_events": 0, "requirements": 1, "remediation_requests": 1, "repeat_unresolved_events": 0, "unresolved_open_bugs": 1, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-11-17（当日）；来源 dingtalk（G1~G5）+gitlab（!104）；时间精度：秒级；未覆盖：部署与复验证据；未知：环境身份", "reason_tag": "fix_not_live / fix_not_effective（描述标签，不在枚举字段）"} |
| 规则引用 | references/recurrence-rules.md §2.4/§2.6；references/output-schema.md §10.2.1/§10.5 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-A3-1 | filter | G1 分类为 requirement，未创建缺陷号 | true |  |
| TC-A3-2 | count | confirmed_defects == 1（G5：修复未生效） | 1 |  |
| TC-A3-3 | merge | 缺陷记录含 derived_from == G1；未与四个存量应用的手工补齐合并 | true |  |
| TC-A3-4 | recurrence | reason_tag 取 fix_not_live / fix_not_effective（只作标签）；occurrence.kind == first；recurrence_events == 0 | true | output-schema §10.2.1；recurrence-rules §2.4 |
| TC-A3-5 | attribution | !104 role == primary_fix（未覆盖新建路径）被记录 | true |  |
| TC-A3-6 | negative | !104 已合并未被判『已修复』；『然后部署』指令未被算缺陷描述 | true |  |
| TC-A3-7 | recurrence | 验证结论未跨环境外推：未给出可归一环境时 verified_environments 报『未知』，不得写 0 或『所有环境已验证』 | true | recurrence-rules §2.6/§3.7 |

### TC-A4　群聊提取

- **类型**：real（真实证据）
- **输入摘要**：G6 2026-11-17 12:13 陈昔「查看原文时需要定位到对应切片的位置」 → G7 15:36 小圈圈「detail_url 已带切片锚点…Playwright 实测 ?chunk=42 时切片 #42 选中」 → G8 2026-11-18 10:37 陈昔「…查看原文时依旧没有定位到对应切片的位置」 → G9 11:29 小圈圈「不是代码问题，是部署被冲掉了…docker-compose.yml 里的 pin 一直停在修复前构建的 dev_20261115_multirepo（bundle 里没有 ?chunk= 解析代码）…已切回含修复镜像并实测定位正常」。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证二次上报「依旧不行」时先核查部署形态：根因为部署 pin 未更新（部署漂移）时，记 1 个交付/部署缺陷，不判代码复发、不新建缺陷。 |
| 预期缺陷数 | 1（修复只以临时镜像挂载、部署仓 pin 未更新，导致次日被自动部署冲回旧镜像） |
| 预期筛选 | G6=category requirement_related（需求）；G8=report（同一现象的二次反馈）；G7=status_evidence（交付执行回执）；G9=background（根因说明）；不因『依旧』二字新建第二个缺陷。 |
| 预期归并 | G6/G7/G8/G9 归并为 1 个条目（同一用户对象：切片定位）；现象层 1 条，根因层为部署漂移。 |
| 预期证据归属 | G6=background（需求背景）；G7=primary_fix（首次交付）；G8=report（二次反馈）；G9=background（根因说明）；修复镜像=related_fix 或 status_evidence（未落 pin）。 |
| 预期复发定性 | 不是复发：代码未回退、无 reopen；属部署形态漂移（临时 service update 未写回 compose pin）。 |
| 判定依据 | G9 明确指出 pin 停在 dev_20261115_multirepo 且 bundle 缺 ?chunk= 解析；G7 的验证在当时成立。 |
| 否定项 | ①不得判为代码回归/复发；②不得把 G8 当独立新缺陷；③不得只信 G7「已验证通过」而不记录部署形态；④不得把 G9 的「已切回」当永久修复（pin 未落盘）；⑤不得把 G6 的需求属性丢掉。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 4, "fix_actions": 1, "independent_occurrences": 1, "recurrence_events": 0, "repeat_unresolved_events": 0, "unresolved_open_bugs": 1, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-11-17~11-18；来源 dingtalk（G6~G9）+gitlab；时间精度：秒级；未覆盖：部署仓 pin 状态与复验；未知：环境身份（仅 raw_text）", "reason_tag": "deployment_drift（描述标签，不在枚举字段）"} |
| 规则引用 | references/recurrence-rules.md §2.4/§2.6；references/output-schema.md §4/§10.2.1/§10.5 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-A4-1 | count | confirmed_defects == 1（归因部署漂移） | 1 |  |
| TC-A4-2 | filter | G8 二次反馈未新建第二个缺陷（candidates == 1） | true |  |
| TC-A4-3 | recurrence | recurrence_events == 0；原因写 reason_tag=deployment_drift（不得写进 occurrence.kind） | true | recurrence-rules §2.4；output-schema §10.2.1 |
| TC-A4-4 | attribution | G6=background（需求背景）、G7=primary_fix（首次交付）、G8=report（二次反馈）、G9=background（根因说明）、修复镜像=related_fix 或 status_evidence | true | output-schema §4 |
| TC-A4-5 | negative | 『已切回修复镜像』未被当作永久修复（pin 未落盘须记 follow_up） | true |  |
| TC-A4-6 | recurrence | 环境维度按 canonical_name 表述；无法归一则保留 raw_text 并进 recurrence_check/field_verify，不得以同属 test 分类视为同一环境 | true | recurrence-rules §2.6；output-schema §10.5 |

### TC-A5　群聊提取

- **类型**：real（真实证据）
- **输入摘要**：G10 2026-11-18 10:46:25 陈昔「soso-dev环境，数据归集-上传文件后，选择智能加工策略，但是匹配加工策略失败」+截图 → G11 11:23:42 小圈圈「匹配逻辑没有问题，是你测试的 10:38~10:49 那几分钟，soso_dc_frontend 正好被重新部署…返回 502（nginx 错误页而非 JSON），前端解析失败就把每个文件统一标成『匹配失败』」。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证环境/瞬时故障不被登记为产品缺陷，但由此暴露的『错误提示不区分 502』必须单独登记为改进项；不因现象描述像功能失效，就把匹配逻辑判为缺陷。 |
| 预期缺陷数 | 1（前端把 502/非 JSON 响应统一显示为『匹配失败』，误导排查；对应 MR !113） |
| 预期筛选 | G10 现象本身 environment_induced（部署闪断），不建『解析/匹配逻辑失效』缺陷；G11 从同一现象里拆出 1 个错误提示/可用性缺陷；部署闪断本身 = environment_event（记事件台账，不入缺陷库）。 |
| 预期归并 | G10 与 G11 归并为同一事件链（现象→环境外因→提示缺陷）；!113 关联到该事件链；不与本群其他缺陷归并。 |
| 预期证据归属 | G10=report（环境诱因说明）；G11=report（诊断结论）；!113=primary_fix（改的是错误提示/异常处理，不是匹配逻辑）。 |
| 预期复发定性 | 无（单次部署窗口 10:38–10:49，无历史同类记录）。 |
| 判定依据 | G11 给出 10:35–10:38 全 200、10:38–10:49 502 的时间线，并明确「匹配逻辑没有问题」；G11 指出前端解析失败后把每个文件统一标『匹配失败』。 |
| 否定项 | ①不得登记『智能加工策略匹配失败』为解析/匹配逻辑缺陷；②不得把部署闪断本身记为产品缺陷；③不得漏掉「错误提示不区分 502」这一改进项（它是本案例唯一的真实缺陷）；④不得把 !113 描述成『修了匹配逻辑』；⑤不得因已归因环境就把 G10 当噪声丢弃（它是现象原点，须保留为 environment_induced 报告）。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 2, "fix_actions": 1, "independent_occurrences": 1, "recurrence_events": 0, "environment_events": 1, "repeat_unresolved_events": 0, "unresolved_open_bugs": 0, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-11-18（当日）；来源 dingtalk（G10/G11）+gitlab（!113）；时间精度：秒级；未覆盖：G10 截图（missing）；未知：nginx 部署记录"} |
| 规则引用 | references/output-schema.md §10.5；references/recurrence-rules.md §2.5 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-A5-1 | filter | 『匹配加工策略失败』未被登记为解析/匹配逻辑缺陷 | true |  |
| TC-A5-2 | count | confirmed_defects == 1（错误提示不区分 502） | 1 |  |
| TC-A5-3 | count | environment_event 登记数 == 1 且未入缺陷库 | true |  |
| TC-A5-4 | attribution | G10 role == report(environment_induced)（现象原点被保留，未当噪声丢弃） | true |  |
| TC-A5-5 | integrity | G10 截图附件缺失已标注 missing（未补造） | true |  |
| TC-A5-6 | negative | !113 未被描述为『修了匹配逻辑』 | true |  |
| TC-A5-7 | recurrence | 环境事件不写入缺陷库；occurrence.environment 不编造 canonical_name（无证据时写 raw_text 或 null） | true | output-schema §10.5；recurrence-rules §2.5 |

### TC-A6　群聊提取

- **类型**：real（真实证据）
- **输入摘要**：G26 2026-11-24 01:47 Audrey：「四连发拆线：我这边拆不了——15:43、18:53、昨晚四连发都是别的线在发（大概率还是你在另一个群下的需求那条线），数据小队群里看不到」；同条要求把外发事故（模块 dc_route、P1、261 次上传）录禅道。G29 2026-11-24 11:51 小圈圈：「任务执行失败。原因：处理失败：员工返回的操作内容不完整或格式异常，本次任务未完成」。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证群内证据缺口必须标 partial 且不得用别群内容补；机器人自报『任务执行失败』属平台侧事件，不能直接当产品缺陷。 |
| 预期缺陷数 | 本群证据内 0 个可独立成立的缺陷；外发事故（#15049 同族）需 GitLab/禅道证据方可建号，本群只有转述 |
| 预期筛选 | G26 作为 evidence_gap 记录（partial=true，缺口原因=「别线操作、本群不可见」）；G29 filter_decision=template，triage_reason=platform_broadcast；不得因「群里看不到」断言四连发未发生或发生了 4 个缺陷。 |
| 预期归并 | 不外推、不跨群归并；外发事故与 #15049 的关联必须由代码/禅道证据建立。 |
| 预期证据归属 | G26 role=evidence_gap；G29 role=platform_incident（不进入业务缺陷库）；外发事故 role=external_reference（待补证据）。 |
| 预期复发定性 | 不适用（无足够证据判定发生/复发）。 |
| 判定依据 | G26 明确写出「数据小队群里看不到」；G29 文本是平台执行失败模板，无业务现象描述。 |
| 否定项 | ①不得用其他群消息补本群证据；②不得把 G29 当产品 Bug；③不得把「看不到」当成「没有发生」或「发生 4 次」；④manifest 必须标 partial 与缺口原因；⑤不得据 G26 单独建缺陷号。 |
| 计数（十项） | {"confirmed_defects": 0, "suspect_defects": 0, "evidence_items": 2, "fix_actions": 0, "independent_occurrences": 0, "recurrence_events": 0, "evidence_gaps": 1, "cross_source_refs": "Z-15049（判分加分项，不计入本簇计数）", "repeat_unresolved_events": 0, "unresolved_open_bugs": 0, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-11-24（当日）；来源 dingtalk（G26/G29）；时间精度：秒级；未覆盖：外发明细（G26 evidence_gap）；未知：外发是否发生"} |
| 规则引用 | references/recurrence-rules.md §3.1；references/output-schema.md §4/§10.2.1 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-A6-1 | filter | G26 记录为 evidence_gap（partial == true，缺口原因已写明） | true |  |
| TC-A6-2 | filter | G29 filter_decision == template 且 triage_reason == platform_broadcast；不得用 excluded | true | output-schema §10.2；filtering-rules §3.1 |
| TC-A6-3 | count | confirmed_defects == 0（本群证据内无独立成立的缺陷） | 0 |  |
| TC-A6-4 | integrity | 『四连发』既未被判『未发生』、也未被判『发生 4 次』 | true |  |
| TC-A6-5 | negative | 未用其他群的聊天内容补本群证据；未据 G26 单独创建缺陷号 | true |  |
| TC-A6-6 | recurrence | 无 occurrence 时不虚增独立发生；说明未入库或 bugs_without_occurrence 口径 | true | recurrence-rules §3.1/§3.7 |
| TC-A6-7 | filter | 外发事故 #15049 若被引用，标 mr_ref_unverified/未核实，不得写入 kind=mr 证据或作归并强证据 | true | output-schema §4/§10.2.1 |

### TC-A7　群聊提取

- **类型**：real（真实证据）
- **输入摘要**：G23 2026-11-23 00:04 Audrey：「速度：批量 76.5 页/分钟，单份大文件 48.9。这一批 99.9% 的页带文本层…」 → G24 2026-11-23 01:29 同人：「【先更正我的错】我 00:04 那条第 5 点说『这批 99.9% 的页带文本层』，错了…51 个 PDF 共 8,041 页，没有文本层的 842 页，占 10.5%；30 字以下 347 页；30 字以上 6,852 页，占 85.2%」，并列出 9 个整本扫描件约 800 页 → G25 2026-11-23 03:51 同批验收核对（X 允许引用）：『不通过：…薄页…』并给出抽样结论——检出 4 页走文本层通道、每页仅出 25~28 字。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证同一提问人后续主动更正前条数字时，以更正后版本为事实基础，保留版本链，不产生两条缺陷/两次事件。 |
| 预期缺陷数 | 1（薄文本层/扫描页未按规则分流）；事实基础取更正后的 G24（8,041 页分母：无文本层 842 页占 10.5%；30 字以下 347 页；30 字以上 6,852 页占 85.2%），量化佐证引 G25（文本层通道抽样 4 页仅出 25~28 字）。 |
| 预期筛选 | G23 中该数字标 superseded_by=G24（保留原文，不删）；G24 为有效事实；不因两条消息建两条缺陷。 |
| 预期归并 | 归并为 1 个缺陷；两版本同为 report 证据的版本链。 |
| 预期证据归属 | G23=report（v1，superseded）；G24=report（v2，权威）；后续修复证据待补。 |
| 预期复发定性 | 不适用。 |
| 判定依据 | 同人、同批次、明确「更正我的错」；更正后给出可核对的页级统计（8041 页 / 842 页 / 347 页 / 6852 页）。 |
| 否定项 | ①不得把两条消息当两个缺陷/两次事件；②不得继续用 99.9% 作为证据；③不得因上游认错就删除原始消息（须保留更正链）；④不得把 10.5% 与 85.2% 混算（同一分母 8,041 页）；⑤不得把「批量 76.5 页/分钟」等指标当缺陷（属基线数据）。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 3, "fix_actions": 0, "independent_occurrences": 1, "recurrence_events": 0, "repeat_unresolved_events": 0, "unresolved_open_bugs": 1, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-11-23（当日）；来源 dingtalk（G23/G24/G25）；时间精度：秒级；未覆盖：样本外的页级统计；未知：无（同分母已核对）"} |
| 规则引用 | references/recurrence-rules.md §3.8；references/output-schema.md §10.4 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-A7-1 | integrity | G23 保留且标 superseded_by == G24（更正链完整，未删原文） | true |  |
| TC-A7-2 | attribution | G23 role == report(v1, superseded)；G24 role == report(v2, authoritative) | true |  |
| TC-A7-3 | count | confirmed_defects == 1（薄文本层/扫描页未按规则分流） | 1 |  |
| TC-A7-4 | count | independent_occurrences == 1（上游更正未产生第二次发生） | 1 |  |
| TC-A7-5 | integrity | 缺陷事实引用的统计与 G24 同分母（8,041 页：842 / 347 / 6,852）且未继续使用『99.9%』 | true |  |
| TC-A7-6 | integrity | G25 引用有输入支持（G25 已纳入本案例输入） | true |  |
| TC-A7-7 | negative | 批量 76.5 页/分钟等速度指标未被计为缺陷 | true |  |
| TC-A7-8 | integrity | G23/G24/G25 同日多消息按 §3.8 事件去重：共享 report 证据才算同一次；原始时间精度保留，不补时分秒 | true | recurrence-rules §3.8 |

### TC-A8　群聊提取

- **类型**：real（真实证据）
- **输入摘要**：G27 2026-11-24 10:56:32 Audrey「防护版发布验收：通过…你还欠两个数：a) 中断时长精确值 b) 87 文档快查」→ G28 11:49:26 同人「欠数验收通过，判定不回滚，两条建议都批」：①「中断 149.8s：如实报收货——规格/镜像分两次 service update 是执行问题，下次合成一次。记台账」；②「健康误杀（11:00:54 那次）记 P-103，录禅道：模块 dc_server/healthcheck，级别 P1」（现象=高负载下 /health 连续超时 10×8-12s + 一次 101 秒 000→swarm 判死重建 exit 137，非 OOM、非 service update；影响=批中在途中断重跑、无数据丢失；修法=healthcheck retries 3→6、timeout 5→10s / cleaning·chunking 挪出 API 进程）；③「embedding 并发叠加记观察项」。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证『验收通过 ≠ 零遗留』：通过回执自身不产生缺陷，但其中未核完的欠项核完后暴露的缺陷必须单独登记；同一条消息里的执行问题、真实缺陷、观察项必须三分，不得合并成一条『发布事故』。 |
| 预期缺陷数 | 1（P-103：dc_server/healthcheck 高负载下被判死重建，P1；尚未修复，只有获批的修法计划） |
| 预期筛选 | G27 为通过回执但 partial=true（open_items=2：中断时长精确值、87 文档快查），本身 0 缺陷，且不得判『已验证闭环』；G28 必须三分：149.8s 中断 = execution_issue（记台账，不入缺陷库）；health 误杀 = 缺陷 P-103；embedding 并发叠加 = observation（不入缺陷库）。 |
| 预期归并 | P-103 与 149.8s 中断互不归并（同窗口但因果不同：一次是发布动作拆两次，一次是 health 判死重建）；P-103 不与 G27 并成一条『发布事故』。 |
| 预期证据归属 | G27=status_evidence（通过回执，partial=true）；G28=report（诊断与分类说明）；P-103 为缺陷主记录（证据 kind=bug_record，role=report）；healthcheck 修复=primary_fix（计划，未发布）；149.8s 与 embedding 并发不作证据 role，分别登记 execution_issue / observation。 |
| 预期复发定性 | 不适用——P-103 为本发布窗口首次登记，无 resolved→reopen 轨迹，不得登记为复发。 |
| 判定依据 | G28 原文明确「记 P-103，录禅道：模块 dc_server/healthcheck，级别 P1」，并给出复现窗口（87 快查批 10:57–11:24，1 秒采样 CSV）；同条明确「149.8s…是执行问题，下次合成一次。记台账」「embedding 并发叠加记观察项」；两条修法『都批』但『随明天的二期回归版一起发（今天不再单独动现网）』→ 尚未修复。 |
| 否定项 | ①不得把 G27『验收通过』当成零遗留/已验证闭环（还欠 2 个数）；②不得把 149.8s 中断登记为缺陷；③不得把 embedding 并发登记为缺陷（观察项）；④不得把 P-103 与 149.8s 合并成 1 条；⑤不得因『修法都批』或『判定不回滚』就判 P-103 已修复/已闭环；⑥不得把『不回滚』当成『无缺陷』。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 2, "fix_actions": 0, "independent_occurrences": 1, "recurrence_events": 0, "execution_issues": 1, "observations": 1, "cross_source_ref": "#15057（P-103，已核实 2026-11-25）", "planned_fix": 1, "repeat_unresolved_events": 0, "unresolved_open_bugs": 1, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-11-24（当日）；来源 dingtalk（G27/G28）+zentao（#15057）；时间精度：秒级；未覆盖：P-103 修复与复验；未知：embedding 并发定级"} |
| 规则引用 | references/output-schema.md §4/§10.2.1；references/recurrence-rules.md §2.5 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-A8-1 | filter | G27 记录为 pass_receipt 且 partial == true、open_items == 2 | true |  |
| TC-A8-2 | count | 三分正确：execution_issue == 1（149.8s）、defects == 1（P-103）、observation == 1（embedding 并发） | true |  |
| TC-A8-3 | count | confirmed_defects == 1 | 1 |  |
| TC-A8-4 | merge | P-103 与 149.8s 中断互不归并；未与 G27 并成一条『发布事故』 | true |  |
| TC-A8-5 | recurrence | recurrence_events == 0 | true |  |
| TC-A8-6 | integrity | P-103 与禅道单号建立关联（参考锚点 #15057）或显式标注『单号待核实』 | true |  |
| TC-A8-7 | negative | 修法获批/判定不回滚未被当作『已修复/已闭环』 | true |  |
| TC-A8-8 | attribution | #15057 为已核实锚点；未核实时不得写成 kind=mr 或作强证据，应标 mr_ref_unverified | true | output-schema §4/§10.2.1 |

## 7. Synthetic 案例（8 条，不得与真实案例混评）

### TC-R1　复发识别（正向）

- **类型**：synthetic（构造边界案例）
- **输入摘要**：S1（构造）禅道单 X1：2026-09-10 打开『列表导出 CSV 中文乱码』；2026-09-15 resolved(fixed)，修复 MR 于 09-16 发布；2026-09-18 验收通过、closed。S2（构造）2026-11-20 上线『导出 Excel』新入口后，Excel 导出再次出现乱码（CSV 入口正常）——时间 11-20、版本 dev_20261120、复现步骤齐全；X1 被 reopened，activatedCount==1。S3（构造）2026-11-21 提交第二轮 MR 修复（Excel 出口编码处理）。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证『已修复并经验证通过后再次发生』被正确判为复发：resolved→closed→reopened 轨迹 + 新现象 + 新时间 + 新版本三要素齐备，输出 recurrence==1 且归并原单，不因两轮修复拆成两条缺陷。 |
| 预期缺陷数 | 1（X1 同一条缺陷贯穿两轮） |
| 预期筛选 | S1=closed 历史；S2=reopen 报告（复发候选）；S3=第二轮修复（related_fix）。 |
| 预期归并 | S2 的复发归并到 X1 原单（同一缺陷），不得新建第二条缺陷。 |
| 预期证据归属 | S1=report（首报）；修复 09-16=primary_fix；S2=report（reopen 复现）；S3=related_fix（第二轮修复，不作为复发依据）。 |
| 预期复发定性 | 狭义复发：S1 到 verified_fixed 并有 dev-1 环境验证证据，S2 在 dev-1 以新时间/新版本/新现象再次出现且无回退证据 → kind=repeat_after_fix，计入广义复发；S3 第二轮修复不作为复发依据（role=related_fix）。recurrence_events=1，recurrence_by_subtype={repeat_after_fix:1, rollback_regress:0}。 |
| 判定依据 | 构造链含完整状态流转与三要素；用于与 TC-008（持续未解决）构成正负对照。 |
| 否定项 | ①不得因出现第二轮修复就把复发拆成两条缺陷；②不得把 S3 当作复发的『证据来源』（复发的证据是 S2）；③不得漏核三要素（缺任一须降级为疑似）。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 3, "fix_actions": 2, "independent_occurrences": 2, "recurrence_events": 1, "repeat_unresolved_events": 0, "unresolved_open_bugs": 1, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 1, "rollback_regress": 0}, "verified_environments": ["dev-1"], "coverage": "时间窗 2026-09-10~11-21；来源 synthetic；时间精度：日级/秒级混合；未覆盖：跨环境验证；未知：无（dev-1 已明确）"} |
| 规则引用 | references/recurrence-rules.md §2.3/§2.6/§3.2；references/output-schema.md §4/§8/§10.5 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-R1-1 | recurrence | recurrence_events == 1 且存在 occurrence.kind == repeat_after_fix；不得使用 reopen_recurrence | true | recurrence-rules §2/§2.3 |
| TC-R1-2 | recurrence | resolved→closed→reopened 流转记录被引用 == true | true | references/recurrence-rules.md §2.3/§2.6/§3.2 |
| TC-R1-3 | count | independent_occurrences == 2 且 confirmed_defects == 1 | true | references/recurrence-rules.md §2.3/§2.6/§3.2 |
| TC-R1-4 | integrity | 三要素（新现象/新时间/新版本）均被核对；任一缺失即降级疑似 | true | references/recurrence-rules.md §2.3/§2.6/§3.2 |
| TC-R1-5 | attribution | S3 role == related_fix（第二轮修复不作为复发依据） | true | output-schema §4；recurrence-rules §2.3 |
| TC-R1-6 | negative | 未因两轮修复输出两条缺陷 | true | references/recurrence-rules.md §2.3/§2.6/§3.2 |
| TC-R1-7 | recurrence | 判复发前核对本次环境 dev-1 落在 S1 verified_fixed 证据覆盖的环境范围内（按 canonical_name，不按分类） | true | recurrence-rules §2.6/§4 步骤 2 |
| TC-R1-8 | integrity | S1 的 verified_fixed 流转行带 environment.canonical_name == dev-1 | true | output-schema §8/§10.5 |

### TC-R2　复发识别（正向）

- **类型**：synthetic（构造边界案例）
- **输入摘要**：S1（构造）禅道单 X2：『导出超时』09-20 打开，09-25 resolved(fixed)（MR 已合并，验收记录写『测试环境复验通过』）。S2（构造）11-22 线上同一现象重现；用户侧报『又复现了』。S3（构造）发布记录：11-21 发布仓对 X2 修复所在服务执行了 rollback，回到 09-10 的旧镜像；测试环境仍在修复版。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证现象重现先核查发布形态：当发布仓已回滚到旧镜像（修复从未在线上生效）时，重现不判复发、不产生 recurrence==1，而是登记一条发布/部署问题。 |
| 预期缺陷数 | 1（X2 仍是同一条缺陷；release 回滚另记 1 条过程问题） |
| 预期筛选 | S2 在核查发布形态前不定性；核查后定性 fix_not_live（修复未在线上生效）；发布回滚登记 process_release_issue 1 条（非产品缺陷）。 |
| 预期归并 | 重现并入 X2；rollback 事件与 X2 记录关联但不合并为同一条缺陷。 |
| 预期证据归属 | S1=report（首报）；09-25 MR=primary_fix（仅 test-1 验证）；S2=report（prod 重现）；S3=status_evidence（回滚记录）。 |
| 预期复发定性 | 不判复发：S1 只在 test-1 环境复验通过（verified_fixed 覆盖 test-1），S3 的回滚发生在 soso-prod，而 soso-prod 从未有过验证通过证据，不满足 §2.4『曾 verified_fixed + 有回退证据』双条件 → 不得判 rollback_regress。S2 是 prod 上一次新的独立发生（独立时间/环境/现象），按 §2.4 第三行登记 repeat_unresolved（计入独立发生、不计复发）；fix_not_live 只作描述标签。recurrence_events=0，repeat_unresolved_events=1，verified_environments=[test-1]。 |
| 判定依据 | 构造链把『验证通过』限定在测试环境、生产被回滚，测判分方是否先查发布形态。 |
| 否定项 | ①不得跳过发布形态核查直接判复发；②不得把回滚事件记成产品缺陷；③不得因『测试环境复验通过』判生产无问题。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 3, "fix_actions": 1, "independent_occurrences": 2, "recurrence_events": 0, "process_release_issues": 1, "repeat_unresolved_events": 1, "unresolved_open_bugs": 1, "related_cases": 0, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": ["test-1"], "coverage": "时间窗 2026-09-20~11-22；来源 synthetic；时间精度：日级；未覆盖：prod 验证证据（不存在）；未知：无", "reason_tag": "fix_not_live（描述标签，不在枚举字段）"} |
| 规则引用 | references/recurrence-rules.md §2.2/§2.4/§2.6；references/output-schema.md §10.2.1/§10.5 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-R2-1 | recurrence | recurrence_events == 0；不得输出 rollback_regress（回滚发生在从未验证过的环境） | true | recurrence-rules §2.4/§2.6 |
| TC-R2-2 | recurrence | 定性前核对 verified_fixed 证据只覆盖 test-1；soso-prod 不在覆盖范围 | true | recurrence-rules §2.6 |
| TC-R2-3 | recurrence | prod 的新发生按 repeat_unresolved 登记（有独立时间/环境/现象证据）；repeat_unresolved_events == 1 | true | recurrence-rules §2.4 第三行/§2.2 |
| TC-R2-4 | schema | fix_not_live 只出现在 reason/basis；occurrence.kind 仍为 repeat_unresolved | true | output-schema §10.2.1 |
| TC-R2-5 | count | process_release_issue 登记数 == 1（非缺陷库条目，不进缺陷库） | true | output-schema §9 |
| TC-R2-6 | recurrence | verified_environments == ['test-1']，不得含 soso-prod，也不得用『测试环境』泛称外推 | true | recurrence-rules §2.6；output-schema §10.5 |
| TC-R2-7 | negative | 未把『测试环境复验通过』当作生产已验证；回滚未被记为产品缺陷；未据回滚字样判 rollback_regress | true | recurrence-rules §2.4/§2.5 |

### TC-R3　复发识别（正向）

- **类型**：synthetic（构造边界案例）
- **输入摘要**：S1（构造）禅道单 X3：『表格切片表头丢失』2026-08-12 打开，08-20 resolved(fixed)（A 切片器获取表头的 bug，已闭环）。S2（构造）2026-11-24 『Word 文档表格首列被凭空拼出表头』禅道单 X4 新开——现象相似（都涉及表头），但根因是无表头表格的兜底拼接逻辑（B 分支）、复现条件（无表头结构文档）与模块均不同于 X3。S3（构造）X4 于 11-25 获独立修复 MR。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证同类相似现象但根因不同时：拆分为 2 条独立缺陷、不自动归并到已闭环的旧单、不计复发。 |
| 预期缺陷数 | 2（X3、X4 各一条） |
| 预期筛选 | S2/S3 → X4 新缺陷（confirmed）；S1 → X3 历史闭环单；两单相似度语义判为 medium（共享关键词），不自动归并。 |
| 预期归并 | 不归并：X4 ≠ X3（根因/复现条件/模块不同）；若归并置信度为 high 即判错误——歧义应进人工复核。 |
| 预期证据归属 | S1=report（X3 首报）；S2=report（X4 首报）；S3=primary_fix（X4）；两条缺陷共享的『表头』关键词只是背景相似，不构成证据角色。 |
| 预期复发定性 | 无复发：X3 已闭环且未 reopened，X4 是同类但根因/复现条件/模块不同的独立缺陷，以 bugs.related[].kind=similar_class 关联，双方 recurrence_events 均为 0、互不生成 occurrence，X3 的 verified_environments 不被 X4 借用。 |
| 判定依据 | 构造链给出可对比的两组根因/条件，测『相似≠同一』边界。 |
| 否定项 | ①不得把 X4 自动并入 X3（已闭环单）；②不得因相似判 X3 复发；③不得把共享关键词当归并依据（置信等级不得为 high）。 |
| 计数（十项） | {"confirmed_defects": 2, "suspect_defects": 0, "evidence_items": 3, "fix_actions": 1, "independent_occurrences": 2, "recurrence_events": 0, "repeat_unresolved_events": 0, "unresolved_open_bugs": 1, "related_cases": 1, "bugs_without_occurrence": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "verified_environments": ["soso-prod"], "coverage": "时间窗 2026-08-12~11-25；来源 synthetic；时间精度：日级；未覆盖：X4 的验证；未知：无"} |
| 规则引用 | references/recurrence-rules.md §3.4/§2.6；references/output-schema.md §3/§10.5 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-R3-1 | count | confirmed_defects == 2 | 2 | references/recurrence-rules.md §3.4/§2.6 |
| TC-R3-2 | merge | X4 未被归并进已闭环的 X3 | true | references/recurrence-rules.md §3.4/§2.6 |
| TC-R3-3 | merge | 若给出归并置信度，则 != high（medium/歧义须进人工复核） | true | references/recurrence-rules.md §3.4/§2.6 |
| TC-R3-4 | recurrence | recurrence_events == 0（X3 未 reopened，X4 只是相似） | true | references/recurrence-rules.md §3.4/§2.6 |
| TC-R3-5 | integrity | 输出引用了至少两条区分依据（根因/复现条件/模块） | true | references/recurrence-rules.md §3.4/§2.6 |
| TC-R3-6 | merge | 关联登记为 bugs.related[].kind=similar_class，且含 similar_points 与 differences；不新建 related_case occurrence | true | recurrence-rules §3.4；output-schema §3 |
| TC-R3-7 | recurrence | X3 的 verified_environments 不被 X4 借用；X4 的首次发生环境独立登记（first） | true | recurrence-rules §2.6/§3.4 |

### TC-R4　复发识别（分环境）

- **类型**：synthetic（构造边界案例）
- **输入摘要**：S0 环境注册表：test-a（别名『测试环境A』/test-a，category=test）、test-b（别名『测试环境B』/test-b，category=test）、soso-prod（production）。S1 X5『导出文件标题被截断』2026-09-01 首报，09-05 修复 MR 合并，09-07 部署 test-a 复测通过（verified_fixed，environment=test-a）。S2 2026-11-20 test-b 出现同一现象（新时间/新环境/新截图；test-b 此前无任何验证记录，无回退证据）。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证分环境验证的适用范围按 canonical_name 判定：test-a 的验证通过不外推到同分类的 test-b；未覆盖环境的再次出现不判复发，进 recurrence_check。 |
| 预期缺陷数 | 1（X5，同一缺陷） |
| 预期筛选 | S1 首报=candidate；S2 是同一缺陷的新现象报告，作为 evidence（role=report）挂到 X5，不新建缺陷候选；不因『测试环境』泛称并入其他环境。 |
| 预期归并 | S2 关联到 X5（同一缺陷），不与其他环境记录合并。 |
| 预期证据归属 | S1 修复=primary_fix；S1 复测回执=status_evidence 且 transition.environment=test-a；S2=report。 |
| 预期复发定性 | 不判复发：verified_fixed 只覆盖 test-a，test-b 同属 test 分类但不是同一环境（§2.6 分类≠身份）。S2 有独立时间/环境/现象证据，但本次出现环境不在验证覆盖范围 → 按 §2.4『已部署但相关场景从未验证通过』与 §2.6 环境门槛，不直接认定复发、也不强行建 occurrence，进 review_queue（type=recurrence_check，missing_evidence 写明 test-b 验证/部署证据缺失）。recurrence_events=0，verified_environments=[test-a]。 |
| 判定依据 | 注册表明确 test-a/test-b 两个 canonical_name 且 category 同为 test；S1 的 verified_fixed 流转只登记 test-a；S2 无回退证据。 |
| 否定项 | ①不得因同属 test 分类把 test-b 当作已验证；②不得判 repeat_after_fix/rollback_regress；③不得把 S2 判成『未发生』；④不得把别名『测试环境A』直接当 canonical_name 而不归一；⑤不得编造 test-b 的验证记录。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 3, "fix_actions": 1, "independent_occurrences": 1, "repeat_unresolved_events": 0, "unresolved_open_bugs": 1, "recurrence_events": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "related_cases": 0, "bugs_without_occurrence": 0, "verified_environments": ["test-a"], "coverage": "时间窗 2026-09-01~11-20；来源 synthetic；时间精度：日级；未覆盖：test-b 的验证与部署证据（不存在）；未知：test-b 缺陷是否成立", "occurrences_pending_review": 1} |
| 规则引用 | references/recurrence-rules.md §2.4/§2.6/§3.7；references/output-schema.md §8/§10.5；config/default.json recurrence.environment_registry |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-R4-1 | recurrence | verified_environments == ['test-a']，不含 test-b（同分类不算同一环境） | true | recurrence-rules §2.6/§3.7 |
| TC-R4-2 | recurrence | 不输出 repeat_after_fix / rollback_regress；recurrence_events == 0 | true | recurrence-rules §2.6/§4 步骤 3 |
| TC-R4-3 | recurrence | S2 进 review_queue（type=recurrence_check），missing_evidence 写明 test-b 验证/部署证据缺失 | true | recurrence-rules §2.6；output-schema §7 |
| TC-R4-4 | attribution | S1 的 verified_fixed 流转行 environment.canonical_name == test-a（不是分类 'test'） | true | output-schema §8/§10.5 |
| TC-R4-5 | integrity | 别名『测试环境A』/『测试环境B』归一为各自 canonical_name；无法归一时保留 raw_text 并标待归一 | true | output-schema §10.5 |
| TC-R4-6 | count | independent_occurrences == 1（S2 未建 occurrence，待复核单列 occurrences_pending_review=1） | true | recurrence-rules §3.1/§3.8 |
| TC-R4-7 | negative | 未把『测试环境』泛称同时归给 test-a/test-b；未据 S2 判『复发』或『已解决』 | true | recurrence-rules §2.6 |
| TC-R4-8 | integrity | coverage 披露已验证环境范围与未覆盖环境，不得写 0 | true | recurrence-rules §3.7 |

### TC-R5　复发识别（回滚重现）

- **类型**：synthetic（构造边界案例）
- **输入摘要**：S0 注册表：soso-prod（production）。S1 X6『登录页验证码不显示』2026-09-02 首报，09-08 修复 MR 合并，09-10 部署 soso-prod，09-11 现场复测通过（verified_fixed，environment=soso-prod）。S2 2026-11-18 soso-prod 同一现象再次出现（新时间/复现步骤/截图）。S3 2026-11-17 发布仓 revert：镜像 tag 由 release-20261110 回滚为 release-20260901，并附回滚操作记录。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证回滚重现（rollback_regress）正向判定：曾 verified_fixed + 明确回退证据 + 同一环境再次出现。 |
| 预期缺陷数 | 1（X6，同一缺陷） |
| 预期筛选 | S1 首报=candidate；S2=candidate 且归并到 X6（同一现象、同一环境、同根因）；S3=evidence（回退证据，role=status_evidence）。 |
| 预期归并 | S2 归并到 X6（merge_confidence=high：同现象+同环境+时间连续），不新建第二个缺陷。 |
| 预期证据归属 | S1 修复=primary_fix；S1 复测回执=status_evidence（environment=soso-prod）；S2=report；S3=status_evidence（回退证据）。 |
| 预期复发定性 | 回滚重现：S1 曾到 verified_fixed 且验证覆盖 soso-prod，S2 在同一 canonical_name 再次独立出现，S3 提供镜像 tag 回退证据 → kind=rollback_regress，计入广义复发。recurrence_events=1，recurrence_by_subtype={repeat_after_fix:0, rollback_regress:1}，independent_occurrences=2（first + rollback_regress）。 |
| 判定依据 | S1 有现场复测通过的验证证据且登记 soso-prod；S2 时间/现象独立；S3 有明确回退证据（镜像 tag 变更 + revert 记录）。 |
| 否定项 | ①不得仅凭『旧镜像』字样判回滚（必须同时有曾 verified_fixed 与回退证据）；②不得把回滚动作记成产品缺陷或 fix_action；③不得因回滚把 kind 改判为 repeat_after_fix；④不得新建重复缺陷。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 3, "fix_actions": 1, "independent_occurrences": 2, "repeat_unresolved_events": 0, "unresolved_open_bugs": 1, "recurrence_events": 1, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 1}, "related_cases": 0, "bugs_without_occurrence": 0, "verified_environments": ["soso-prod"], "coverage": "时间窗 2026-09-02~11-18；来源 synthetic；时间精度：日级；未覆盖：无（回退与验证证据齐备）；未知：无"} |
| 规则引用 | references/recurrence-rules.md §2.4/§2.6/§3.2/§3.6；references/output-schema.md §5/§8/§10.5 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-R5-1 | recurrence | 判定前核对 verified_fixed 证据覆盖 soso-prod（按 canonical_name） | true | recurrence-rules §2.6/§4 步骤 2 |
| TC-R5-2 | recurrence | occurrence.kind == rollback_regress，且 basis 引用回退证据（镜像 tag 变更 + revert 记录） | true | recurrence-rules §2.4 |
| TC-R5-3 | count | recurrence_events == 1 且 recurrence_by_subtype == {repeat_after_fix:0, rollback_regress:1}（总数与子类型同报） | true | recurrence-rules §3.2 |
| TC-R5-4 | count | independent_occurrences == 2（first + rollback_regress） | true | recurrence-rules §3.1 |
| TC-R5-5 | filter | 不得仅凭『部署漂移/旧镜像』字样定性；必须同时具备『曾 verified_fixed』与『回退证据』 | true | recurrence-rules §2.4 |
| TC-R5-6 | count | 回滚动作不计入 fix_actions（fix_actions == 1，只有 09-08 修复） | true | recurrence-rules §3.6 |
| TC-R5-7 | negative | 未新建重复缺陷；未把回滚记为产品缺陷 | true | recurrence-rules §2.4/§2.5 |

### TC-R6　事件去重（精度混合）

- **类型**：synthetic（构造边界案例）
- **输入摘要**：S0 主记录 DC-9001（历史库已存在，项目时区 Asia/Shanghai）。S1 OC-alt-1 observed_at='2026-10-12'（仅日期），evidence=E1（群报障原文+截图，role=report）。S2 OC-alt-2 observed_at='2026-10-12T09:14:00+08:00'，evidence=E1（同一截图）+E2（MR-700，primary_fix）。S3 OC-alt-3 observed_at='2026-10-12'（仅日期），evidence 仅 E2（MR-700，primary_fix）。S4 OC-alt-4 observed_at='2026-10-13T10:05:00+08:00'，evidence=E3（新的报障原文+不同复现操作，环境 raw_text='客户现场'），与 E1 无交集。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证事件去重细则：日期精度与精确时间混合、仅 report 证据计入交集、反证阻断、原始精度保留、歧义进复核。 |
| 预期缺陷数 | 1（DC-9001） |
| 预期筛选 | 4 条 occurrence 均属 DC-9001；E1 计入 report 交集资格，E2 为 primary_fix、E3 为新的 report。 |
| 预期归并 | 不涉及缺陷归并；S1/S2 合并为同一事件，S4 保持独立，S2/S3 进复核。 |
| 预期证据归属 | E1=report；E2=primary_fix；E3=report。 |
| 预期复发定性 | 先按主记录 DC-9001 聚合，再在缺陷内做事件去重：S1/S2 同自然日且共享 role=report 的 E1 → 合并为 1 次（已确认合并 1 组）；S2/S3 只共享 E2（primary_fix，修复证据）→ 不构成交集、不得自动合并，也说不清是两次 → 进 recurrence_check（待复核 1 条）；S4 有独立触发证据（新报障原文/不同复现/不同环境）→ 反证阻断，保持独立 1 次。已确认独立发生 2 次，另有 1 条待复核不并入确定性计数。 |
| 判定依据 | S1/S2 同自然日（Asia/Shanghai）+ 共享 E1（现象首报类）；S2/S3 仅共享 MR；S4 有独立报障与不同复现条件。 |
| 否定项 | ①不得仅因同日就合并；②不得把只共享 MR/Commit 的记录当作交集；③不得仅因交集缺失就判两次独立发生；④不得补造缺失的时分秒；⑤不得物理删除原始 occurrence 记录。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 4, "fix_actions": null, "independent_occurrences": 2, "independent_occurrences_pending_review": 1, "repeat_unresolved_events": 0, "unresolved_open_bugs": 1, "recurrence_events": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "related_cases": 0, "bugs_without_occurrence": 0, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-10-12~10-13；来源 synthetic；时间精度：2 条仅日期 + 2 条秒级（混合）；已合并 1 组、待复核 1 条；无 observed_at 的记录 0 条；未知：环境身份（仅 raw_text）"} |
| 规则引用 | references/recurrence-rules.md §3.8（判定顺序 1–6）；config/default.json recurrence.event_dedupe；references/output-schema.md §5/§10.4 |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-R6-1 | integrity | 先去重前按主记录聚合、再在缺陷内去重（顺序不跳步） | true | recurrence-rules §3.8 步骤 1 |
| TC-R6-2 | count | S1/S2 合并为 1 次；已确认合并组数 == 1 | true | recurrence-rules §3.8 步骤 2/3 |
| TC-R6-3 | recurrence | S2/S3 仅共享 primary_fix 证据 → 不得自动合并，进 recurrence_check（待复核 1 条） | true | recurrence-rules §3.8 步骤 3/5 |
| TC-R6-4 | recurrence | S4 有独立触发证据（新报障原文/不同复现/不同环境）→ 反证阻断，不与 S1/S2 合并 | true | recurrence-rules §3.8 步骤 4 |
| TC-R6-5 | integrity | 原始 observed_at 精度保留（S1/S3 仍为日期，不补时分秒） | true | recurrence-rules §3.8 步骤 2/6 |
| TC-R6-6 | integrity | 同时披露已确认合并数、待复核数、coverage（混合精度条数/无日期条数） | true | recurrence-rules §3.8 |
| TC-R6-7 | negative | 未仅因同日合并；未仅因交集缺失判两次独立发生；未删除原始 occurrence | true | recurrence-rules §3.8 步骤 5/6 |

### TC-R7　归并迁移（occurrence）

- **类型**：synthetic（构造边界案例）
- **输入摘要**：S0 主记录 DC-9001（已存在，含 OC-0001 first 2026-10-12T09:14）。S1 别名记录 DC-9002（同一缺陷『导出乱码』，2026-10-20 登记，merge.merged_into=DC-9001，confidence=high），别名下有 OC-0007 kind=repeat_unresolved observed_at=2026-10-19T11:00，证据 E9（新截图+新时间，与原次无交集）。S2 归并审计：原编号、证据映射、merged_at 保留。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证归并时 occurrence 只迁移不重判、别名不重复计数、审计信息不丢失。 |
| 预期缺陷数 | 1（DC-9001，DC-9002 为别名） |
| 预期筛选 | DC-9002 及其 occurrence 不新建候选，按归并迁移处理。 |
| 预期归并 | DC-9002 → DC-9001（merge_confidence=high），occurrence 全部迁移，别名冻结、只追加证据归档。 |
| 预期证据归属 | E9 迁移后在主记录上 role=report；不新增修复类 role。 |
| 预期复发定性 | 迁移后主记录 occurrences = OC-0001(first) + OC-0007(repeat_unresolved，kind 保持原样)；归并动作不重判、不补记复发；independent_occurrences=2（不是 3/4）；recurrence_events=0（该缺陷从未 verified_fixed，repeat_unresolved 不计复发）。 |
| 判定依据 | dedup §4.3 规定归并时 occurrence 只迁移不重判；OC-0007 与原次时间不同、证据无交集，不构成同一事件。 |
| 否定项 | ①不得在归并动作内把 kind 改判为 repeat_after_fix/复发；②不得删除别名记录或重排 occurrence 编号；③不得主记录与别名各自计数（2 而非 3/4）；④不得把归并本身当复发。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 2, "fix_actions": 1, "independent_occurrences": 2, "repeat_unresolved_events": 1, "unresolved_open_bugs": 1, "recurrence_events": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "related_cases": 0, "bugs_without_occurrence": 0, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "时间窗 2026-10-12~10-20；来源 synthetic；时间精度：秒级；未覆盖：验证证据；未知：环境身份；别名 1 条"} |
| 规则引用 | references/dedup-rules.md §4.3；references/recurrence-rules.md §2/§3.1；references/output-schema.md §3（merge） |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-R7-1 | merge | 别名 occurrence 全部迁移到主记录，无孤儿 occurrence | true | dedup-rules §4.3 |
| TC-R7-2 | merge | 迁移后 OC-0007.kind 仍为 repeat_unresolved，未在归并动作内改判 | true | dedup-rules §4.3 |
| TC-R7-3 | recurrence | 归并未补记任何一方复发；recurrence_events == 0 | true | recurrence-rules §3.4；dedup §4.3 |
| TC-R7-4 | count | 按主记录聚合，independent_occurrences == 2（别名不重复计数） | true | recurrence-rules §3.1；dedup §4.3 |
| TC-R7-5 | integrity | 别名编号、证据映射、发生记录审计保留，报告列出别名与归属 | true | dedup-rules §4.3 |
| TC-R7-6 | negative | 未删除别名记录、未重排 occurrence 编号、未把归并当复发 | true | dedup-rules §4.3 |
| TC-R7-7 | integrity | 如需重判，只能用主记录全量证据按 §2/§3.8 单独判定，不在归并内顺手改判 | true | dedup-rules §4.3；recurrence-rules §3.8 |

### TC-R8　运行边界（offline）

- **类型**：synthetic（构造边界案例）
- **输入摘要**：S0 config/default.json（meta.skill_version=V0.1.3，storage.storage_root=null，mode_default=offline）。S1 项目配置 soso_data_center.json 含 5 处 __TBD__（仓库 ID、群 ID、环境名、编号前缀、时区）。S2 离线输入包：1 条修复类 commit（正文含现象+修复）、1 条 test commit（body 空）、1 条禅道 active 快照（模拟输入，非正式库）。S3 运行参数：mode=offline，offline_root=/tmp/offline-root，run_id 由运行方指定。

| 项目 | 内容 |
|---|---|
| 测试目标 | 验证 offline 模式写入隔离、临时编号纪律、配置降级与版本一致性。 |
| 预期缺陷数 | 1（修复类 commit 描述的现象） |
| 预期筛选 | 修复类 commit=candidate（role=primary_fix）；test commit=template（triage_reason=template_noise）；禅道快照=status_evidence。 |
| 预期归并 | 仅 1 个缺陷，无归并。 |
| 预期证据归属 | 修复类 commit=primary_fix；禅道快照=status_evidence；test commit 不入缺陷。 |
| 预期复发定性 | 无复发（仅一次首次发生）；occurrence.kind=first；不复核。 |
| 判定依据 | offline 模式按 SKILL §2 第 5 条加载全部核心文件；写入边界见 output-schema §1.2/§1.3；编号纪律见 execution-rules §5。 |
| 否定项 | ①不得写正式 data/<project>/ 或 state.json；②不得分配任何正式编号；③不得把 __TBD__ 当真实参数；④不得因 storage_root=null 仍启动正式采集/入库；⑤不得把本地目录当跨任务持久化。 |
| 计数（十项） | {"confirmed_defects": 1, "suspect_defects": 0, "evidence_items": 3, "fix_actions": 0, "independent_occurrences": 1, "repeat_unresolved_events": 0, "unresolved_open_bugs": 0, "recurrence_events": 0, "recurrence_by_subtype": {"repeat_after_fix": 0, "rollback_regress": 0}, "related_cases": 0, "bugs_without_occurrence": 0, "verified_environments": "未知（输入未给出可归一环境；按 §3.7 报未知，不写 0）", "coverage": "offline 试验；时间精度：秒级；未覆盖：正式模式（collect/process/analyze）行为；未知：项目参数（__TBD__）", "formal_numbering_attempts": 0} |
| 规则引用 | references/output-schema.md §1.2/§1.3/§2；references/execution-rules.md §4/§5/§9/§10；SKILL.md §2/§3；config/default.json meta/storage |

**断言**

| ID | 阶段 | 检查项 | 期望 | 规则 |
|---|---|---|---|---|
| TC-R8-1 | integrity | 正式 state.json/library/raw 与编号计数器在运行前后字节不变（不存在写入） | true | output-schema §1.2/§1.3 |
| TC-R8-2 | integrity | 输出中无 DC-/EV-/OC-/RV-/TR- 正式编号，所有对象为 offline-<run_id>- 临时键 | true | output-schema §1.2；execution-rules §5 |
| TC-R8-3 | integrity | 产物只落 <offline_root>/<run_id>/，含 runs/<run_id>.json、reports/ 与自检报告 | true | output-schema §1.3 |
| TC-R8-4 | integrity | 运行声明 skill_version == V0.1.3，与 SKILL/规则文件版本头一致 | true | SKILL.md §2；config/default.json meta |
| TC-R8-5 | filter | 项目配置含 __TBD__ → 按不完整配置处理（只按通用默认值跑，报告列缺失项），不把 TBD 当真实参数 | true | SKILL.md §2/§7 |
| TC-R8-6 | integrity | storage.storage_root=null → 仅 offline，不启动正式采集/入库/编号分配 | true | execution-rules §4 |
| TC-R8-7 | integrity | quality-checklist 按 offline 模式执行并出结论，不自称完成正式测试或独立测试通过 | true | SKILL.md §6；quality-checklist |
| TC-R8-8 | negative | 未读写正式水位、未改案例库、未把本地目录当跨任务持久化 | true | execution-rules §4/§10 |

## 8. 覆盖矩阵

| 场景 | 案例 | 覆盖内容 | 规则 |
|---|---|---|---|
| 数据清洗（纯 Merge/同步/无关 chore） | TC-001 | 已用真实证据覆盖 |  |
| Commit 筛选：Merge 正文独有 Bug 信息 | TC-002 | 已用真实证据覆盖 |  |
| Commit 筛选：feat 中隐藏 Bug 修复 | TC-003 | 已用真实证据覆盖 |  |
| Commit 筛选：无前缀缺陷修复 + 编号归并 | TC-004 | 已用真实证据覆盖 |  |
| 跨源去重：一缺陷多提交/复测反馈 | TC-005 | 已用真实证据覆盖 |  |
| 问题链拆分：相同业务流程不同缺陷 | TC-006 | 已用真实证据覆盖 |  |
| 证据归属：多域整改批 vs 单缺陷多修法（不强制数量） | TC-007 | 已用真实证据覆盖（V1.3 修订计数口径） |  |
| 复发识别（负向）：持续未解决/反复跟进 ≠ 复发 | TC-008 | 已用真实证据覆盖（V1.3 增计数分离断言） |  |
| 信息完整性：证据不足/状态不明 | TC-009 | 已用真实证据覆盖 |  |
| 群聊提取：跨多消息归并同一缺陷（环境漂移） | TC-A1 | 已用真实证据覆盖 |  |
| 群聊提取：一条长消息拆多缺陷 + 性能/边界/执行问题分口径 | TC-A2 | 已用真实证据覆盖（V1.3 修订计数口径） |  |
| 群聊提取：需求→修复未生效 | TC-A3 | 已用真实证据覆盖 |  |
| 群聊提取：部署 pin 漂移（二次上报先查部署形态） | TC-A4 | 已用真实证据覆盖 |  |
| 群聊提取：环境闪断不记缺陷 + 提示缺陷单独登记 | TC-A5 | 已用真实证据覆盖 |  |
| 群聊提取：证据缺口 partial + 平台播报不记缺陷 | TC-A6 | 已用真实证据覆盖 |  |
| 群聊提取：上游更正的事实版本管理 | TC-A7 | 已用真实证据覆盖（V1.3 补 G25 输入） |  |
| 群聊提取：验收通过≠零遗留、执行问题/缺陷/观察项三分 | TC-A8 | 已用真实证据覆盖（P-103 已核实 = 禅道 #15057） |  |
| 复发识别（正向）：已修复验证通过后 reopen 再发生 | TC-R1 | 已合成覆盖（synthetic） |  |
| 复发识别（正向）：发布回滚/未部署到位导致重现 ≠ 复发 | TC-R2 | 已合成覆盖（synthetic） |  |
| 复发识别（正向）：同类现象不同根因 → 两条独立缺陷 | TC-R3 | 已合成覆盖（synthetic） |  |
| 历史提交处理：悬空 vs 可达去重/独有缺陷 | — | 本轮未覆盖：需对仓库 refs/reflog 做可达性分析，未采集，留待下一批 |  |
| 分环境验证适用范围按 canonical_name 判定（同分类不同环境） | TC-R4 | verified_fixed 只覆盖 test-a；test-b 不继承；未覆盖环境进 recurrence_check | recurrence-rules §2.6/§4；output-schema §8/§10.5 |
| 回滚重现正向（rollback_regress） | TC-R5 | 曾 verified_fixed + 回退证据 + 同环境再出现 → 计入广义复发，子类型分报 | recurrence-rules §2.4/§3.2 |
| 事件去重（日期精度混合 / report 交集 / 反证阻断） | TC-R6 | 同日合并仅认 report 交集；仅共享修复证据不合并；反证阻断；歧义进复核；原精度保留 | recurrence-rules §3.8 |
| 归并时 occurrence 只迁移不重判 | TC-R7 | 迁移不改 kind、不补记复发、别名不重复计数、审计保留 | dedup-rules §4.3 |
| offline 写入隔离与临时编号纪律 | TC-R8 | 不写正式库/水位/编号；offline- 前缀；__TBD__ 降级；版本一致性 | output-schema §1.2/§1.3；execution-rules §4/§5/§9 |

## 9. 证据缺口

1. 历史提交处理（悬空/可达）：本地克隆仅含单分支历史，未做 refs/reflog 可达性分层分析，本批未出该类案例。
2. MR 评审/审批流水（评论、diff 讨论）未随证据包采集；如需测『MR 讨论抽取』场景需另补。
3. 附件类证据缺失已逐条标注（G10 截图、#15036 files=[]、E14 自述缺失项、G26 外发明细），不得补造。
4. 群聊场景采样限于「数据小队」群 2026-11-16~11-24 窗口；撤回/编辑消息、跨群转发等形态未采样。
5. TC-R1/R2/R3 为 synthetic：其构造输入与答案均需评审确认后才可进入正式判分集。
6. 全部『预期结果/断言』为按规则推导的候选参考答案，须人工确认；未经确认不得作为自动判分基准。
7. 案例应作为独立测试集存放于 skill-evaluation/test-inputs 与 expected-results，不并入技能 examples/confirmed-cases。
8. 分环境验证缺少真实跨环境证据（现有 TC-R1/R2/R4/R5 均为 synthetic），真实案例未采集到带 canonical_name 的复测记录。
9. 事件去重缺少真实同日多源 occurrence 数据（TC-R6 为 synthetic），真实案例尚无同日两条以上 occurrence。
10. 归并迁移缺少真实别名记录（TC-R7 为 synthetic），现有真实案例未出现 merge.merged_into 与 occurrence 并存。
11. offline 隔离缺少真实运行留痕（TC-R8 为 synthetic），本轮为静态规则推导，未实际执行。
12. coverage / verified_environments 无结构化字段定义（见《规则问题与待确认清单-V1.4》Q-09/Q-10），只能用文本断言判分。

## 10. 关联文件

| 文件 | 用途 |
|---|---|
| `candidate-cases-V1.4.json` | 带注释的完整候选包（证据+预期+断言+规则引用+覆盖），用于评审与维护 |
| `test-inputs-V1.4.json` | 独立测试输入（仅原始数据与必要元数据；real_inputs / synthetic_inputs 分区），喂给被测 Skill |
| `expected-results-V1.4.json` | 候选参考答案（expected_* + expected_counts + assertions + rule_refs + judge_notes），判分/人工确认用 |
| `案例集修订说明-V1.4-20261126.md` | 逐项要求→落实对照 + 逐案例检查记录 |
| `规则问题与待确认清单-V1.4-20261126.md` | 规则矛盾/无法形成确定预期的点（不擅自改规则） |
| `一致性检查结果-V1.4-20261126.md` | 静态一致性检查（0 error / 0 warning） |

