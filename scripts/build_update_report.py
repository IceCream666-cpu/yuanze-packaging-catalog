#!/usr/bin/env python3
"""Build the evidence-grounded internal history report. Does not access live data."""
import json
from pathlib import Path
import re
import subprocess
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table,
    TableStyle, LongTable, PageBreak, KeepTogether,
)
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs/建设更新日志-20261007.json'
OUTPUT = ROOT / 'output/pdf/源泽包材库_建设与更新日志_20260922-20261007.pdf'
FONT = Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
TEAL = colors.HexColor('#164B47')
IVORY = colors.HexColor('#F7F4ED')
MIST = colors.HexColor('#E5EDE7')
INK = colors.HexColor('#243D39')
MUTED = colors.HexColor('#617770')
LINE = colors.HexColor('#CEDBD3')
COPPER = colors.HexColor('#B88C69')
WHITE = colors.white
WIDTH, HEIGHT = landscape(A4)
MARGIN = 32
INNER = WIDTH - 2 * MARGIN

COMMIT_LABELS = {
    '47fb32e': ('初始化正式工程、协作规则与回归验证', '工程建立'),
    'b812863': ('后端数据库职责、只读健康检查与 Sites 说明', '档案／检查'),
    'f78da2e': ('恢复安全客户目录及三角色中英文界面', '功能实现'),
    '723253f': ('翻译服务端注入的登录默认文字', '补充修复'),
    'c667dbe': ('补齐导入类目与可访问动作翻译', '补充修复'),
    'b2a618c': ('私有 Git 交接及历史资料边界', '交接档案'),
    'f3bd53d': ('双语手机展厅预览与公司证书', '预览实现'),
    '8e9cd64': ('独立客户分页和安全选型工具', '预览实现'),
    'aef53cb': ('响应式客户展厅正式发布与维护指南', '功能发布'),
    '078c908': ('展厅上线验证及两端维护档案', '上线记录'),
    '9867fbe': ('包材选型前的登录保护双语海报栏目', '功能实现'),
    'bc5ebdf': ('修复 Linux WebP 响应 MIME 类型', '发布修复'),
    '0a6e3cd': ('海报发布验证与维护边界', '上线记录'),
    '24867f5': ('图片统一风格及样板验收标准', '规范档案'),
    '9bddb3e': ('图片专用更新、审计与待核对范围', '功能实现'),
    'c6f1514': ('批量上传前等待视觉检索索引', '稳定性修复'),
    '2a652ef': ('已修正系列封面优先于保留原图', '展示修复'),
    'f664db1': ('图片正式发布和剩余队列记录', '上线记录'),
    'f09b36b': ('并行图片任务避重和产品占用保护', '处理工具'),
    '6c07bb8': ('200 张图片发布及繁忙上传安全重试', '图片发布'),
    '10266b0': ('跨聊天重复审计与累计口径纠正', '核验记录'),
    'd87da6e': ('另一聊天独立尾批 200 张发布', '图片记录'),
    '46e3891': ('新增十张已审核客户产品海报', '素材更新'),
    '94c8017': ('容量搜索名称调整为规格', '界面调整'),
    '116649f': ('十张海报正式发布验证', '上线记录'),
    '617c1b6': ('规格筛选名称正式发布验证', '上线记录'),
    '5059942': ('移除十七张同系列模特海报', '素材调整'),
    '687d80e': ('同款包材归并及已确认规格图标注', '功能／图片'),
    '4352604': ('首页业务改为 OEM／ODM／OBM／Private Label', '内容调整'),
    '58f1e86': ('同款归并上线及待映射规格记录', '上线记录'),
    '939d920': ('首页业务标签正式发布验证', '上线记录'),
    '4f2fefe': ('限定图片批次的客户批准校验', '权限验证'),
    'a8e0fc1': ('五十张不同来源优化图及隔离核验', '图片发布'),
    '0a02857': ('十七张海报移除上线验证', '上线记录'),
    'b6d04cf': ('完成提交后自动上传私有 GitHub', '工程工具'),
    'e01acb4': ('200 张优化图片客户开放验证', '上线记录'),
    '0998d42': ('员工及客户已授权图片下载', '功能发布'),
}


