"""Flask 表现层：只负责取参数、调服务、渲染页面，不做业务判断。"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for

from .domain.entities import PolicyType, RegistrationStatus
from .domain.errors import DomainError
from .repositories import connect, init_schema, seed_demo
from .services import build_services


def create_app(db_path: str | Path | None = None) -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("CAMPUSEVENT_SECRET", "campusevent-demo-secret")

    db_path = db_path or os.environ.get("CAMPUSEVENT_DB", str(Path(__file__).resolve().parent.parent / "data" / "campusevent.db"))
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    init_schema(conn)
    seed_demo(conn)

    services = build_services(conn)
    app.extensions["services"] = services

    # ---------------- 模板辅助 --------------
    @app.template_filter("dt")
    def fmt_dt(value):
        return value.strftime("%Y-%m-%d %H:%M") if value else ""

    @app.context_processor
    def inject_globals():
        student_id = session.get("student_id", "S001")
        student = services.students.get(student_id)
        all_students = services.students.list_all()
        return {
            "students": all_students,
            "current_student": student,
            "current_student_id": student_id,
            "student_map": {s.student_id: s.name for s in all_students},
            "status_labels": {s.value: s.label for s in RegistrationStatus},
            "policy_labels": {p.value: p.label for p in PolicyType},
        }

    def current_student_id() -> str:
        return session.get("student_id", "S001")

    def run_action(fn, *args):
        try:
            fn(*args)
            return True
        except DomainError as exc:
            flash(exc.message, "error")
            return False

    # ---------------- 学生端 --------------
    @app.get("/")
    def index():
        q = request.args.get("q", "").strip()
        rows = services.registrations.all_with_stats(q)
        my_active = {}
        for reg in services.registrations.my_registrations(current_student_id()):
            if reg.is_active:
                my_active[reg.activity_id] = reg
        return render_template("activities.html", rows=rows, q=q, my_active=my_active)

    @app.get("/activity/<int:activity_id>")
    def activity_detail(activity_id):
        activity = services.registrations.get_activity(activity_id)
        stats = services.registrations.stats(activity_id)
        my_regs = [r for r in services.registrations.my_registrations(current_student_id()) if r.activity_id == activity_id]
        active = next((r for r in my_regs if r.is_active), None)
        return render_template("activity_detail.html", activity=activity, stats=stats, active=active, my_regs=my_regs)

    @app.post("/activity/<int:activity_id>/register")
    def register(activity_id):
        try:
            services.registrations.register(current_student_id(), activity_id)
            flash("报名已提交，请查看站内消息", "ok")
        except DomainError as exc:
            flash(exc.message, "error")
        return redirect(url_for("activity_detail", activity_id=activity_id))

    @app.post("/registration/<int:registration_id>/cancel")
    def cancel(registration_id):
        try:
            services.registrations.cancel(current_student_id(), registration_id)
            flash("已取消报名", "ok")
        except DomainError as exc:
            flash(exc.message, "error")
        return redirect(request.referrer or url_for("me"))

    @app.get("/me")
    def me():
        sid = current_student_id()
        regs = services.registrations.my_registrations(sid)
        activities = {a.activity_id: a for a in services.activities.list()}
        messages = services.messages.list_by_student(sid)
        return render_template("me.html", regs=regs, activities=activities, messages=messages)

    @app.post("/messages/read")
    def read_messages():
        services.messages.mark_all_read(current_student_id())
        return redirect(url_for("me"))

    @app.get("/switch/<student_id>")
    def switch_student(student_id):
        if services.students.get(student_id):
            session["student_id"] = student_id
        return redirect(url_for("index"))

    # ---------------- 管理端 --------------
    @app.get("/admin/activities")
    def admin_activities():
        return render_template(
            "admin_activities.html",
            rows=services.registrations.all_with_stats(),
        )

    @app.post("/admin/activities")
    def admin_create_activity():
        form = request.form
        try:
            start_at = datetime.strptime(form["start_at"], "%Y-%m-%dT%H:%M")
            services.activities.create(
                title=form.get("title", ""),
                category=form.get("category", ""),
                start_at=start_at,
                location=form.get("location", ""),
                capacity=int(form.get("capacity", "0") or 0),
                policy_type=form.get("policy_type", "DIRECT"),
            )
            flash("活动创建成功", "ok")
        except (DomainError, ValueError) as exc:
            flash(getattr(exc, "message", str(exc)), "error")
        return redirect(url_for("admin_activities"))

    @app.post("/admin/activities/<int:activity_id>/delete")
    def admin_delete_activity(activity_id):
        run_action(services.activities.delete, activity_id)
        return redirect(url_for("admin_activities"))

    @app.post("/admin/activities/<int:activity_id>/capacity")
    def admin_update_capacity(activity_id):
        try:
            services.activities.update(activity_id, capacity=int(request.form.get("capacity", "0") or 0))
            flash("人数上限已更新", "ok")
        except (DomainError, ValueError) as exc:
            flash(getattr(exc, "message", str(exc)), "error")
        return redirect(url_for("admin_activities"))

    @app.get("/admin/approvals")
    def admin_approvals():
        rows = []
        for activity, stats in services.registrations.all_with_stats():
            pending = services.registrations.pending_list(activity.activity_id)
            if pending:
                rows.append((activity, stats, pending))
        return render_template("admin_approvals.html", rows=rows)

    @app.post("/admin/approvals/<int:registration_id>/<decision>")
    def admin_decide(registration_id, decision):
        if decision == "approve":
            run_action(services.registrations.approve, registration_id)
        elif decision == "reject":
            run_action(services.registrations.reject, registration_id)
        else:
            flash("未知的审批操作", "error")
        return redirect(url_for("admin_approvals"))

    return app
