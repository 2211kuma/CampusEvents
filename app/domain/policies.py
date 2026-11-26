"""报名策略（Strategy Pattern）。

设计要点：
1. RegistrationPolicy 是稳定抽象，只回答一个问题：这次报名应当得到什么状态。
2. 名额检查是公共规则（CapacityRule），不写在任何一个策略里，
   因为直接报名和审批通过都必须遵守同一条名额约束。
3. 新增报名方式 = 新增一个策略类并在 PolicyRegistry 注册，主流程不改。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .entities import Activity, PolicyType, RegistrationStatus, Student
from .errors import CapacityExceededError, GradeNotAllowedError


@dataclass(frozen=True)
class PolicyContext:
    activity: Activity
    approved_count: int
    student: Student | None = None


class CapacityRule:
    """公共规则：名额统计只按“已通过”计算，待审核不占名额。"""

    @staticmethod
    def has_room(activity: Activity, approved_count: int) -> bool:
        return approved_count < activity.capacity

    @classmethod
    def ensure_room(cls, activity: Activity, approved_count: int) -> None:
        if not cls.has_room(activity, approved_count):
            raise CapacityExceededError(
                f"活动《{activity.title}》名额已满（上限 {activity.capacity} 人）"
            )


class RegistrationPolicy(ABC):
    """报名规则抽象：决定一次报名的结果状态。"""

    policy_type: PolicyType

    @abstractmethod
    def decide(self, ctx: PolicyContext) -> RegistrationStatus:
        raise NotImplementedError


class DirectRegistrationPolicy(RegistrationPolicy):
    """直接报名：名额充足则立即通过，满员则失败。"""

    policy_type = PolicyType.DIRECT

    def decide(self, ctx: PolicyContext) -> RegistrationStatus:
        CapacityRule.ensure_room(ctx.activity, ctx.approved_count)
        return RegistrationStatus.APPROVED


class AuditRegistrationPolicy(RegistrationPolicy):
    """审核报名：先进入待审核，不占用名额，由管理员批准时再校验名额。"""

    policy_type = PolicyType.AUDIT

    def decide(self, ctx: PolicyContext) -> RegistrationStatus:
        return RegistrationStatus.PENDING


class GradeLimitedRegistrationPolicy(RegistrationPolicy):
    """CR-01：年级限定直接报名，仅大二、大三可报名，其余年级明确拒绝。

    名额、活动时间与重复报名仍由公共规则/服务把控，本策略只追加年级条件。
    """

    policy_type = PolicyType.GRADE_LIMITED
    allowed_grades = (2, 3)

    def decide(self, ctx: PolicyContext) -> RegistrationStatus:
        student = ctx.student
        if student is None:
            raise GradeNotAllowedError('缺少学生信息，无法校验年级')
        if student.grade not in self.allowed_grades:
            raise GradeNotAllowedError(
                f'活动《{ctx.activity.title}》仅限大二、大三学生报名，'
                f'你当前为{student.grade_label}（年级 {student.grade}）'
            )
        CapacityRule.ensure_room(ctx.activity, ctx.approved_count)
        return RegistrationStatus.APPROVED


class PolicyRegistry:
    """策略注册表，业务层通过它取得策略，而不是写 if/elif。"""

    def __init__(self):
        self._policies: dict[PolicyType, RegistrationPolicy] = {}
        for policy in (
            DirectRegistrationPolicy(),
            AuditRegistrationPolicy(),
            GradeLimitedRegistrationPolicy(),
        ):
            self.register(policy)

    def register(self, policy: RegistrationPolicy) -> None:
        self._policies[policy.policy_type] = policy

    def get(self, policy_type: PolicyType | str) -> RegistrationPolicy:
        try:
            key = PolicyType(policy_type)
        except ValueError as exc:
            raise ValueError(f"未知的报名方式：{policy_type}") from exc
        return self._policies[key]