def commits_at_source(source_head):
    """Freeze the appendix at the website source revision, even after report commit."""
    result = subprocess.check_output(
        ['git', '-C', str(ROOT), 'log', '--reverse',
         '--format=%h|%ad', '--date=format-local:%m-%d %H:%M', source_head],
        text=True,
    )
    commits = [line.split('|') for line in result.splitlines()]
    if set(h for h, _ in commits) != set(COMMIT_LABELS):
        raise ValueError('Commit appendix no longer matches the frozen source history')
    return commits


def p(text, style='body'):
    return Paragraph(escape(str(text)).replace('\n', '<br/>'), STYLES[style])


def status_p(text):
    match = re.match(r'(已上线|已完成|部分完成|方案阶段|已恢复|未实施)', text)
    if not match:
        return p(text)
    label = match.group(1)
    colour = '#164B47' if label in {'已上线', '已完成', '已恢复'} else '#936C46'
    html = '<font color="{}">{}</font>{}'.format(colour, escape(label), escape(text[len(label):]))
    return Paragraph(html, STYLES['body'])


def make_table(headers, rows, widths, status_column=None, body_style='body', padding=7):
    data = [[p(h, 'th') for h in headers]]
    for row in rows:
        data.append([
            status_p(value) if i == status_column else p(value, body_style)
            for i, value in enumerate(row)
        ])
    table = LongTable(data, colWidths=widths, repeatRows=1, hAlign='LEFT', splitByRow=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TEAL),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, colors.HexColor('#F3F6F2')]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), padding),
        ('BOTTOMPADDING', (0, 0), (-1, -1), padding),
        ('LINEBELOW', (0, 0), (-1, 0), 0.8, TEAL),
        ('LINEBELOW', (0, 1), (-1, -1), 0.35, LINE),
        ('BOX', (0, 0), (-1, -1), 0.6, LINE),
    ]))
    return table


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.states = []

    def showPage(self):
        self.states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self.states)
        for state in self.states:
            self.__dict__.update(state)
            self.setFont('CJK', 8)
            self.setFillColor(MUTED)
            self.drawRightString(WIDTH - MARGIN, 23, f'{self._pageNumber} / {total}')
            super().showPage()
        super().save()


def page_header(c, doc):
    c.saveState()
    c.setFillColor(TEAL)
    c.rect(0, HEIGHT - 7, WIDTH, 7, fill=1, stroke=0)
    c.setFont('CJK', 9)
    c.drawString(MARGIN, HEIGHT - 28, 'YUANZE  /  广州源泽药业有限公司')
    c.setFillColor(MUTED)
    c.drawRightString(WIDTH - MARGIN, HEIGHT - 28, '包材库建设与更新日志 · 内部汇报')
    c.setStrokeColor(LINE)
    c.line(MARGIN, 39, WIDTH - MARGIN, 39)
    c.setFont('CJK', 8)
    c.drawString(MARGIN, 23, '2026-09-22 至 2026-10-07  |  统计截止：10-07 19:33 北京时间')
    c.restoreState()


def section(title, note=None, new_page=True):
    result = [PageBreak()] if new_page else []
    result.extend([p(title, 'h1')])
    if note:
        result.extend([p(note, 'note'), Spacer(1, 8)])
    return result


