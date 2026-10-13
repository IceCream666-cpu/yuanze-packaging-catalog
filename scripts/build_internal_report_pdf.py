#!/usr/bin/env python3
"""Render the frozen, sanitized catalog work report; no live database or chat reads."""
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import BaseDocTemplate, Frame, LongTable, PageBreak, PageTemplate, Paragraph, Spacer, TableStyle

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs/包材库内部汇报-20261013.json'
OUTPUT = ROOT / 'output/pdf/源泽包材库_更新微调与工作时段汇报_20260922-20261013.pdf'
FONT = Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
WIDTH, HEIGHT = landscape(A4)
MARGIN = 32
INNER = WIDTH - 2 * MARGIN
TEAL = colors.HexColor('#164B47')
IVORY = colors.HexColor('#F7F4ED')
MIST = colors.HexColor('#E5EDE7')
INK = colors.HexColor('#243D39')
MUTED = colors.HexColor('#617770')
LINE = colors.HexColor('#CEDBD3')
WHITE = colors.white
STYLES = {}
REPORT = {}


def compact(value):
    return re.sub(r'\s+', '', str(value))


def local_time(value, date=True):
    if not value:
        return '未记录'
    stamp = datetime.fromisoformat(value)
    return stamp.strftime('%m-%d\n%H:%M:%S') if date else stamp.strftime('%H:%M:%S')


def minute_label(value):
    return '未记录' if value is None else f'{value:.2f}'


def local_span(start, end):
    """Two fully dated lines, in start/end order, avoid repeated four-line labels."""
    def stamp(value):
        return datetime.fromisoformat(value).strftime('%m-%d %H:%M:%S') if value else '未记录'
    return stamp(start) + '\n' + stamp(end)


def day_end(value, day):
    """A split interval ending at the next midnight is 24:00 of its report day."""
    dt = datetime.fromisoformat(value)
    if dt.date().isoformat() != day and dt.hour == dt.minute == dt.second == 0:
        return '24:00:00'
    return local_time(value, date=False)


def hours_label(value):
    return '未记录' if value is None else f'{value / 60:.2f} 小时'


def hms(value):
    seconds = round(value * 60)
    return f'{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}'


def p(text, style='body'):
    return Paragraph(escape(str(text)).replace('\n', '<br/>'), STYLES[style])


def coloured(text, style='body'):
    safe = escape(str(text)).replace('\n', '<br/>')
    colour = '#164B47' if str(text).startswith(('已上线', '已完成', '本轮结束')) else '#936C46'
    return Paragraph(f'<font color="{colour}">{safe}</font>', STYLES[style])


def table(headers, rows, widths, coloured_columns=(), font='body', padding=6):
    cells = [[p(h, 'header') for h in headers]]
    cells.extend([[coloured(v, font) if i in coloured_columns else p(v, font)
                   for i, v in enumerate(row)] for row in rows])
    result = LongTable(cells, colWidths=widths, repeatRows=1, hAlign='LEFT', splitByRow=1, splitInRow=1)
    result.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TEAL),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, colors.HexColor('#F3F6F2')]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        # CJK line breaking can hang final punctuation by one glyph. Reserve a
        # full glyph at the right edge rather than letting it cross the frame.
        ('RIGHTPADDING', (0, 0), (-1, -1), 11),
        ('TOPPADDING', (0, 0), (-1, -1), padding),
        ('BOTTOMPADDING', (0, 0), (-1, -1), padding),
        ('LINEBELOW', (0, 0), (-1, 0), .7, TEAL),
        ('LINEBELOW', (0, 1), (-1, -1), .35, LINE),
        ('BOX', (0, 0), (-1, -1), .5, LINE),
    ]))
    return result


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.saved_pages = []

    def showPage(self):
        self.saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self.saved_pages)
        for state in self.saved_pages:
            self.__dict__.update(state)
            self.setFont('ReportCJK', 8)
            self.setFillColor(MUTED)
            self.drawRightString(WIDTH - MARGIN, 22, f'{self._pageNumber} / {total}')
            super().showPage()
        super().save()


