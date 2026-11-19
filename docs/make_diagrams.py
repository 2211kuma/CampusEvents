"""生成实验二设计任务 D 所需四张 UML 图（PNG）。"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyBboxPatch, Polygon, Rectangle

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 9

OUT = "diagrams"


def new_axes(w=128, h=95, figsize=(11, 8.2)):
    fig, ax = plt.subplots(figsize=figsize, dpi=220)
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    ax.set_aspect("equal")
    return fig, ax


def save(fig, name):
    fig.savefig(f"{OUT}/{name}", bbox_inches="tight", pad_inches=0.15, facecolor="white")
    plt.close(fig)
    print("saved", name)


def arrow(ax, start, end, style="-|>", dashed=False, color="black", lw=1.0, scale=11):
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops=dict(
            arrowstyle=style, color=color, lw=lw,
            linestyle="--" if dashed else "-",
            shrinkA=0, shrinkB=0, mutation_scale=scale,
            facecolor="white" if style == "-|>" else color,
        ),
        zorder=4,
    )


def cls_box(ax, x, y, w, h, name, attrs=(), methods=(), stereotype=None, head_h=6.2, fsize=6.8):
    ax.add_patch(Rectangle((x, y), w, h, fill=True, facecolor="white", edgecolor="#333333", lw=0.9, zorder=2))
    head_top = y + h
    title_y = head_top - 3.4
    if stereotype:
        ax.text(x + w / 2, head_top - 1.8, stereotype, ha="center", va="center", fontsize=6.8, style="italic", zorder=3)
        title_y = head_top - 4.6
    ax.text(x + w / 2, title_y, name, ha="center", va="center", fontsize=8.4, fontweight="bold", zorder=3)
    sep1 = head_top - head_h
    ax.plot([x, x + w], [sep1, sep1], color="#333333", lw=0.7, zorder=3)
    line_y = sep1 - 2.2
    for item in attrs:
        ax.text(x + 1.2, line_y, item, ha="left", va="center", fontsize=fsize, zorder=3)
        line_y -= 2.25
    sep2 = line_y + 1.0
    ax.plot([x, x + w], [sep2, sep2], color="#333333", lw=0.7, zorder=3)
    line_y = sep2 - 2.2
    for item in methods:
        ax.text(x + 1.2, line_y, item, ha="left", va="center", fontsize=fsize, zorder=3)
        line_y -= 2.25


# ---------------- 图1 用例图 ----------------
def usecase():
    fig, ax = new_axes(w=100, h=100, figsize=(8.6, 8.6))
    ax.add_patch(Rectangle((16, 8), 68, 84, fill=True, facecolor="#FAFAFA", edgecolor="#444444", lw=1.1, zorder=1))
    ax.text(50, 88.8, "CampusEvent 校园活动报名与管理系统", ha="center", va="center", fontsize=9.2, fontweight="bold")

    def actor(x, y, label):
        ax.add_patch(Ellipse((x, y + 6), 3.0, 3.0, facecolor="white", edgecolor="#222222", lw=1.0, zorder=2))
        ax.plot([x, x], [y + 4.4, y + 1.2], color="#222222", lw=1.0, zorder=2)
        ax.plot([x - 2.6, x, x + 2.6], [y + 3.2, y + 3.2, y + 3.2], color="#222222", lw=1.0, zorder=2)
        ax.plot([x, x - 2.2], [y + 1.2, y - 1.4], color="#222222", lw=1.0, zorder=2)
        ax.plot([x, x + 2.2], [y + 1.2, y - 1.4], color="#222222", lw=1.0, zorder=2)
        ax.text(x, y - 3.6, label, ha="center", va="center", fontsize=9)

    actor(8, 52, "学生")
    actor(92, 52, "管理员")

    def uc(cx, cy, text, w=25, h=9.5):
        ax.add_patch(Ellipse((cx, cy), w, h, facecolor="white", edgecolor="#333333", lw=0.9, zorder=2))
        ax.text(cx, cy, text, ha="center", va="center", fontsize=8, zorder=3)
        return (cx, cy, w, h)

    u1 = uc(34, 79, "浏览与筛选活动")
    u2 = uc(34, 66, "报名活动")
    u3 = uc(27, 55, "取消报名", w=20)
    u4 = uc(28, 34, "查看我的报名\n与站内消息", h=11, w=22)
    u5 = uc(65, 79, "创建/编辑/删除\n活动", h=11)
    u6 = uc(65, 66, "审批报名")
    u7 = uc(74, 51, "查看名额统计")
    u8 = uc(55, 21, "校验名额与\n重复报名", h=11, w=26)

    for e in (u1, u2, u3, u4):
        ax.plot([10.5, e[0] - e[2] / 2], [58, e[1]], color="#333333", lw=0.9, zorder=2)
    for e in (u5, u6, u7):
        ax.plot([89.5, e[0] + e[2] / 2], [58, e[1]], color="#333333", lw=0.9, zorder=2)

    arrow(ax, (39, 60.9), (51, 26.3), dashed=True, lw=0.9)
    ax.text(37.0, 44.0, "«include»", fontsize=7.5, ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))
    arrow(ax, (60, 60.9), (57, 26.3), dashed=True, lw=0.9)
    ax.text(67.0, 43.0, "«include»", fontsize=7.5, ha="left", va="center",
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))
    save(fig, "fig1_usecase.png")


# ---------------- 图2 类图 ----------------
def class_diagram():
    fig, ax = new_axes(w=142, h=114, figsize=(13.4, 10.8))
    ax.text(71, 110.8, "图例：实线=关联    空心三角=泛化    虚线箭头=依赖    空心菱形=聚合（整体-部分）",
            fontsize=8, ha="center")

    cls_box(ax, 2, 80, 20, 22, "Student",
            attrs=["- studentId: str", "- name: str"], head_h=6.4)
    cls_box(ax, 34, 76, 32, 30, "Registration",
            attrs=["- registrationId: int", "- activityId: int", "- studentId: str",
                   "- status: RegistrationStatus", "- createdAt: datetime"],
            methods=["+ isActive(): bool", "+ canCancel(): bool"], head_h=6.4, fsize=6.6)
    cls_box(ax, 78, 76, 30, 30, "Activity",
            attrs=["- activityId: int", "- title/category: str", "- startAt: datetime",
                   "- location: str", "- capacity: int", "- policyType: PolicyType"],
            methods=["+ remaining(approved): int", "+ isOpen(now): bool"], head_h=6.4, fsize=6.6)

    cls_box(ax, 28, 46, 38, 22, "RegistrationService",
            attrs=["- policies / events / repos"], head_h=7.0,
            methods=["+ register(studentId, activityId)", "+ cancel(studentId, regId)",
                     "+ approve(regId) / reject(regId)", "+ stats(activityId): dict"], fsize=6.6)
    cls_box(ax, 78, 44, 28, 24, "RegistrationPolicy", stereotype="«interface»",
            attrs=["- policyType: PolicyType"],
            methods=["+ decide(ctx)", "    : RegistrationStatus"], head_h=8.4, fsize=6.8)
    cls_box(ax, 112, 44, 28, 24, "EventBus",
            attrs=["- subscribers: list"],
            methods=["+ subscribe(handler)", "+ publish(event)", "    : list[str]"], head_h=7.0, fsize=6.6)

    cls_box(ax, 4, 16, 24, 22, "DirectPolicy", methods=["+ decide(ctx)", "  名额不足→抛异常"], head_h=7.4)
    cls_box(ax, 34, 16, 26, 22, "CapacityRule", stereotype="«utility»",
            methods=["+ hasRoom(activity, n)", "+ ensureRoom(activity, n)"], head_h=8.4, fsize=6.6)
    cls_box(ax, 64, 16, 24, 22, "AuditPolicy", methods=["+ decide(ctx)", "  返回 PENDING"], head_h=7.4)
    cls_box(ax, 96, 16, 44, 22, "InAppNotificationObserver",
            attrs=["- CONTENT: dict"],
            methods=["+ __call__(event)", "  按 eventId 幂等写消息"], head_h=7.4, fsize=6.8)

    ax.add_patch(Rectangle((40, 2), 96, 8, facecolor="white", edgecolor="#333333", lw=0.9, zorder=2))
    ax.text(88, 6.0, "Repository 层：Activity / Registration / Message / Event 仓储实现",
            ha="center", va="center", fontsize=6.8, zorder=3)

    # 关联 Student 1 — 0..* Registration
    ax.plot([22, 34], [91, 91], color="#333333", lw=1.0, zorder=3)
    ax.text(24.6, 92.6, "1", fontsize=7)
    ax.text(30.4, 88.2, "0..*", fontsize=7)

    # 聚合 Activity ◆ 1 — 0..* Registration
    ax.plot([78, 66], [91, 91], color="#333333", lw=1.0, zorder=3)
    ax.add_patch(Polygon([[78, 91], [74.8, 93.2], [71.6, 91], [74.8, 88.8]],
                         closed=True, fill=False, edgecolor="#333333", lw=0.9, zorder=3))
    ax.text(75.6, 86.6, "1", fontsize=7, ha="center")
    ax.text(69.0, 92.6, "0..*", fontsize=7)

    # Service → Policy
    arrow(ax, (66, 58), (78, 58), dashed=True, lw=0.9)
    ax.text(72, 60.0, "依赖抽象", fontsize=6.8, ha="center")

    # 泛化 DirectPolicy / AuditPolicy → RegistrationPolicy
    arrow(ax, (16, 38), (80, 44), style="-|>", lw=0.9, scale=13)
    arrow(ax, (76, 38), (92, 44), style="-|>", lw=0.9, scale=13)
    ax.text(68, 40.0, "泛化", fontsize=6.8, zorder=6,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))

    # Service → CapacityRule（公共规则）
    arrow(ax, (58, 46), (48, 38), dashed=True, lw=0.9)
    ax.text(55.5, 41.2, "公共规则", fontsize=6.8, zorder=6,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))

    # DirectPolicy → CapacityRule
    arrow(ax, (28, 27), (34, 27), dashed=True, lw=0.9)
    ax.text(31, 28.8, "调用", fontsize=6.6, ha="center", zorder=6)

    # Service → EventBus（经行间空隙的折线）
    ax.plot([47, 47, 126, 126], [68, 71, 71, 68.2], color="#333333", lw=0.9, zorder=3)
    ax.annotate("", xy=(126, 68), xytext=(126, 70.2),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=0.9, mutation_scale=11,
                                facecolor="white", shrinkA=0, shrinkB=0))
    ax.text(78, 72.0, "publish(event)", fontsize=6.8)

    # EventBus → Observer
    arrow(ax, (126, 44), (126, 38.2), lw=0.9)
    ax.text(127.4, 41.0, "notify", fontsize=6.8)

    # Service / Observer → Repository
    arrow(ax, (62, 46), (62, 10.2), dashed=True, lw=0.9)
    ax.text(66.5, 12.8, "持久化", fontsize=6.6, ha="left", zorder=6,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))
    arrow(ax, (118, 16), (118, 10.2), dashed=True, lw=0.9)
    ax.text(119.4, 12.8, "写消息", fontsize=6.6)

    save(fig, "fig2_class.png")


# ---------------- 图3/图4 时序图 ----------------
def sequence(participants, messages, fn, note=None, figsize=(12.6, 9.4)):
    w = 132
    fig, ax = new_axes(w=w, h=110, figsize=figsize)
    xs = {name: 8 + i * (116 / (len(participants) - 1)) for i, name in enumerate(participants)}
    top = 104
    for name, x in xs.items():
        box_w = 18
        ax.add_patch(FancyBboxPatch((x - box_w / 2, top), box_w, 5.6,
                                    boxstyle="round,pad=0.15,rounding_size=0.5",
                                    facecolor="#F2F2F2", edgecolor="#333333", lw=0.9, zorder=2))
        ax.text(x, top + 2.8, name, ha="center", va="center", fontsize=8.2, zorder=3)
        ax.plot([x, x], [8, top], color="#AAAAAA", lw=0.8, linestyle="--", zorder=1)

    y = top - 9
    alt_top = None
    for msg in messages:
        kind = msg[0]
        if kind == "alt_start":
            alt_top = y + 3.2
            ax.text(4.0, y + 1.0, msg[1], fontsize=7.4, fontweight="bold", va="center")
            y -= 5.2
        elif kind == "divider":
            ax.plot([1.5, 130.5], [y + 3.2, y + 3.2], color="#666666", lw=0.8, linestyle="--", zorder=2)
            ax.text(4.0, y + 1.0, msg[1], fontsize=7.4, fontweight="bold", va="center")
            y -= 5.2
        elif kind == "alt_end":
            ax.add_patch(Rectangle((1.5, y + 3.2), 129, alt_top - (y + 3.2),
                                   fill=False, edgecolor="#666666", lw=0.9, linestyle="--", zorder=2))
            ax.text(3.0, y + 4.6, msg[1], fontsize=6.6, va="bottom", color="#555555")
            y -= 2.6
        elif kind == "note":
            ax.text(xs[msg[1]] + 1.5, y + 1.0, msg[2], fontsize=6.6, va="center",
                    bbox=dict(boxstyle="round,pad=0.2", fc="#FFFDF2", ec="#BBBBBB", lw=0.7))
            y -= 4.2
        else:
            _, src, dst, text = msg[:4]
            ret = len(msg) > 4 and msg[4] == "return"
            y1 = y
            ax.annotate("", xy=(xs[dst], y1), xytext=(xs[src], y1),
                        arrowprops=dict(arrowstyle="-|>", color="#222222", lw=1.0,
                                        linestyle="--" if ret else "-", shrinkA=0, shrinkB=0, mutation_scale=9),
                        zorder=3)
            ax.text((xs[src] + xs[dst]) / 2, y1 + 1.6, text, ha="center", va="bottom", fontsize=7.0, zorder=3)
            y -= 5.2

    if note:
        ax.text(1.8, 3.5, note, fontsize=7.0, ha="left", va="bottom", color="#333333")
    save(fig, fn)


def seq_register():
    participants = ["学生", "报名服务", "报名策略", "名额规则", "报名仓储", "事件总线", "站内通知"]
    messages = [
        ("msg", "学生", "报名服务", "register(S001, 活动)"),
        ("msg", "报名服务", "报名仓储", "findActive(活动, 学生)"),
        ("msg", "报名仓储", "报名服务", "无重复有效报名", "return"),
        ("msg", "报名服务", "报名策略", "decide(PolicyContext)"),
        ("alt_start", "alt  [直接报名]"),
        ("msg", "报名策略", "名额规则", "ensureRoom(活动, 已通过数)"),
        ("msg", "名额规则", "报名策略", "通过 / 抛名额已满异常", "return"),
        ("divider", "else  [审核报名]"),
        ("note", "报名策略", "审核型不校验名额，直接返回待审核"),
        ("alt_end", "报名分支结束"),
        ("msg", "报名策略", "报名服务", "返回 已通过 / 待审核", "return"),
        ("msg", "报名服务", "报名仓储", "add(报名, 状态)"),
        ("msg", "报名仓储", "报名服务", "registration", "return"),
        ("msg", "报名服务", "事件总线", "publish(RegistrationEvent)"),
        ("msg", "事件总线", "站内通知", "__call__(event)"),
        ("msg", "站内通知", "事件总线", "claim(eventId) 通过→写消息", "return"),
    ]
    sequence(participants, messages, "fig3_seq_register.png",
             note="说明：通知在报名事务提交后由事件总线派发，订阅者异常被捕获并留痕，不影响已提交的报名结果。")


def seq_approve():
    participants = ["管理员", "报名服务", "名额规则", "报名仓储", "事件总线", "站内通知"]
    messages = [
        ("msg", "管理员", "报名服务", "approve(报名ID)"),
        ("msg", "报名服务", "报名仓储", "get(报名ID)"),
        ("msg", "报名仓储", "报名服务", "Registration(PENDING)", "return"),
        ("msg", "报名服务", "名额规则", "ensureRoom(活动, 已通过数)"),
        ("alt_start", "alt  [名额已满]"),
        ("msg", "名额规则", "报名服务", "抛出 CapacityExceededError", "return"),
        ("msg", "报名服务", "管理员", "批准失败：不改状态、不发通知", "return"),
        ("divider", "else  [名额充足]"),
        ("msg", "名额规则", "报名服务", "ok", "return"),
        ("msg", "报名服务", "报名仓储", "updateStatus(APPROVED)"),
        ("msg", "报名仓储", "报名服务", "ok", "return"),
        ("msg", "报名服务", "事件总线", "publish(approved 事件)"),
        ("msg", "事件总线", "站内通知", "__call__(event)"),
        ("msg", "站内通知", "事件总线", "写入消息（幂等）", "return"),
        ("msg", "报名服务", "管理员", "批准成功", "return"),
        ("alt_end", "审批分支结束"),
    ]
    sequence(participants, messages, "fig4_seq_approve.png",
             note="说明：审批失败只返回业务错误，不产生状态变更与通知；审批成功后才发布事件。")


if __name__ == "__main__":
    usecase()
    class_diagram()
    seq_register()
    seq_approve()
