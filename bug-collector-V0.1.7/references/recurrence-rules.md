# recurrence-rules.md — 独立发生、持续未解决、复发与同类关联判定规则

> 版本：V0.1.7（2026-11-27，在 V0.1.6 上同步：附件内容未获取不影响发生/复发判定口径（见 collection-rules §2.4）；本次无其他正文改动；V0.1.6 基线保留）
> V0.1.5 变更：新增 §2.8 occurrence 证据与时间门槛。
> V0.1.4 变更：按环境判定 `repeat_unresolved`、事件去重唯一口径、关闭与历史验证、验证结论更正。
> 引用入口：`SKILL.md` §4.5「更新案例库与识别复发」。
> 加载时机：**全部四种模式都必须加载**。`process` 判定候选是新发生、持续未解决还是复发；`analyze` 做复发统计与高频分析；`offline` 核对复发结论（本轮不涉及复发分析时，相关检查可标 `N/A`，但不得跳过本文件）；`collect` 不判定发生，仅在采集回读时按本文识别线索。加载约定见 `SKILL.md` §7。
> 分工边界：**是不是同一条记录 / 同一个缺陷**见 `references/dedup-rules.md`；occurrence、recurrence_signals 的字段结构、枚举与编号见 `references/output-schema.md` §5、§10；分批、水位与正式持久化见 `references/execution-rules.md`（V0.1.3 起已编写，正式 collect / process / analyze 必读）。本文回答三个问题：**这次出现算不算一次发生**、**算不算复发、算哪一类**、**各项次数怎么数**。

## 1. 术语

| 术语 | 定义 | 不成立的典型 |
|---|---|---|
| 发生（occurrence） | 缺陷在某个时间、某个环境、以可核验的现象独立出现一次，形成一条 occurrence 记录。**V0.1.2 只有四种 kind 构成有效发生：`first` / `repeat_unresolved` / `repeat_after_fix` / `rollback_regress`**（§2） | 同一现象的多张截图、多人转述同一件事、同一时段的消息刷屏 |
| 持续未解决（unresolved） | 缺陷在**某个具体环境**上自首次发生起从未被确认修复（该环境无有效 `verified_fixed` 证据），表现为多轮跟进与补修。**它是一种处理状态，不是发生事件**，由 `lifecycle`、`transitions.jsonl`（按 `environment` 分环境）与证据链表达；**不得仅凭全局 `lifecycle` 判定某环境未解决** | 把每一轮「还是不行」都记成一次发生；因全局 `verified_fixed` 就认为所有环境都解决了 |
| 持续未解决期间的再次发生（`repeat_unresolved`） | 同一缺陷（身份已确认）在**未确认修复的那个环境**上出现**新的独立触发或异常发生证据**（新的时间点、环境/版本或场景/触发条件，且不复用原次证据），登记为一次 occurrence | 同一时段的无新证据重复反馈、多人转述、补修轮数；仅现象相似即认定为同一缺陷 |
| 复发（recurrence，**广义**） | 缺陷曾被确认修复并验证通过，之后再次出现。由两个子类型构成：`repeat_after_fix`（狭义复发）与 `rollback_regress`（回滚重现） | 修复从未上线或从未验证；同类但不同根因 |
| 回滚重现（`rollback_regress`） | 曾到 `verified_fixed`，此后因发布回滚、镜像/版本回退、`pin` 改回旧版、配置恢复旧值而使同一缺陷重新生效或重现 | 修复从未生效；没有回退证据的「又出现了」 |
| 同类关联（`similar_class`） | 与另一缺陷现象/模式相同或高度相似，但根因或修复手段不同，属同类风险而非复发。**以 `bugs.related[].kind=similar_class` 表达，不新建 occurrence** | 同一根因的再次出现 |
| 修复动作（fix_action） | 为使某缺陷闭环而执行的一次可识别独立处置（代码 MR、配置或数据订正、人工修复） | 一次修复被拆成多个提交；合并产生的多条记录 |

## 2. 事件分类（`occurrence.kind`）

枚举取值以 `references/output-schema.md` §5、§10.2 为准；判定条件与计数归属以本节为准。**V0.1.2 只允许下表四种 kind。**

| kind | 判定条件（需同时满足） | 计入独立发生 | 计入广义复发 |
|---|---|---|---|
| `first` | 缺陷主记录**全局**第一次可核验出现；本项目历史库中无对应已登记缺陷（或本条即新建缺陷主记录的首个发生）。**不按环境重复生成 `first`** | 是 | 否 |
| `repeat_unresolved` | 同一缺陷（身份已确认）在**该环境**未被确认修复（该环境无有效 `verified_fixed` 证据，不得只看全局 `lifecycle`）；未解决期间出现**新的独立触发或异常发生证据**（时间、环境/版本或场景至少一项独立，且不复用原次证据）；证据可回查 | 是 | 否 |
| `repeat_after_fix` | 曾到 `verified_fixed` 且之后再次出现，具备独立的时间/环境/现象证据，未确认存在回退（狭义复发） | 是 | 是 |
| `rollback_regress` | 曾到 `verified_fixed`，此后因发布回滚、镜像/版本回退、`pin` 改回旧版或配置恢复旧值，使同一缺陷重新生效/重现 | 是 | 是（回滚子类型） |

