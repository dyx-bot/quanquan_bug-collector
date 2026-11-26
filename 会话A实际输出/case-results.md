# 案例级结果（actual_output / test_result / fail_reason）

> `test_result=PASS` 仅表示本案例按规则完成处理并通过流程自检，不代表参考答案判定通过或功能测试通过。


## TC-001 两条非缺陷提交：test commit 与合并前 diff 落点调整
- actual_output：2 条原始记录均判为 template/context_only；0 候选、0 缺陷、0 发生。E1 test commit（body 空）与 E2 合并前 diff 落点调整均未误建缺陷。
- test_result：PASS
- fail_reason：null
- note：关键点：空 body 的 test commit 与纯合并准备提交不得生成候选。

## TC-002 Merge commit 内的修复描述（token 过期→502）
- actual_output：E3 识别为 Merge commit（父提交=2），完整 message 提取出 1 个缺陷候选并建 1 个缺陷、1 条 first 发生；lifecycle=fixed_unverified（合并 develop，未部署验证）；MR !188 仅记 mr_ref_unverified 复核，未写成 kind=mr 证据。
- test_result：PASS
- fail_reason：null
- note：关键点：Merge 提交必须按父提交数识别并分析完整正文；未核实 MR 引用不得冒充快照。

## TC-003 feat 前缀提交内夹带存量 bug 修复
- actual_output：E4 未因 feat 前缀跳过；正文中的存量 bug 提取为 1 个缺陷、1 条 first 发生；设计美化/新增 DESIGN.md 等按需求侧处理，未误计为缺陷。
- test_result：PASS
- fail_reason：null
- note：关键点：feat 前缀按内容判断，不遗漏夹带的缺陷修复；新增功能/设计改动不算缺陷。

## TC-004 同一禅道单 #14686 的修复提交 + 禅道快照
- actual_output：commit 与禅道 #14686 按 high 置信归并为 1 个缺陷；source_status 保留禅道 resolved/fixed 快照；1 条 first 发生；lifecycle=fixed_unverified（resolved+commit 不等于部署验证）。
- test_result：PASS
- fail_reason：null
- note：关键点：同号+内容吻合才 high 归并；禅道 resolved 不自动等于 verified_fixed。

## TC-005 同一缺陷多轮修复/补测（#14686）不得计多次发生
- actual_output：4 个 commit + 禅道归并为 1 个缺陷；仅 1 条 first 发生；E6 测试提交记 evidence_only/related_fix；E7/E8 记 related_fix，未因补修轮数生成 repeat_unresolved；fix_actions=3（主修/表头重置/多切片器同步）。
- test_result：PASS
- fail_reason：null
- note：关键点：多轮补修与补测不等于多次发生；fix_actions 可枚举为 3。

## TC-006 同批 3 个禅道单（15030/15032/15036）与各自提交
- actual_output：同批 10 条证据拆为 3 个独立缺陷（15030/15032/15036），各 1 条 first；E10:merge 与其源提交判 duplicate_record 不重复计数；E11 多提交归入 15036；3 单 source_status 均 active，而修复 MR 已合并 → lifecycle=fixed_unverified，未误判 verified。
- test_result：PASS
- fail_reason：null
- note：关键点：同批/同作者不等于同一缺陷；merge 与其源提交不重复建缺陷。

## TC-007 两个不同业务的 Merge commit（路由质检批次 / 15030）
- actual_output：两个 Merge commit 分别按内容建 2 个缺陷：E12 为批次级摘要 → suspect + 复核（字段缺失）；E9 明示 15030 → defect。未因同批/同作者合并，也未把批次摘要当成已确认缺陷。
- test_result：PASS
- fail_reason：null
- note：关键点：Merge 提交按内容分流；批次摘要不足时降为 suspect 进复核，不硬判。

## TC-008 禅道 #15048 与两轮跟进 Merge（标题噪声）
- actual_output：禅道 #15048 + 两轮跟进 Merge 归并为 1 个缺陷；仅 1 条 first；两轮补修记 related_fix，未生成 repeat_unresolved；禅道仍 active、无验证 → lifecycle=fixing。
- test_result：PASS
- fail_reason：null
- note：关键点：跟进轮次不等于发生次数，禅道 active 保持未解决状态。

## TC-009 新增功能类 feat（云端解析接入）不得判为缺陷
- actual_output：E14 识别为新增功能（feat，默认不启用），未生成缺陷候选/缺陷/发生；作为需求线索单独登记（requirement_clues）。未因『未验证 Aura 端点/OCR』误判为缺陷。
- test_result：PASS
- fail_reason：null
- note：关键点：缺预期依据的新增功能不得判为 Bug（红线 1）。

