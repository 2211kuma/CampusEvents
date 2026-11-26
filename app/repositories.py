"""SQLite 持久化层：只负责存取，不做业务判断。"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from .domain.entities import Activity, Message, PolicyType, Registration, RegistrationStatus, Student


SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    grade INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS activities (
    activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    start_at TEXT NOT NULL,
    location TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    policy_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    deleted INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS registrations (
    registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id INTEGER NOT NULL REFERENCES activities(activity_id),
    student_id TEXT NOT NULL REFERENCES students(student_id),
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_registration_activity ON registrations(activity_id, status);
CREATE INDEX IF NOT EXISTS idx_registration_student ON registrations(student_id);

CREATE TABLE IF NOT EXISTS messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    activity_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS processed_events (
    event_id TEXT PRIMARY KEY,
    processed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notification_failures (
    failure_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS email_outbox (
    email_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_email_event ON email_outbox(event_id);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    # Flask 开发服务器为多线程，允许跨线程复用同一连接（单机演示场景足够）
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()


def _migrate(conn: sqlite3.Connection) -> None:
    """轻量迁移：老库补字段，避免变更版要求重建数据库。"""
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(students)").fetchall()}
    if "grade" not in cols:
        conn.execute("ALTER TABLE students ADD COLUMN grade INTEGER NOT NULL DEFAULT 1")
    conn.commit()


def seed_demo(conn: sqlite3.Connection) -> None:
    """固定演示账号与示例活动。"""
    students = [
        ("S001", "张小明", 2),
        ("S002", "李小红", 3),
        ("S003", "王小雨", 1),
        ("S004", "陈大四", 4),
    ]
    for student_id, name, grade in students:
        # 演示账号以代码为准：老库升级时同步校正年级，避免 CR-01 演示口径不一致
        conn.execute(
            "INSERT INTO students (student_id, name, grade) VALUES (?, ?, ?) "
            "ON CONFLICT(student_id) DO UPDATE SET name = excluded.name, grade = excluded.grade",
            (student_id, name, grade),
        )
    if conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        rows = [
            ("程序设计竞赛校内选拔", "竞赛", "2026-12-05 14:00", "信息楼 A301", 30, "DIRECT"),
            ("冬季校园公益跑", "体育", "2026-12-12 09:00", "东区运动场", 5, "AUDIT"),
            ("软件工程课程分享会", "讲座", "2026-12-20 19:00", "图书馆报告厅", 50, "DIRECT"),
        ]
        for row in rows:
            conn.execute(
                "INSERT INTO activities (title, category, start_at, location, capacity, policy_type, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (*row, now),
            )
    # CR-01 演示用：年级限定活动，始终确保存在一条
    if conn.execute("SELECT COUNT(*) FROM activities WHERE policy_type = 'GRADE_LIMITED'").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO activities (title, category, start_at, location, capacity, policy_type, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("大二大三专属：实验室开放日", "实践", "2026-12-26 15:00", "工程训练中心 B102", 20, "GRADE_LIMITED",
             datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
    conn.commit()


def _dt(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M")


def _fmt(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M")


class StudentRepository:
    def __init__(self, conn): self.conn = conn

    def get(self, student_id: str) -> Student | None:
        row = self.conn.execute(
            "SELECT student_id, name, grade FROM students WHERE student_id = ?", (student_id,)
        ).fetchone()
        return Student(row["student_id"], row["name"], row["grade"]) if row else None

    def list_all(self) -> list[Student]:
        rows = self.conn.execute("SELECT student_id, name, grade FROM students ORDER BY student_id").fetchall()
        return [Student(r["student_id"], r["name"], r["grade"]) for r in rows]

    def set_grade(self, student_id: str, grade: int) -> None:
        self.conn.execute("UPDATE students SET grade = ? WHERE student_id = ?", (grade, student_id))
        self.conn.commit()


class ActivityRepository:
    def __init__(self, conn): self.conn = conn

    def add(self, title, category, start_at, location, capacity, policy_type) -> int:
        cur = self.conn.execute(
            "INSERT INTO activities (title, category, start_at, location, capacity, policy_type, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                title, category, _fmt(start_at), location, capacity,
                policy_type.value if isinstance(policy_type, PolicyType) else str(policy_type),
                _fmt(datetime.now()),
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def update(self, activity_id, **fields) -> None:
        allowed = {"title", "category", "start_at", "location", "capacity", "policy_type"}
        data = {k: v for k, v in fields.items() if k in allowed}
        if not data:
            return
        if "start_at" in data:
            data["start_at"] = _fmt(data["start_at"])
        sets = ", ".join(f"{k} = ?" for k in data)
        self.conn.execute(f"UPDATE activities SET {sets} WHERE activity_id = ?", (*data.values(), activity_id))
        self.conn.commit()

    def soft_delete(self, activity_id: int) -> None:
        self.conn.execute("UPDATE activities SET deleted = 1 WHERE activity_id = ?", (activity_id,))
        self.conn.commit()

    def get(self, activity_id: int, include_deleted: bool = False) -> Activity | None:
        sql = "SELECT * FROM activities WHERE activity_id = ?"
        if not include_deleted:
            sql += " AND deleted = 0"
        row = self.conn.execute(sql, (activity_id,)).fetchone()
        return self._to_entity(row) if row else None

    def list_all(self, keyword: str = "") -> list[Activity]:
        rows = self.conn.execute(
            "SELECT * FROM activities WHERE deleted = 0 AND title LIKE ? ORDER BY start_at",
            (f"%{keyword}%",),
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    @staticmethod
    def _to_entity(row: sqlite3.Row) -> Activity:
        return Activity(
            activity_id=row["activity_id"],
            title=row["title"],
            category=row["category"],
            start_at=_dt(row["start_at"]),
            location=row["location"],
            capacity=row["capacity"],
            policy_type=PolicyType(row["policy_type"]),
            created_at=_dt(row["created_at"]),
            deleted=bool(row["deleted"]),
        )


class RegistrationRepository:
    def __init__(self, conn): self.conn = conn

    def add(self, activity_id: int, student_id: str, status: RegistrationStatus) -> Registration:
        now = datetime.now()
        cur = self.conn.execute(
            "INSERT INTO registrations (activity_id, student_id, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (activity_id, student_id, status.value, _fmt(now), _fmt(now)),
        )
        self.conn.commit()
        return Registration(cur.lastrowid, activity_id, student_id, status, now, now)

    def get(self, registration_id: int) -> Registration | None:
        row = self.conn.execute("SELECT * FROM registrations WHERE registration_id = ?", (registration_id,)).fetchone()
        return self._to_entity(row) if row else None

    def update_status(self, registration_id: int, status: RegistrationStatus) -> None:
        self.conn.execute(
            "UPDATE registrations SET status = ?, updated_at = ? WHERE registration_id = ?",
            (status.value, _fmt(datetime.now()), registration_id),
        )
        self.conn.commit()

    def find_active(self, activity_id: int, student_id: str) -> Registration | None:
        row = self.conn.execute(
            "SELECT * FROM registrations WHERE activity_id = ? AND student_id = ? AND status IN (?, ?)",
            (activity_id, student_id, RegistrationStatus.PENDING.value, RegistrationStatus.APPROVED.value),
        ).fetchone()
        return self._to_entity(row) if row else None

    def count_status(self, activity_id: int, status: RegistrationStatus) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM registrations WHERE activity_id = ? AND status = ?",
            (activity_id, status.value),
        ).fetchone()[0]

    def list_by_activity(self, activity_id: int, statuses: tuple[RegistrationStatus, ...] | None = None) -> list[Registration]:
        sql = "SELECT * FROM registrations WHERE activity_id = ?"
        params: list = [activity_id]
        if statuses:
            sql += " AND status IN (" + ",".join("?" for _ in statuses) + ")"
            params.extend(s.value for s in statuses)
        sql += " ORDER BY created_at"
        return [self._to_entity(r) for r in self.conn.execute(sql, params).fetchall()]

    def list_by_student(self, student_id: str) -> list[Registration]:
        rows = self.conn.execute(
            "SELECT * FROM registrations WHERE student_id = ? ORDER BY created_at DESC", (student_id,)
        ).fetchall()
        return [self._to_entity(r) for r in rows]

    def has_active_for_activity(self, activity_id: int) -> bool:
        return self.conn.execute(
            "SELECT COUNT(*) FROM registrations WHERE activity_id = ? AND status IN (?, ?)",
            (activity_id, RegistrationStatus.PENDING.value, RegistrationStatus.APPROVED.value),
        ).fetchone()[0] > 0

    @staticmethod
    def _to_entity(row: sqlite3.Row) -> Registration:
        return Registration(
            registration_id=row["registration_id"],
            activity_id=row["activity_id"],
            student_id=row["student_id"],
            status=RegistrationStatus(row["status"]),
            created_at=_dt(row["created_at"]),
            updated_at=_dt(row["updated_at"]),
        )


class MessageRepository:
    def __init__(self, conn): self.conn = conn

    def add(self, student_id: str, activity_id: int, content: str, created_at: datetime) -> int:
        cur = self.conn.execute(
            "INSERT INTO messages (student_id, activity_id, content, created_at, is_read) VALUES (?, ?, ?, ?, 0)",
            (student_id, activity_id, content, _fmt(created_at)),
        )
        self.conn.commit()
        return cur.lastrowid

    def list_by_student(self, student_id: str) -> list[Message]:
        rows = self.conn.execute(
            "SELECT * FROM messages WHERE student_id = ? ORDER BY created_at DESC", (student_id,)
        ).fetchall()
        return [
            Message(r["message_id"], r["student_id"], r["activity_id"], r["content"], _dt(r["created_at"]), bool(r["is_read"]))
            for r in rows
        ]

    def count(self, student_id: str | None = None) -> int:
        if student_id is None:
            return self.conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        return self.conn.execute("SELECT COUNT(*) FROM messages WHERE student_id = ?", (student_id,)).fetchone()[0]

    def mark_all_read(self, student_id: str) -> None:
        self.conn.execute("UPDATE messages SET is_read = 1 WHERE student_id = ?", (student_id,))
        self.conn.commit()


class ProcessedEventRepository:
    def __init__(self, conn): self.conn = conn

    def claim(self, event_id: str, now: datetime) -> bool:
        """返回 True 表示本次成功占用该事件（首次处理），False 表示已处理过。"""
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO processed_events (event_id, processed_at) VALUES (?, ?)",
            (event_id, _fmt(now)),
        )
        self.conn.commit()
        return cur.rowcount == 1


class NotificationFailureRepository:
    def __init__(self, conn): self.conn = conn

    def add(self, event_id: str, channel: str, detail: str, now: datetime) -> None:
        self.conn.execute(
            "INSERT INTO notification_failures (event_id, channel, detail, created_at) VALUES (?, ?, ?, ?)",
            (event_id, channel, detail[:500], _fmt(now)),
        )
        self.conn.commit()

    def list_all(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM notification_failures ORDER BY failure_id").fetchall()
        return [dict(r) for r in rows]


class EmailRepository:
    """CR-02：模拟邮件发件箱，记录收件人、主题、内容、状态与时间。"""

    def __init__(self, conn): self.conn = conn

    def add(self, event_id, recipient, subject, body, status, detail, now) -> int:
        cur = self.conn.execute(
            "INSERT INTO email_outbox (event_id, recipient, subject, body, status, detail, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (event_id, recipient, subject, body, status, detail[:500], _fmt(now)),
        )
        self.conn.commit()
        return cur.lastrowid

    def list_all(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM email_outbox ORDER BY email_id DESC").fetchall()
        return [dict(r) for r in rows]

    def count(self, status: str | None = None) -> int:
        if status is None:
            return self.conn.execute("SELECT COUNT(*) FROM email_outbox").fetchone()[0]
        return self.conn.execute(
            "SELECT COUNT(*) FROM email_outbox WHERE status = ?", (status,)
        ).fetchone()[0]

    def count_by_event(self, event_id: str) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM email_outbox WHERE event_id = ?", (event_id,)
        ).fetchone()[0]