def decorate(c, doc):
    c.saveState()
    c.setFillColor(TEAL)
    c.rect(0, HEIGHT - 7, WIDTH, 7, fill=1, stroke=0)
    c.setFont('ReportCJK', 9)
    c.drawString(MARGIN, HEIGHT - 27, 'YUANZE  /  广州源泽药业有限公司')
    c.setFillColor(MUTED)
    c.drawRightString(WIDTH - MARGIN, HEIGHT - 27, '包材库更新、微调与工作时段 · 内部汇报')
    c.setStrokeColor(LINE)
    c.line(MARGIN, 39, WIDTH - MARGIN, 39)
    c.setFont('ReportCJK', 8)
    c.drawString(MARGIN, 22, '2026-09-22 至 2026-10-13  |  北京时间  |  执行时长不等于人工工时')
    c.restoreState()


def section(title, note='', new_page=True):
    story = [PageBreak()] if new_page else []
    story.append(p(title, 'heading'))
    if note:
        story.extend([p(note, 'note'), Spacer(1, 7)])
    return story


def summary(d):
    t = d['totals']
    result = [p('包材库更新、微调与工作时段汇报', 'title'),
              p(d['period'] + '  |  截止 ' + datetime.fromisoformat(d['as_of']).strftime('%m-%d %H:%M:%S') + ' 北京时间', 'subtitle'),
              Spacer(1, 11)]
    rows = [
        ['更新与微调', f"{t['update_count']} 项，按目的、操作、结果、状态和关联任务逐项列示"],
        ['用户提示目的', f"{t['request_count']} 条，含补充、确认、重试与状态查询；不导出原始聊天"],
        ['工作记录', f"{t['primary_task_count']} 个主任务、{t['subtask_count']} 个关联子任务，{t.get('included_session_count', t['related_session_count'])} 个实际计入会话"],
        ['可观测活动时长', f"{t['deduplicated_hours']:.2f} 小时（{hms(t['deduplicated_minutes'])}），覆盖 {t['recorded_days']} 个有记录日期、{t['segment_count']} 段去重活动区间"],
        ['工程与发布依据', f"{t['commit_count']} 个提交；冻结至 {d['source_head'][:7]}；最新核验发布 {d['production_evidence']}"],
        ['统计范围', d['scope']],
    ]
    result.append(table(['项目', '汇报口径'], rows, [112, INNER - 112], padding=7))
    audit = []
    if t.get('lifecycle_calendar_union_minutes') is not None:
        audit.append('生命周期窗口并集 ' + hours_label(t['lifecycle_calendar_union_minutes']) + '：含无活动空档，仅为日历跨度辅助上界。')
    if t.get('long_tool_wait_union_minutes') is not None:
        audit.append('其中有明确起止的长工具处理／等待区间并集 ' + hours_label(t['long_tool_wait_union_minutes']) + '：已包含在主活动指标内，不再相加。')
    if audit:
        result.extend([Spacer(1, 8)] + [p(x, 'note') for x in audit])
    result.extend([Spacer(1, 12), p('阅读方法', 'subheading')])
    for text in [
        'U编号是更新事项；P编号是用户提示目的；T编号是同一轮主任务；W编号是并行去重、按北京时间跨午夜拆开的执行区间。',
        '同一T可能同时覆盖多个U/P。U、P行显示的是共享任务时长，不能跨行相加。唯一可加总口径为W区间及其按日汇总。',
        '主指标为可观测活动及明确持续的工具处理／等待区间。生命周期起止之间可能存在数小时空档，不能把全部跨度直接计为工作；这里也没有员工实际人工计时数据。',
        '更新来源期与执行事件时间是两种证据。早期资料缺精确事件时不从Git提交差、日期跨度或上线时间倒推时长。',
    ]:
        result.append(p(text, 'note'))
        result.append(Spacer(1, 4))
    result.extend(section('统计方法与完成边界', new_page=True))
    result.append(table(['序号', '时间及状态统计方法'], [[str(i), x] for i, x in enumerate(d['method_notes'], 1)], [45, INNER - 45], padding=3))
    result.extend([Spacer(1, 12), p('仍需补充或继续完善', 'subheading')])
    for i, text in enumerate(d['pending'], 1):
        result.append(p(f'{i}. {text}', 'body'))
        result.append(Spacer(1, 4))
    result.extend([Spacer(1, 8), p('本报告没有重新读取当前生产数据库。旧统计只作为带日期的历史证据；完成状态以项目档案和对应发布核验为准。', 'note')])
    return result


