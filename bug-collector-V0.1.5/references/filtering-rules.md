# filtering-rules.md — 清洗、筛选与缺陷候选提取规则

> 版本：V0.1.5（2026-11-26，P0 整改：新增 filter_decision=context、非缺陷事件留痕、MR 多问题域逐域候选）。
> 引用入口：`SKILL.md` §4.2「数据清洗与规则筛选」与 §4.3「语义分析与 Bug 候选提取」。
> 加载时机：`process` 模式，对采集批次做清洗、分流与候选提取；`offline` 模式同样加载本文件。
> 分工边界：字段结构与编号见 `references/output-schema.md`；「是否同一缺陷」的判定见 `references/dedup-rules.md`。本文件负责——**把原始记录变成干净的候选，并完成第一次分流**。

## 1. 角色边界：规则初筛 vs 语义判定
- 规则层（正则/关键词/字段条件）只做**分流与优先级**，输出 filter_decision 与理由；**规则命中与否永远不是缺陷成立与否的结论**。
- 缺陷是否成立由语义分析判定；语义分析必须读过上下文，不能只看命中片段。
- 确定性强的清洗（时间归一、实体解码、记录去重）由标准库脚本完成；带判断的筛选条件写在配置里可复查，不硬编码进流程。
- **未命中规则的记录默认保留**：规则层只排除「已确认无关」的记录；无法确认无关的进入低优先级语义分析（§3.1）。

## 2. 通用清洗（三源共同）
1. **时间归一**：统一 ISO 8601 北京时间；「今天/昨天/上周五」等相对时间在保留原文的同时，按**消息发送日**折算为绝对时间（历史日按整日 00:00–23:59 口径）。
2. **实体解码**：禅道 steps 里的 HTML 实体与标签（`&nbsp;` `&lt;` `&gt;` `&amp;`、`<br>`）解码复原；钉钉 @ 占位展开成姓名。
3. **重复采集记录**：同源同幂等键出现多条快照时，保留最新快照并可保留历史版本；**跨源同内容不属于重复采集**（群消息 ≠ 禅道单 ≠ Commit，各自成立）；**不同仓库的相同 SHA 也不是重复采集**（见 `references/collection-rules.md` §4.4）。
4. **模板与同步内容打标**：机器人任务回执（如「任务：……」正文 +「在圈圈查看任务」尾注）、push 活动流、CI/部署通知、纯 merge/sync 记录——标记 `template/sync`，默认不生成候选，但保留作上下文证据。只有确认不含业务描述时才标 template/sync。
5. **无关内容标 noise**：闲聊、日程安排、招聘、与业务无关的转发，确认无关后记录排除理由。
6. **异常样本不丢弃**：字段缺失统一 null；乱码/空标题等异常标记后进复核池——异常本身常是缺陷线索（如上报内容为空就是缺陷现象）。

## 3. 预筛选分流

### 3.1 分流结果（所有源统一）
| filter_decision | 含义 |
|---|---|
| `candidate` | 进入语义分析；`priority=low` 表示规则未命中或信号弱，仍需语义分析，不得直接排除 |
| `evidence_only` | **已确认能指向某条已登记缺陷**，不单独成候选，作为该缺陷的潜在证据；必须填写 `linked_bug_id` 与 `evidence_role` |
| `template` / `sync` / `noise` | **已确认**排除出候选；原记录与理由保留，可重查。`template` 含纯合并模板与机器人回执，`sync` 含发布/部署/同步通知 |
| `context` | **非缺陷事件**（环境事件、平台播报、证据缺口、需求、操作指令、执行回执、性能问题、能力边界、统计口径差异、一次性整改）；原记录与理由保留，并在 `context_events.jsonl` 结构化登记（V0.1.5） |

- **默认放行原则**：规则未命中且无法确认与缺陷无关的记录，一律 `candidate` + `priority=low` + `triage_reason=unmatched_low_priority`，进入低优先级语义分析。**不得因为「没命中关键词」「格式不规范」「发送人是机器人」就直接排除。**
- `evidence_only` 需要能指向具体已登记缺陷；指不出来时按 `candidate` 处理。
- **无法关联已知缺陷的上下文记录**：纯合并、纯部署、纯同步记录若既不能指向已登记缺陷、也不含业务描述，标 `template` / `sync` 并记 `triage_reason=context_only`，原记录保留作上下文证据；**不得为它们生成缺陷候选**，也不得为了让其「有用」而写成 `evidence_only`。
- **阶段枚举分离**：`filter_decision` 只回答「这条记录怎么分流」，不回答缺陷是否成立（`category`）、是否与历史重复（`match_result`）或是否复发（`occurrence.kind`）；四组枚举不得混用（`references/output-schema.md` §10.2.2）。
- **非缺陷事件不得丢弃（V0.1.5）**：`context` / `template` / `sync` / `noise` 的每条记录都要在 `process/<batch_id>/context_events.jsonl` 留一条结构化记录（或对 `noise` 写明 `noise_scope=confirmed_irrelevant` + 理由）。`context_events` 字段：`event_id`、`event_type`、`source_key`、`summary`、`reason`、`evidence_ids`（可空）、`created_at`；`event_type` 枚举见 `references/output-schema.md` §10.2。**「没建缺陷」不等于「不用记录」**，否则部署闪断、平台播报、证据缺口会在流程里消失。
- **一条修复记录多个问题域（TC-007）**：Merge/MR 正文并列多个问题域、但各域没有独立现象证据时，逐域登记 `category=suspect` 候选并标 `unconfirmed`，不合成单一缺陷、不自动归并、不生成 occurrence；缺陷数量给 `undetermined_until_evidence` 或区间。已有禅道/缺陷锚点的域可确认，其余进复核。
- 被排除的记录必须能按理由追溯与重跑；排除理由不足以复核时，降级为 `candidate`。

