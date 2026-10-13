#!/usr/bin/env python3
"""Curate report data from private inventory and session evidence; never export raw chats."""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'work/internal-report-20261013'
OUTPUT = ROOT / 'docs/包材库内部汇报-20261013.json'
BJT = timezone(timedelta(hours=8))
SOURCE_HEAD = '15e1550acc95b2435ba0d6c9061c7419710b57e6'

# Purpose summaries, not prompt quotations. Account names, passwords, tokens and
# full source attachments are intentionally absent, including credential-only replies.
PURPOSES = {
13:'设计内部包材库框架、检索与分类，等待补充素材',14:'确认员工能看采购成本、供应商及套装组合；讨论样品管理',
15:'接入已提供的阿里云服务器',16:'准备服务器登录和接口配置',17:'确认服务器登录身份',18:'确认服务器连接准备状态',19:'接管Chrome操作运行中的服务器',20:'确认公钥授权已完成',
21:'讨论公司内部网站使用指定域名',22:'确认尚未购买域名',23:'寻求免费域名建议',24:'确定让公司员工使用系统的最简部署方案',
25:'整理新增图册、原产品表及核心包材字段，缺失留空',26:'确认同系列每个规格单独存档；客户隐藏供应商与采购价',27:'参考分类图优化材质、瓶型、规格及检索',28:'增加上传图片寻找相似包材功能',29:'确认搜图优先瓶型与结构，颜色印刷次之',30:'暂不录入浮动印刷费用，后续提供标准',31:'建立管理员信息维护系统',32:'确认独立管理员账号，员工仅查询',33:'重试管理员功能建设任务',34:'再次重试中断任务',35:'评估剩余额度及工程适用模型',36:'导入当日素材，增加分类侧栏并部署更新',
37:'重试素材整理与部署',38:'再次重试未完成任务',39:'判断失败是否由网络引起',40:'再次尝试继续处理',41:'整理三端网址及登录方式',42:'优化翻页过渡和每页数量选择',43:'增加跳页、稳定产品编号、编号表及精确编号搜索',44:'诊断用户也无法打开网站的问题',45:'确认远程控制已登录，可继续故障排查',46:'确认远程控制已在本机Chrome打开',47:'维护表附对应图片、无图标注及后续整理字段',48:'确认维护表需支持批量更新网站',49:'统一登录链接，按员工与管理员账号进入不同角色',
50:'接入DeepSeek辅助审查网站',51:'选择DeepSeek网页登录方式进行审查',52:'确认已在Safari登录DeepSeek',53:'讨论用API接入指定DeepSeek模型与代理工具',54:'确认接入当前Codex工具',55:'打开本机密钥填写目录',56:'确认本机密钥已填写',57:'确认API来自DeepSeek官方开放平台',58:'补充接口配置准备信息',59:'阅读Safari中的接入教程并配置',60:'确认API账户已充值',61:'另一工程审查包材库文档与功能，排除幻觉并完善',62:'切换回GPT模型',63:'复核DeepSeek改动并查漏补缺',
64:'审查九宫格、整页参考图，按具体包材区分项目',65:'精简主导航，增加护理部位与面膜分区',66:'删除确实无图产品、归纳明确参数，并按品牌草图美化UI动效',67:'明确仅删除原表无图项目，保留有图待细分项目',68:'增加侧栏显示与关闭按钮',69:'修复管理员账号不能登录',70:'分区与搜索打通，扩充用途、多选条件、多图与价格栏目',71:'排查其他手机电脑账号登录失败',72:'补充失败设备使用的登录入口和角色',73:'调整员工登录凭据，验证浏览器；跳过微信验证',74:'调整管理员登录凭据',75:'排查管理员凭据同步并实际浏览器验证',76:'更正管理员登录凭据',77:'诊断员工网络错误并接入公司域名',78:'区分域名状态是否影响内部跳转',79:'全面筛查频繁登录故障并修复根源',80:'取消任意员工数量限制，核对管理员能独立建号',81:'建立客户角色，隐藏供应商和采购价',82:'评估去水印图片处理、预计用量及模型',83:'要求先报告图片处理评估，再决定是否执行',84:'补充模型及剩余用量情况',85:'评估Safari网页模式能否免额度处理图片',86:'暂缓图片处理，先完成客户界面预览',87:'复制项目到桌面并初始化Git、规则、测试和提交',88:'确认现工程复制到桌面正式目录',89:'盘点后端数据库并比较Sites替代可能',90:'确认优先整理现有后端，说明三种工具使用方案',91:'评估DeepSeek能否替代当前模型',92:'恢复丰富客户选型界面，三端增加中英文切换',93:'讨论手机客户独立展厅设计',94:'确认客户登录后查看、源泽整体业务及专属业务员联系方向',95:'确认多款意向清单及统一接待兜底方向',
96:'说明另一台设备继续网站编辑的交接方法',97:'把当前工程纳入Git备份',98:'增加真实展厅、公司前台和公司中英文介绍',99:'增加ISO与GMPC中英文证书展示',100:'重试客户素材展示任务',101:'客户底栏首页、产品、联系独立分页；产品隐藏供应商价格',102:'再次明确客户独立分页与安全选型要求',103:'建立两端维护档案并发布客户更新，核对PC与手机一致性',104:'确认PC宽版顶部导航，手机底栏，多列响应式产品',105:'产品区增加海报，先展示海报再进入包材选择',
106:'讨论更符合直觉的侧栏检索顺序',107:'确认用途与参数两种入口及系列卡片展示方向',108:'用途标签后补，要求增加用途筛选',109:'澄清已有用途项，要求读取数据分析侧栏分类',110:'暂停分类讨论，转向参考图风格的主图优化',111:'确认统一场景与光线，保留原材质颜色瓶型',112:'授权批量美化、去水印并直接上线',113:'将待核对图片也纳入优化范围',114:'提出全库八千多张图片的优化目标',115:'执行前评估用量是否足够及推荐模型',116:'继续处理200张图片并上线',117:'检查已完成与未完成图片任务，继续处理',118:'另一工程读取包材库并确认可编辑范围',119:'另一工程按不同顺序处理图片，避开原工程占用',120:'跨工程检查重复图片',121:'确认批次是否已上线',122:'排除另一工程重复，继续50张优化图片',123:'另一工程准备向客户海报区添加素材',124:'确认先审查现状再补充素材',125:'补充海报图片素材',126:'另一工程合并同款多规格并标规格，审查重复图',127:'把搜索项“容量”改成“规格”',128:'另一工程讨论简洁侧栏，把琐碎条件放入搜索',129:'确认侧栏只保留大类，细项使用搜索',130:'明确按身体、面部、头部分类，具体用途后补',131:'删除指定样式的同系列模特海报',132:'核对另一工程图片修改是否已上线',133:'公司业务标签改为OEM、ODM、OBM、Private Label',134:'发布公司业务标签到客户网站',135:'另一工程要求同步客户包材优化图片',136:'配置本地所有已提交包材库更新自动上传私有GitHub',137:'设计五张客户产品轮播背景图比例',138:'检查同款不同规格是否都能检索',139:'另一工程要求两端图片开放下载',140:'询问当前会话能否制作轮播海报',141:'再次检查多规格对应搜索',142:'重试轮播海报制作',143:'咨询多规格整理使用模型',144:'再次尝试多规格搜索核验',145:'开放客户端与业务端授权图片下载',146:'继续请求制作客户轮播海报',147:'明确轮播构图留白、Logo与系列名，并补充精修素材',148:'制作从搭建至当时的完整建设更新PDF汇报',
149:'确认轮播效果并要求上线',150:'检查此前本机DeepSeek API配置是否仍保存',151:'继续当日包材主图优化',152:'确认本轮处理50张',153:'继续核对多规格检索',154:'检查所有并行工程图片是否完整同步客户',155:'核对是否迁入新服务器及当前服务器信息',156:'管理员采用业务目录布局，支持原位编辑及新增产品',157:'先讨论管理员修改方案',158:'确认在原产品详情直接编辑与保存',159:'制作管理员前端Demo预览',160:'批准按管理员Demo正式上线',161:'补充服务器连接准备信息',162:'确认连接配置准备情况',163:'判断是否需要重新连接服务器',164:'统一上传未同步和部分同步的跨工程图片',165:'设置下次产品明细调整和实拍搜图优化待办提醒',166:'确认已打开远程控制以协助恢复连接',167:'补充远程控制登录准备信息',168:'诊断手机业务端与客户端产品图片加载慢',169:'补充使用手机4G／5G网络条件',170:'确认最慢阶段是登录后产品列表及图片',171:'按诊断顺序优化移动端及服务器响应',172:'查看已设置的待办提醒',173:'再次检查客户界面加载慢',174:'明确首页及海报是主要慢点',175:'讨论并优化服务器传输算法',176:'提供手动打开网址的审查协助',177:'按实际瓶与膏霜罐区分同图产品，系列内汇总各规格',178:'要求从原产品图册查缺失参数，禁止仅凭图片猜测',179:'制作紧凑详情Demo：裸瓶价、材质、规格、MOQ、货期、用途、工艺',180:'确认工艺可估算后补真实标准，客户不展示内部信息',181:'批准详情Demo正式上线，核对批量删改及工艺改价能力',182:'确认真实工艺价格表后补',183:'要求按已批准Demo格式部署',184:'核对业务端供应商信息是否保留',185:'合并250／500mL洗手液系列，独立裸瓶价和规格图片联动、翻页提示',186:'将所有已标注价格归入标准价格字段',187:'明确普通参考价即裸瓶价',188:'讨论适合不专业员工寻找精华包材的检索方式',189:'确认先展示候选，再用图片和简单问题缩小范围',190:'为包材整理常见多用途，避免重复分类过多',191:'确认来源明确用途与结构参考用途分开标示',192:'修复实拍图能上传但匹配不相似的问题',193:'确认失败发生在结果匹配而非上传',194:'要求全链路筛查各种可能问题并优化',195:'增加查看高清原图按钮，改善点击下载响应'
}