**否定性约定（V0.1.2 新增，逐条执行）**：

- `related_case` **不是 V0.1.2 的合法 kind**。同类关联一律走 `bugs.related[].kind=similar_class`（§3.4）；`related_case` 仅用于读取历史数据，折算口径见 §3.5。新增或更新记录中不得再写 `related_case`。
- `fix_not_live`、`fix_not_effective`、`deployment_drift` 是**具体原因或处理状态标签**，不是 `occurrence.kind`。只能写在 `basis`、`diff_note`、`review_queue.reason` 等文本字段，或在报告中作为原因说明；不得写进 `occurrence.kind`，也不得据字样直接判定复发或排除复发。标签清单见 `references/output-schema.md` §10.2 描述标签表。
- **不得为每个缺陷固定生成一条 `repeat_unresolved`**。没有新的独立发生证据时不建 occurrence；「持续未解决」由 `lifecycle`（`open` / `fixing`）、`transitions.jsonl` 及关联证据体现。
- 同一缺陷可以有 `occurrence_ids` 为空的情况（历史缺陷缺乏发生证据）；不得为了让缺陷数量与发生次数相等而虚构事件。

### 2.1 `first`

- 项目历史库中不存在同一条缺陷时，首个可核验出现登记为 `first`，同时建立缺陷主记录。
- **`first` 是缺陷主记录（`bug_id`）的全局首次，不按环境重复生成**：同一缺陷后续在其他环境又出现，不另立 `first`，按 §2.2 判 `repeat_unresolved` 或按 §2.3/§2.4 判复发（V0.1.4，Q-05）。
- 同类但独立的缺陷，其首次已知发生**仍登记为 `first`**（另用 `similar_class` 关联，见 §3.4），不要用 `related_case` 承载。

### 2.2 `repeat_unresolved`（按环境判定的核心口径，V0.1.4 收窄）

`repeat_unresolved` 是**环境范围内**的「未解决期间再次发生」：缺陷主记录全局唯一（`bug_id` 不按环境拆分），但「是否已修复 / 是否已验证」按环境（`canonical_name`）分别管理（§2.6）。判定需**同时**满足：

1. **缺陷身份已确认**：本次现象可归属到同一 `bug_id`——有同一禅道单 / 同一缺陷记录锚点，或（无单号时）同模块且同根因并有非现象类独立证据支撑。**仅「现象相似」不足以认定为同一缺陷**；不得仅凭相似就把它当作本缺陷的发生记录。
2. **该环境未被确认修复**：按**本次出现所涉环境**（`canonical_name`）查 `transitions.jsonl`，该环境没有有效的 `verified_fixed` 证据（或曾有但已按 §8 撤销并有流转记录）。**不得仅凭全局 `lifecycle` 判定该环境处于未解决状态**——全局 `lifecycle=verified_fixed` 只代表已验证环境范围内通过（§2.6），不代表其他环境已修复。
3. **有新的独立触发或异常发生证据**：出现新的时间点、新的环境/版本，或新的场景/触发条件；证据不得复用原次发生的截图、日志、回执。
4. **证据可回查**：`evidence_ids` 非空，`basis` 写明本次独立的依据。

处理：

- 全部满足：登记一条 `repeat_unresolved` occurrence，计入独立发生次数（§3.1），**不计入复发**；`basis` 写明「同一缺陷 + 该环境从未验证通过 + 本次独立的证据」。
- 只有多人转述、多轮补修、MR 跟进，而**没有**新的独立发生证据：不建 occurrence，只追加状态证据（`role=status_evidence` / `related_fix`）与流转记录，`repeat_unresolved_events` 保持 0。
- **不能确认缺陷身份、事件独立性或该环境有效验证状态**：进 `review_queue`（`type=recurrence_check`），保留 `missing_evidence`，不预填结论。**不得仅因缺少部署记录就否定一个已具充分独立证据的发生事件**（缺部署记录只影响「修复是否上线」判断，不否定该次发生本身）；也**不得仅凭现象相似认定为同一缺陷**。
- 同一缺陷在其他环境的独立发生按本条判 `repeat_unresolved`（或按 §2.3/§2.4 判复发），**不另立 `first`**。

### 2.3 判 `repeat_after_fix` 的三要素

1. **原缺陷曾确认修复并验证**：`lifecycle` 曾到 `verified_fixed`，且有验证类证据（复测记录、现场确认消息、回归通过记录）。**MR 合并、禅道 resolved、CI 通过都不算验证通过。**
2. **新出现是独立一次**：独立时间、独立环境/版本、独立证据；不得复用原次发生的截图、日志、回执。同一现象的多张截图、多人转述只算一次。
3. **可由原根因解释**：现象与触发条件与首次一致，或可由原修复所覆盖的同一根因解释。根因明显不同 → 不是复发，按 §3.4 建同类关联。

