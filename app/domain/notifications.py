"""通知订阅者：只做“把事件变成站内消息”，不碰报名状态。"""

from __future__ import annotations

from datetime import datetime

from .entities import RegistrationStatus
from .events import RegistrationEvent


class InAppNotificationObserver:
    """站内通知渠道。通过 event_id 幂等，避免重复通知。"""

    CONTENT = {
        ("submitted", RegistrationStatus.PENDING): "报名《{title}》已提交，等待管理员审核。",
        ("submitted", RegistrationStatus.APPROVED): "报名《{title}》成功，已通过。",
        ("approved", RegistrationStatus.APPROVED): "你报名《{title}》的申请已通过。",
        ("rejected", RegistrationStatus.REJECTED): "你报名《{title}》的申请已被拒绝。",
        ("cancelled", RegistrationStatus.CANCELLED): "你已取消《{title}》的报名。",
    }

    def __init__(self, message_repository, processed_event_repository):
        self.messages = message_repository
        self.processed = processed_event_repository

    def __call__(self, event: RegistrationEvent) -> None:
        if not self.processed.claim(event.event_id, datetime.now()):
            return  # 已处理过，跳过，保证不重复通知
        template = self.CONTENT.get((event.action, event.status), "《{title}》报名状态更新。")
        self.messages.add(
            student_id=event.student_id,
            activity_id=event.activity_id,
            content=template.format(title=event.activity_title),
            created_at=event.occurred_at,
        )
