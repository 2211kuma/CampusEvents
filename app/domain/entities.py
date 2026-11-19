"""领域实体：只表达数据 + 自身不变量，不依赖数据库与框架。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class RegistrationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

    @property
    def label(self) -> str:
        return {
            "PENDING": "待审核",
            "APPROVED": "已通过",
            "REJECTED": "已拒绝",
            "CANCELLED": "已取消",
        }[self.value]

    @property
    def is_active(self) -> bool:
        return self in (RegistrationStatus.PENDING, RegistrationStatus.APPROVED)


class PolicyType(str, Enum):
    DIRECT = "DIRECT"      # 直接报名
    AUDIT = "AUDIT"        # 管理员审核

    @property
    def label(self) -> str:
        return {"DIRECT": "直接报名", "AUDIT": "需管理员审核"}[self.value]


@dataclass
class Student:
    student_id: str
    name: str


@dataclass
class Activity:
    activity_id: int
    title: str
    category: str
    start_at: datetime
    location: str
    capacity: int
    policy_type: PolicyType
    created_at: datetime
    deleted: bool = False

    def remaining(self, approved_count: int) -> int:
        return max(0, self.capacity - approved_count)

    def is_open(self, now: datetime | None = None) -> bool:
        return (now or datetime.now()) < self.start_at


@dataclass
class Registration:
    registration_id: int
    activity_id: int
    student_id: str
    status: RegistrationStatus
    created_at: datetime
    updated_at: datetime

    @property
    def is_active(self) -> bool:
        return self.status.is_active

    def can_cancel(self) -> bool:
        return self.status in (RegistrationStatus.PENDING, RegistrationStatus.APPROVED)


@dataclass
class Message:
    message_id: int
    student_id: str
    activity_id: int
    content: str
    created_at: datetime
    is_read: bool = False
