"""通知订阅者：只做“把事件变成通知”，不碰报名状态。

两个渠道：
- InAppNotificationObserver：站内消息（baseline-v1 已有）
- EmailNotificationObserver：模拟邮件（CR-02），失败只留痕、不回滚报名
两者都用“事件键 + 渠道后缀”在已处理事件表占用，互不干扰，也不重复发送。
"""

from __future__ import annotations

from datetime import datetime

from .entities import RegistrationStatus
from .events import RegistrationEvent


class InAppNotificationObserver:
    """站内通知渠道。通过 event_id:inapp 幂等，避免重复通知。"""

    CONTENT = {
        ("submitted", RegistrationStatus.PENDING): "报名《{title}》已提交，等待管理员审核。",
        ("submitted", RegistrationStatus.APPROVED): "报名《{title}》成功，已通过。",
        ("approved", RegistrationStatus.APPROVED): "你报名《{title}》的申请已通过。",
        ("rejected", RegistrationStatus.REJECTED): "你报名《{title}》的申请已被拒绝。",
        ("cancelled", RegistrationStatus.CANCELLED): "你已取消《{title}》的报名。",
    }

    channel = "inapp"

    def __init__(self, message_repository, processed_event_repository):
        self.messages = message_repository
        self.processed = processed_event_repository

    def __call__(self, event: RegistrationEvent) -> None:
        key = f"{event.event_id}:{self.channel}"
        if not self.processed.claim(key, datetime.now()):
            return  # 已处理过，跳过，保证不重复通知
        template = self.CONTENT.get((event.action, event.status), "《{title}》报名状态更新。")
        self.messages.add(
            student_id=event.student_id,
            activity_id=event.activity_id,
            content=template.format(title=event.activity_title),
            created_at=event.occurred_at,
        )


class MockEmailSender:
    """模拟邮件网关：不接真实 SMTP，可配置对某些学号模拟发送失败（教学演示 CR2-03）。"""

    def __init__(self, fail_for: tuple[str, ...] = ()):
        self.fail_for = tuple(fail_for)
        self.outbox: list[tuple[str, str, str]] = []

    def send(self, to: str, subject: str, body: str) -> None:
        if any(flag in to for flag in self.fail_for):
            raise RuntimeError("模拟邮件网关超时")
        self.outbox.append((to, subject, body))


class EmailNotificationObserver:
    """CR-02 邮件渠道：只对“报名通过 / 审核通过 / 拒绝”三类事件发信。"""

    channel = "email"

    TARGETS = {
        ("submitted", RegistrationStatus.APPROVED),
        ("approved", RegistrationStatus.APPROVED),
        ("rejected", RegistrationStatus.REJECTED),
    }

    SUBJECTS = {
        ("submitted", RegistrationStatus.APPROVED): "报名成功：{title}",
        ("approved", RegistrationStatus.APPROVED): "报名通过：{title}",
        ("rejected", RegistrationStatus.REJECTED): "报名未通过：{title}",
    }

    BODIES = {
        ("submitted", RegistrationStatus.APPROVED): "你报名的《{title}》已通过，请按时参加。",
        ("approved", RegistrationStatus.APPROVED): "你报名《{title}》的申请已通过，请按时参加。",
        ("rejected", RegistrationStatus.REJECTED): "很抱歉，你报名《{title}》的申请未通过。",
    }

    def __init__(self, email_repository, processed_event_repository, sender, student_repository=None):
        self.emails = email_repository
        self.processed = processed_event_repository
        self.sender = sender
        self.students = student_repository

    def recipient_of(self, student_id: str) -> str:
        if self.students is not None:
            student = self.students.get(student_id)
            if student is not None:
                return f"{student.student_id.lower()}.{student.name}@campus.example.edu"
        return f"{student_id.lower()}@campus.example.edu"

    def __call__(self, event: RegistrationEvent) -> None:
        if (event.action, event.status) not in self.TARGETS:
            return  # 其余事件（待审核、取消）按 CR-02 不发邮件
        key = f"{event.event_id}:{self.channel}"
        if not self.processed.claim(key, datetime.now()):
            return  # 同一业务动作重复派发时不再发第二封

        recipient = self.recipient_of(event.student_id)
        subject = self.SUBJECTS[(event.action, event.status)].format(title=event.activity_title)
        content = self.BODIES[(event.action, event.status)].format(title=event.activity_title)
        try:
            self.sender.send(recipient, subject, content)
            self.emails.add(event.event_id, recipient, subject, content, "sent", "", event.occurred_at)
        except Exception as exc:  # noqa: BLE001 - 邮件失败必须留痕但不得回滚报名
            self.emails.add(
                event.event_id, recipient, subject, content, "failed",
                f"{type(exc).__name__}: {exc}", event.occurred_at,
            )
            raise