### 3.2 钉钉群消息
- 正向信号：bug、缺陷、报错、异常、失败、复现、挂了、回滚、修复、阻塞、卡住、数据不对、对不上、环境失效、禅道号（`#数字` 或 bug 链接）、MR/commit 链接、附截图的现象描述。
- 负向信号：周报、值班、发布通知、日程、招聘、纯寒暄——仅作为**降权依据**，确认与缺陷无关后才可标 noise。
- 命中后先拉前后文（`references/collection-rules.md` §2.3）再判；未命中不等于排除，仍按 §3.1 默认放行原则进入低优先级语义分析。
- 机器人的任务回执：若回执正文包含缺陷现象、复现信息或修复结论，按 `candidate` 处理，不因 `is_robot=true` 排除。

### 3.3 禅道记录
- 禅道本身就是缺陷库：**全部记录默认 candidate**，不做关键词预筛。
- 仅两类由预筛降级，且都要给判定依据：① 历史库已确认的建单链路测试/探针单（标 template，除非有新现象描述）② 去重规则已认定的同源重复登记。不得凭标题主观判断。

### 3.4 GitLab 提交与 MR
- 前缀优先级：`fix`/`bugfix`/`hotfix` 优先分析；`feat`、`refactor`、`test`、`chore`、`ci`、`docs`、`style`、`perf` 及不规范/自造前缀**按实际内容判断**——`feat` 里可能藏着缺陷修复，`fix` 也可能是误标。
- Merge commit 与普通 commit 都要分析完整 message；合并类型按**父提交数量 ≥ 2** 识别（不限定恰好两个父提交），title 前缀只是参考。
- **MR 独立参与分流**：即使没有对应的 commit message 引用，也要按 MR 自身标题与描述评估；`orphan_mr`（无对应 Commit）不得跳过（见 `references/collection-rules.md` §4.3）。
- 内容拆成三类分别评估：①合并模板文字（`Merge branch 'x' into y`）②MR/工单引用（`!123`、`#456`、链接）③业务描述正文。只有①②没有③的记录：标 `template`（纯合并）或 `sync`（部署/同步），`triage_reason=context_only`，保留为上下文证据但不生成候选；若①②能指向具体已登记缺陷，可改记 `evidence_only` 并填 `linked_bug_id`；**若①②指向的 MR 描述里含业务缺陷描述，则回到 MR 自身按 ③ 评估，不能因为 commit message 只有引用就漏掉**。
- **MR 引用未核实**：引用的 `!iid` / MR 链接尚未按 `references/collection-rules.md` §4.3 独立采集并核对归属时，记 `triage_reason=mr_ref_unverified`，只作待核查线索；不得声称已有 MR 快照，也不得据以归并（必要时建 `review_queue` 的 `field_verify`）。
- 单个提交或单个 MR 混多个主题：按段落拆开分别评估。
- 不可达提交按 `references/collection-rules.md` §4.4 处理后进入同一分流，不孤立删除。

## 4. 语义分析与候选提取（SKILL.md §4.3 细则）

### 4.1 判定分类（六类）
| 类型 | 判定要点 | 处理 |
|---|---|---|
| 明确缺陷 | 有实际现象 + 有预期依据，二者冲突 | 生成或并入候选（category=defect） |
| 疑似缺陷 | 现象可疑，但缺预期依据/复现/环境信息 | 生成候选，category=suspect，缺失项进复核池 |
| 修复/部署证据（已登记缺陷） | commit、MR、禅道解决/关闭、上线或回滚记录，能对应到历史库已有缺陷 | 不开新候选；按内容挂 role（见下表），不是一律 `status_evidence` |
| 修复类记录（历史库未登记） | 修复类 Commit/MR/禅道解决记录描述了具体现象、根因或改动目的，但历史库没有对应缺陷 | **生成独有缺陷候选**：现象与预期清晰 → category=defect；信息不足 → category=suspect；不得一律当作关联证据 |
| 需求/优化 | 用户主动要的新能力或体验改进，未描述错误行为 | 不算缺陷；另存为需求线索供 analyze 参考 |
| 无关信息 | 已确认与缺陷无关 | noise / template |