### 2.4 判 `rollback_regress` 的附加要求，以及「部署漂移」的统一口径

**V0.1.6 收紧：以下四要素必须同时满足，缺一不得判 `rollback_regress`**——① 同一缺陷身份（禅道单 / 已登记缺陷锚点，或同模块同根因且有非现象类独立证据）；② 该缺陷在**相关环境**曾有有效验证通过记录（带 `environment` 的 `verified_fixed` 流转或可确认的验证证据）；③ 本次是**再次独立发生**（新的时间/环境/触发，且不复用原次证据）；④ 有**回退证据**。**不得用需求背景虚构历史首次缺陷来凑身份或凑发生**（见 §2.9）。

- 必须有回滚/回退证据：发布记录、镜像 tag 变更、`pin` 变更、配置恢复旧值的变更记录、回退操作记录。
- 必须区分四件事，不得混写成一条：

| 情形 | 判据 | 结论 |
|---|---|---|
| **回滚重现** | 曾 `verified_fixed`，有回退证据（回滚/镜像回退/配置恢复旧值/`pin` 回退） | `rollback_regress`，计入广义复发 |
| **修复从未生效** | 只合并未部署、`pin` 停在旧镜像、配置未下发、部署目标环境不对；原缺陷从未 `verified_fixed` | **不计复发**。有新的独立发生证据 → 按 §2.2 判 `repeat_unresolved`；无则只在复核项记 `fix_not_live` 处理状态 |
| **已部署但相关场景从未验证通过** | 有部署记录，但没有任何复测/现场确认证明该场景已恢复 | **不直接认定复发**。有新的独立发生证据 → `repeat_unresolved`；否则进 `recurrence_check` 待核实 |
| **修复无效** | 已部署且相关场景验证通过，之后未回滚仍再次出现 | 按 `repeat_after_fix` 处理，并在 `basis` 注明「原修复未覆盖该根因」 |

- **不得仅根据「部署漂移」「旧镜像」等字样判断是否复发**。必须先核实：①此前是否在**相关目标环境**验证通过；②本次是否存在回退证据。两项缺一即不能判 `rollback_regress`。
- 若无法确认是否曾 `verified_fixed`，不得判回滚重现，进 `recurrence_check` 复核。

### 2.5 不得判为复发的情形（反复出现的误判）

- **禅道重新激活/重新打开**：既不是复发成立的必要条件，也不是充分条件。只写 `bugs.recurrence_signals`（status=pending）并生成 `recurrence_check`；取得新的现象/时间/环境证据后才可能转成 occurrence，重新激活本身不是发生。
- **只有「部署漂移 / 旧镜像 / 配置被临时改动」等字样**：见 §2.4，必须核实验证与回退证据。
- **修了两次/两轮「跟进」MR**：修复轮数 ≠ 发生次数；没有新的独立发生证据时不建 occurrence。
- **同类但不同根因**：`similar_class` 关联，不是复发（见 §3.4）。
- **修复从未生效**：不计复发（见 §2.4）。
- **一次故障链上的多个断点**：按 `references/dedup-rules.md` §5 拆分并关联，不互相计复发。
- **时间相近、同一批用户、同一条群消息**：不构成独立发生。

### 2.6 分环境验证与 `verified_fixed` 的适用范围（V0.1.3 新增）

- **环境名为主、版本为辅**：验证结论的适用范围按**环境身份**（项目 `environment_registry` 的 `canonical_name`）登记；版本号、Commit SHA、镜像 tag 等是辅助信息，有证据时登记，未知时不推测。具体环境名称、标识与别名映射由 `config/projects/<project>.json` 定义；通用默认只定义分类语义与未知环境处理（`config/default.json` `recurrence.environment_registry`）。
- **分类 ≠ 身份**：两个环境同属一个分类（如同为 `test`）不代表是同一环境；验证适用范围与跨环境比对一律按 `canonical_name` 判定。
- **一环境验证通过不外推**：修复在某一环境验证通过，不自动代表其他环境（含同分类其他环境）验证通过；跨环境验证结论需各自独立证据。
- **`lifecycle=verified_fixed` 的含义收窄**：它表示「已登记验证证据覆盖的环境范围内验证通过」，**不得解释为所有环境均已验证**。结构化承载：lifecycle 推进的 `transitions.jsonl` 行（field=lifecycle，to=verified_fixed / closed）**登记可选 `environment` 字段**（canonical_name / category / version / raw_text；版本未知写 `null`，结构见 `references/output-schema.md` §8、§10.5）；「已验证环境清单」`verified_environments` 是**派生信息**（由流转行 + 其引用的证据得到，写入运行概览 / 报告，不在 bugs 上另立字段）。旧数据行缺失该字段时不补造，按证据原文判断或进 `recurrence_check`（新增字段理由、字段归属与兼容方案见 CHANGELOG-V0.1.3 §2）。
- **判复发的环境门槛**：判 `repeat_after_fix` / `rollback_regress` 前，先核实本次出现所涉环境（canonical_name）此前是否有验证通过证据；没有 → 不判复发，按 §2.4 / §2.2 处理或进 `recurrence_check`。
- **信息缺失不硬判**：环境或版本信息缺失且影响复发判定时，进入 `recurrence_check`，不强行判定复发；报告披露已验证环境范围与未覆盖/未知部分（不得因「找不到环境信息」而判成 0 或判成全环境验证）。