## TC-A1 钉钉长线程：切片「无章节标题」两类根因 + 修复部署验证
- actual_output：10 条消息中：G12/G13/G17/G19/G21 作为候选证据，G14/G15/G18/G20 记 evidence_only 状态证据；按两个独立根因拆 2 个缺陷（代码缺标题栈 / 存量未回填），另记 1 个页脚噪声 suspect；两者在 soso-dev 经部署+现场复验 → verified_fixed；机器人回执未被 is_robot 排除。
- test_result：PASS
- fail_reason：null
- note：关键点：同一现象两根因须拆分；机器人回执含现象/修复结论可用；环境 81=soso-dev 归一；回填数量不一致进复核。

## TC-A2 长消息：验收要求 + 多条必须修的缺陷（两轮质检）
- actual_output：两条长消息拆出 10 个独立缺陷（音视频超时、ES 断管、任务文案/分页/ETA、压测数据混入、多级表头、表格结构、页眉页脚、OXR 幻觉），各 1 条 first；5 项验收目标（速度/利用率/成功率/完整性/准确性）及『>1000页自动拆分』『11种格式支持』按需求线索处理，未计为缺陷。
- test_result：PASS
- fail_reason：null
- note：关键点：长消息须拆分；需求验收口径与具体缺陷分列，不把整段当 1 个 Bug。

## TC-A3 同线程两个问题：新建应用内置配置缺失 / 非默认应用详情 404
- actual_output：同线程拆 2 个缺陷：新建应用内置配置缺失（G1，!104 部署后 G5 新应用复现 → first+repeat_unresolved，soso-dev 场景未验证）；非默认应用详情 404（G2，!105 部署但未人眼验证 → fixed_unverified + 复核）。G3/G4 记状态证据。
- test_result：PASS
- fail_reason：null
- note：关键点：不要因同线程/同机器人回执把两个不同缺陷并成一个；MR 部署≠验证通过；新应用复现判 repeat_unresolved。

## TC-A4 查看原文不定位切片：修复验证后被部署覆盖（回滚重现）
- actual_output：同一缺陷：G6 首报 → G7 验证通过（soso-dev，Playwright）→ G8 实测仍不定位 → G9 查明 compose pin 停在修复前镜像、部署冲回旧镜像并复测恢复，判 rollback_regress（计入广义复发 1 次）；另记兜底链路缺锚点 suspect。
- test_result：PASS
- fail_reason：null
- note：关键点：验证通过后因 pin/镜像回退重现 = rollback_regress，不是 repeat_after_fix，也不是 fix_not_live。

## TC-A5 『匹配失败』实为部署期 502：区分环境异常与产品缺陷
- actual_output：『匹配失败』主现象经 G11 判定为重新部署窗口期 502 瞬时异常（环境/执行异常，不计产品缺陷）；从中拆出两个真实产品问题：前端吞 502/401 无重试（suspect）、mp4 按文件名误匹配 FAQ 策略（defect），各 1 条 first。
- test_result：PASS
- fail_reason：null
- note：关键点：不要把部署窗口期瞬时 502 记成产品缺陷；但要从同回执里识别真实缺陷（吞错、误匹配）。

## TC-A6 数据外泄 P1 + 正式环境修复与隔离模块缺失
- actual_output：G26 一条长消息拆 2 个独立缺陷（外发事故 P1、发布缺 #15030/!176），各 1 条 first；两条消息原句均未给出已登记环境别名，environment 留空并各建 field_verify；G29 为机器人任务失败模板回执，标 template/context_only，不建缺陷。
- test_result：PASS
- fail_reason：null
- note：关键点：安全事件照常登记为缺陷；外部通报/责任结论属人工，AI 只做证据与记录。

## TC-A7 MAT-050 质检：89 页丢失 + 多类结构缺陷 + DP/OXR 口径
- actual_output：MAT-050 质检拆出 6 个明确缺陷（丢 89 页、page_coverage 误报、convert 空闲、多级表头、表格结构、页眉页脚）+ 1 个 DP 字符数口径 suspect（进复核）；速度/利用率/准确率目标、薄页 OXR 决策按需求/决策处理；G25 与本案例多级表头/结构/页眉页脚为同源同现象的佐证，统一归属本案例对应缺陷，避免跨案例重复计数。
- test_result：PASS
- fail_reason：null
- note：关键点：G25 与 TC-A2 同源，需按现象归属，避免同一现象在两案例重复建缺陷（本轮各案例独立处理，TC-A7 引用 G23 主证据，G25 作佐证）。

## TC-A8 healthcheck 误杀 P-103 + 验收回执与观察项
- actual_output：G28 记 1 个 P1 缺陷（healthcheck 误杀，首次 11-24 11:00:54），环境原句未给已登记别名 → environment 留空 + field_verify；G27 为验收回执，标 template/context_only；G28 中 15032 生效/P-98 闭环不属本案例缺陷，仅作背景，不补记发生、不扩大验证范围；embedding 并发为观察项，不单独成缺陷。
- test_result：PASS
- fail_reason：null
- note：关键点：15032 生效/P-98 闭环只作背景，不因提及就补记发生或扩大验证范围；观察项（并发）不算缺陷；环境不猜归。
