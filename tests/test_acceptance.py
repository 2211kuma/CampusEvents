"""C1–C10 初始版本验收测试 + 通知失败隔离测试。

运行：python -m pytest -q
"""
import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.domain.entities import PolicyType, RegistrationStatus
from app.domain.errors import (
    ActivityClosedError,
    CapacityExceededError,
    DuplicateRegistrationError,
    InvalidStateError,
)
from app.repositories import connect, init_schema, seed_demo
from app.services import build_services
from app.web import create_app


def new_env(tmp_path, name="test.db"):
    db = tmp_path / name
    conn = connect(db)
    init_schema(conn)
    seed_demo(conn)
    return conn, build_services(conn)


def make_activity(sv, capacity=2, policy=PolicyType.DIRECT, title="测试活动", days=10):
    return sv.activities.create(
        title=title,
        category="竞赛",
        start_at=datetime.now() + timedelta(days=days),
        location="信息楼",
        capacity=capacity,
        policy_type=policy.value,
    )


@pytest.fixture
def env(tmp_path):
    conn, sv = new_env(tmp_path)
    yield sv
    conn.close()


# C1 管理员创建直接报名活动，容量 2
def test_c1_create_direct_activity(env):
    a = make_activity(env, capacity=2, policy=PolicyType.DIRECT, title="直接报名容量2")
    assert a.activity_id > 0
    assert a.capacity == 2
    assert a.policy_type == PolicyType.DIRECT
    assert a.is_open()


# C2 学生报名直接报名活动 → 已通过 + 通知
def test_c2_direct_register_approved_and_notified(env):
    a = make_activity(env)
    reg = env.registrations.register("S001", a.activity_id)
    assert reg.status == RegistrationStatus.APPROVED
    msgs = env.messages.list_by_student("S001")
    mine = [m for m in msgs if m.activity_id == a.activity_id]
    assert len(mine) == 1
    assert "已通过" in mine[0].content


# C3 重复有效报名被拒绝
def test_c3_duplicate_register_rejected(env):
    a = make_activity(env)
    env.registrations.register("S001", a.activity_id)
    with pytest.raises(DuplicateRegistrationError):
        env.registrations.register("S001", a.activity_id)
    assert env.registrations.stats(a.activity_id)["approval"] == 1


# C4 名额满后第三名学生报名失败
def test_c4_capacity_blocks_third_student(env):
    a = make_activity(env, capacity=2)
    assert env.registrations.register("S001", a.activity_id).status == RegistrationStatus.APPROVED
    assert env.registrations.register("S002", a.activity_id).status == RegistrationStatus.APPROVED
    with pytest.raises(CapacityExceededError):
        env.registrations.register("S003", a.activity_id)
    assert env.registrations.stats(a.activity_id)["approval"] == 2


# C5 审核型活动：报名进入待审核，不占名额
def test_c5_audit_register_pending_without_occupying(env):
    a = make_activity(env, capacity=1, policy=PolicyType.AUDIT)
    reg = env.registrations.register("S001", a.activity_id)
    assert reg.status == RegistrationStatus.PENDING
    stats = env.registrations.stats(a.activity_id)
    assert stats["approval"] == 0
    assert stats["pending"] == 1
    assert stats["remaining"] == 1


# C6 批准待审核报名 → 已通过 + 通知
def test_c6_approve_pending(env):
    a = make_activity(env, capacity=3, policy=PolicyType.AUDIT)
    reg = env.registrations.register("S001", a.activity_id)
    approved = env.registrations.approve(reg.registration_id)
    assert approved.status == RegistrationStatus.APPROVED
    texts = [m.content for m in env.messages.list_by_student("S001")]
    assert any("已通过" in t and a.title in t for t in texts)


# C7 拒绝待审核报名 → 已拒绝 + 通知
def test_c7_reject_pending(env):
    a = make_activity(env, capacity=3, policy=PolicyType.AUDIT)
    reg = env.registrations.register("S001", a.activity_id)
    rejected = env.registrations.reject(reg.registration_id)
    assert rejected.status == RegistrationStatus.REJECTED
    texts = [m.content for m in env.messages.list_by_student("S001")]
    assert any("拒绝" in t for t in texts)


# C8 批准时名额已满 → 批准失败，不超上限
def test_c8_approve_when_full(env):
    a = make_activity(env, capacity=1, policy=PolicyType.AUDIT)
    first = env.registrations.register("S001", a.activity_id)
    second = env.registrations.register("S002", a.activity_id)
    env.registrations.approve(first.registration_id)
    with pytest.raises(CapacityExceededError):
        env.registrations.approve(second.registration_id)
    assert env.registrations.stats(a.activity_id)["approval"] == 1
    still = env.registrations.registrations.get(second.registration_id)
    assert still.status == RegistrationStatus.PENDING
    texts = [m.content for m in env.messages.list_by_student("S002")]
    assert not any("申请已通过" in t for t in texts)