def updates(d):
    story = section('一、全部更新与微调', f"完整 {len(d['updates'])} 项。来源期为资料归属日期；相关T见工作记录。缺事件部分未补推时长。")
    rows = []
    for x in d['updates']:
        rows.append([
            x['id'] + '\n' + x['date'],
            x['module'] + '\n\n目的：' + x['purpose'],
            x['change'],
            x['status'] + '\n\n' + x['result'],
            '、'.join(x['task_ids']) + ('\n共享 ' + minute_label(x['shared_execution_minutes']) + ' 分钟' if x['shared_execution_minutes'] is not None else '\n时长未记录'),
            x['evidence'],
        ])
    widths = [73, 143, 169, 196, 82, INNER - 663]
    story.append(table(['事项／来源期', '模块与提示目的', '具体操作', '完成情况与结果', '关联任务／共享时长', '核对依据'], rows, widths, coloured_columns=(3,), padding=6))
    return story


def requests(d):
    tasks = {x['id']: x for x in d['tasks']}
    story = section('二、完整用户提示目的与工作时段', f"完整 {len(d['requests'])} 条。需求记录时间为本机日志写入的时间，未必等同人工发送瞬时。提示目的已脱敏概括；同一任务共用执行窗口，持续分钟不能逐行相加。")
    rows = []
    for x in d['requests']:
        t = tasks[x['task_id']]
        timing = local_span(t['start'], t['end'])
        rows.append([x['id'] + '\n' + x['kind'], local_time(x['time']), x['purpose'], x['task_id'], timing,
                     minute_label(t['execution_minutes']), t['basis'] + '\n' + t['lifecycle']])
    story.append(table(['目的编号／类型', '需求记录时间', '目的与微调要求', '共享任务', '任务开始→结束（北京时间）', '共享活动分钟', '记录精度／轮次状态'],
                       rows, [72, 76, 252, 52, 132, 72, INNER - 656], padding=5))
    story.extend([Spacer(1, 9), p('“本轮结束”只是任务生命周期结束，不能代替功能交付状态。U表中的完成／上线结论另以档案、代码和核验回执确认。', 'note')])
    return story


def timing(d):
    story = section('三、按日可观测活动汇总（唯一加总口径）', '汇总主会话、子任务与并行工程的活动区间并集；每日首末时间之间可能有停顿，不能把首末跨度当作当日投入。次日午夜记为当日24:00。')
    rows = [[x['date'], local_time(x['first'], date=False), day_end(x['last'], x['date']), str(x['request_count']), str(x['segment_count']),
             f"{x['minutes']:.2f}", hms(x['minutes']), '、'.join(x['segment_ids'])] for x in d['daily']]
    t = d['totals']
    rows.append(['总计', '', '', str(t['request_count']), str(t['segment_count']), f"{t['deduplicated_minutes']:.2f}", hms(t['deduplicated_minutes']), '仅按W区间加总'])
    story.append(table(['日期', '首段开始', '末段结束', '提示数', '区间数', '去重分钟', '时:分:秒', '对应去重区间'], rows, [85, 78, 78, 50, 50, 80, 87, INNER - 508], padding=6))
    story.extend(section('四、全部去重可观测活动区间', f"完整 {len(d['segments'])} 段。包含关联子任务有证据的延续活动，已经合并全部重叠区间。跨日按午夜分段，W持续分钟可加总。生命周期长空档不直接计入。"))
    spans = [[x['id'], x['date'], local_time(x['start'], False), day_end(x['end'], x['date']), f"{x['minutes']:.4f}", hms(x['minutes']), x['method']] for x in d['segments']]
    story.append(table(['区间编号', '日期', '开始', '结束', '持续分钟', '时:分:秒', '去重口径'], spans, [66, 90, 90, 90, 85, 90, INNER - 511], padding=5))
    exceptions = [x for x in d['tasks'] if x['lifecycle'] != '本轮结束' or '生命周期完整' not in x['basis'] or (x.get('unobserved_gap_minutes') or 0) > 5]
    story.extend(section('五、中断、空档与缺失记录审计', f"共 {len(exceptions)} 个主任务有中断、缺终止、观测范围或超过5分钟的无活动空档。系统运行记录、生命周期跨度与主活动分钟分别列示，不做混合加总。"))
    rows = []
    for x in exceptions:
        rows.append([x['id'] + '\n' + ('、'.join(x['request_ids']) or '延续任务'), x['purpose'],
                     local_span(x['start'], x['end']) + '\n跨度 ' + minute_label(x['elapsed_minutes']) + ' 分钟',
                     minute_label(x['execution_minutes']), minute_label(x.get('recorded_runtime_minutes')),
                     minute_label(x.get('unobserved_gap_minutes')), x['basis'] + '\n' + x['lifecycle']])
    if rows:
        story.append(table(['任务／提示', '工作目的', '生命周期窗口／跨度', '主活动分钟', '系统运行记录分钟', '排除无活动空档分钟', '记录精度／轮次状态'],
                           rows, [79, 220, 136, 74, 74, 76, INNER - 659], padding=6))
    else:
        story.append(p('没有符合本节条件的主任务。', 'body'))
    return story