def cover(d, total_steps):
    story = [Spacer(1, 32), p('YUANZE', 'brand'), Spacer(1, 8),
             p('包材库建设与更新日志', 'cover'),
             p('具体操作 · 完成情况 · 发布验证 · 后续待办', 'sub'),
             Spacer(1, 20), p(d['period'], 'date'), Spacer(1, 25)]
    blocks = [
        ['汇报对象', '广州源泽药业有限公司内部'],
        ['报告范围', f'10 个建设阶段 / {total_steps} 项更新步骤 / 37 个 Git 提交'],
        ['当前成果', '员工选型、管理员维护、客户展厅三角色系统；搜索、系列归并、中英文与图片下载。'],
        ['统计依据', '发布档案、源码提交、资料处理清单、线上只读数据库核对及最新验收记录。'],
    ]
    table = Table([[p(a, 'label'), p(b, 'body')] for a, b in blocks], colWidths=[100, INNER - 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), MIST),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ('TOPPADDING', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
        ('LINEBELOW', (0, 0), (-1, -2), 0.4, WHITE),
    ]))
    story.extend([table, Spacer(1, 17), p(
        '汇报口径：已上线、已完成、部分完成、方案阶段分别列示。'
        '记录数不等于独立款式数；图片制作次数不等于不同原图数；'
        '代码备份不等于生产数据完整备份。本报告不包含密码、密钥或采购价格明细。', 'note')])
    return story