### 2.7 `closed`、历史验证事实与验证结论的更正（V0.1.4 新增，Q-03 / Q-04）

- **`closed` 不新增、不扩大分环境验证范围**：缺陷关闭（`closed` / `wont_fix`）不产生新的环境验证结论，也不把「已验证环境」自动扩大到其他环境；`closed` 时已有有效验证记录继续保留，未被验证过的环境仍是「未知/未覆盖」，不得因关闭而认定其验证通过。
- **区分历史验证事实与当前环境状态**：`transitions.jsonl` 中已登记的 `verified_fixed`（带 `environment`）是**历史事实**，不因后续复发、回滚重现或关闭而被抹去或改写。
- **验证结论的撤销需审计**：原验证记录错误或证据无效时，只能通过一条**有审计记录的更正流转**撤销（`field=lifecycle` 的反向流转 + `reason` 说明原证据为何无效 + 引用新证据），不得静默删除或覆盖历史行；撤销后该环境的「已验证」不再成立，但其历史上确有过的验证动作与记录仍留档。
- **复发 / 回滚不抹去历史**：后续出现 `repeat_after_fix` / `rollback_regress` 只追加新的 occurrence 与流转，不回填、不删除此前的 `verified_fixed` 行；`verified_environments` 按历史有效验证记录计算，必要时在报告中同时标注「当前是否仍生效」。

### 2.8 occurrence 的证据与时间门槛（V0.1.5，DEF-001/DEF-002/DEF-003）

- **无证据不建 occurrence**：每条 `occurrences.json` 记录必须至少引用 1 条真实证据（`evidence_ids` 非空、证据存在、且已关联到同一 `bug_id`）。证据缺失、身份不可回查或仅凭「应该有」推断的，只记 `recurrence_check` 线索，不得写 occurrence。
- **发生时间来自来源记录**：`observed_at` 必须等于其 `evidence_ids` 中某条证据的 `source_record_time`；不得使用运行时间、采集时间、其他消息时间或相邻事件时间。原文只有日期时保留日期精度，不补时分秒。
- **事实可回查**：occurrence 的 `basis` 必须能在所引证据原文中找到对应现象描述；关键数字必须由该证据支持。不得把 A 消息的页数/比例挂到 B 消息上。
- **案例隔离**：occurrence 只能引用本案例输入内的证据；跨案例补证不成立。
- 以上任一项不满足，该 occurrence 不得计入 `independent_occurrences` / `recurrence_events`，对应缺陷降级或进复核。

### 2.9 需求背景、缺陷身份与历史首报边界（V0.1.6）

- **用户功能要求 ≠ 历史缺陷首报**：「希望支持 / 需要增加 / 能不能做 / 最好能有」类表述优先归需求侧（`context_events.event_type=requirement`）；**不得**仅因为用户提过一个功能要求，就把后续该功能交付失败登记成该功能的历史缺陷 `first`，也不得据此虚构一条「原缺陷」。
- **判 `first` / `repeat_unresolved` 前先确认缺陷身份**：是否有禅道单 / 已登记缺陷锚点，或同模块同根因且有非现象类独立证据。身份已确认且该环境未验证 → `repeat_unresolved`；身份未确认 → `recurrence_check`，不硬判（也不因「看起来是同一个功能」就认定）。
- **`rollback_regress` 不得靠需求背景虚构首次缺陷**：若功能此前从未作为缺陷登记、也没有验证通过记录，本次「功能交付失败」按 `first`（若构成缺陷）或需求线索处理，不构成回滚重现。
- 该边界同时适用于测试断言：功能要求原文的存在不证明历史缺陷存在，也不证明发生过两次。

### 2.10 更正消息与数字口径（V0.1.6）

- **更正只替换被明确更正的事实**：同一发送人对同一指标的更正（如 99.9% → 实际分母 8041）只覆盖该指标及其直接推算值；原消息中未被更正的事实（其他页数、其他比例、范围描述）继续有效，并保留在 `supersedes` / `superseded_by` 链的原始证据里。
- **数字三要素核对**：引用任何数字时必须同时确认**分母/基数、指标名称、适用范围（环境/时间窗/版本）**；不得把更正后的分母套到未更正的指标上，也不得把某环境/时间窗的统计外推到全量。
- **更正不增加发生次数**：更正链是同一事实的版本链，不产生第二条缺陷，也不新增 occurrence（与 §2.8 一致）。
- 数字无法在证据原文中定位到分母与口径时，该数字只作线索，写入 `review.fields_unverified`，不作为计数或断言依据。

## 3. 计数口径（固定）

