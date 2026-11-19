"""领域事件与事件总线（观察者模式）。

报名业务只负责发布事件，不关心谁去发消息。订阅者异常被隔离记录，
不影响已经合法提交的报名事务。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from .entities import RegistrationStatus


@dataclass(frozen=True)
class RegistrationEvent:
    event_id: str
    action: str                 # submitted / approved / rejected / cancelled
    registration_id: int
    activity_id: int
    activity_title: str
    student_id: str
    status: RegistrationStatus
    occurred_at: datetime


class EventBus:
    def __init__(self, failure_recorder: Callable[[RegistrationEvent, str, str], None] | None = None):
        self._subscribers: list[Callable[[RegistrationEvent], None]] = []
        self._failure_recorder = failure_recorder

    def subscribe(self, handler: Callable[[RegistrationEvent], None]) -> None:
        self._subscribers.append(handler)

    def publish(self, event: RegistrationEvent) -> list[str]:
        """逐个通知订阅者；失败只留痕并返回错误摘要，绝不向上抛出。"""
        failures: list[str] = []
        for handler in self._subscribers:
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001 - 通知失败不应中断报名
                detail = f"{type(exc).__name__}: {exc}"
                failures.append(detail)
                if self._failure_recorder is not None:
                    try:
                        self._failure_recorder(event, type(handler).__name__ if hasattr(handler, "__class__") else "handler", detail)
                    except Exception:  # noqa: BLE001 - 留痕失败也不能影响主流程
                        pass
        return failures
