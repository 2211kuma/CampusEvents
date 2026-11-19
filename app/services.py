"""业务服务：编排流程、执行公共校验，不实现具体报名规则（交给策略）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .domain.entities import Activity, PolicyType, Registration, RegistrationStatus, Student
from .domain.errors import (
    ActivityClosedError,
    CapacityExceededError,
    DomainError,
    DuplicateRegistrationError,
    ForbiddenOperationError,
    InvalidStateError,
    NotFoundError,
)
from .domain.events import EventBus, RegistrationEvent
from .domain.notifications import InAppNotificationObserver
from .domain.policies import CapacityRule, PolicyContext, PolicyRegistry
from .repositories import (
    ActivityRepository,
    MessageRepository,
    NotificationFailureRepository,
    ProcessedEventRepository,
    RegistrationRepository,
    StudentRepository,
)


class ActivityService:
    def __init__(self, activities: ActivityRepository, registrations: RegistrationRepository):
        self.activities = activities
        self.registrations = registrations

    def create(self, title, category, start_at, location, capacity, policy_type) -> Activity:
        if capacity <= 0:
            raise DomainError("人数上限必须为正整数")
        if not title.strip():
            raise DomainError("活动名称不能为空")
        if start_at <= datetime.now():
            raise DomainError("活动开始时间必须晚于当前时间")
        activity_id = self.activities.add(
            title.strip(), category.strip() or "其他", start_at, location.strip(),
            capacity, PolicyType(policy_type),
        )
        return self.activities.get(activity_id)

    def update(self, activity_id: int, **fields) -> Activity:
        activity = self.activities.get(activity_id)
        if activity is None:
            raise NotFoundError("活动不存在或已下架")
        if "capacity" in fields:
            approved = self.registrations.count_status(activity_id, RegistrationStatus.APPROVED)
            if fields["capacity"] < approved:
                raise DomainError(f"已有 {approved} 人通过，容量不能小于该人数")
            if fields["capacity"] <= 0:
                raise DomainError("人数上限必须为正整数")
        self.activities.update(activity_id, **fields)
        return self.activities.get(activity_id)

    def delete(self, activity_id: int) -> None:
        """已有有效报名时拒绝删除，避免学生报名记录无声消失。"""
        activity = self.activities.get(activity_id)
        if activity is None:
            raise NotFoundError("活动不存在或已下架")
        if self.registrations.has_active_for_activity(activity_id):
            raise DomainError("该活动已有待审核或已通过的报名，不能删除；请先处理报名或修改活动信息")
        self.activities.soft_delete(activity_id)

    def list(self, keyword: str = "") -> list[Activity]:
        return self.activities.list_all(keyword)

    def get(self, activity_id: int) -> Activity:
        activity = self.activities.get(activity_id)
        if activity is None:
            raise NotFoundError("活动不存在或已下架")
        return activity


class RegistrationService:
    def __init__(
        self,
        activities: ActivityRepository,
        registrations: RegistrationRepository,
        students: StudentRepository,
        events: EventBus,
        registry: PolicyRegistry | None = None,
    ):
        self.activities = activities
        self.registrations = registrations
        self.students = students
        self.events = events
        self.registry = registry or PolicyRegistry()

    # ---------- 查询 ----------
    def get_activity(self, activity_id: int) -> Activity:
        activity = self.activities.get(activity_id)
        if activity is None:
            raise NotFoundError("活动不存在或已下架")
        return activity

    def student(self, student_id: str) -> Student:
        student = self.students.get(student_id)
        if student is None:
            raise NotFoundError("学生不存在")
        return student

    def stats(self, activity_id: int) -> dict:
        activity = self.get_activity(activity_id)
        approved = self.registrations.count_status(activity_id, RegistrationStatus.APPROVED)
        pending = self.registrations.count_status(activity_id, RegistrationStatus.PENDING)
        return {
            "approval": approved,
            "pending": pending,
            "remaining": activity.remaining(approved),
            "capacity": activity.capacity,
        }

    def my_registrations(self, student_id: str) -> list[Registration]:
        return self.registrations.list_by_student(student_id)

    def pending_list(self, activity_id: int) -> list[Registration]:
        return self.registrations.list_by_activity(activity_id, (RegistrationStatus.PENDING,))

    def all_with_stats(self, keyword: str = "") -> list[tuple[Activity, dict]]:
        return [(a, self.stats(a.activity_id)) for a in self.activities.list_all(keyword)]

    # ---------- 命令 ----------
    def register(self, student_id: str, activity_id: int, now: datetime | None = None) -> Registration:
        now = now or datetime.now()
        student = self.student(student_id)
        activity = self.get_activity(activity_id)

        if not activity.is_open(now):
            raise ActivityClosedError(f"活动《{activity.title}》已开始，停止报名")
        if self.registrations.find_active(activity_id, student_id):
            raise DuplicateRegistrationError("你已报名该活动（待审核或已通过），不能重复报名")

        policy = self.registry.get(activity.policy_type)
        approved = self.registrations.count_status(activity_id, RegistrationStatus.APPROVED)
        status = policy.decide(PolicyContext(activity=activity, approved_count=approved))

        registration = self.registrations.add(activity_id, student.student_id, status)
        self._publish(registration, activity, "submitted", now)
        return registration

    def cancel(self, student_id: str, registration_id: int, now: datetime | None = None) -> Registration:
        now = now or datetime.now()
        registration = self.registrations.get(registration_id)
        if registration is None:
            raise NotFoundError("报名记录不存在")
        if registration.student_id != student_id:
            raise ForbiddenOperationError("只能取消自己的报名")
        if not registration.can_cancel():
            raise InvalidStateError("只有待审核或已通过的报名可以取消")

        activity = self.get_activity(registration.activity_id)
        if not activity.is_open(now):
            raise ActivityClosedError("活动已开始，不能取消报名")

        self.registrations.update_status(registration_id, RegistrationStatus.CANCELLED)
        updated = self.registrations.get(registration_id)
        self._publish(updated, activity, "cancelled", now)
        return updated

    def approve(self, registration_id: int, admin_id: str = "admin", now: datetime | None = None) -> Registration:
        now = now or datetime.now()
        registration = self.registrations.get(registration_id)
        if registration is None:
            raise NotFoundError("报名记录不存在")
        if registration.status != RegistrationStatus.PENDING:
            raise InvalidStateError("只有待审核的报名可以批准")

        activity = self.get_activity(registration.activity_id)
        approved = self.registrations.count_status(activity.activity_id, RegistrationStatus.APPROVED)
        CapacityRule.ensure_room(activity, approved)

        self.registrations.update_status(registration_id, RegistrationStatus.APPROVED)
        updated = self.registrations.get(registration_id)
        self._publish(updated, activity, "approved", now)
        return updated

    def reject(self, registration_id: int, admin_id: str = "admin", now: datetime | None = None) -> Registration:
        now = now or datetime.now()
        registration = self.registrations.get(registration_id)
        if registration is None:
            raise NotFoundError("报名记录不存在")
        if registration.status != RegistrationStatus.PENDING:
            raise InvalidStateError("只有待审核的报名可以拒绝")

        activity = self.get_activity(registration.activity_id)
        self.registrations.update_status(registration_id, RegistrationStatus.REJECTED)
        updated = self.registrations.get(registration_id)
        self._publish(updated, activity, "rejected", now)
        return updated

    # ---------- 事件 ----------
    def _publish(self, registration: Registration, activity: Activity, action: str, now: datetime) -> None:
        event = RegistrationEvent(
            event_id=f"reg:{registration.registration_id}:{action}",
            action=action,
            registration_id=registration.registration_id,
            activity_id=activity.activity_id,
            activity_title=activity.title,
            student_id=registration.student_id,
            status=registration.status,
            occurred_at=now,
        )
        self.events.publish(event)


@dataclass
class Services:
    activities: ActivityService
    registrations: RegistrationService
    messages: MessageRepository
    students: StudentRepository
    failures: NotificationFailureRepository


def build_services(conn) -> Services:
    student_repo = StudentRepository(conn)
    activity_repo = ActivityRepository(conn)
    registration_repo = RegistrationRepository(conn)
    message_repo = MessageRepository(conn)
    processed_repo = ProcessedEventRepository(conn)
    failure_repo = NotificationFailureRepository(conn)

    def record_failure(event, channel, detail):
        failure_repo.add(event.event_id, channel, detail, datetime.now())

    bus = EventBus(failure_recorder=record_failure)
    bus.subscribe(InAppNotificationObserver(message_repo, processed_repo))

    return Services(
        activities=ActivityService(activity_repo, registration_repo),
        registrations=RegistrationService(activity_repo, registration_repo, student_repo, bus),
        messages=message_repo,
        students=student_repo,
        failures=failure_repo,
    )