总则：各项指标互不替代，必须分开输出；不得用消息数、Commit 数、MR 数或来源数代替任何一项。统计前先按**主记录归属聚合**（别名记录的 occurrence 经 `merge.merged_into` 归入主记录，见 `references/dedup-rules.md` §4.3），再在主记录范围内按**事件**去重——同一次具体发生的重复表达只计一次。事件去重的时间精度折算、证据交集口径与反证处理，以 §3.8 为唯一细则（策略配置固化于 `config/default.json` `recurrence.event_dedupe`）。

### 3.1 独立发生次数

`independent_occurrences` = `first` + `repeat_unresolved` + `repeat_after_fix` + `rollback_regress` 四类**有效 occurrence 记录数**（事件去重后）。

- `repeat_unresolved` **计入**独立发生次数（本次统一口径），但不计入复发。
- 缺乏发生证据的历史缺陷允许 `occurrence_ids` 为空，不虚构事件；统计时单列「无发生记录缺陷数」，不得用缺陷数反推发生数。
- 旧数据 `related_case` 的折算见 §3.5。

### 3.2 广义复发次数 = 狭义复发 + 回滚重现，子类型保留

- **广义复发次数** `recurrence_events = repeat_after_fix 条数 + rollback_regress 条数`。
- **子类型必须保留**：`recurrence_by_subtype = {repeat_after_fix: n, rollback_regress: n}`；只报总数不报子类型视为不完整输出。
- 狭义复发（`repeat_after_fix`）作为子集单独可查，**不另立一套判定**。
- `recurrence_events` 是**派生统计量**，由 occurrence 记录按 kind 统计得出；不得在单条记录上另写一个「是否广义复发」字段，也不得把两类合并成同一个 kind 登记——事件本身按真实性质落 `repeat_after_fix` 或 `rollback_regress`。
- 报告口径示例：`复发 2 次（修复后再次发生 1 次、回滚重现 1 次）`。

### 3.3 持续未解决事件（派生指标）

- `repeat_unresolved_events` = `repeat_unresolved` occurrence 记录数，与 `independent_occurrences` 中的该 kind 同源。
- **不按缺陷固定计 1，也不随反馈轮数或补修轮数增长**。
- 缺陷处于未解决状态但无新的独立证据时，该值为 0，由 `lifecycle=open/fixing` 与流转日志表达「持续未解决」。报告须同时给出处于未解决状态的缺陷数（`unresolved_open_bugs`），避免把「0 次重复发生」误读为「已解决」。

### 3.4 同类缺陷建立关联，不计入彼此的复发次数

- 同类关联登记为 `bugs.related[]`，`kind = similar_class`（枚举同步见 `references/output-schema.md` §3），并在 `note` 写明同类理由。
- **计数**：新缺陷这一次是**它自己的独立发生**，按其性质登记 `first`（或 `repeat_unresolved` / `repeat_after_fix` / `rollback_regress`），计入本缺陷的 `independent_occurrences`；但本缺陷与对方的 `recurrence_events` **均不增加**，也不生成对方的 occurrence，**不新建 `related_case` occurrence**。
- 关联需写清 `similar_points`（现象/模块/触发条件）与 `differences`（根因、修复手段、环境或版本差异）及对应证据；不得只写「相似」。
- 若后续核实两者实为同一根因，按 `references/dedup-rules.md` 归并；归并本身**不补记任何一方的复发**，归并后如需判复发，按 §2 重新用证据判定（归并后的发生计数规则见 `references/dedup-rules.md` §4.3）。

### 3.5 旧数据兼容：`related_case` 折算

- 读取 V0.1.1 及更早数据时，`occurrence.kind=related_case` 的记录视为「该缺陷自身的一次独立发生」。
- **防重复计数（统一按 §3.8 事件去重，V0.1.4 收窄）**：是否属同一事件一律按 §3.8 判定——先按主记录聚合，再要求「同一次具体发生」的**现象报告类（`role=report`）证据交集**且无独立发生反证；**仅共享修复 Commit / MR / 部署记录 / 背景资料不算交集**；无法判定时进 `recurrence_check`。不得再用「`evidence_ids` 有任意交集即同一事件」的宽松口径。
- 新增/更新记录不得再写 `related_case`；需要同类关联时改用 `similar_class`。
- 报告中若存在旧 `related_case` 记录，须在附注标明遗留条数与折算方式（原始记录保留，不物理改写）。

### 3.6 修复动作次数是可选统计指标

- 字段名 `fix_actions`，语义为「为使该缺陷闭环而执行的可识别独立处置次数」。
- **只在证据能逐条枚举独立处置时给整数**：同一动作的多轮提交、多次讨论、多次合并算 **1 次**；同一 MR 修多个缺陷时，各缺陷各记 1 次；配置/数据订正与代码修复分属不同动作时分别计数。
- **无法确定时不强行计算**：只知道「修了几轮」「有几个 MR」但无法确认是否为独立处置时，写 `null`，并在 `fix_actions_note` 与复核项注明原因；不得用轮数、MR 数、Commit 数、消息数估算。
- **已知没有执行任何修复动作时必须写 `0`，不得留 `null`**（V0.1.6）：例如仅登记现象、尚无任何修复证据或整改动作的缺陷。`null` 只用于「不确定是否有/有几次」，且必须附说明。
- `fix_actions` **不参与复发判定**，也不是必填计分项；缺失或为 `null` 不影响其余指标的有效性。
- 修复动作次数与复发次数无换算关系：`fix_actions=2` 不代表发生 2 次，也不代表复发 1 次。