- **红线 1：缺少预期依据时不得把新增功能直接认定为 Bug**；「建议/希望/最好」类表述优先归需求侧，除非同时描述了错误行为。
- **红线 2：修复类记录不得因为「是修复/是已合并状态」就默认它对应历史库里的某条缺陷。** 先做归属核对：能指向已登记缺陷才挂证据；指向不了或指向的缺陷与描述不符，必须生成新的缺陷候选或疑似候选，并在 `related` 中登记与疑似原缺陷的关系。
- 部署、回滚、发布记录若不含任何缺陷现象描述，只作 `status_evidence`，不生成候选；含现象描述时按修复类记录同口径处理。
- **角色分配口径**（role 写在 `evidence.bug_links[]`，不是证据固有属性）：直接修该缺陷且归属已核验 → `primary_fix`；同链路顺带改动或跟进补修 → `related_fix`；部署/发布/复测/关闭/重新激活回执 → `status_evidence`；截图、日志、文档里的上下文引用 → `background`；用户首报或复述 → `report`。同一证据对不同缺陷可用不同 role。

### 4.2 候选字段提取
按 `references/output-schema.md` 的缺陷结构逐字段填写，规则：
- 标题自拟，格式 `[模块] 现象摘要`，不整句照抄原文。
- 只填有证据支撑的字段；无依据字段留空，并把字段名列入 review.fields_unverified。
- 推断必须标注：未做代码级确认前 root_cause.status=inferred；环境缺失时把原句存入 environment.raw_text；环境归属以项目 `environment_registry` 的 canonical_name 归一（同分类 ≠ 同环境，见 `references/recurrence-rules.md` §2.6）。
- 观察时间取证据中最早可信时间；「recently/忽然」等模糊时间保留原文并标注近似。
- 一条记录包含多个独立缺陷时拆分候选（各候选引用同一 source）；多条记录同讲一件事（谁首报、谁补充、谁确认修复）时并入同一候选的证据列表。
- 候选写入 `process/<batch_id>/candidates.jsonl`（结构见 `references/output-schema.md` §1.1、§4），带稳定候选键和来源幂等键，便于重放与匹配。

### 4.3 上下文使用
- 修复确认语（「发了」「好了」「重启后恢复」）是状态证据，不构成新候选——但仅限能对应到具体缺陷时；对应不上时按疑似候选或复核项处理。
- 同现象的多人复述（「我也遇到」）是发生记录的素材，不是新缺陷。
- 相对时间按消息发送日折算；跨天连续话题按首报时间记 first_observed_at。
- 禅道状态变为「重新激活」只作为复发线索，不直接生成新的发生记录，也不生成新缺陷（见 `references/dedup-rules.md` §4.2 与 `references/output-schema.md` §8）。

## 5. 项目专项规则（SKILL.md §4.2 首段的落地）
- 首次接入一个项目或新数据源时，先做样本观察（字段命名、消息习惯、常见误命中），把结论写成 `config/projects/<project>.json` 的 overrides 建议（词表、排除词、模块名映射、编号区间、延迟特征），**经项目方确认后才启用**。
- 项目规则只做叠加，不覆盖通用红线（「缺预期不算 Bug」「人工结论不预填」「未命中不直接排除」不允许被项目规则推翻）。
- 项目级经验与异常样本沉淀到 `examples/<project>/project-rules.md`；已确认正反例存 `confirmed-cases.md`。数据中心等项目的实测注记只能放这里，不得写进通用规则。

## 6. 筛选留痕
- 每条记录的 filter_decision、priority、triage_reason、reason 全部写入 `process/<batch_id>/filter_results.jsonl`（结构见 `references/output-schema.md` §1.1、§9）。
- **过程可观察性**：同时记录 `record_type`（commit_normal / commit_merge / mr / message / zentao_bug / file）与 `analyzed_fields`（实际读到的内容，如 `title`、`message_body`），使离线测试可核查「是否读了完整 Commit Message、是否识别 Merge、依据是什么」；每条记录还写 `candidate_ids`，与候选的 `source_refs` 双向回查，避免只凭最终缺陷数量反推过程正确。
- 排除记录留在原批次文件里，不物理删除；候选、匹配结果、状态流转分别落在 `candidates.jsonl`、`match_results.json`、`library/transitions.jsonl`，保证从原始记录到缺陷的每一步可追溯。
- 同一批次可重放；decision 发生变化时保留变更历史（上一版 decision + 变更 run_id + 原因）。

## 7. 自检（对照 SKILL.md §6）
- 排除记录全部有理由；抽查排除项中是否混入真缺陷；未命中规则的记录确已进入低优先级语义分析，而非被丢掉。
- 修复/部署证据没有被误开成候选；历史库未登记的修复类记录没有被漏成「仅关联证据」。
- 需求类没有误标缺陷；模板与同步内容的计数与原文对得上；候选标题没有整段照抄原文。
- 留空的字段都有对应的 fields_unverified 标记，推断与已确认事实分列。
- 筛选结果、候选与匹配结果都能按 run_id / batch_id 回溯到原始证据。
