#!/usr/bin/env python3
"""Create the catalog report in real event order from a frozen sanitized dataset."""
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import BaseDocTemplate, Frame, LongTable, PageBreak, PageTemplate, Paragraph, Spacer, TableStyle

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs/包材库时间线汇报-20261013.json'
OUTPUT = ROOT / 'output/pdf/源泽包材库_时间线汇报_20260922-20261013.pdf'
FONT = '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
WIDTH, HEIGHT = landscape(A4)
MARGIN = 32
INNER = WIDTH - 2 * MARGIN
TEAL, INK, MUTED, LINE = [colors.HexColor(x) for x in ('#164B47', '#243D39', '#617770', '#CEDBD3')]
STYLES = {}


def p(text, style='body'):
    return Paragraph(escape(str(text)).replace('\n', '<br/>'), STYLES[style])


def stamp(value):
    return datetime.fromisoformat(value).strftime('%Y-%m-%d %H:%M:%S') if value else '未记录'


def hms(minutes):
    seconds = round(minutes * 60)
    return f'{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}'


def table(headers, rows, widths, padding=6):
    """Rows may contain paragraphs; keep each event or update row intact."""
    cells = [[p(x, 'header') for x in headers]]
    cells += [[x if isinstance(x, Paragraph) else p(x) for x in row] for row in rows]
    t = LongTable(cells, colWidths=widths, repeatRows=1, splitByRow=1, splitInRow=0, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TEAL),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F3F6F2')]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 11),
        ('TOPPADDING', (0, 0), (-1, -1), padding),
        ('BOTTOMPADDING', (0, 0), (-1, -1), padding),
        ('LINEBELOW', (0, 0), (-1, 0), .7, TEAL),
        ('LINEBELOW', (0, 1), (-1, -1), .35, LINE),
        ('BOX', (0, 0), (-1, -1), .5, LINE),
    ]))
    return t


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
            self.setFont('TimelineCJK', 8)
            self.setFillColor(MUTED)
            self.drawRightString(WIDTH - MARGIN, 22, f'{self._pageNumber} / {total}')
            super().showPage()
        super().save()


def decorate(c, doc):
    c.saveState()
    c.setFillColor(TEAL)
    c.rect(0, HEIGHT - 7, WIDTH, 7, stroke=0, fill=1)
    c.setFont('TimelineCJK', 9)
    c.drawString(MARGIN, HEIGHT - 27, 'YUANZE  /  广州源泽药业有限公司')
    c.setFillColor(MUTED)
    c.drawRightString(WIDTH - MARGIN, HEIGHT - 27, '包材库时间线汇报 · 内部资料')
    c.setStrokeColor(LINE)
    c.line(MARGIN, 39, WIDTH - MARGIN, 39)
    c.setFont('TimelineCJK', 8)
    c.drawString(MARGIN, 22, '2026-09-22 至 2026-10-13  |  北京时间  |  事件时间与截至状态分别列示')
    c.restoreState()