### 3.7 指标对照表

| 指标 | 字段 | 口径 | 是否可为 null / 缺省 |
|---|---|---|---|
| 独立发生次数 | `independent_occurrences` | `first` + `repeat_unresolved` + `repeat_after_fix` + `rollback_regress` 的记录数（事件去重后） | 否（无则 0；待核验时进复核并说明） |
| 持续未解决事件 | `repeat_unresolved_events` | `repeat_unresolved` 记录数（派生），不按缺陷固定计 1 | 否（无则 0） |
| 未解决状态缺陷数 | `unresolved_open_bugs` | `lifecycle` 为 `open` / `fixing` 的**缺陷数**（派生，按 `bug_id` 计、**不按环境计**；全局 `lifecycle` 取该缺陷所有有证据环境中最不先进的状态——如已在 test-a 验证通过但 test-b 仍复现，则全局仍为 `fixing`），用于表达「持续未解决」而非发生次数；历史验证事实保留在 transitions，不因全局为 open/fixing 而抹去（§2.7） | 否（无则 0） |
| 广义复发次数 | `recurrence_events` | `repeat_after_fix` + `rollback_regress` | 否（无则 0） |
| 复发子类型分布 | `recurrence_by_subtype` | `{repeat_after_fix, rollback_regress}` 分项计数 | 否（无则各 0） |
| 同类关联数 | `related_cases` | `similar_class` 关联条数，**不计入复发** | 否（无则 0） |
| 修复动作次数 | `fix_actions` | 可枚举的独立处置次数 | **是，未知写 `null`** |
| 无发生记录缺陷数 | `bugs_without_occurrence` | 有缺陷主记录但无有效 occurrence 的缺陷数 | 否（无则 0） |
| 验证适用环境 | `verified_environments` | 派生：lifecycle 到 `verified_fixed`/`closed` 的流转行（含所引证据）可确认的 canonical_name 去重集合（§2.6） | 是——全无可归一环境时报告「未知/未披露环境数」，不得写 0 冒充 |
| 统计覆盖范围 | `coverage` | 时间窗、来源、批次、**时间精度覆盖**、未覆盖部分与未知数量、**事件去重已确认合并数与待复核数**（V0.1.6，STAT-008） | 否（须写明） |

- 报告必须同时给出**已确认数量**、**未知/待核实数量**与**数据覆盖范围**；不得把「无记录」写成「数量为 0 且已确认」。缺证不是检查通过，也不代表缺陷不存在。

### 3.8 事件去重细则（**唯一权威定义**，V0.1.4；其余文件只引用不另立）

> 事件去重总口径 = `同一缺陷主记录 + 同一次具体发生的证据交集`；时间精度只是**比较方式**，不改变「必须属于同一次具体发生」的实质要求。策略配置固化于 `config/default.json` `recurrence.event_dedupe`。本细则针对历史数据的时间精度缺口（至少一方仅有日期）；双方均有精确时间时直接按精确时间比较（第 2 条）。

判定顺序（固定，不跳步；配置值锚定 `config/default.json` `recurrence.event_dedupe`——键名 `aggregate / precise_time_policy / date_only_policy / preserve_original_precision / evidence_intersection / counter_evidence_blocks_auto_merge / ambiguous_policy / keep_raw_occurrence_records`，取值 `by_primary_bug_record_first / compare_after_unified_timezone_normalization / same_natural_day_in_project_timezone / true / qualifying_roles=["report"] / true / review_queue_disclose_pending / true`）：

1. **先聚合、后去重**：先按缺陷**主记录**归属聚合——别名记录的 occurrence 经 `merge.merged_into` 归入主记录（`references/dedup-rules.md` §4.3）；事件去重只在**同一缺陷内部**进行，不得借此把不同缺陷并库。
2. **时间比较**：
   - 双方均有精确时间（时分秒齐全）：按本项目配置时区归一后的精确时间比较；不同时区必须先归一（不改原始值）。
   - 至少一方仅有日期精度：按**同一自然日**（配置时区下 `observed_at` 折算的日历日）比较；不虚构任何缺失的时分秒，原始值照存。
3. **证据交集**：同日的两条记录还须共享「能证明同一次具体发生」的证据——证据按内容是**现象首报/复述类证据**（`role=report`：同一现象的报障原文、截图、日志；先按内容定 role，再判是否计入交集；不管采自哪个群、哪个通道）。`qualifying_roles` 以 `config/default.json` 为口径，项目**不得覆盖放宽**。
   - **仅共享修复/部署类证据不算交集**：两条记录只共享 MR、Commit、SHA、部署记录或复测回执（`primary_fix` / `related_fix` / `status_evidence`），或共享的只是背景资料等上下文材料（`background`）——不能作为自动去重依据。
   - 交集可跨源：「同一天的群消息 + 同一天的同一截图」算现象层交集；「同一天的 Commit + 同一天的 MR」只是修复侧共享，不算。
