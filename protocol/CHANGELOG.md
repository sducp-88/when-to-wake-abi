# CHANGELOG

## 2026-08-04 - Severity measurement correction (SAP amendment v1.4)

- Restricted eICU neurologic eligibility to the exact GCS Total field and valid values from 3 to 15.
- Superseded the earlier eICU transport estimate and rebuilt the formal transport analysis as version 1.2.
- Added outcome-blind weighted balance diagnostics for MIMIC GCS components, eICU valid GCS Total, and eICU APACHE IVa score and acute physiology score.
- Added a time-valid APACHE IVa sensitivity feasibility audit. The model failed the maximum-weighted-SMD and early-strategy ESS-ratio gates; no effect estimate or confidence interval from that model is released or interpreted.
- The primary MIMIC-IV estimand, cohort, result, sensitivity analyses, and inference are unchanged.

## 2026-08-01 — First BigQuery smoke test denied

- 对 `physionet-data.mimiciv_v3_1_icu.icustays` 的首次汇总查询返回 `bigquery.tables.getData` Access Denied。
- SQL 语法与官方 v3.1 schema 名称一致；当前不能区分版本化数据集授权、Google 登录账号不一致或授权同步问题。
- 新增只读诊断脚本 `00b_access_smoke_test_alias.sql`，使用官方 BigQuery 指南列出的 `mimiciv_icu` 别名。
- 本次失败仅为访问诊断，不涉及患者级输出、镇静策略比较或结局分析。

## 2026-08-01 — MIMIC-IV BigQuery access granted

- 用户提供的 PhysioNet 绿色提示确认：MIMIC-IV v3.1 的 GCP BigQuery 权限已授予绑定的 Google 账号。
- 尚未运行任何数据查询，故状态记录为 `bigquery_granted_unqueried`，不提前宣称访问测试通过。
- 下一步为创建/选择 Google Cloud 查询项目，并运行只返回汇总计数与时间范围的 smoke test。

## 2026-08-01 — Project DUAs signed and HiRID request submitted

- 用户确认 MIMIC-IV 与 eICU-CRD 项目 DUA 已签署；访问状态暂记为待验证，未提前标记为已获得数据。
- HiRID 具体研究申请已发送，状态更新为等待 contributor review。
- 下一操作为配置 MIMIC-IV BigQuery 并运行只返回安全汇总的访问测试。
- 冻结的可行性方案、暴露候选阈值和 Go/No-Go 标准未改变。

## 2026-08-01 — PhysioNet training active

- 用户确认 PhysioNet 已审核通过 CITI training，状态更新为 `Active`。
- 阶段 0 下一步转为逐库权限申请：MIMIC-IV DUA、eICU-CRD DUA、HiRID contributor review。
- 冻结方案、共同数据模型及 Go/No-Go 标准均未改变。

## 2026-07-25 — CITI training submitted

- 完成 `Data or Specimens Only Research`（含 HIPAA）课程。
- 完整 training report 已提交 PhysioNet。
- Certification 状态确认为 `Under review`。
- 下一步：等待状态转为 `Active`，随后签署 MIMIC-IV/eICU-CRD DUA，并提交 HiRID 具体研究问题。

## 2026-07-25 — v0.1

- 正式启动 WHEN-TO-WAKE ABI。
- 冻结核心人群、序贯目标试验框架、主要结局和数据库优先级。
- 明确先导阶段禁止查看治疗效果。
- 建立 Go/No-Go 门槛。
- 记录初始环境状态：PhysioNet 未登录，本地未发现数据库副本，未检测到常用数据库 CLI。

- 当前无 Active/Under review 培训记录；下一阻塞为完成并上传 CITI Data or Specimens Only Research（含 HIPAA）完整 training report。