# Links mean the same task covered these updates; durations are shared and are
# never summed across update rows. No claim of exclusive per-feature time allocation.
UPDATE_REQUESTS = {
1:[13,25],2:[14,26,27],3:[25],4:[15,19,20],5:[31,32],6:[28,29],7:[25,36],8:[25,36],9:[27,36,70],10:[36],11:[36],12:[42,43],13:[44,45,46],14:[44,45],15:[43],16:[43],17:[43,47,48],18:[49],19:list(range(50,61)),20:[61,63],21:[61,63],22:[63],23:[64],24:[66,67],25:[66],26:[66],27:[65,70],28:[68],29:[70],30:[70],31:[70],32:[70],33:[69,71,73,74,75,76],34:[77,78],35:[79],36:[79],37:[80],38:[81,86],39:[87,88],40:[89,90],41:[92],42:[96,97],43:[98],44:[99],45:[101,102],46:[103,104],47:[105],48:[105],49:[93,94,95,101,102],50:[110,111,114,115],51:[112,113],52:[119,120],53:[116,117],54:[119,132],55:[122],56:[135],57:[120],58:[123,125],59:[127],60:[126],61:[126],62:[133,134],63:[131],64:[136],65:[136],66:[145],67:[145],68:[145],69:[148],70:[148],71:[138,141,144,153],72:[156,158,160],73:[128,129,130,156],74:[156,160],75:[153,156],76:[160],77:[156,160],78:[151,152],79:[154,164],80:[154,164],81:[137,146,147,149],82:[161,163,166,167],83:[168,169,170],84:[171],85:[171],86:[171],87:[171],88:[173,174],89:[173,174],90:[173],91:[175,176],92:[177,178],93:[178],94:[179,180],95:[181,183],96:[181],97:[180,181,182],98:[184],99:[185],100:[185],101:[186,187],102:[188,189,190],103:[190,191],104:[190,191],105:[192,193,194],106:[192,194],107:[192,194],108:[192,194],109:[192,194],110:[192,194],111:[195],112:[195],113:[195],114:[195]
}