4. **反证阻断**：存在明确的独立触发证据（不同时间的新报障原文、不同的复现操作）、环境/版本冲突或其他反证时，**不得**因同日且有交集而合并——保留两条，或其中一条标注「与另一条疑似同一事件」进 `recurrence_check`。
5. **对称约束**：
   - **不得仅因同日就合并**——同日只说明时间接近，没有第 3 条的证据交集就不能合并；
   - **不得仅因证据交集缺失就自动判为两次独立发生**——不足以判「同一次发生」、又说不清是「两次」时，进 `recurrence_check` 待人工复核，并在报告中披露**待复核数量**；
   - 事件去重只解释「几条 occurrence 表示几次发生」，不解释「几个缺陷」；不同缺陷的归并仍按 `references/dedup-rules.md` 判定。
6. **原始记录保留**：无论合并与否，原始 occurrence 记录不物理删除；判定结果写入运行概览（合并了几组、按什么依据），供复核与审计。

- 「无法判断」的两条出路：能判「同一次」→ 合并计 1；不能判「同一次」也说不清「两次」→ `recurrence_check`，不强行给数。
- 报告须同时给：已确认合并的事件数、待复核数（`recurrence_check` 中 `type=recurrence_check` 且 reason 涉及事件去重的条数）、以及 **coverage**（时间精度覆盖情况、无日期值的历史条数）。

## 4. 判定流程（按顺序执行，不跳步）

1. **是不是一次独立发生**：时间、环境/版本、证据是否独立？否则不新建 occurrence（只追加证据与状态）。
2. **历史是否曾 `verified_fixed`、验证证据覆盖哪些环境**：查本缺陷 `lifecycle` 与流转日志（`transitions.jsonl`），确认有无验证类证据；并按 §2.6 核对**本次出现所涉环境**是否落在已验证证据适用的环境范围内（按 canonical_name 判，分类相同不算）。
3. **验证覆盖本次环境 → 判复发类型**：有回滚/版本回退/配置恢复旧值证据 → `rollback_regress`；未回退但同根因再次独立出现 → `repeat_after_fix`。
   - **验证未覆盖本次环境，或环境/版本信息缺失影响判定** → 不强行判复发：按 §2.4 判持续性情形或进 `recurrence_check`，由复核定案后按实际性质补记。
4. **从未验证修复 → 不进复发**：有新的独立发生证据 → `repeat_unresolved`；没有 → 不建 occurrence（记录状态证据与流转，必要时按 §2.4 复核 `fix_not_live`）。
5. **现象相似但根因不同 → `similar_class` 关联**（`bugs.related[]`），本缺陷按其自身性质登记 `first` 等，双方复发计数均不变。
6. **证据不足 → `recurrence_check` 复核**，保留 `similar_points / differences / missing_evidence`，不得预填人工结论。

## 5. 记录与证据要求

- 每次发生一条 occurrence，独立编号（`OC-NNNN`），编号不复用；由 `references/output-schema.md` §5 定义结构。
- 复发类记录（`repeat_after_fix` / `rollback_regress`）必须在 `basis` 写明：原修复的验证证据来源（哪次复测/哪条现场确认）、本次出现的独立证据；在 `diff_note` 写与上次发生的差异（环境、版本、触发条件），回滚类另注明回退依据。
- `repeat_unresolved` 必须在 `basis` 写明本次的**新独立证据**（时间/环境/场景哪一项独立）；写不出则退回不建 occurrence。
- 不新增字段承载上述内容，避免跨文件字段漂移；结构以 `references/output-schema.md` §5 为准。
- 同一缺陷关联多个禅道单时，各单状态快照分别保留；某单 `resolved` 不自动代表本地 `verified_fixed`，也不自动生成复发或关闭结论。

## 6. 典型场景对照

