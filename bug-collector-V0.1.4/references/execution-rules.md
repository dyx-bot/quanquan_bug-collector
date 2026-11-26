# execution-rules.md — 分批执行、水位推进、幂等、持久化与失败恢复规则

> 版本：V0.1.4（2026-11-26，首轮离线测试前最小范围修订：新增运行开始输出 effective-config.json 与 offline TEST 前缀纪律）。
> 引用入口：`SKILL.md` §3 执行模式、§5「增量执行与异常处理」、§7 配套文件表。
> 加载时机：正式 `collect / process / analyze` 必读；`offline` 不读写正式水位与持久化（本文 §2 水位、§3 持久化、§5 编号部分对 offline 按隔离口径 N/A），但 §1 执行预算与 §10 的输出纪律对 offline 同样适用。
> 分工边界：批次与完整性判定见 `references/collection-rules.md` §6；水位、缺口与计数器字段见 `references/output-schema.md` §6；模式写权限见 `references/output-schema.md` §1.3；事件去重与统计口径见 `references/recurrence-rules.md` §3。本文回答——**怎么分批、水位何时推进、写到哪里、失败后怎么续跑**。

## 1. 执行预算（硬约束）

- 单条命令 `timeout ≤ 60s`；单轮响应预算 3 分钟（180 秒）；不启动后台任务。
- 超预算或临近超时时，先在**安全批次边界**停下：该批数据文件与 manifest 已完整落盘、run log 已更新，才允许停。
- 每个批次必须可以在预算内独立完成「落盘 + manifest + 水位核验」；宁可多批不大批。
- 中途放弃或被截断的批次一律标 `partial`，进入 pending_batches，不冒充已完成。
- 交付前必须完成 `references/quality-checklist.md` 按模式的检查模块，再把本次结果报为完成；自检本身未完成的检查项不得标 PASS。

## 2. 分批规则

- 拆分维度：`数据源 × 日期窗 ×（接口类型）`；批次不跨源、不跨口径。
- `batch_id = <source>-<YYYYMMDD>-<HHMM>-<seq>`（如 `gitlab-20261124-1800-01`），后续 manifest、process 目录、match 结果都以它回查。
- 每批产物：数据文件 + batch manifest（结构见 `references/collection-rules.md` §6.2）同目录存放；每批完成立即写 manifest，不得攒批后补写。
- 批次内不换查询口径（collection-rules §1.5）；要扩大/缩小范围另开批次并注明原因。
- 批次顺序：优先补齐 `unresolved_ids` 与 pending_batches 中旧缺口，再开新窗口；**缺口未补齐前，缺口之后的窗口不得开新批次**（缺口阻断）。

## 3. 水位推进与幂等（正式模式）

### 3.1 双水位独立维护

- `collected_through`（原始数据完整落盘到哪）与 `processed_through`（筛选分析入库到哪）分立推进，见 `references/output-schema.md` §6；处理跟不上采集是常态。
- **collected_through 推进条件（须同时满足）**：
  1. 本源当前批次 `completeness=complete`（无未解释缺口、`unresolved_ids` 为空、`failed_ids` 全为 `not_found_confirmed`）；
  2. 批次数据 + manifest 已持久化并回读验证；
  3. 该批自检相关项无未决 FAIL。
- **processed_through 推进条件（须同时满足）**：
  1. 对应原始批次已完整处理：`filter_results / candidates / match_results` 落盘并回读验证；
  2. 该批处理的 quality-checklist §4 / §5 / §6 适用项无未决 FAIL；
  3. `collected_through` 已覆盖该批（处理水位不得超过采集水位）。
- **缺口阻断**：`gaps` 非空或批次 `unresolved_ids` 非空时，两水位都不得越过缺口；partial 批次挂起，补齐并确认后才能推进。
- 采集失败批次不推进其窗口的 collected_through；处理失败的批次不推进 processed_through，均在 run log 记录失败原因与重试位置。

### 3.2 幂等与重放