def summary(d):
    t = d['totals']
    rows = [
        ['时间线事件', f"{len(d['events'])} 条：{t['request_count']} 条需求／补充／重试记录，{t['commit_count']} 次代码提交，按秒排序"],
        ['关联更新与微调', f"{t['update_count']} 项完整列示。各项关联最早对应的需求，完成／上线状态截至统计截止，不冒充事件当时状态。"],
        ['记录覆盖', f"{t['primary_task_count']} 轮主任务、{t['recorded_days']} 个活动日期、{t['segment_count']} 段并行去重活动区间"],
        ['已记录执行与等待', f"{hms(t['deduplicated_minutes'])}（{t['deduplicated_hours']:.2f} 小时）；AI／工具运行及等待，不是员工实际人工工时。"],
        ['统计范围', '本机包材库主会话、明确关联的并行工程、子任务、工程档案与Git历史；不含独立ERP背景及本次报表制作。'],
    ]
    images = d.get('image_summary')
    if images:
        rows.insert(3, ['多个图片工程', '用户同时打开多个Codex工程，共用同一正式包材库站点。下文逐批标明主工程及bao、yue、du-qu等并行分工。'])
        rows.insert(4, ['核对图片产出', f"场景主图 {images['through_20261013_verified_style_versions']} 个合格版本；规格标注编辑 {images['spec_annotation_versions']} 个版本；合计 {images['through_20261013_verified_product_edit_versions_including_annotations']} 个包材图片制作／编辑版本，来源去重 {images['through_20261013_verified_product_edit_unique_sources_including_annotations']} 个。旧同步是开放客户权限，不是新增生成。"])
    story = [p('包材库建设与更新时间线', 'title'), p(d['period'] + '  |  截止 ' + stamp(d['as_of']) + ' 北京时间', 'subtitle'), Spacer(1, 12)]
    story.append(table(['汇报项目', '内容与口径'], rows, [112, INNER - 112], padding=7))
    story += [Spacer(1, 13), p('如何阅读时间线', 'heading')]
    for text in [
        '先按日期查看，再按HH:mm:ss追踪需求、确认、重试与提交。P为提示目的编号，T为任务编号，U为更新事项编号，E为时间线事件编号。',
        '需求事件时间为本机日志中的记录时间；代码提交时间为Git事件时间。二者均精确显示至秒，不据此虚构具体实施或上线时刻。',
        '每条需求列出其完整任务开始、结束与共享活动分钟。一个任务可能对应多条提示和多个成果，共享时长不能逐行相加。',
        '“关联成果”列逐项保留目的、操作、截至状态、结果与证据；该成果关联到需求，不代表在该秒已完成或已上线。',
        '跨任务或并行工程累计以去重活动区间为准。提交间隔、每日首末跨度、后台进程存活和无活动空档均不直接算工作时间。',
    ]:
        story += [p(text, 'note'), Spacer(1, 5)]
    story += [PageBreak(), p('统计口径与后续待办', 'title')]
    story.append(table(['序号', '时间及完成情况统计方法'], [[str(i), x] for i, x in enumerate(d['method_notes'], 1)], [45, INNER - 45], padding=3))
    story += [Spacer(1, 11), p('仍需补充或继续完善', 'heading')]
    for i, text in enumerate(d['pending'], 1):
        story += [p(f'{i}. {text}'), Spacer(1, 4)]
    return story


def task_cell(event):
    t = event.get('task')
    if not t:
        return '提交事件\n不作为工作起止或上线证明'
    minutes = t['execution_minutes']
    duration = '未记录' if minutes is None else f'{minutes:.2f} 分钟'
    return ('任务 ' + t['id'] + '\n开始 ' + stamp(t['start']) + '\n结束 ' + stamp(t['end']) +
            '\n共享活动 ' + duration + '\n' + t['lifecycle'])