| 场景 | kind | independent_occurrences | recurrence_events | fix_actions |
|---|---|---|---|---|
| 首次报障 + 两轮「跟进」MR，禅道始终 active、从未 resolved、无新独立证据 | `first` | 1 | 0 | 可枚举则 2，否则 `null` |
| 首次后未解决期间，另一次独立触发（不同环境/不同场景，均有证据） | `first` + `repeat_unresolved` | 2 | 0 | 按证据 |
| 修复上线复测通过，两周后同现象在新版本再次独立出现 | `first` + `repeat_after_fix` | 2 | 1（repeat_after_fix=1） | 按证据，可 `null` |
| 修复上线验证通过，发布仓回滚到旧镜像/配置恢复旧值后同缺陷重现 | `first` + `rollback_regress` | 2 | 1（rollback_regress=1） | 按证据，可 `null` |
| 只合并未部署，用户侧仍复现（pin 停在旧镜像），期间无新独立证据 | `first` | 1 | 0（`fix_not_live` 仅记处理状态） | 按证据 |
| 只合并未部署，期间在另一环境出现新触发且有证据 | `first` + `repeat_unresolved` | 2 | 0 | 按证据 |
| 已部署但相关场景从未验证通过，之后又出现 | `first` + `repeat_unresolved` 或仅复核 | 1 或 2（视证据） | 0 | 按证据，可 `null` |
| 修复已在环境 A 验证通过，同缺陷（身份已确认）在从未验证过的环境 B 又独立出现（A、B 同分类不同 `canonical_name`），有独立时间/环境/现象证据 | `first` + `repeat_unresolved`（B 未被确认修复，§2.2） | 2 | 0（A 的验证证据按 §2.6 不覆盖 B，不得判 `repeat_after_fix`；B 的发生也不计复发） | 按证据，可 `null` |
| 同上现象在环境 B 出现，但**无法确认与 A 的缺陷为同一缺陷**（仅现象相似、无单号/同根因锚点） | 不硬判：进 `recurrence_check` / merge_candidate，不当作本缺陷的 `repeat_unresolved`，也不据此判复发 | 视复核结果 | 0 | 按证据，可 `null` |
| 与历史缺陷同类但根因不同（不同模块引入相同现象） | 本缺陷 `first` + `similar_class` 关联 | 1 | 0（双方均不计） | 按证据 |
| 历史数据里同一次发生同时有 `first` 与遗留 `related_case` | 按事件去重后计 1 | 1 | 0 | 按证据 |

## 7. 自检（对照 `SKILL.md` §6）

- 每条复发记录都能说出「曾 `verified_fixed` 的验证证据」与「本次独立证据」；说不出则退回 `repeat_unresolved` 或不建 occurrence / 复核。
- `repeat_unresolved` 只在有新的独立发生证据时存在；没有把补修轮数、多人转述当发生，也没有为每个缺陷固定生成一条。
- 广义复发次数 = `repeat_after_fix` + `rollback_regress`，且子类型分别报出；没有把回滚重现漏计，也没有把 `repeat_unresolved` 混进复发。
- 回滚重现、修复从未生效（`fix_not_live`）、已部署未验证、修复无效四者已分开，没有合并成一条，也没有把 `fix_not_live` / `deployment_drift` 写成 `occurrence.kind`。
- 仅有部署漂移字样时未直接判复发或排除，已核实验证与回退证据。
- 同类缺陷只建 `similar_class` 关联，未新建 `related_case` occurrence，未计入任何一方复发次数；遗留 `related_case` 已按 §3.5 折算且未重复计数。
- `fix_actions` 只在可枚举时给整数，未知写 `null` 并注明；没有用 MR 数、Commit 数或消息轮数推算。
- 禅道重新激活仍停留在 `recurrence_signals`，未被直接当成发生或复发（重新激活既非必要条件也非充分条件）。
- **验证适用范围按 §2.6 环境（canonical_name）登记**：`lifecycle=verified_fixed` 未被解释成「所有环境均已验证」；一环境的验证通过证据没有被外推到其他环境（含同分类环境），也没有被用于另一环境的复发判定；涉及分环境时报告列了「已验证环境范围」与未覆盖/未知部分；环境或版本缺失影响判定时进了 `recurrence_check` 而非硬判。
- **`repeat_unresolved` 按环境判定（§2.2，Q-05）**：`first` 只属于缺陷主记录全局首次，没有按环境重复生成 `first`；判定某环境是否未解决时查了该环境的 `transitions.jsonl` 验证证据，没有只看全局 `lifecycle`；同一缺陷在从未验证过的环境独立发生且证据充分时登记了 `repeat_unresolved`（计入独立发生、不计复发），没有因「缺少部署记录」误判为不存在发生，也没有仅凭现象相似就认定同一缺陷。
- **`closed` 与历史验证（§2.7，Q-03 / Q-04）**：`closed` 没有新增或扩大验证范围，也没有因关闭认定其他环境验证通过；历史 `verified_fixed` 事实未被复发/回滚/关闭抹去；撤销验证结论走了有审计记录的更正流转，而非静默覆盖。
- **事件去重按 §3.8 执行**：先按主记录聚合再判同一次发生；精确时间先归一时区再比较；日期精度缺失用同自然日口径且原始精度保留（未虚构时分秒）；证据交集只计现象报告类（`role=report`），仅共享修复 MR/Commit/部署/背景材料未被当成自动去重依据；存在反证时未按同日+交集强行合并；歧义进了 `recurrence_check` 且待复核数量已披露；原始 occurrence 记录全部保留。
- 统计同时给出已确认数量、未知数量与覆盖范围；无发生记录的缺陷单列，未用缺陷数反推发生数。
- **回滚四要素与需求边界（V0.1.6）**：每条 `rollback_regress` 都同时具备同一缺陷身份、该环境有效验证、再次独立发生、回退证据；没有用需求背景虚构历史首次缺陷；用户功能要求未被当作历史缺陷首报。
- **更正与数字（V0.1.6）**：更正链只替换被明确更正的事实，原记录保留；数字引用核对了分母、指标名称与适用范围，未把更正后的分母套到其他指标。
- 人工结论字段（`confirmed_by=human` 的结论、复核结论）未被 AI 代填。
