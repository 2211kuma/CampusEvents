# -*- coding: utf-8 -*-
"""生成《实验二 设计任务D 设计材料》Word 文档。"""

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BASE = Path(r"D:\test\CampusEvent\docs")
OUT = Path(r"D:\test\实验二设计任务D-设计说明书.docx")

CN_BODY = "宋体"
CN_HEAD = "黑体"
EN = "Times New Roman"


def set_run_font(run, cn=CN_BODY, size=12, bold=False, color=None):
    run.font.name = EN
    run.font.size = Pt(size)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), EN)
    rfonts.set(qn("w:hAnsi"), EN)
    rfonts.set(qn("w:eastAsia"), cn)


def body(doc, text, size=12, indent=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = align
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    if indent:
        p.paragraph_format.first_line_indent = Pt(size * 2)
    run = p.add_run(text)
    set_run_font(run, size=size)
    return p


def heading(doc, text, level):
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    sizes = {1: 16, 2: 14, 3: 12}
    spaces = {1: (14, 6), 2: (11, 5), 3: (9, 4)}
    p.paragraph_format.space_before = Pt(spaces[level][0])
    p.paragraph_format.space_after = Pt(spaces[level][1])
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.paragraph_format.first_line_indent = Pt(0)
    style_name = f"Heading {level}"
    try:
        p.style = doc.styles[style_name]
    except KeyError:
        pass
    run = p.add_run(text)
    set_run_font(run, cn=CN_HEAD, size=sizes[level], bold=True, color=RGBColor(0, 0, 0))
    return p


def caption(doc, text, keep_next=False):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.keep_with_next = keep_next
    run = p.add_run(text)
    set_run_font(run, size=10.5)
    return p


def add_picture(doc, name, width_cm, cap_text):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(BASE / "diagrams" / name), width=Cm(width_cm))
    caption(doc, cap_text)


def _set_cell_bg(cell, color="D9D9D9"):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcpr.append(shd)


TBLPR_ORDER = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize",
               "tblStyleColBandSize", "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders",
               "shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription"]


def insert_ordered(parent, el, order):
    tag = el.tag.split("}")[1]
    idx = order.index(tag)
    for child in list(parent):
        ctag = child.tag.split("}")[1]
        if ctag in order and order.index(ctag) > idx:
            child.addprevious(el)
            return
    parent.append(el)


def _table_borders(table):
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "000000")
        borders.append(el)
    insert_ordered(table._tbl.tblPr, borders, TBLPR_ORDER)


def _cell_margins(table):
    margins = OxmlElement("w:tblCellMar")
    for edge, val in (("top", 40), ("bottom", 40), ("left", 108), ("right", 108)):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        margins.append(el)
    insert_ordered(table._tbl.tblPr, margins, TBLPR_ORDER)


def add_table(doc, cap, headers, rows, widths_cm, center_cols=(0,), font_size=10.5):
    caption(doc, cap, keep_next=True)
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    _table_borders(table)
    _cell_margins(table)

    hdr = table.rows[0]
    trpr = hdr._tr.get_or_add_trPr()
    trpr.append(OxmlElement("w:cantSplit"))
    trpr.append(OxmlElement("w:tblHeader"))

    for i, text in enumerate(headers):
        cell = hdr.cells[i]
        cell.width = Cm(widths_cm[i])
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        _set_cell_bg(cell)
        p = cell.paragraphs[0]
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        run = p.add_run(text)
        set_run_font(run, size=font_size, bold=True)

    for row_data in rows:
        row = table.add_row()
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for i, text in enumerate(row_data):
            cell = row.cells[i]
            cell.width = Cm(widths_cm[i])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.alignment = (
                WD_ALIGN_PARAGRAPH.CENTER if i in center_cols else WD_ALIGN_PARAGRAPH.LEFT
            )
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.first_line_indent = Pt(0)
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            run = p.add_run(text)
            set_run_font(run, size=font_size)

    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def add_field(paragraph, instr, placeholder=""):
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr_el = OxmlElement("w:instrText")
    instr_el.set(qn("xml:space"), "preserve")
    instr_el.text = instr
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    text_el = OxmlElement("w:t")
    text_el.text = placeholder
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    for el in (fld_begin, instr_el, fld_sep, text_el, fld_end):
        run._r.append(el)
    set_run_font(run, size=12)


