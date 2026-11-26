class DomainError(Exception):
    """业务规则被违反时抛出，由表现层转换为用户可读提示。"""

    default_message = "操作失败"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)
        self.message = message or self.default_message


class NotFoundError(DomainError):
    default_message = "对象不存在"


class ActivityClosedError(DomainError):
    default_message = "活动已开始或已结束，不能报名"


class DuplicateRegistrationError(DomainError):
    default_message = "你已有一条第待审核或已通过的报名记录"


class CapacityExceededError(DomainError):
    default_message = "该活动名额已满"


class InvalidStateError(DomainError):
    default_message = "当前状态不允许此操作"


class ForbiddenOperationError(DomainError):
    default_message = "无权执行此操作"


class GradeNotAllowedError(DomainError):
    default_message = "该活动仅限大二、大三学生报名"