- 幂等键四类按 `references/collection-rules.md` §6.1 执行：`dingtalk:<conversationId>:<messageId>`、`zentao:<实例标识>:<bugId>`、`gitlab:<项目ID>:<SHA>`、`gitlab:<项目ID>:mr:<iid>`；**任何键不含 state/status 等可变属性**。
- 窗口重叠（默认 60 分钟，可配置）兜底迟到数据；重复记录按幂等键合并，保留首末两次采集时间，不重复建号、不重复进入候选计数。
- 禅道等有更新语义的源按「最后更新时间」补采（collection-rules §3.3）；快照追加按 §6.3（相同 `snapshot_at + state` 视为重复快照，不重复追加）。
- 幂等键冲突（同键、不同对象）→ 视为数据异常：停止写入受影响记录，进 review_queue（type=other）人工复核，不猜谁对。
- 重跑、重放、多次执行不得重复分配任何正式编号；先查既有对象再新建。

## 4. 持久化与运行边界

- 正式持久化必须使用经授权的外部存储（`config/default.json` `storage.storage_root` + `persistence`；典型为独立质量控制 GitLab 仓库）；配置缺失时**只允许 offline**，不得做正式采集/入库/编号分配。
- 本地环境与 memory 不作为可靠跨任务存储；跨任务信息只以正式库落盘为准。
- 库文件（library/）、批次 manifest 与 state（水位 + 计数器）作为**一致状态**提交：优先同一提交内完成；平台不支持原子提交时，按「先写库 → 回读验证 → 再推水位」顺序，不得颠倒。
- 每次写入后回读验证：读回 state 计数器与 library 末条记录核对；不一致按 §6 失败处理，不重试到「看起来对」。
- 并发写入：读 `state.version` 做单调性校验；`version` 不升或非本人预期时，重新读取复核，不盲目覆盖（output-schema §6）。避免多个任务并发写同一项目状态。
- 不得写入业务代码仓库、不得泄露凭据；配置只存凭证引用（需求清单 §4 口径）。
- **运行开始先合并配置并输出 `effective-config.json`（V0.1.4，Q-C1）**：按 `config/default.json` `config_merge` 做**字段级深度合并**（非整对象替换），项目配置只覆盖其显式字段；核对锁定约束（`config_merge.locked_constraints`）未被覆盖或放宽；把合并后实际生效配置、来源文件与锁定项核验结果写入本轮运行目录（offline 写隔离目录），供验收与排查。

## 5. 编号分配纪律

- `<PREFIX>-NNNN / EV-NNNN / OC-NNNN / RV-NNNN / TR-NNNN` 各自独立递增，分配即写回 state 计数器，永久不复用（`references/output-schema.md` §2）。
- 编号分配只在 `process` 模式进行；collect / offline 不分配正式编号。
- **offline TEST 前缀（V0.1.4，Q-C2）**：offline 项目允许以 `TEST` 作项目标识，但 `prefix` 仅用于标识、**不得生成任何正式编号**（`TEST-NNNN` 及 EV/OC/RV/TR 一律不分配）；转正式前必须替换为真实前缀（见 `config/default.json` `numbering`）。
- 编号分配与案例库写入提交绑定；写入失败或验证失败时，本轮已分配但未验证的编号作废，不得在后续轮次不查重即复用（分配记录已入 run log 的，须先按 run log 对账）。
- offline / 试验产物使用 `offline-<run_id>-` 前缀临时键，不读写正式计数器（output-schema §1.2）。

## 6. 失败分类与恢复

### 6.1 失败分类与处置

| 分类 | 含义 | 处置 |
|---|---|---|
| 参数错误 | 查询/提交参数不合法 | 不重试；更正后重开批次，本批标 `failed` |
| 权限不足 | 无授权访问源或存储 | 不绕过；记录缺口，报告需授权范围；不入 unresolved 续跑 |
| 超时/瞬态失败 | transient_error / timeout | 按重试策略（配置 `retry`）重试；重试耗尽记 failed_ids，批次标 `partial` |
| 分页中断 | 分页读取未到空页或元数据不完整 | 保留已读数据与 next_cursor，续跑从断点继续；批次标 `partial` |
| 写入冲突 | 持久化目标 version 冲突或回读不一致 | 重新读取复核后再写；不盲目覆盖；冲突期间不推进水位、不分配编号 |
| 案例库写验失败 | library/state 提交后回读不一致 | 冻结受影响记录；不推进水位；进 review_queue（type=other）人工处理 |

### 6.2 缺口管理（与 collection-rules §6.2 对齐）