def merge_intervals(intervals):
    out = []
    for a, b in sorted(intervals):
        if b <= a:
            continue
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def instant(value):
    return datetime.fromisoformat(value).timestamp() if value else None


def iso(epoch):
    return datetime.fromtimestamp(round(epoch * 1000) / 1000, BJT).isoformat(timespec='milliseconds')


def observed_spans(turn):
    """Use source epoch intervals, not the rounded second-only display columns."""
    return [[iso(a),iso(b)] for a,b in turn['execution_intervals_epoch'] if b > a]


def minutes(intervals):
    return sum(b - a for a, b in merge_intervals(intervals)) / 60


def safe_evidence(row):
    commits = sorted(set(re.findall(r'\b[0-9a-f]{7}\b', ' '.join(row['evidence']))))
    labels = []
    if int(row['id'][1:]) <= 69:
        labels.append('10-07建设日志／' + row.get('phase', '').split(' ', 1)[-1])
    if '客户端档案' in str(row['evidence']): labels.append('客户端维护档案')
    if '业务端档案' in str(row['evidence']): labels.append('业务端维护档案')
    if '搜图优化' in str(row['evidence']): labels.append('10-10搜图专项档案')
    if '手机端加载' in str(row['evidence']): labels.append('10-09移动性能档案')
    if any('deployment-result' in x or 'activation' in x for x in row['evidence']): labels.append('发布验收回执')
    if any('verification' in x or '核验' in x for x in row['evidence']): labels.append('专项核验记录')
    if not labels: labels.append('项目专项档案／核验记录')
    if commits: labels.append('提交 ' + '、'.join(commits))
    return '；'.join(dict.fromkeys(labels))


