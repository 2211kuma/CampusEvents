# -*- coding: utf-8 -*-
"""生成精简版《实验二 设计任务D 设计材料》。复用 build_report 的排版工具函数。"""

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from build_report import (
    CN_BODY,
    CN_HEAD,
    EN,
    add_field,
    add_picture,
    add_table,
    body,
    caption,
    heading,
    set_run_font,
    setup_section,
)
from pathlib import Path

OUT_LEAN = Path(r'D:\test\实验二设计任务D-设计说明书（精简版）.docx')


def build_cover(doc):
    for _ in range(5):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)

    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(16)
    run = p.add_run('《软件工程》实验二')
    set_run_font(run, cn=CN_HEAD, size=22, bold=True)

    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run('校园活动报名与管理系统（CampusEvent）')
    set_run_font(run, cn=CN_HEAD, size=18, bold=True)

    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(30)
    run = p.add_run('设计任务D　设计材料与评审（设计版本 V1）')
    set_run_font(run, cn='楷体', size=14)

    info = [
        ('班　　级', '【班级】'),
        ('学　　号', '【学号】'),
        ('姓　　名', '【姓名】'),
        ('指导教师', '林卫中、赵丽萍'),
        ('提交日期', '2026年11月21日'),
    ]
    table = doc.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for label, value in info:
        row = table.add_row()
        for i, text in enumerate((label, value)):
            cell = row.cells[i]
            cell.width = Cm(4.4 if i == 0 else 8.6)
            p = cell.paragraphs[0]
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
            run = p.add_run(text)
            set_run_font(run, size=12, bold=(i == 0))