- 缺口 kinds：`unresolved_ids` / `failed_ids`（permission_denied / transient_error / timeout / unresolved）/ 未解释空结果 / 未完成分页。
- 只有 `not_found_confirmed` 的编号才可视为空号并排除；其余一律保留在缺口中，水位不得跨越。
- 缺口补齐的动作：单独小批次重查失败 ID 或缺失窗口 → 结果落盘 → 更新 manifest（ins 将 unresolved_ids 清空或转为确认空号）→ 该批转 complete → 才可推进对应水位。
- 断点续采以 manifest 的 next_cursor / 重叠窗自然衔接，不从第一页反复重扫；续跑结果与原批次按幂等键合并。
- 长时间无法补齐的缺口在报告中持续披露（未解决数量、影响范围、最早发生时间），不得静默丢弃。

### 6.3 恢复流程（每次失败后的固定动作）

1. 保留现场：已采数据、失败清单、错误原文落盘（不清理现场再排查）。
2. 更新 run log：失败阶段、原因分类、已持久化范围、续跑位置（`resume_from`：batch_id / next_cursor / 失败 ID 清单）。
3. 不在本轮强行推进任何水位或重新分配编号。
4. 续跑从 `resume_from` 开始：先补缺口，再按 §3 推进水位；完成后在新 run 中更新。

## 7. 重跑与续跑

- **重跑口径**：重跑只补缺口与失败批次——立足 manifest 与 state 判断「哪些批已确认完整、哪些批 partial」，已确认完整的批次不重复采集（必要时按幂等键合并快照），不重置正式编号。
- **从断点续**：分页中断用 next_cursor 续；失败 ID 用单独小批次重查；时间窗用重叠区衔接。
- **续跑验证**：副本续跑完成后，先与原 partial 批次做记录比对（本批次记录数、unresolved_ids 清零情况），再更新 manifest 与水位。
- **禁止**：为求「一次跑通全量」而放弃水位管理全量重扫；删除原记录重写；重复分配正式编号。

## 8. runs / reports 与执行留痕

- 每轮运行写 `runs/<run_id>.json`（run_id 格式 `<YYYYMMDD>-<mode>-<序号>`）：记录 run_id、技能版本、输入快照、各源数量及完整性、未解缺口、新增/更新/复发/待复核数量、水位推进结果、写入验证结果、失败原因及续跑位置。
- 本结构由 output-schema §9 输出物及 runs 日志承载；报告（`reports/`）注明 run_id、数据截止时间和未核范围。
- 统计输出按 `references/recurrence-rules.md` §3 重算并交叉核对（运行概览 vs occurrences 记录逐项对得上）；已确认数量、未知数量与覆盖范围同报。
- run log 是水位与编号审计的唯一依据：任何水位推进、编号分配、归并操作都要能在 run log 找到对应记录。

## 9. 各模式执行要点

| 模式 | 核心动作 | 主要产物 | 水位/编号 |
|---|---|---|---|
| `offline` | 加载七份核心文件，隔离目录内分析；不改正式库/水位/编号 | `<offline_root>/<run_id>/` 下试验产物 + 自检报告 | 不读写；全用临时键 |
| `collect` | 按源分批采集 + 保存原始 + 对账（MR 三路径）+ manifest | `raw/`、manifest、`reconcile/<run_id>.json` | 仅推进 `collected_through` |
| `process` | 处理未完成批次：筛选 → 候选 → 匹配入库 → 流转记录 | `process/<batch_id>/`、`library/`、运行日志 | 推进 `processed_through`；分配编号 |
| `analyze` | 统计复发/高频/测试候选；不改库 | `reports/`、运行日志 | 无推进、无编号；需改库时输出「待 process 处理」清单 |

- `process` 必须以未处理批次为单位推进（对应原始批次以 collected_through 为界），处理完一批推一批，不攒库后一次性补账。
- `analyze` 的统计必须从 `occurrences.json` / `bugs.json` 重算，不使用上一轮报告的数字直接转发。

## 10. 禁止事项

- 不得蛮力跨缺口推进双水位；不得以「批次大体完成」跳过缺口。
- 不得用本地文件、会话记忆或上一轮报告代替持久化回读验证。
- 不得在失败轮次重分配编号或复用已分配但未验证的编号。
- 不得把一次出表当成持久化成功；写库必须配套回读。
- 不得启动后台任务或轮询等待超预算。
- 不得在 review_queue 中替人工填写 `resolution / resolved_by / resolved_at`。
