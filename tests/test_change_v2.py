"""变更版本 change-v2 验收测试：CR1-01~05、CR2-01~05。

运行：python -m pytest -q
"""
import os
import subprocess
import sys
from datetime import datetime, timedelta

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.domain.entities import PolicyType, RegistrationStatus
from app.domain.errors import GradeNotAllowedError
from app.domain.notifications import MockEmailSender
from app.repositories import connect, init_schema, seed_demo
from app.services import build_services


def new_env(tmp_path, name="v2.db", sender=None):
    conn = connect(tmp_path / name)
    init_schema(conn)
    seed_demo(conn)
    return conn, build_services(conn, email_sender=sender)


def make_activity(sv, capacity=3, policy=PolicyType.GRADE_LIMITED, title="年级限定活动", days=10):
    return sv.activities.create(
        title=title, category="实践",
        start_at=datetime.now() + timedelta(days=days),
        location="工程训练中心", capacity=capacity, policy_type=policy.value,
    )


@pytest.fixture
def env(tmp_path):
    conn, sv = new_env(tmp_path)
    yield sv
    conn.close()


# ---------------- CR-01 年级限定 ----------------
# CR1-01 大二学生（S001）报名成功
def test_cr1_01_sophomore_approved(env):
    a = make_activity(env)
    reg = env.registrations.register("S001", a.activity_id)
    assert reg.status == RegistrationStatus.APPROVED
    assert env.students.get("S001").grade == 2


# CR1-02 大三学生（S002）报名成功
def test_cr1_02_junior_approved(env):
    a = make_activity(env)
    reg = env.registrations.register("S002", a.activity_id)
    assert reg.status == RegistrationStatus.APPROVED
    assert env.students.get("S002").grade == 3


# CR1-03 大一学生（S003）被拒绝，提示含年级原因
def test_cr1_03_freshman_rejected(env):
    a = make_activity(env)
    with pytest.raises(GradeNotAllowedError) as exc:
        env.registrations.register("S003", a.activity_id)
    assert "仅限大二、大三" in str(exc.value)
    assert env.registrations.stats(a.activity_id)["approval"] == 0


# CR1-04 大四学生（S004）被拒绝，提示含年级原因
def test_cr1_04_senior_rejected(env):
    a = make_activity(env)
    with pytest.raises(GradeNotAllowedError) as exc:
        env.registrations.register("S004", a.activity_id)
    assert "仅限大二、大三" in str(exc.value)


# CR1-05 重跑 C1–C10 全部通过
def test_cr1_05_regression_c1_c10():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", os.path.join(ROOT, "tests", "test_acceptance.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


# 年级限定活动仍遵守名额规则
def test_cr1_capacity_still_enforced(env):
    a = make_activity(env, capacity=1)
    env.registrations.register("S001", a.activity_id)
    from app.domain.errors import CapacityExceededError
    with pytest.raises(CapacityExceededError):
        env.registrations.register("S002", a.activity_id)


# ---------------- CR-02 模拟邮件 ----------------
# CR2-01 直接报名通过 → 站内消息 + 邮件两条记录
def test_cr2_01_direct_register_two_channels(env):
    a = make_activity(env, policy=PolicyType.DIRECT)
    reg = env.registrations.register("S001", a.activity_id)
    assert reg.status == RegistrationStatus.APPROVED
    assert any(m.activity_id == a.activity_id for m in env.messages.list_by_student("S001"))
    mails = [m for m in env.emails.list_all() if m["event_id"] == f"reg:{reg.registration_id}:submitted"]
    assert len(mails) == 1
    assert mails[0]["status"] == "sent"
    assert a.title in mails[0]["subject"]


# CR2-02 审核通过 / 拒绝都与站内消息对应
def test_cr2_02_audit_approve_and_reject(env):
    ok = make_activity(env, policy=PolicyType.AUDIT, title="审核通过活动")
    no = make_activity(env, policy=PolicyType.AUDIT, title="审核拒绝活动")
    r1 = env.registrations.register("S001", ok.activity_id)
    r2 = env.registrations.register("S001", no.activity_id)
    env.registrations.approve(r1.registration_id)
    env.registrations.reject(r2.registration_id)

    mails = env.emails.list_all()
    approved_mails = [m for m in mails if m["event_id"] == f"reg:{r1.registration_id}:approved"]
    rejected_mails = [m for m in mails if m["event_id"] == f"reg:{r2.registration_id}:rejected"]
    assert len(approved_mails) == 1 and approved_mails[0]["status"] == "sent"
    assert len(rejected_mails) == 1 and rejected_mails[0]["status"] == "sent"
    assert "通过" in approved_mails[0]["subject"]
    assert "未通过" in rejected_mails[0]["subject"]
    texts = [m.content for m in env.messages.list_by_student("S001")]
    assert any("已通过" in t for t in texts) and any("拒绝" in t for t in texts)


# CR2-03 邮件失败：报名状态正确、失败有留痕、不回滚
def test_cr2_03_email_failure_keeps_registration(tmp_path):
    conn, sv = new_env(tmp_path, "mailfail.db", sender=MockEmailSender(fail_for=("s001",)))
    try:
        a = make_activity(sv, policy=PolicyType.DIRECT)
        reg = sv.registrations.register("S001", a.activity_id)
        assert reg.status == RegistrationStatus.APPROVED
        assert sv.registrations.registrations.get(reg.registration_id).status == RegistrationStatus.APPROVED
        assert sv.registrations.stats(a.activity_id)["approval"] == 1
        mails = sv.emails.list_all()
        assert any(m["status"] == "failed" and "模拟邮件网关超时" in m["detail"] for m in mails)
        assert any(f["channel"] == "email" for f in sv.failures.list_all())
        # 站内消息渠道不受影响
        assert sv.messages.count("S001") >= 1
    finally:
        conn.close()


# CR2-04 重复提交同一事件不重复发信
def test_cr2_04_no_duplicate_notification(env):
    a = make_activity(env, policy=PolicyType.DIRECT)
    reg = env.registrations.register("S001", a.activity_id)
    mails_before = [m for m in env.emails.list_all() if m["event_id"] == f"reg:{reg.registration_id}:submitted"]
    assert len(mails_before) == 1

    # 直接重复派发同一事件，模拟网络重试
    from app.domain.events import RegistrationEvent
    bus_services = env.registrations.events
    event = RegistrationEvent(
        event_id=f"reg:{reg.registration_id}:submitted", action="submitted",
        registration_id=reg.registration_id, activity_id=a.activity_id,
        activity_title=a.title, student_id="S001", status=RegistrationStatus.APPROVED,
        occurred_at=datetime.now(),
    )
    bus_services.publish(event)
    mails_after = [m for m in env.emails.list_all() if m["event_id"] == f"reg:{reg.registration_id}:submitted"]
    assert len(mails_after) == 1
    assert env.messages.count("S001") == 1


# CR2-05 重跑 C1–C10 全部通过
def test_cr2_05_regression_c1_c10():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", os.path.join(ROOT, "tests", "test_acceptance.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


# 邮件记录页面可访问
def test_web_emails_page(tmp_path):
    from app.web import create_app
    app = create_app(tmp_path / "web2.db")
    app.config.update(TESTING=True)
    client = app.test_client()
    resp = client.get("/admin/emails")
    assert resp.status_code == 200