def timeline(d):
    story = []
    events = {x['id']: x for x in d['events']}
    headers = ['事件时间／编号', '提示目的／模块', '任务起止／共享时长', '具体操作与核对依据', '截至状态与关联成果']
    widths = [82, 141, 157, 212, INNER - 592]
    for day in d['days']:
        group = [events[x] for x in day['event_ids']]
        counts = Counter(x['event_type'] for x in group)
        story += [PageBreak(), p(day['date'], 'date'), p('北京时间  |  当日 ' + str(len(group)) + ' 个事件：' + '、'.join(f'{k} {v} 条' for k, v in counts.items()), 'note'), Spacer(1, 7)]
        activity = day.get('activity_summary')
        if activity:
            story += [p('活动首末：' + stamp(activity['first']) + ' 至 ' + stamp(activity['last']) +
                        f"；去重 {activity['minutes']:.2f} 分钟。首末之间可能有停顿，不能直接相减作为当日投入。", 'note'), Spacer(1, 7)]
        if not group:
            story += [p('无新需求／提交，上一日任务跨日延续', 'heading')]
            segments = [x for x in d['segments'] if x['date'] == day['date']]
            rows = [[x['id'], stamp(x['start']), stamp(x['end']), f"{x['minutes']:.4f}", x['method']] for x in segments]
            story.append(table(['活动区间', '实际开始', '实际结束', '持续分钟', '核对口径'], rows, [80, 160, 160, 90, INNER - 490], padding=8))
            continue
        rows = []
        for e in group:
            clock = Paragraph(f'<font size="13" color="#164B47">{escape(e["clock"])}</font><br/>{escape(e["id"])}<br/>{escape(e["event_type"])}<br/>{escape(e.get("request_id") or e.get("commit_id") or "")}', STYLES['body'])
            project = ('\n\n工程：' + e['project_label'] + ('\n会话：' + e['project_session_short'] if e.get('project_session_short') else '')) if e.get('project_label') else ''
            batch = '\n批次：' + '、'.join(e.get('batch_ids', [])) if e.get('batch_ids') else ''
            rows.append([clock, e['purpose'] + project + batch, task_cell(e), e['operation'] + '\n\n依据：' + e['evidence'] + '\n' + e['time_basis'], e['status']])
            for u in e['updates']:
                task_id = e['task']['id'] if e.get('task') else ''
                rows.append([
                    p(u['id'] + '\n关联 ' + e['id'] + '\n' + (e.get('request_id') or '') + '\n需求时间共用', 'muted'),
                    u['module'] + '\n\n目的：' + u['purpose'],
                    '共用 ' + task_id + '\n不重复计时\n来源期：' + u['date'],
                    u['change'] + '\n\n依据：' + u['evidence'],
                    '关联成果（截至统计截止）\n' + u['status'] + '\n\n' + u['result'],
                ])
        story.append(table(headers, rows, widths))
    return story