def main():
    doc = Document()
    normal = doc.styles['Normal']
    normal.font.name = EN
    normal.font.size = Pt(12)
    normal.element.rPr.rFonts.set(qn('w:eastAsia'), CN_BODY)

    setup_section(doc.sections[0])
    build_cover(doc)

    # 正文另起一页，页码从 1 开始
    sec = doc.add_section(WD_SECTION.NEW_PAGE)
    setup_section(sec)
    sec.footer.is_linked_to_previous = False
    pg = OxmlElement('w:pgNumType')
    pg.set(qn('w:start'), '1')
    cols = sec._sectPr.find(qn('w:cols'))
    if cols is not None:
        cols.addprevious(pg)
    else:
        sec._sectPr.append(pg)
    footer_p = sec.footer.paragraphs[0]
    footer_p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_field(footer_p, ' PAGE ', placeholder='1')

    # 1 任务与范围
    heading(doc, '1　任务与范围', 1)
    body(doc,
         '实验二要求在 AI 编码之前完成设计与评审：提交需求用例图或用例说明、UML 类图、报名与审批时序图各一张、设计原则说明，'
         '并由其他学生评审签名后，才进入实现阶段。本文档只保留这四类材料及评审记录，对应的设计版本是 CampusEvent 的 V1。')
    body(doc,
         '设计范围限定为初始的 8 项功能，不实现注册、复杂权限、邮件渠道与消息队列。须遵守的硬约束是：名额只按“已通过”统计、待审核不占名额；'
         '同一学生同一活动至多一条有效报名；活动开始后不得新增报名；学生只能取消自己的待审核或已通过报名；通知失败必须留痕但不得让报名记录消失。')

    # 2 用例
    heading(doc, '2　用例模型', 1)
    body(doc,
         '参与者只有学生与管理员。“校验名额与重复报名”作为被包含的公共子流程，不单独由参与者发起。用例与参与者关系如图1。')
    add_picture(doc, 'fig1_usecase.png', 12.4, '图1　CampusEvent 系统用例图')
    body(doc, '八个用例的目标如表1，报名与审批的执行细节在表2、表3展开。')
    add_table(
        doc,
        '表1　用例清单',
        ['编号', '用例名称', '参与者', '用例目标'],
        [
            ('UC-01', '浏览与筛选活动', '学生', '按名称筛选并查看可报名活动'),
            ('UC-02', '报名活动', '学生', '按报名方式生成已通过或待审核记录'),
            ('UC-03', '取消报名', '学生', '撤回自己的待审核或已通过报名'),
            ('UC-04', '查看我的报名与站内消息', '学生', '掌握报名进度与通知内容'),
            ('UC-05', '创建、编辑、删除活动', '管理员', '维护活动信息与人数上限'),
            ('UC-06', '审批报名', '管理员', '批准或拒绝待审核申请'),
            ('UC-07', '查看名额统计', '管理员', '查看已通过、待审核与剩余名额'),
            ('UC-08', '校验名额与重复报名', '系统', '被 UC-02、UC-06 包含的公共校验'),
        ],
        widths_cm=[1.8, 5.0, 2.2, 7.0],
    )
    add_table(
        doc,
        '表2　用例 UC-02“报名活动”说明',
        ['项目', '内容'],
        [
            ('前置条件', '学生已登录；活动存在且未开始'),
            ('基本流程', '1 提交报名；2 校验活动可用；3 校验无有效报名；4 按报名方式取策略；'
                        '5 直接报名在名额充足时置为已通过，审核报名置为待审核；6 落库、发布事件、写站内消息'),
            ('扩展流程', 'E1 活动不存在或已开始：终止；E2 已有有效报名：拒绝重复报名；'
                        'E3 直接报名且名额为 0：失败且不产生记录；E4 消息写入失败：留痕，报名不回滚'),
            ('后置条件', '状态为已通过或待审核；名额统计同步更新'),
        ],
        widths_cm=[2.6, 13.4],
    )
    add_table(
        doc,
        '表3　用例 UC-06“审批报名”说明',
        ['项目', '内容'],
        [
            ('前置条件', '报名记录为待审核'),
            ('基本流程', '1 管理员选择待审核记录；2 校验状态仍为待审核；3 批准时复查已通过数小于容量；'
                        '4 更新为已通过并发布事件；5 拒绝时更新为已拒绝并发布事件'),
            ('扩展流程', 'E1 名额已满：批准失败，状态不变，不发通过通知；E2 状态已变更：拒绝本次操作'),
            ('后置条件', '状态为已通过或已拒绝；学生收到结果通知'),
        ],
        widths_cm=[2.6, 13.4],
    )

    # 3 类设计
    heading(doc, '3　类设计', 1)
    body(doc,
         '职责划分的标准是：谁拥有数据谁维护与该数据相关的不变量，跨对象流程由服务编排，规则由策略表达，通知由订阅者承担。各类职责如表4。')
    add_table(
        doc,
        '表4　类职责',
        ['类', '职责', '不承担'],
        [
            ('Activity', '活动信息与容量；剩余名额与开放状态', '不写报名、不发通知'),
            ('Registration', '一条报名记录及其状态约束', '不查重、不查名额、不写消息'),
            ('RegistrationService', '编排报名与审批流程、执行公共校验、发布事件', '不硬编码报名方式，不直接写消息'),
            ('RegistrationPolicy', '稳定抽象：只回答本次报名应得到什么状态', '不访问数据库、不统计名额'),
            ('Direct / Audit Policy', '分别返回已通过（含名额断言）与待审核', '不承担名额统计口径'),
            ('CapacityRule', '公共规则：按已通过计数判定并断言名额', '不决定状态、不写库'),
            ('EventBus / 订阅者', '派发事件并隔离异常；把事件转成站内消息（按 eventId 幂等）', '不修改报名状态'),
            ('Repository 层', 'SQL 存取与实体映射', '不做业务判断'),
        ],
        widths_cm=[4.0, 7.4, 4.6],
    )
    body(doc, '类图如图2，图中给出属性、关键方法、关系类型与多重度。')
    add_picture(doc, 'fig2_class.png', 15.6, '图2　CampusEvent 初始版本 UML 类图')
    body(doc,
         '关系上，学生与报名、活动与报名均为一对多，活动与报名之间是聚合，取消后仍保留历史。RegistrationService 依赖策略抽象、容量规则、事件总线与仓储，'
         '不依赖任何具体策略；报名记录与消息之间没有关联，消息由事件产生。状态上，待审核经批准转为已通过、经拒绝转为已拒绝，待审核与已通过可取消为已取消；'
         '已取消与已拒绝保留历史，再次申请生成新记录。')

    # 4 时序
    heading(doc, '4　时序设计', 1)
    body(doc,
         '报名时序如图3。流程先做两项公共校验，再进入策略决策；直接报名需要调用容量规则并可能抛出名额异常，审核报名不校验名额而直接返回待审核。')
    add_picture(doc, 'fig3_seq_register.png', 15.6, '图3　报名活动时序图')
    body(doc,
         '审批时序如图4。批准先复查记录状态防止重复审批，再复查名额；名额不足时抛异常直接返回，既不改状态也不发事件，因此不会产生错误的通过通知。')
    add_picture(doc, 'fig4_seq_approve.png', 15.6, '图4　审批报名时序图')
    body(doc,
         '通知与报名的事务边界是“先提交业务、再派发事件”。报名落库提交后服务才发事件，订阅者异常被捕获并写入通知失败记录，不回滚已提交的报名；'
         '重复通知用事件键 reg:报名号:动作 在已处理事件表中占用，占用成功才写消息。代价是可能出现“报名成功但无消息”，可用失败记录补偿；'
         '收益是绝不出现“有消息但报名丢失”。该幂等只在单库内有效。')

    # 5 设计原则
    heading(doc, '5　设计原则说明', 1)
    body(doc,
         '报名规则采用策略模式。抽象 RegistrationPolicy 只有一个操作 decide(上下文)，上下文只携带活动与当前已通过数；'
         '直接报名与审核报名是两个实现，选择点集中在 PolicyRegistry，主流程没有类型判断。新增一种报名方式只需新增类并注册，服务代码与页面不改，'
         '回归范围可限定在新策略的单元测试与报名入口的集成测试。')
    body(doc,
         '报名与通知采用观察者机制解耦。业务只发布报名已提交、已通过、已拒绝、已取消四类事件，不关心谁订阅、发到哪个渠道；'
         '新增渠道只需新增订阅者，关闭渠道只需取消订阅。代价是链路变长，排查时需依次检查事件、订阅、幂等占用与失败记录，因此保留失败表把静默失败变成可查询记录。')
    body(doc,
         '名额检查属于公共规则，放在 CapacityRule，由直接报名策略在决策时调用、由审批在批准时再次调用。'
         '若把它分别写进两个策略，同一条约束会有两份实现，口径容易分叉；名额由活动容量与已通过报名数共同决定，属于领域不变量，不属于某种报名方式。')
    body(doc,
         '也不能把名额检查整体上移到服务主流程：审核型明确允许满员时进入待审核，若在服务里统一断言，就会迫使主流程重新加入类型判断，'
         '违背“服务依赖抽象、不硬编码类型判断”。公共规则加策略决策的组合同时满足一致性与差异表达。五项原则的落点见表5。')
    add_table(
        doc,
        '表5　SOLID 原则落点',
        ['原则', '落点'],
        [
            ('单一职责', '活动管名额，报名记录管状态，服务只编排流程'),
            ('开闭原则', '新增报名方式只加策略实现与注册项'),
            ('里氏替换', '两种策略共享“返回状态或抛业务异常”的契约'),
            ('接口隔离', '策略接口只有 decide 一个操作'),
            ('依赖倒置', '服务依赖策略抽象与事件总线，不依赖具体实现'),
        ],
        widths_cm=[3.2, 12.8],
    )
    body(doc,
         '代价同样需要如实说明：策略与事件机制增加了接口、注册表、事件总线与失败的幂等表；事件派发为进程内同步，会占用请求时间；幂等只在单库内成立。'
         '这些结构成本换来的是报名方式与通知渠道的扩展不再改动业务主流程。')

    # 6 评审
    heading(doc, '6　设计评审', 1)
    body(doc, '评审按指导书附录 B.3 逐条核对，结论与证据如表6。')
    add_table(
        doc,
        '表6　设计评审检查表',
        ['检查项', '结论', '证据'],
        [
            ('类图体现活动、学生、报名与通知职责', '通过', '图2'),
            ('至少一个策略接口与两种实现，说明策略选择与公共规则位置', '通过', '图2、5.1、5.3'),
            ('通知通过观察者或等价事件机制解耦', '通过', '图2、4.3'),
            ('报名（直接/审核）与审批各一张时序图', '通过', '图3、图4'),
            ('名额超限、重复报名、取消、审批冲突的边界明确', '通过', '表2、表3 扩展流程'),
            ('说明设计取舍与扩展方式、成本', '通过', '5.1–5.4'),
            ('设计可支撑验收用例 C1–C10', '通过', '表2、表3、4.3'),
        ],
        widths_cm=[7.4, 2.0, 6.6],
        center_cols=(1,),
    )
    body(doc, '评审采用交叉评审，由同组之外的一名学生核对材料，结论与签署见表7。')
    add_table(
        doc,
        '表7　评审结论与签署',
        ['项目', '内容'],
        [
            ('评审人', '【评审学生姓名】'),
            ('评审日期', '【评审日期】'),
            ('评审结论', '□ 通过　　□ 有条件通过　　□ 不通过'),
            ('主要意见', '【评审人填写】'),
            ('评审人签名', '【签名】　　设计者签名：【签名】'),
        ],
        widths_cm=[2.6, 13.4],
    )
    body(doc,
         '评审通过并签名后，本文档的类图与接口定义作为 AI 编码的约束基线；如需调整设计，先更新文档再改代码，并以 C1–C10 作为回归基线。')

    doc.save(OUT_LEAN)
    print('saved', OUT_LEAN)


if __name__ == '__main__':
    main()