# C9 取消报名 → 已取消，统计同步
def test_c9_cancel_updates_stats(env):
    a = make_activity(env, capacity=2)
    reg = env.registrations.register("S001", a.activity_id)
    env.registrations.cancel("S001", reg.registration_id)
    stats = env.registrations.stats(a.activity_id)
    assert stats["approval"] == 0
    assert stats["remaining"] == 2
    # 取消后可再次报名，生成新记录
    again = env.registrations.register("S001", a.activity_id)
    assert again.registration_id != reg.registration_id
    # 不能取消他人的报名
    with pytest.raises(Exception):
        env.registrations.cancel("S002", reg.registration_id)


# C10 重启服务后数据仍一致
def test_c10_persistence_after_restart(tmp_path):
    conn, sv = new_env(tmp_path, "persist.db")
    a = make_activity(sv, capacity=2)
    sv.registrations.register("S001", a.activity_id)
    conn.close()

    conn2, sv2 = new_env(tmp_path, "persist.db")
    try:
        count = sv2.messages.count("S001")
        assert count >= 1
        regs = [r for r in sv2.registrations.my_registrations("S001") if r.activity_id == a.activity_id]
        assert len(regs) == 1
        assert regs[0].status == RegistrationStatus.APPROVED
        assert sv2.registrations.stats(a.activity_id)["approval"] == 1
    finally:
        conn2.close()


# 业务边界：活动开始后不能报名
def test_closed_activity_rejects_register(env):
    a = make_activity(env, capacity=5)
    env.activities.activities.update(a.activity_id, start_at=datetime.now() - timedelta(hours=1))
    with pytest.raises(ActivityClosedError):
        env.registrations.register("S001", a.activity_id)


# 业务边界：有有效报名的活动不能删除
def test_delete_activity_with_active_registration_blocked(env):
    a = make_activity(env, capacity=2)
    env.registrations.register("S001", a.activity_id)
    with pytest.raises(Exception) as exc:
        env.activities.delete(a.activity_id)
    assert "不能删除" in str(exc.value)


# 业务边界：重复审批被拒绝
def test_repeat_approve_rejected(env):
    a = make_activity(env, capacity=3, policy=PolicyType.AUDIT)
    reg = env.registrations.register("S001", a.activity_id)
    env.registrations.approve(reg.registration_id)
    with pytest.raises(InvalidStateError):
        env.registrations.approve(reg.registration_id)


# 通知失败不影响报名，且留痕
def test_notification_failure_does_not_rollback(tmp_path):
    conn = connect(tmp_path / "fail.db")
    init_schema(conn)
    seed_demo(conn)

    from app.domain.events import EventBus
    from app.domain.notifications import InAppNotificationObserver
    from app.repositories import (
        ActivityRepository, MessageRepository, NotificationFailureRepository,
        ProcessedEventRepository, RegistrationRepository, StudentRepository,
    )
    from app.services import ActivityService, RegistrationService

    msg_repo = MessageRepository(conn)
    failures = NotificationFailureRepository(conn)

    def recorder(event, channel, detail):
        failures.add(event.event_id, channel, detail, datetime.now())

    bus = EventBus(failure_recorder=recorder)
    bus.subscribe(InAppNotificationObserver(msg_repo, ProcessedEventRepository(conn)))

    class BrokenChannel:
        def __call__(self, event):
            raise RuntimeError("渠道超时")

    bus.subscribe(BrokenChannel())

    activities = ActivityRepository(conn)
    regs = RegistrationRepository(conn)
    sv = RegistrationService(activities, regs, StudentRepository(conn), bus)
    act_sv = ActivityService(activities, regs)
    a = act_sv.create("通知失败活动", "讲座", datetime.now() + timedelta(days=5), "报告厅", 5, "DIRECT")
    reg = sv.register("S001", a.activity_id)
    assert reg.status == RegistrationStatus.APPROVED
    assert regs.get(reg.registration_id) is not None
    assert len(failures.list_all()) >= 1
    # 正常渠道仍写入消息
    assert msg_repo.count("S001") >= 1
    conn.close()


# 页面冒烟：主要页面可访问，报名流程可走通
def test_web_smoke(tmp_path):
    app = create_app(tmp_path / "web.db")
    app.config.update(TESTING=True)
    client = app.test_client()
    for url in ("/", "/me", "/admin/activities", "/admin/approvals"):
        resp = client.get(url)
        assert resp.status_code == 200, url

    sv = app.extensions["services"]
    a = make_activity(sv, capacity=3, title="页面报名测试")
    resp = client.post(f"/activity/{a.activity_id}/register", follow_redirects=True)
    assert "已通过" in resp.get_data(as_text=True)
    resp = client.get(f"/activity/{a.activity_id}")
    assert resp.status_code == 200