def image_batch_appendix(d):
    batches = d.get('image_batches', [])
    if not batches:
        return []
    story = [PageBreak(), p('并行图片工程与逐批产出', 'title'),
             p('工程标签表示同一包材库网站内的职责分工；并行工作区间与每批产出分别记录。合格制作／发布版本不是全部生成尝试，同原图重做版本与独立原图数量不能混算。', 'note'), Spacer(1, 8)]
    rows = []
    for b in batches:
        def number(key):
            value = b.get(key)
            return '未独立核对' if value is None else str(value)
        timing = '开始 ' + stamp(b.get('first_started_at')) + '\n结束 ' + stamp(b.get('last_finished_at'))
        refs = '\n'.join(b.get('source_refs', []))
        safe_refs = '\n'.join(Path(x).name if x.startswith(('/Users/', '/var/', 'work/', 'docs/')) else x for x in refs.splitlines())
        overlap = '、'.join(b.get('overlaps_with', [])) or '无已核对重叠批次'
        rows.append([
            b['batch_id'] + '\n' + b['title'] + '\n类别：' + b['batch_kind'] + '\n工程：' + b['project_label'] + '\n会话：' + b.get('project_session_short', '') + '\n' + '、'.join(b.get('request_ids', [])) + '\n' + '、'.join(b.get('update_ids', [])),
            timing + '\n\n' + b['time_basis'],
            '合格制作／发布版本：' + number('produced_versions') + '\n新增独立原图：' + number('new_unique_sources') + '\n重做原图：' + number('reprocessed_sources') + '\n关联产品记录：' + number('product_associations'),
            b['status'] + '\n\n核对依据：' + b['number_basis'] + '\n核验时间：' + stamp(b.get('verification_time')) + ('\n' + safe_refs if safe_refs else ''),
            '工作区间重叠：' + overlap + '\n\n整批数量不能当作相交时段的即时产量。',
        ])
    story.append(table(['批次／分工工程', '真实关联工作起止', '产出数量与口径', '截至状态与核对依据', '并行关系'], rows, [155, 164, 135, 214, INNER - 668], padding=6))
    story += [PageBreak(), p('图片数量与重复统计口径', 'title')]
    im = d['image_summary']
    counts = [
        ['10-08七批场景主图快照', f"{im['through_20261008_batch_style_versions']} 个合格版本；{im['through_20261008_batch_style_unique_source_sha256']} 个不同源SHA；不含重试尝试"],
        ['10-10洗手液新增规格主图', f"{im['handwash_additional_style_versions_20261010']} 个版本，{im['handwash_additional_sources_20261010']} 个源图"],
        ['截至本报告场景主图', f"{im['through_20261013_verified_style_versions']} 个版本；{im['through_20261013_verified_style_unique_sources']} 个不同来源"],
        ['规格标注编辑', f"{im['spec_annotation_versions']} 个版本；为AI编辑，另列性质，不混称场景主图"],
        ['以上两类合格包材编辑总量', f"{im['through_20261013_verified_product_edit_versions_including_annotations']} 个制作／编辑版本；{im['through_20261013_verified_product_edit_unique_sources_including_annotations']} 个不同来源；不是全期所有AI资产或生成尝试总量"],
        ['10-08客户开放快照', f"{im['eight_batches_total_versions']} 个既有版本统一同步；{im['client_effective_images_snapshot_20261008']} 张有效客户图；同步不是新增生成，不称当前客户图总数"],
    ]
    story.append(table(['指标／时点', '数量与解释'], counts, [212, INNER - 212], padding=7))
    story += [Spacer(1, 12)]
    for i, text in enumerate(d.get('image_method_notes', []), 1):
        story += [p(f'{i}. {text}', 'note'), Spacer(1, 4)]
    operations = d.get('image_operations', [])
    if operations:
        story += [PageBreak(), p('其他图片与素材操作', 'title'), p('素材导入、删除、裁切、轮播与客户权限同步分别记录，不与场景主图产量相加。', 'note'), Spacer(1, 8)]
        rows = [[x['batch_id'] + '\n' + x['title'] + '\n' + x['batch_kind'], x['project_label'] + '\n会话：' + x.get('project_session_short', '') + '\n' + '、'.join(x.get('request_ids', [])),
                 '开始 ' + stamp(x.get('first_started_at')) + '\n结束 ' + stamp(x.get('last_finished_at')) + '\n' + x['time_basis'],
                 str(x.get('produced_versions')) + '\n' + x['status'], x['number_basis'] + '\n核验时间：' + stamp(x.get('verification_time'))] for x in operations]
        story.append(table(['操作／素材类别', '分工工程／提示', '真实关联工作起止', '操作数量／截至状态', '核对依据'], rows, [140, 147, 164, 171, INNER - 622], padding=6))
    windows = d.get('parallel_windows', [])
    if windows:
        story += [PageBreak(), p('同时打开工程的真实重叠时段', 'title'), p('下列为已记录的任务生命周期窗口相交，精确到北京时间日期与秒。没有逐张统计相交期间产量；整批张数和工作并集分别核对，不能重复累计并行投入。', 'note'), Spacer(1, 8)]
        rows = []
        for x in windows:
            for interval in x['intervals']:
                rows.append(['、'.join(x['batch_ids']) + '\n' + '\n'.join(x['projects']),
                             stamp(interval['start']), stamp(interval['end']), '、'.join(interval['tasks']), x['note']])
        story.append(table(['批次／同时运行工程', '重叠开始', '重叠结束', '关联任务', '交叠与产量统计边界'], rows, [192, 142, 142, 83, INNER - 559], padding=7))
    return story


