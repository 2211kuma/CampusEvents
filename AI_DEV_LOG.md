# AI_DEV_LOG

记录人机协作的关键轮次，用于实验二的“AI 交互记录”与可维护性对照。

## 轮次 1｜读需求

- 输入：实验指导书 3.2–3.5、附录 B。
- 产出：8 项功能（P2-F01~F08）、C1–C10 验收用例、7 条硬约束清单。
- 结论：先做设计材料（任务D），再编码；编码以评审通过的类图为约束。

## 轮次 2｜定职责与接口

- 输入：任务A/B/C 要求。
- 决策：
  1. 名额检查抽为 `CapacityRule`（公共规则），策略只决定状态；
  2. 报名与通知用 `EventBus` + 订阅者解耦；
  3. 事件 `event_id = reg:{registration_id}:{action}` 做幂等键。
- 反驳记录：AI 曾建议把名额校验写进 `AuditPolicy` 并在批准时再写一遍。否决理由：同一条约束两处实现，口径易分叉；且审核型允许满员待审核，策略阶段不能断言名额。

## 轮次 3｜生成代码（baseline-v1）

- 一次性生成 `domain/`、`repositories.py`、`services.py`、`web.py`。
- 人工修改点：
  1. `connect()` 增加 `check_same_thread=False`——原生代码在 Flask 多线程下抛 `sqlite3.ProgrammingError`，页面 500；
  2. `web.py` 上下文补充 `student_map`，供审批台显示学生姓名；
  3. 模板中把“是否有有效报名”“是否已开始”的判断留在模板显示层，业务判断仍在服务层。

## 轮次 4｜测试

- 新增 `tests/test_acceptance.py`：C1–C10 加 4 条边界（活动已开始、有报名不能删、重复审批、通知失败隔离）+ 页面冒烟。
- 首次运行 15 passed；修复连接线程问题后复跑仍 15 passed。

## 轮次 5｜界面

- 5 个页面（列表、详情、我的报名与消息、活动管理、审批台），纯 CSS 无框架。
- 验收：`/`、`/me`、`/admin/activities`、`/admin/approvals`、`/static/style.css` 均 200；账号切换、报名按钮、统计数字渲染正确。

## 待办（下一版本 change-v2）

- 等待教师 CR；收到后先写影响分析（涉及类、风险、新增测试、预计改动范围），再从 baseline-v1 拉分支实现。

## 轮次 6｜变更影响分析（CR-01 / CR-02）

- 输入：教师变更单全文（`docs/cr_read.txt`）。
- 产出：`docs/变更影响分析-CR01-CR02.md`，先分析后编码，含涉及类、风险与应对、新增测试、可维护性指标（新增类 5、核心类改动 7、回归失败 0、耗时约 1.5 小时）。
- 判断：两项均为扩展式改动，不动 `CapacityRule`、不改既有策略逻辑、不重写服务层。

## 轮次 7｜实现 change-v2

- CR-01：新增 `GRADE_LIMITED` 策略类型与 `GradeLimitedRegistrationPolicy`，`PolicyContext` 增可选 `student`；`students` 表加 `grade` 并通过 `_migrate()` 增量补列，老库免重建；`RegistrationService.register` 仅多传一行上下文。
- CR-02：新增 `EmailRepository` / `MockEmailSender` / `EmailNotificationObserver`；幂等键改为 `事件:渠道`，两渠道互不吞事件；`EventBus` 失败留痕改用订阅者 `channel`；新增 `/admin/emails` 页面。
- 分歧与取舍：AI 建议把年级判断直接写进 `register()` 的 if 分支，否决——违反策略模式约束，且与 CR-01“新增独立策略”要求直接冲突；改为策略内先校验年级、再校验名额，提示按最直接原因给出。
- 回归：`pytest -q` 27 passed（15 条原用例 + 8 条 CR 用例 + 2 条扩展 + 页面冒烟），失败 0。

## 轮次 8｜变更版部署

- 服务器 `git pull` 后重启 `campusevent` 服务，现网库自动迁移（补 `grade` 列、建 `email_outbox`），公网复查页面与邮件记录页均 200。