def setup_section(section):
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)


def main():
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = EN
    normal.font.size = Pt(12)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), CN_BODY)

    # 让打开文档时刷新域
    settings = doc.settings.element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    compat = settings.find(qn("w:compat"))
    if compat is not None:
        compat.addprevious(update)
    else:
        settings.append(update)

    setup_section(doc.sections[0])

    # ---------------- 封面 ----------------
    for _ in range(4):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)

    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    run = p.add_run("《软件工程》课程实验二")
    set_run_font(run, cn=CN_HEAD, size=22, bold=True)

    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run("基于设计模式的校园活动报名与管理系统")
    set_run_font(run, cn=CN_HEAD, size=18, bold=True)

    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(24)
    run = p.add_run("设计任务D：设计材料的生成与评审（设计版本V1）")
    set_run_font(run, cn="楷体", size=14)

    info = [
        ("项目代号", "CampusEvent"),
        ("设计版本", "V1（初始版，对应 baseline-v1）"),
        ("班　　级", "【班级】"),
        ("学　　号", "【学号】"),
        ("姓　　名", "【姓名】"),
        ("指导教师", "林卫中、赵丽萍"),
        ("提交日期", "2026年11月19日"),
    ]
    table = doc.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for label, value in info:
        row = table.add_row()
        for i, text in enumerate((label, value)):
            cell = row.cells[i]
            cell.width = Cm(4.6 if i == 0 else 8.4)
            p = cell.paragraphs[0]
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
            run = p.add_run(text)
            set_run_font(run, size=12, bold=(i == 0))

    # ---------------- 目录 ----------------
    sec_toc = doc.add_section(WD_SECTION.NEW_PAGE)
    setup_section(sec_toc)
    sec_toc.footer.is_linked_to_previous = False

    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    run = p.add_run("目　　录")
    set_run_font(run, cn=CN_HEAD, size=16, bold=True)

    toc_p = doc.add_paragraph()
    toc_p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    add_field(toc_p, 'TOC \\o "1-2" \\h \\z \\u', placeholder="打开文档后按 F9 或右键“更新域”生成目录")

    # ---------------- 正文 ----------------
    sec_body = doc.add_section(WD_SECTION.NEW_PAGE)
    setup_section(sec_body)
    sec_body.footer.is_linked_to_previous = False
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:start"), "1")
    cols = sec_body._sectPr.find(qn("w:cols"))
    if cols is not None:
        cols.addprevious(pg)
    else:
        sec_body._sectPr.append(pg)

    footer_p = sec_body.footer.paragraphs[0]
    footer_p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_field(footer_p, " PAGE ", placeholder="1")

    # 1 任务概述
    heading(doc, "1　任务概述", 1)
    heading(doc, "1.1　任务来源与要求", 2)
    body(doc,
         "本设计材料依据《软件工程》实验指导书第三章“实验二：基于设计模式的校园活动报名与管理系统”编写。"
         "实验二要求学生在 AI 编码之前先完成设计与评审，设计任务D明确规定：AI 生成代码前，学生必须使用 AI 生成需求用例图或用例说明、UML 类图、关键交互时序图（报名与审批各至少 1 张）、设计原则说明；"
         "这些材料须由其他学生评审通过并签名确认，才能进入 AI 实现阶段。本文档即上述四项材料的汇总，覆盖 CampusEvent 初始版本（V1）的完整设计。")
    body(doc,
         "文档的设计输入是指导书 3.2 节的 8 项功能需求（P2-F01 至 P2-F08）、3.5 节的 10 条验收用例（C1 至 C10）以及附录 B 的领域数据、业务规则与设计检查表。"
         "文档中的类名、接口名和关键方法名将作为后续 AI 编码的约束条件，AI 不得擅自合并策略接口、删减事件分发结构或把通知逻辑写回报名业务。")

    heading(doc, "1.2　交付物清单", 2)
    body(doc, "任务D要求提交的材料与本文档章节的对应关系如表1所示。")
    add_table(
        doc,
        "表1　设计任务D交付物清单",
        ["序号", "交付材料", "内容要点", "对应章节"],
        [
            ("1", "需求用例图或用例说明", "参与者与用例边界、8 个用例清单、报名与审批的详细用例说明", "第2章"),
            ("2", "UML 类图", "领域对象、业务服务、策略接口、事件总线、仓储层的属性、方法与依赖关系", "第3章"),
            ("3", "关键交互时序图", "报名时序（含直接报名与审核报名分支）、审批时序（含名额不足分支）", "第4章"),
            ("4", "设计原则说明", "策略模式与观察者机制的应用理由、名额检查归属论证、SOLID 对照、成本与收益", "第5章"),
            ("5", "评审记录", "评审检查表、评审意见、结论与签名栏", "第6章"),
        ],
        widths_cm=[1.5, 4.2, 7.8, 2.5],
    )

    heading(doc, "1.3　设计范围与约束", 2)
    body(doc,
         "设计范围严格限定在初始版本的 8 项功能，不实现用户注册、复杂权限、邮件或短信通知、消息队列与云部署。"
         "通知只设计站内消息一种渠道，邮件渠道留作后续需求变更的扩展点，不在 V1 中实现，这与工作量边界中“两类报名规则及两类通知机制”的约束一致。")
    body(doc,
         "设计须满足以下不可协商的约束：名额统计只按“已通过”计算，待审核不占用名额；同一学生对同一活动不得同时存在“待审核”或“已通过”的有效报名；"
         "学生只能取消“待审核”或“已通过”的报名，活动开始后不得新增报名；通知失败必须留痕，但不得使已合法提交的报名记录无声消失。"
         "上述约束分别体现在类图中的 CapacityRule、RegistrationService 与 EventBus 三处，而不是散落在页面层。")

    # 2 用例模型
    heading(doc, "2　用例模型", 1)
    heading(doc, "2.1　参与者与系统边界", 2)
    body(doc,
         "系统有两个参与者。学生负责浏览活动、提交报名、取消报名、查看自己的报名与站内消息；管理员负责创建、编辑、删除活动，审批待审核报名，查看名额统计。"
         "两类参与者都通过固定的演示账号进入，系统不设注册与复杂权限，但“只能取消自己的报名”这一归属校验仍由业务层承担。")
    body(doc,
         "系统边界为 CampusEvent 应用本身。数据库、文件系统与通知渠道属于外部支撑设施，不作为参与者。用例的粒度控制在一名学生或管理员一次完整业务目标，"
         "“校验名额与重复报名”不单独作为参与者发起的用例，而作为被报名与审批包含的公共子流程。")

    heading(doc, "2.2　用例图", 2)
    body(doc, "系统用例及参与者关系如图1所示。图中虚线箭头表示包含关系，报名活动和审批报名都包含“校验名额与重复报名”这一公共子流程。")
    add_picture(doc, "fig1_usecase.png", 12.6, "图1　CampusEvent 系统用例图")

    heading(doc, "2.3　用例清单", 2)
    body(doc, "各用例的目标与主要成功场景汇总如表2，其中 UC-02 与 UC-06 的执行细节分别在 2.4 节与 2.5 节展开。")
    add_table(
        doc,
        "表2　系统用例清单",
        ["编号", "用例名称", "参与者", "用例目标", "主要成功场景"],
        [
            ("UC-01", "浏览与筛选活动", "学生", "查看可报名活动", "进入活动列表，按名称筛选，打开活动详情"),
            ("UC-02", "报名活动", "学生", "完成一次有效报名", "选择活动并提交，系统按报名方式生成已通过或待审核记录"),
            ("UC-03", "取消报名", "学生", "撤回自己的报名", "选择待审核或已通过记录，取消后状态变为已取消"),
            ("UC-04", "查看我的报名与站内消息", "学生", "掌握报名进度", "查看报名列表、状态与通知内容"),
            ("UC-05", "创建、编辑、删除活动", "管理员", "维护活动信息", "填写名称、类型、时间、地点、容量与报名方式并保存"),
            ("UC-06", "审批报名", "管理员", "处理待审核申请", "批准或拒绝，批准前复查剩余名额"),
            ("UC-07", "查看名额统计", "管理员", "掌握报名结构", "按活动查看已通过数、待审核数与剩余名额"),
            ("UC-08", "校验名额与重复报名", "系统", "保证业务约束", "被 UC-02、UC-06 包含，校验重复有效报名与名额上限"),
        ],
        widths_cm=[1.6, 4.6, 1.9, 3.6, 5.9],
    )

    heading(doc, "2.4　用例 UC-02“报名活动”说明", 2)
    body(doc, "报名是系统中分支最多、约束最集中的用例，其详细说明如表3。")
    add_table(
        doc,
        "表3　用例 UC-02“报名活动”说明",
        ["项目", "内容"],
        [
            ("用例编号", "UC-02"),
            ("参与者", "学生（主参与者），系统（支撑）"),
            ("前置条件", "学生已以演示账号登录；活动存在且未下架；活动开始时间晚于当前时间"),
            ("触发事件", "学生在活动详情页点击“报名”"),
            ("基本流程", "1. 学生选择活动并提交报名。\n"
                        "2. 系统校验活动存在且尚未开始。\n"
                        "3. 系统校验该学生在此活动下不存在“待审核”或“已通过”的报名。\n"
                        "4. 系统读取活动的报名方式，从策略注册表取得对应策略。\n"
                        "5. 策略作出决定：直接报名在名额充足时置为“已通过”；审核报名置为“待审核”。\n"
                        "6. 系统持久化报名记录，发布报名事件，由订阅者写入站内消息。"),
            ("扩展流程", "E1 活动不存在或已开始：提示后终止，不产生记录。\n"
                        "E2 已存在有效报名：拒绝重复报名，保留原记录。\n"
                        "E3 直接报名且剩余名额为 0：报名失败，不产生记录。\n"
                        "E4 站内消息写入失败：记录失败日志，报名结果不回滚。"),
            ("后置条件", "报名记录状态为“已通过”或“待审核”；学生收到站内消息（失败时留失败记录）；名额统计随之变化"),
            ("业务规则", "名额按“已通过”统计；待审核不占名额；同一学生同一活动最多一条有效报名"),
            ("对应验收用例", "C2、C3、C4、C5"),
        ],
        widths_cm=[2.6, 13.4],
        center_cols=(0,),
    )

    heading(doc, "2.5　用例 UC-06“审批报名”说明", 2)
    body(doc,
         "审批用例的关键在于“批准时再次检查名额”。待审核阶段不占名额，因此审批台可能同时存在多于剩余名额的申请，"
         "先到先得与逐条复查是保证不超出人数上限的唯一方式。详细说明如表4。")
    add_table(
        doc,
        "表4　用例 UC-06“审批报名”说明",
        ["项目", "内容"],
        [
            ("用例编号", "UC-06"),
            ("参与者", "管理员（主参与者），系统（支撑）"),
            ("前置条件", "报名记录状态为“待审核”；对应活动未下架"),
            ("触发事件", "管理员在审批台点击“批准”或“拒绝”"),
            ("基本流程", "1. 管理员选择一条待审核报名。\n"
                        "2. 系统校验该记录仍为“待审核”，防止重复审批。\n"
                        "3. 批准时系统复查该活动当前“已通过”数是否小于容量。\n"
                        "4. 名额充足则更新为“已通过”，发布审批事件并通知学生。\n"
                        "5. 拒绝时直接更新为“已拒绝”，发布事件并通知学生。"),
            ("扩展流程", "E1 名额已满：批准失败，状态保持“待审核”，不发送通过通知。\n"
                        "E2 记录状态已变更：拒绝本次操作，提示刷新后重试。"),
            ("后置条件", "报名状态为“已通过”或“已拒绝”；学生收到审批结果通知；名额统计同步更新"),
            ("对应验收用例", "C6、C7、C8"),
        ],
        widths_cm=[2.6, 13.4],
        center_cols=(0,),
    )

    # 3 静态设计
    heading(doc, "3　静态设计：UML 类图", 1)
    heading(doc, "3.1　类的职责划分", 2)
    body(doc,
         "职责划分遵循一个判断标准：谁拥有数据，谁负责维护与该数据直接相关的不变量；跨对象的流程由服务编排，规则由策略表达，通知由订阅者承担。"
         "按此标准，系统的类职责如表5。表中“不承担”一列是设计评审的重点，越界往往意味着职责错位。")
    add_table(
        doc,
        "表5　领域类与服务的职责划分",
        ["类", "职责（负责维护的不变量）", "不承担"],
        [
            ("Student", "保存学号与姓名，学号唯一", "不判断能否报名，不持有报名集合"),
            ("Activity", "活动信息、容量、报名方式、开始时间；剩余名额计算 remaining()；开放状态判断 isOpen()", "不写报名记录，不发通知"),
            ("Registration", "一条报名记录及其状态；isActive() 与 canCancel() 表达状态约束", "不查名额，不查重，不写消息"),
            ("RegistrationService", "编排报名、取消、审批流程；执行公共校验；发布领域事件", "不硬编码报名方式分支，不直接写站内消息"),
            ("RegistrationPolicy", "报名规则的稳定抽象，只回答“本次报名应得到什么状态”", "不访问数据库，不统计名额，不发通知"),
            ("DirectRegistrationPolicy", "名额充足则返回“已通过”，不足时抛出名额异常", "不处理审核逻辑"),
            ("AuditRegistrationPolicy", "返回“待审核”，不占用名额", "不处理名额校验（由审批环节复查）"),
            ("CapacityRule", "名额公共规则：按“已通过”统计，提供判定与断言", "不决定报名状态，不写库"),
            ("EventBus", "订阅管理与事件派发；隔离订阅者异常并留痕", "不决定通知内容，不修改报名状态"),
            ("InAppNotificationObserver", "把报名事件转换为站内消息；按 eventId 幂等", "不修改报名状态，不做业务校验"),
            ("Repository 层", "SQL 存取与实体映射", "不做业务判断"),
        ],
        widths_cm=[4.3, 7.4, 4.3],
    )

    heading(doc, "3.2　UML 类图", 2)
    body(doc,
         "类图如图2所示。图中同时给出属性、关键方法与关系类型，关联线上标注多重度，泛化用空心三角，依赖用虚线箭头，活动与报名之间用空心菱形表示聚合。")
    add_picture(doc, "fig2_class.png", 15.6, "图2　CampusEvent 初始版本 UML 类图")

    heading(doc, "3.3　关系与依赖方向", 2)
    body(doc,
         "类图表达了三组关系。第一组是领域对象之间的关联：一名学生对应零到多条报名，一个活动对应零到多条报名，活动与报名之间为聚合，"
         "表示报名依附活动存在但拥有独立生命周期（取消后仍保留历史）。第二组是泛化：两种报名策略实现同一接口，接口只有 decide 一个操作，"
         "实现类共享“返回状态或抛出业务异常”的契约。第三组是依赖：RegistrationService 依赖策略抽象、容量规则、仓储与事件总线；"
         "EventBus 依赖订阅者；订阅者依赖消息仓储。")
    body(doc,
         "依赖方向是本设计的核心约束。RegistrationService 只依赖 RegistrationPolicy 抽象，不依赖任何一个具体策略，因此新增报名方式不会修改服务代码；"
         "同理，报名业务只依赖“发布事件”这一动作，不依赖通知渠道，因此新增邮件渠道只需新增订阅者。"
         "需要特别说明的是，Registration 与 Message 之间没有关联：消息由事件产生，而不是由报名记录直接创建，这是解耦在类图上的可见证据。")

    heading(doc, "3.4　报名状态约束", 2)
    body(doc,
         "状态机是报名记录自身的不变量，转换规则如表6。表中最后一行表示“已取消”与“已拒绝”保留历史，学生可再次申请，但会生成新的报名记录而不是复活旧记录。")
    add_table(
        doc,
        "表6　报名状态转换与约束",
        ["当前状态", "触发事件", "目标状态", "约束条件"],
        [
            ("（无记录）", "学生报名（直接报名）", "已通过", "活动未开始；名额充足；无有效报名"),
            ("（无记录）", "学生报名（审核报名）", "待审核", "活动未开始；无有效报名"),
            ("待审核", "管理员批准", "已通过", "复查时“已通过”数小于容量"),
            ("待审核", "管理员拒绝", "已拒绝", "记录仍为待审核"),
            ("待审核", "学生取消", "已取消", "操作者本人；活动未开始"),
            ("已通过", "学生取消", "已取消", "操作者本人；活动未开始"),
            ("已取消 / 已拒绝", "学生重新报名", "待审核或已通过", "按当前活动报名方式重新走策略"),
        ],
        widths_cm=[3.4, 4.6, 3.2, 5.3],
    )

    # 4 动态设计
    heading(doc, "4　动态设计：关键交互时序图", 1)
    heading(doc, "4.1　报名时序", 2)
    body(doc,
         "报名时序如图3所示。流程先完成两项公共校验（活动可用、无重复有效报名），再进入策略决策。"
         "组合片段区分两种报名方式：直接报名需要调用容量规则并可能抛出名额异常；审核报名不校验名额，直接返回待审核状态，"
         "这正是把名额检查作为公共规则、把状态决策交给策略的原因。")
    add_picture(doc, "fig3_seq_register.png", 15.6, "图3　报名活动时序图（含直接报名与审核报名分支）")

    heading(doc, "4.2　审批时序", 2)
    body(doc,
         "审批时序如图4所示。批准操作的第一步是复查记录状态，防止两名管理员或重复点击造成的重复审批；第二步是复查名额，"
         "这一步使用的正是报名时同一套容量规则。名额不足时抛出业务异常，服务直接返回失败，既不改状态也不发布事件，因此学生不会收到“已通过”的错误通知。")
    add_picture(doc, "fig4_seq_approve.png", 15.6, "图4　审批报名时序图（含名额不足分支）")

    heading(doc, "4.3　通知的事务边界与幂等", 2)
    body(doc,
         "通知与报名的事务边界采用“先提交业务、再派发事件”的顺序。报名记录写入并提交后，服务才向事件总线发布事件；"
         "事件总线逐个调用订阅者，任一订阅者抛出异常都被捕获并写入通知失败记录，不会向上传播，也不会回滚已提交的报名。"
         "这样处理的代价是可能出现“报名成功但没有消息”的短暂不一致，收益是绝不出现“有消息但报名丢失”的更严重不一致，"
         "前者可以通过失败记录补偿重发，后者无法自愈。")
    body(doc,
         "重复通知通过事件标识 event_id 控制，格式为“reg:报名编号:动作”。订阅者写消息前先在已处理事件表中占用该标识，"
         "占用成功才写消息，占用失败说明事件已处理，直接跳过。该机制保证同一事件在重试或重复派发时最多产生一条站内消息。"
         "需要说明其边界：幂等只在单一数据库内有效，跨进程多实例部署时需要改用数据库唯一约束或分布式锁。")

    # 5 设计原则
    heading(doc, "5　设计原则与模式应用", 1)
    heading(doc, "5.1　用策略模式表达变化的报名规则", 2)
    body(doc,
         "报名规则的稳定抽象是 RegistrationPolicy，只暴露 decide(PolicyContext) 一个操作，上下文只携带活动与当前已通过数。"
         "直接报名与审核报名分别实现为 DirectRegistrationPolicy 与 AuditRegistrationPolicy，二者共享“返回状态或抛出业务异常”的契约。"
         "选择点集中在 PolicyRegistry，服务按活动的报名方式取策略，主流程中没有 if 判断。")
    body(doc,
         "这样设计的扩展成本可以量化：新增第三种报名方式（例如候补），需要新增一个策略类并在注册表登记，"
         "RegistrationService 与页面层的修改量为零，回归范围可限定在新策略的单元测试与报名入口的集成测试。"
         "若不采用策略而把规则写在服务里，新增一种方式就要改动主流程并重新回归所有报名分支，"
         "随着规则增多，主流程会演变成难以测试的条件分支集合。")

    heading(doc, "5.2　用观察者机制解耦报名与通知", 2)
    body(doc,
         "报名业务只发布“报名已提交、已通过、已拒绝、已取消”四类事件，不关心谁订阅、如何发送、发送到哪个渠道。"
         "EventBus 维护订阅者列表，InAppNotificationObserver 订阅并写入站内消息。"
         "新增通知渠道只需新增一个订阅者并注册，报名业务代码不变；关闭某个渠道只需取消订阅，不需要在业务中加开关。")
    body(doc,
         "这种解耦的代价是链路变长、排查变难：消息没发出时，需要依次检查事件是否发布、订阅者是否注册、"
         "幂等占用是否成功、失败记录是否有内容。为此本设计保留通知失败表，把“没有消息”从不可解释的静默失败变成可查询的记录。")

    heading(doc, "5.3　名额检查的归属论证", 2)
    body(doc,
         "名额检查属于公共规则，而不是某一个策略的责任。本设计把它抽为 CapacityRule，由直接报名策略在决策时调用，"
         "由审批流程在批准时再次调用。理由有三点。")
    body(doc,
         "第一，同一条约束被两个入口使用。报名时的直接通过、审批时的批准，都必须保证“已通过数小于容量”，"
         "若把检查分别写进两个策略，会出现两份实现，任何一处修改都可能造成口径不一致。")
    body(doc,
         "第二，名额是活动自身的领域不变量。容量属于活动，已通过数属于报名集合，二者共同决定剩余名额，"
         "这与“这次报名是直接通过还是先审核”属于不同层次的问题。把不变量放在策略里，等于让规则类去承担数据一致性的职责。")
    body(doc,
         "第三，两类策略对名额的依赖程度不同。审核报名明确允许在满员时进入待审核，因此它不能在决策阶段执行名额断言；"
         "直接报名必须在决策阶段执行。若把名额检查整体上移到服务主流程，审核型“满员仍可申请”的差异又会被迫回到主流程的条件判断，"
         "违背任务B“服务依赖抽象、不硬编码类型判断”的要求。公共规则加策略决策的组合，恰好同时满足一致性与差异表达。")

    heading(doc, "5.4　SOLID 原则的落实", 2)
    body(doc, "五项原则在本设计中的具体落点如表7，评审时按“证据”一列核对，而不是只看是否声明使用模式。")
    add_table(
        doc,
        "表7　SOLID 原则落实对照",
        ["原则", "本设计的落点", "可核对证据"],
        [
            ("单一职责", "活动只管名额与开放状态，报名记录只管状态，服务只编排流程", "表5 的“不承担”列；类图中无跨对象写操作"),
            ("开闭原则", "新增报名方式只新增策略实现，主流程不修改", "PolicyRegistry 注册点唯一；服务只调用接口"),
            ("里氏替换", "两种策略实现同一契约，调用方对实现无差别", "decide 返回状态或抛出业务异常；服务统一处理异常"),
            ("接口隔离", "策略接口仅一个操作，不暴露无关方法", "图2 中 RegistrationPolicy 仅有 decide"),
            ("依赖倒置", "服务依赖策略抽象与事件总线，不依赖具体实现", "图2 的虚线依赖方向；构造时可替换注册表"),
        ],
        widths_cm=[3.0, 7.2, 5.8],
    )

    heading(doc, "5.5　模式的成本与局限", 2)
    body(doc,
         "设计评审要求如实报告模式的代价。策略与事件机制带来的结构成本、能力收益与当前局限如表8，后续需求变更的可维护性对照将以本表为基线。")
    add_table(
        doc,
        "表8　模式引入的成本、收益与局限",
        ["设计点", "新增的结构成本", "换来的能力", "尚未解决的局限"],
        [
            ("策略抽象", "一个接口、一个注册表、两个实现类", "报名方式可扩展；主流程无类型判断", "多种规则的组合（如满员候补）仍需新增策略，规则叠加能力有限"),
            ("事件总线", "一个组件、一张通知失败表、订阅注册代码", "报名与通知解耦；可加渠道；失败隔离", "当前为进程内同步派发，不是真正异步，通知耗时会占用请求时间"),
            ("幂等表", "一张已处理事件表与占用逻辑", "重复事件不重复通知", "仅单库内有效，多实例部署需替换为唯一约束或分布式锁"),
            ("状态枚举", "四种状态及转换校验", "状态非法转换被拒绝", "状态增多后需要显式状态机，当前用方法内判断维护"),
        ],
        widths_cm=[2.9, 4.6, 4.3, 4.7],
    )

    # 6 评审
    heading(doc, "6　设计评审", 1)
    heading(doc, "6.1　评审检查表", 2)
    body(doc,
         "评审按指导书附录 B.3 的七项要求逐条核对，结论与证据如表9。评审人应独立核对类图与时序图，确认证据可追溯，而不是仅确认“材料齐全”。")
    add_table(
        doc,
        "表9　设计评审检查表",
        ["检查项", "结论", "证据与说明"],
        [
            ("类图体现活动、学生、报名记录、报名业务与通知职责", "通过", "图2：Activity、Student、Registration、RegistrationService、InAppNotificationObserver"),
            ("至少一个策略接口及两种实现，说明策略选择与公共规则位置", "通过", "图2 与 5.1、5.3；策略选择点在 PolicyRegistry，名额规则在 CapacityRule"),
            ("通知通过观察者或等价事件分发机制解耦", "通过", "图2、图3；EventBus 与订阅者，报名记录与消息无直接关联"),
            ("至少两张时序图：直接/审核型报名、审核批准", "通过", "图3（含 alt 两个分支）、图4（含名额不足分支）"),
            ("明确名额超限、重复报名、取消报名、审批冲突的边界处理", "通过", "表3 扩展流程 E1–E4；表4 扩展流程 E1–E2；表6 状态约束"),
            ("提供设计取舍说明：为何使用模式、增加哪些成本、未来如何扩展", "通过", "5.1–5.5；表8 成本、收益与局限"),
            ("设计可支撑验收用例 C1–C10", "通过", "表3、表4 的对应验收用例列；C9 取消与 C10 持久化由状态表与仓储层覆盖"),
        ],
        widths_cm=[7.6, 2.2, 6.2],
        center_cols=(0, 1),
    )

    heading(doc, "6.2　评审意见与签署", 2)
    body(doc,
         "评审采用交叉评审方式，由同组之外的一名学生核对上述材料，重点检查依赖方向与职责越界。评审结论与签署信息如表10，签名须手写或以电子签名确认。")
    add_table(
        doc,
        "表10　评审结论与签署",
        ["项目", "内容"],
        [
            ("评审人", "【评审学生姓名】"),
            ("评审日期", "【评审日期】"),
            ("评审方式", "交叉评审：逐条核对表9，抽查类图依赖方向与时序图分支"),
            ("评审结论", "□ 通过，可进入 AI 实现　　□ 有条件通过，按意见修改后复核　　□ 不通过"),
            ("主要意见", "【评审人填写：至少一条具体修改意见或确认意见】"),
            ("评审人签名", "【签名】"),
            ("学生确认", "【设计者签名】"),
        ],
        widths_cm=[2.6, 13.4],
        center_cols=(0,),
    )

    heading(doc, "6.3　进入 AI 实现的前置条件", 2)
    body(doc,
         "评审通过并完成签名后，本文档中的类图与接口定义作为 AI 编码的约束基线：AI 不得合并策略接口、不得删除事件分发结构、"
         "不得把通知写入报名服务；如需调整设计，应先更新本文档并说明理由，再修改代码。"
         "实现完成后，验收用例 C1 至 C10 作为回归基线，任何设计偏离都必须在回归记录中体现。")

    doc.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