def activity_appendix(d):
    story = [PageBreak(), p('按日活动时长核对', 'title'), p('日期与具体时间是时间线主框架；下表仅核对投入口径。首末跨度可能包含停顿，累计只按W区间并集。跨日午夜在所属日期记为24:00:00。', 'note'), Spacer(1, 8)]
    def clock(value):
        return datetime.fromisoformat(value).strftime('%H:%M:%S')
    def end(value, date):
        v = datetime.fromisoformat(value)
        return '24:00:00' if v.date().isoformat() != date and v.hour == v.minute == v.second == 0 else clock(value)
    rows = [[x['date'], clock(x['first']), end(x['last'], x['date']), str(x['request_count']), str(x['segment_count']), f"{x['minutes']:.2f}", hms(x['minutes'])] for x in d['daily']]
    t = d['totals']
    rows.append(['总计', '', '', str(t['request_count']), str(t['segment_count']), f"{t['deduplicated_minutes']:.2f}", hms(t['deduplicated_minutes'])])
    story.append(table(['日期', '首段开始', '末段结束', '提示数', '去重区间数', '去重分钟', '时:分:秒'], rows, [110, 110, 110, 80, 100, 120, INNER - 630], padding=4))
    story += [PageBreak(), p('完整去重活动时段', 'title'), p(str(len(d['segments'])) + '段W活动区间为唯一可加总时长口径。包含有明确起止的AI／工具处理与等待，排除无记录的空档；不是员工人工工时。任务起止精度统一为活动／工具区间核对；生命周期完整。', 'note'), Spacer(1, 8)]
    rows = [[x['id'], x['date'], clock(x['start']), end(x['end'], x['date']), f"{x['minutes']:.4f}", hms(x['minutes']), x['method']] for x in d['segments']]
    story.append(table(['区间', '日期', '开始', '结束', '分钟', '时:分:秒', '口径'], rows, [64, 90, 88, 88, 88, 90, INNER - 508], padding=5))
    return story


def build(data_path=DATA, output=OUTPUT):
    global STYLES
    d = json.loads(Path(data_path).read_text())
    pdfmetrics.registerFont(TTFont('TimelineCJK', FONT))
    pdfmetrics.registerFontFamily('TimelineCJK', normal='TimelineCJK', bold='TimelineCJK', italic='TimelineCJK', boldItalic='TimelineCJK')
    STYLES = {
        'body': ParagraphStyle('Body', fontName='TimelineCJK', fontSize=9.2, leading=12.6, textColor=INK, wordWrap='CJK', splitLongWords=True),
        'muted': ParagraphStyle('Muted', fontName='TimelineCJK', fontSize=9.2, leading=12.6, textColor=MUTED, wordWrap='CJK'),
        'header': ParagraphStyle('Header', fontName='TimelineCJK', fontSize=9.2, leading=12.6, textColor=colors.white, wordWrap='CJK'),
        'date': ParagraphStyle('Date', fontName='TimelineCJK', fontSize=23, leading=30, textColor=TEAL, spaceAfter=5, keepWithNext=True),
        'heading': ParagraphStyle('Heading', fontName='TimelineCJK', fontSize=12, leading=18, textColor=TEAL, spaceAfter=6, keepWithNext=True),
        'note': ParagraphStyle('Note', fontName='TimelineCJK', fontSize=9.3, leading=13.4, textColor=MUTED, wordWrap='CJK'),
        'title': ParagraphStyle('Title', fontName='TimelineCJK', fontSize=25, leading=33, textColor=TEAL, spaceAfter=9),
        'subtitle': ParagraphStyle('Subtitle', fontName='TimelineCJK', fontSize=11, leading=17, textColor=MUTED),
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(output), pagesize=(WIDTH, HEIGHT), title=d['title'], author='广州源泽药业有限公司', leftMargin=MARGIN, rightMargin=MARGIN, topMargin=47, bottomMargin=49)
    frame = Frame(MARGIN, 49, INNER, HEIGHT - 96, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id='timeline', frames=frame, onPage=decorate))
    doc.build(summary(d) + image_batch_appendix(d) + timeline(d) + activity_appendix(d), canvasmaker=NumberedCanvas)
    print(json.dumps({'output': str(output), 'events': len(d['events']), 'updates': sum(len(x['updates']) for x in d['events'])}, ensure_ascii=False))
    return output


if __name__ == '__main__':
    build()
