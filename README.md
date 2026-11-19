# CampusEvent 校园活动报名与管理系统（baseline-v1）

《软件工程》实验二初始版本。Flask + SQLite，单机可运行，覆盖 P2-F01 至 P2-F08 八项功能。

## 运行

```powershell
cd D:\test\CampusEvent
"C:\Users\79874\AppData\Local\Programs\Python\Python314\python.exe" run.py
```

浏览器打开 http://127.0.0.1:5000 。

- 演示账号：S001 张小明、S002 李小红、S003 王小雨（右上角切换）
- 重置数据：`python seed.py --reset`
- 跑测试：`python -m pytest -q`

## 目录

```
app/
  domain/          领域层（不依赖 Flask）
    entities.py      实体与状态枚举
    policies.py      RegistrationPolicy 抽象 + 直接/审核两种策略 + CapacityRule
    events.py        RegistrationEvent + EventBus（观察者）
    notifications.py 站内通知订阅者（按 eventId 幂等）
    errors.py        业务异常
  repositories.py  SQLite 存取（6 张表）
  services.py      ActivityService / RegistrationService / build_services
  web.py           Flask 路由（只取参数、调服务、渲染）
  templates/       5 个页面
  static/style.css
tests/test_acceptance.py   C1–C10 + 边界 + 通知失败隔离，共 15 条
docs/              设计说明书与 UML 图生成脚本
```

## 关键设计落点

| 约束 | 落点 |
| --- | --- |
| 名额只按“已通过”统计，待审核不占名额 | `CapacityRule` 公共规则；`AuditPolicy` 不校验名额，批准时再校验 |
| 同一学生同一活动至多一条有效报名 | `RegistrationService.register` + `find_active` |
| 活动开始后不得报名/取消 | `Activity.is_open()` 在服务层校验 |
| 通知失败不得让报名消失 | `EventBus` 捕获订阅者异常写 `notification_failures`，事务不回滚 |
| 不重复通知 | `processed_events` 以 `reg:{id}:{action}` 幂等 |
| 有有效报名的活动不允许删除 | `ActivityService.delete` 抛错，否则软删除 |

## 已验收

`python -m pytest -q` → 15 passed。