def build():
    inv = json.loads((INPUT / 'update_inventory.json').read_text())
    timing = json.loads((INPUT / 'session_turns.json').read_text())
    method = json.loads((INPUT / 'timing_method.json').read_text())
    all_turns = [x for x in timing['turns'] if x.get('included_in_historical_totals')]
    main = [x for x in all_turns if not x['is_subagent']]
    main.sort(key=lambda x: x.get('start_epoch') or x.get('end_epoch') or 0)
    # Session + turn is the identity: inherited event IDs in forked histories are not unique alone.
    turn_map = {}
    tasks = []
    for n, t in enumerate(main, 1):
        uid = f'T{n:03d}'
        turn_map[(t['session_id'], t['id'])] = uid
        own_requests = [r for r in t['user_requests'] if r.get('included_in_historical_report') and int(r['request_id'][1:]) >= 13]
        ids = [r['request_id'] for r in own_requests]
        labels = [PURPOSES[int(r['request_id'][1:])] for r in own_requests]
        task = {'id':uid,'purpose':'；'.join(labels) or '延续已授权包材库任务／状态核验', 'request_ids':ids,
                'start':t['start_bjt'],'end':t['end_bjt'],'elapsed_minutes':t['elapsed_minutes'],
                'execution_minutes':t['execution_minutes_before_cross_turn_dedup'],
                'recorded_runtime_minutes':t.get('recorded_runtime_minutes'),
                'unobserved_gap_minutes':t.get('unobserved_gap_minutes'),
                'long_tool_wait_minutes':t.get('long_tool_wait_minutes'),
                'explicit_wait_minutes':t['excluded_explicit_input_wait_minutes'],
                'basis':'活动／工具区间核对；生命周期完整' if t.get('start_line') and t.get('end_line') else '活动／工具区间核对；生命周期缺事件',
                'lifecycle':{'complete':'本轮结束','aborted':'本轮中断'}.get(t['lifecycle_status'],'缺终止记录'),
                'intervals':observed_spans(t),
                'source':{'session_id':t['session_id'],'turn_id':t['id'], 'start_line':t.get('start_line'), 'end_line':t.get('end_line')}}
        tasks.append(task)
    by_task = {x['id']:x for x in tasks}
    requests=[]
    for r in timing['user_requests']:
        i = int(r['request_id'][1:])
        if not r.get('included_in_historical_report') or i < 13: continue
        if i not in PURPOSES: raise ValueError(f'Uncurated request P{i:03d}')
        task_id = turn_map.get((r['session_id'], r['turn_id']))
        if not task_id: raise ValueError(f'Request without scoped task: {r["request_id"]}')
        requests.append({'id':r['request_id'],'time':r['timestamp_bjt'],'purpose':PURPOSES[i],
                         'kind':'补充／确认' if r['is_followup_or_confirmation'] else ('重试／查询' if any(k in PURPOSES[i] for k in ('重试','再次尝试','核对是否','检查是否','查看已')) else '需求／调整'),
                         'task_id':task_id,'source':{'session_id':r['session_id'],'event_line':r['line']}})
    by_request = {int(x['id'][1:]):x for x in requests}
    updates=[]
    for row in inv['rows']:
        i = int(row['id'][1:])
        task_ids=list(dict.fromkeys(by_request[p]['task_id'] for p in UPDATE_REQUESTS[i] if p in by_request))
        intervals=[(instant(a),instant(b)) for k in task_ids for a,b in by_task[k]['intervals']]
        intervals=merge_intervals(intervals)
        # Exact task clocks are visible in the work table; missing events remain unknown, never zero-filled.
        shared_duration=round(minutes(intervals),4) if intervals else None
        result = row['result']
        change = row['change']
        if i == 34:
            result = '当时域名接入尚未解决；后续客户展厅于10-04上线，10-13正式域名三角色及客户高清浏览器验证已通过。域名早期状态不代表当前故障。'
        if i == 99:
            change = '两记录归一系列，250mL／500mL切换独立产品编号、对应裸瓶价和主图；从原对照图左／右分别制作规格图，旧图保留内部。'
        updates.append({'id':row['id'],'date':row['date_or_range'],'module':row['module'],
                        'purpose':row['purpose'],'change':change,'result':result,'status':row['status'],
                        'evidence':safe_evidence(row),'request_ids':[f'P{x:03d}' for x in UPDATE_REQUESTS[i]],
                        'task_ids':task_ids,'shared_execution_minutes':shared_duration,
                        'time_note':'关联任务共享时长，不能跨事项相加；缺事件部分未补推',
                        'source_refs':row['evidence'], 'historical_snapshot':i <= 69})
    intervals=[]
    for t in all_turns:
        intervals += [(instant(a), instant(b)) for a,b in observed_spans(t)]
    merged=merge_intervals(intervals)
    days={}
    for a,b in merged:
        while a < b:
            day = datetime.fromtimestamp(a,BJT).date()
            midnight=datetime.combine(day+timedelta(days=1),datetime.min.time(),BJT).timestamp()
            end=min(b,midnight)
            days.setdefault(day.isoformat(),[]).append((a,end))
            a=end
    segments=[]; daily=[]
    for day, spans in sorted(days.items()):
        ids=[]
        for a,b in spans:
            uid=f'W{len(segments)+1:03d}'; ids.append(uid)
            segments.append({'id':uid,'date':day,'start':iso(a),'end':iso(b),'minutes':round((b-a)/60,6),'method':'主／子任务及并行工程取并集，跨午夜拆分'})
        daily.append({'date':day,'first':iso(spans[0][0]),'last':iso(spans[-1][1]),
                      'segment_ids':ids,'segment_count':len(spans),'minutes':round(sum(b-a for a,b in spans)/60,6),
                      'request_count':sum(x['time'].startswith(day) for x in requests)})
    log=subprocess.check_output(['git','-C',str(ROOT),'log','--reverse','--format=%h|%aI|%s',SOURCE_HEAD],text=True)
    commits=[{'id':line.split('|',2)[0],'time':line.split('|',2)[1],'subject':line.split('|',2)[2]} for line in log.splitlines()]
    cutoff=max(b for a,b in merged)
    data={'schema_version':1,'title':'源泽包材库更新、微调与工作时段汇报','period':'2026-09-22 至 2026-10-13',
          'timezone':'北京时间（UTC+08:00）','as_of':iso(cutoff),'source_head':SOURCE_HEAD,
          'production_evidence':'20261013-client-hd-v1（此前发布回执与正式浏览器核验）',
          'scope':'本机已存包材库主会话、明确关联的并行工程、子任务与现工程档案；不含早期独立ERP／打样总体设计及本次报表制作',
          'method_notes':[
              '主指标是已记录AI／工具运行及等待时长，包含推理、命令、网络与工具处理；不是员工实际人工工时、额度消耗或开发人日。',
              '相邻活动间隔不超过5分钟视为连续；超过5分钟且没有工具持续运行证据的空档排除。明确长工具起止保留，因此仍含生成／处理等待。',
              '工具区间优先采用日志中的实际调用到返回；本地预览服务器、SSH等后台进程持续存活不计入使用时长，仅计实际启动／轮询调用。',
              '汇总以主会话、子任务与并行工程活动区间取并集；跨午夜按北京时间拆分。跨轮用户等待、跨夜无活动空档与明确阻塞输入等待不计。',
              '异步提问返回后仍可执行独立工作，不能把从提问到用户答复的全部时间直接扣除。无明确等待证据不假定为空闲。',
              '更新事项按目的拆分；一个任务可能完成多个微调。更新行及多条提示目的共用T编号时，时长属于同一轮共享，禁止再加总。',
              '任务开始／结束以task_started/task_complete或turn_aborted核对；生命周期跨度只作辅助范围，不能直接算连续工作。不用Git时间差补推。',
              '系统duration_ms换算分钟按原值保留，仅用于核对，不由日历跨度倒推，不跨并行任务直接相加。计算保留毫秒，显示至秒／两位分钟。',
              '本轮结束不等于功能完成或上线；功能状态以档案、代码与发布／验收记录核对。重试、中断和方案保留在明细中。',
              '历史统计均按对应验收时点理解；产品记录、系列卡片、原图来源、制作版本、图片关联是不同口径。',
              '未同步到本机的其他设备或云端历史、离线人工工作、键盘实际工作时长不在本次可核对范围。',
              '提示词目的的时间是本机UserMessage事件记录时间，不冒充人工点击发送的瞬时时刻；任务生命周期、实际活动与提示时间分列。',
              '提示词仅按目的概括，删除账号密码、密钥、采购价明细、附件全文和私人连接路径。'] ,
          'updates':updates,'requests':requests,'tasks':tasks,'segments':segments,'daily':daily,'commits':commits,
          'totals':{'update_count':len(updates),'request_count':len(requests),'primary_task_count':len(tasks),
                    'subtask_count':sum(x['is_subagent'] for x in all_turns),'related_session_count':len(timing['sessions']),
                    'primary_session_count':timing['totals']['primary_session_count'],'recorded_days':len(daily),
                    'deduplicated_minutes':round(sum(b-a for a,b in merged)/60,6),'deduplicated_hours':round(sum(b-a for a,b in merged)/3600,6),
                    'deduplicated_seconds':round(sum(b-a for a,b in merged),3),
                    'segment_count':len(segments),'commit_count':len(commits),
                    'lifecycle_calendar_union_minutes':timing['totals'].get('lifecycle_calendar_union_minutes'),
                    'long_tool_wait_union_minutes':timing['totals']['long_tool_wait_union_seconds']/60,
                    'included_session_count':timing['totals'].get('included_session_count'),
                    'task_status_counts':dict(Counter(x['lifecycle'] for x in tasks)),
                    'task_basis_counts':dict(Counter(x['basis'] for x in tasks))},
          'pending':[
              '8项真实工艺价格及材质差异标准待用户补充；空值不作为零费用估算。',
              '全库图片优化未全部完成；已上线批次与剩余原图队列分别保留，不以发布次数当独立原图数。',
              '部分图册OCR、分型、图片与规格对应尚需来源核对；确定资料与待核对标记继续保留。',
              '业务员专属联系链接、真实询盘提交／通知及意向清单跨设备保存待完善。',
              '新手逐问检索仍为方案；现已支持多用途、资料用途与参考用途分开、候选搜索。',
              '管理员已可维护产品、账号、图片、批量产品及工艺；公司首页照片／证书／海报全部网页化编辑尚未证实全覆盖。',
              '持续搜图评测需更多真实用户照片；15张小样本结果不能代表全库或所有手机条件准确率。'],
          'excluded':{'erp_request_ids':[f'P{x:03d}' for x in range(1,13)],'legacy_erp_update_count':2,
                      'report_generation_excluded':True,'source_note':'本次报告制作不计入历史投入；无活动日期不补零，也不从日期跨度推工时。'},
          'historical_snapshot':{'label':'2026-10-07历史快照，未在本次重新访问生产数据库', **inv['legacy_snapshot']},
          'source_registry':[{'id':'S1','title':'本机任务生命周期及用户目的记录','detail':'6个明确包材库主会话与子任务；以会话ID＋事件行号定位'},
                             {'id':'S2','title':'10-07建设更新日志','detail':'旧报告69条包材事项；2条ERP背景单列排除'},
                             {'id':'S3','title':'客户端与业务端维护档案','detail':'以最新发布段优先，区分预览、实现与验收'},
                             {'id':'S4','title':'专项图片、性能、分型、用途与搜图核验','detail':'相应资料日期及专门发布回执'},
                             {'id':'S5','title':'Git提交历史','detail':'冻结至15e1550；提交时间仅证明提交事件，不作为工时起点'}]}
    OUTPUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(OUTPUT),'totals':data['totals'],'as_of':data['as_of']},ensure_ascii=False))


if __name__ == '__main__':
    build()