def build():
    global STYLES
    pdfmetrics.registerFont(TTFont('CJK', str(FONT)))
    pdfmetrics.registerFontFamily('CJK', normal='CJK', bold='CJK', italic='CJK', boldItalic='CJK')
    STYLES = {
        'body': ParagraphStyle('body', fontName='CJK', fontSize=9.4, leading=13.3,
                               textColor=INK, wordWrap='CJK', splitLongWords=True),
        'small': ParagraphStyle('small', fontName='CJK', fontSize=8.9, leading=12.8,
                                textColor=INK, wordWrap='CJK'),
        'th': ParagraphStyle('th', fontName='CJK', fontSize=9.3, leading=13.2,
                             textColor=WHITE, wordWrap='CJK'),
        'h1': ParagraphStyle('h1', fontName='CJK', fontSize=17, leading=25,
                             textColor=TEAL, spaceBefore=10, spaceAfter=7, keepWithNext=True),
        'note': ParagraphStyle('note', fontName='CJK', fontSize=9.3, leading=14,
                               textColor=MUTED, wordWrap='CJK'),
        'noteKeep': ParagraphStyle('noteKeep', fontName='CJK', fontSize=9.3, leading=14,
                                   textColor=MUTED, wordWrap='CJK', keepWithNext=True),
        'brand': ParagraphStyle('brand', fontName='Times-Roman', fontSize=26, leading=31,
                                textColor=TEAL),
        'cover': ParagraphStyle('cover', fontName='CJK', fontSize=30, leading=42,
                                textColor=TEAL),
        'sub': ParagraphStyle('sub', fontName='CJK', fontSize=13, leading=21, textColor=MUTED),
        'date': ParagraphStyle('date', fontName='CJK', fontSize=19, leading=26, textColor=INK),
        'label': ParagraphStyle('label', fontName='CJK', fontSize=10, leading=14, textColor=TEAL),
    }
    d = json.loads(DATA.read_text())
    steps = sum(len(phase['rows']) for phase in d['phases'])
    commits = commits_at_source(d['sourceHead'])
    story = cover(d, steps)

    story.extend(section('当前成果与统计口径', '以下资料统计为 2026-10-07 19:33 的线上只读快照；图片队列统计来自对应本机发布清单。'))
    rows = [
        ['在线资料', '11,851 条有效 / 11,858 条总计', '8,846 条包材 + 2,867 条图册图片线索 + 91 条工艺参考 + 47 条其他资料；7 条归档。'],
        ['产品编号', '8,853 个累计唯一编号', '包含 7 条已归档产品。编号稳定、不复用；来源记录与独立款式不是同一口径。'],
        ['客户开放', '224 条产品 / 212 个图片路径', '只开放批准的安全展示图；隐藏供应商及价格。系列图片可关联多条产品记录。'],
        ['图片优化', '478 / 5,764 个源图（约 8.3%）', '队列尚余 5,286 个；当前有效资料共 6,267 个不同图片路径，另含来源图和新生成图，不与队列混算。'],
        ['同款归并', '252 组 / 831 条底层记录', '展示减少 579 张重复卡；原规格、报价和编号保留。229 个多规格组仍待逐瓶映射。'],
        ['客户海报', '当前 24 张', '首次 31 张，追加 10 张，再移除 17 张；缩略图和完整海报按权限展示。'],
        ['数据完整性', 'quick_check：ok / 外键错误：0', '本次只读检查通过；不代表已完成所有参数真实性、图片水印和全库同款人工审查。'],
        ['现网代码', d['release'], '截至网站源码 0998d42，三角色网关及公网 IP 登录、图片下载验收通过；本机公网域名仍连接重置。'],
    ]
    story.append(make_table(['指标', '当前结果', '说明'], rows, [90, 220, INNER - 310]))
    story.extend([Spacer(1, 12), p('完成状态说明', 'h1')])
    story.append(make_table(['状态', '汇报含义'], d['statusDefinitions'], [95, INNER - 95]))

    story.extend(section('三角色功能与建设边界', '当前可用功能与早期完整业务系统方案分开报告；上线不等于所有素材和参数均已整理完。'))
    story.append(make_table(['功能域', '已实现内容／当前行为', '完成情况与限制'], d['capabilities'], [100, 360, INNER - 460]))

    story.append(PageBreak())
    n = 0
    for phase in d['phases']:
        title = ('建设过程逐项更新表 / ' if n == 0 else '') + phase['title']
        story.extend([p(title, 'h1'), p(phase['range'] + '。' + phase['note'], 'noteKeep')])
        table_rows = []
        for date, item, action, status, source in phase['rows']:
            n += 1
            table_rows.append([date, f'{n:02d}  {item}', action, status, source.replace('/', '\n')])
        story.append(make_table([phase['title'][:2] + ' / 日期', '更新事项', '具体操作', '完成情况与核验', '依据'],
                                table_rows, [69, 135, 289, INNER - 544, 51], status_column=3))
        story.append(Spacer(1, 12))

    story.extend(section('尚未完成及下一步事项', '按实际状态列示，不把讨论、接口预留或代码存在写成正式完成。优先级为本报告建议，不代表新增任务已经执行。'))
    story.append(make_table(['建议优先级', '事项', '当前缺口／依据', '建议下一步'], d['pending'], [64, 139, 300, INNER - 503]))

    story.extend(section('Git 提交追踪附表', '覆盖网站源码 47fb32e 至 0998d42 的全部 37 个提交。时间是提交时间，不自动等于上线时间；实际上线情况以更新表和发布档案为准。'))
    commit_rows = []
    for i, (sha, date) in enumerate(commits, 1):
        meaning, kind = COMMIT_LABELS[sha]
        commit_rows.append([f'{i:02d}', date, sha, meaning, kind])
    story.append(make_table(['序号', '提交时间（2026）', '短哈希', '改动内容（中文整理）', '类型'],
                            commit_rows, [43, 123, 79, INNER - 352, 107], padding=4))

    story.extend(section('报告依据与可追溯说明', '正式工程为桌面“包材库”；“旧工程”指 Documents/Codex/2026-09-22/claude-code，仅用于回溯历史材料，不作为当前源码。'))
    story.append(make_table(['编号', '记录来源', '文件／范围'], d['sources'], [51, 160, INNER - 211], body_style='small'))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(OUTPUT), pagesize=landscape(A4),
                          leftMargin=MARGIN, rightMargin=MARGIN, topMargin=49, bottomMargin=47,
                          title=d['title'], author=d['company'], subject='内部汇报：建设过程、具体操作与完成情况',
                          creator='Yuanze packaging project report', pageCompression=1,
                          allowSplitting=True)
    frame = Frame(MARGIN, 47, INNER, HEIGHT - 96, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id='Report', frames=frame, onPage=page_header)])
    doc.build(story, canvasmaker=NumberedCanvas)
    print(json.dumps({'pdf': str(OUTPUT), 'milestones': steps, 'commits': len(commits)}, ensure_ascii=False))


if __name__ == '__main__':
    build()