def evidence(d):
    story = section('六、资料来源与提交事件', '提交时间仅证明提交事件，不用来计算持续时间。详细原始记录在本机保留；本报告不公开账号、密码、密钥、原文报价或私有连接路径。')
    story.append(table(['来源编号', '资料名称', '核对方式'], [[x['id'], x['title'], x['detail']] for x in d['source_registry']], [70, 245, INNER - 315], padding=7))
    story.extend([Spacer(1, 12), p('完整冻结提交记录', 'subheadingLoose')])
    rows = [[x['id'], datetime.fromisoformat(x['time']).strftime('%m-%d %H:%M:%S'), x['subject']] for x in d['commits']]
    story.append(table(['提交', '提交时间（北京时间）', '记录摘要'], rows, [90, 140, INNER - 230], padding=5))
    return story


def build(data_path=DATA, output=OUTPUT):
    global STYLES, REPORT
    REPORT = json.loads(Path(data_path).read_text())
    pdfmetrics.registerFont(TTFont('ReportCJK', str(FONT)))
    pdfmetrics.registerFontFamily('ReportCJK', normal='ReportCJK', bold='ReportCJK', italic='ReportCJK', boldItalic='ReportCJK')
    STYLES = {
        'body': ParagraphStyle('ReportBody', fontName='ReportCJK', fontSize=9.2, leading=12.6, textColor=INK, wordWrap='CJK', splitLongWords=True),
        'header': ParagraphStyle('ReportHeader', fontName='ReportCJK', fontSize=9.2, leading=12.6, textColor=WHITE, wordWrap='CJK'),
        'heading': ParagraphStyle('ReportHeading', fontName='ReportCJK', fontSize=17, leading=24, textColor=TEAL, spaceAfter=8, keepWithNext=True),
        'subheading': ParagraphStyle('ReportSubheading', fontName='ReportCJK', fontSize=12, leading=18, textColor=TEAL, spaceAfter=6, keepWithNext=True),
        'subheadingLoose': ParagraphStyle('ReportSubheadingLoose', fontName='ReportCJK', fontSize=12, leading=18, textColor=TEAL, spaceAfter=6, keepWithNext=False),
        'note': ParagraphStyle('ReportNote', fontName='ReportCJK', fontSize=9.3, leading=13.5, textColor=MUTED, wordWrap='CJK'),
        'title': ParagraphStyle('ReportTitle', fontName='ReportCJK', fontSize=25, leading=34, textColor=TEAL, spaceAfter=8),
        'subtitle': ParagraphStyle('ReportSubtitle', fontName='ReportCJK', fontSize=11, leading=17, textColor=MUTED),
    }
    story = summary(REPORT) + updates(REPORT) + requests(REPORT) + timing(REPORT) + evidence(REPORT)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(output), pagesize=(WIDTH, HEIGHT), title=REPORT['title'], author='广州源泽药业有限公司',
                          leftMargin=MARGIN, rightMargin=MARGIN, topMargin=47, bottomMargin=49)
    frame = Frame(MARGIN, 49, INNER, HEIGHT - 96, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id='report', frames=frame, onPage=decorate))
    doc.build(story, canvasmaker=NumberedCanvas)
    print(json.dumps({'output': str(output), 'update_count': len(REPORT['updates']), 'request_count': len(REPORT['requests']),
                      'interval_count': len(REPORT['segments'])}, ensure_ascii=False))
    return output


if __name__ == '__main__':
    build()
