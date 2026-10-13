#!/usr/bin/env python3
"""Reframe verified report evidence chronologically, without inventing execution times."""
from collections import defaultdict
from datetime import datetime
import hashlib
import ast
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/包材库内部汇报-20261013.json'
OUT=ROOT/'docs/包材库时间线汇报-20261013.json'
IMAGE_INPUT=ROOT/'work/timeline-report-20261013/image_batch_inventory.json'
EXTRA_COMMIT_LABELS={
 'f518e05':'交付第一份建设更新PDF汇报',
 '1c8c8ad':'修复同系列各规格独立检索', '2818a10':'记录多规格检索验证',
 '2319471':'管理员采用共享目录与原位编辑', '66c1721':'记录新增50张图片核验',
 'b995e86':'记录新服务器管理员功能上线验证', '51f9737':'同步并行工程审核图片到客户展示',
 'bedd6dd':'记录客户轮播与全工程图片同步验证', '3cad563':'优化手机分页加载与缩略图',
 'e304fba':'记录手机加载优化正式发布验证', 'a4b0eb6':'优化客户首页与海报加载',
 '7af0580':'记录传输BBR与展厅加载优化核验', '7a85873':'按实际瓶罐类型归并并核对图册规格',
 '28927b8':'记录分型归并上线及待核对规格', '4ad3597':'制作紧凑详情与工艺估算Demo',
 'ac80db8':'上线紧凑详情与管理员批量维护', '5ff808f':'记录详情与工艺后台发布验证',
 '0a7ef69':'建立洗手液250与500mL独立规格图', '50e9e46':'将普通参考价标准化为裸瓶价格',
 'd53a0aa':'记录洗手液与裸瓶价格上线核验', 'dd0b799':'整理资料用途与结构参考用途',
 'd31f60e':'记录常见用途上线与边界核验', '6c3fa00':'修复实拍搜图与候选读取上限',
 '4e14e44':'修复审核局部图缓存与结果显示', '80e22be':'建立审核裁剪与展示图片来源绑定',
 '6c80995':'记录实拍搜图正式发布及评测限制', '6b8ca0a':'新增安全高清原图与快速下载反馈',
 '15e1550':'记录客户高清查看与下载正式验收',
}
PROJECTS={
 '01a0c869':'主工程／包材库建设与图片优化',
 '01a1147a':'并行工程A／尾批图片优化与客户同步',
 '01a11546':'并行工程B／客户海报与轮播',
 '01a11550':'并行工程C／同款归并与规格图片',
 '01a1156d':'并行工程D／侧栏与管理员维护',
 '01a0e639':'审查工程／功能真实性核对',
}


def sanitize_sources(value):
    if isinstance(value,dict):return {k:sanitize_sources(v) for k,v in value.items()}
    if isinstance(value,list):return [sanitize_sources(v) for v in value]
    if isinstance(value,str):
        value=value.replace(str(ROOT)+'/', '')
        return re.sub(r'/(?:Users|var/folders)/[^\s；;]+',lambda m:Path(m.group()).name,value)
    return value


def build():
    raw=BASE.read_bytes(); base=json.loads(raw)
    syntax=ast.parse((ROOT/'scripts/build_update_report.py').read_text())
    old_labels=next(ast.literal_eval(x.value) for x in syntax.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='COMMIT_LABELS' for t in x.targets))
    labels={sha:text[0] for sha,text in old_labels.items()}|EXTRA_COMMIT_LABELS
    tasks={x['id']:x for x in base['tasks']}
    req={x['id']:x for x in base['requests']}
    outcomes=defaultdict(list)
    for u in base['updates']:
        candidates=[req[p] for p in u['request_ids'] if p in req]
        if not candidates: raise ValueError('Unlinked update '+u['id'])
        owner=min(candidates,key=lambda x:datetime.fromisoformat(x['time']).timestamp())
        outcomes[owner['id']].append(u)
    events=[]
    for p in base['requests']:
        t=tasks[p['task_id']]
        events.append({'time':p['time'],'event_type':p['kind'],'purpose':p['purpose'],
                       'project_session_short':t['source']['session_id'][:8],
                       'project_label':PROJECTS[t['source']['session_id'][:8]],
                       'request_id':p['id'],'commit_id':None,'task':t,'updates':outcomes[p['id']],
                       'operation':'需求、补充或查询记录；相关成果在本事件下按U编号列示。',
                       'status':t['lifecycle']+'；功能状态见关联成果，不等于此时已上线。',
                       'evidence':f'会话 {p["source"]["session_id"][:8]}／事件行 {p["source"]["event_line"]}；{t["id"]}',
                       'time_basis':'需求记录时间（UserMessage日志）；不冒充人工发送瞬时'})
    for c in base['commits']:
        if c['id'] not in labels: raise ValueError('Untranslated commit '+c['id'])
        events.append({'time':c['time'],'event_type':'代码提交','purpose':labels[c['id']],
                       'project_session_short':None,'project_label':'共享正式工程／Git提交事件',
                       'request_id':None,'commit_id':c['id'],'task':None,'updates':[],
                       'operation':'将代码或维护档案保存为Git提交，保留回滚和核对依据。',
                       'status':'已提交；提交时刻不等于上线时刻，不用于推算工时。',
                       'evidence':'Git '+c['id'],'source_subject':c['subject'],'time_basis':'Git提交事件时间'})
    events.sort(key=lambda x:(datetime.fromisoformat(x['time']).timestamp(),x['commit_id'] is not None,x.get('request_id') or x['commit_id']))
    image_data=sanitize_sources(json.loads(IMAGE_INPUT.read_text()))
    image_batches=image_data['image_batches']
    image_operations=image_data['image_operations']
    for e in events:
        e['batch_ids']=[b['batch_id'] for b in image_batches+image_operations if e['request_id'] in b['request_ids']]
    days=defaultdict(list)
    for n,e in enumerate(events,1):
        e['id']=f'E{n:03d}'
        e['date']=datetime.fromisoformat(e['time']).strftime('%Y-%m-%d')
        e['clock']=datetime.fromisoformat(e['time']).strftime('%H:%M:%S')
        days[e['date']].append(e['id'])
    for day in base['daily']:
        days.setdefault(day['date'],[])
    result={'schema_version':1,'title':'源泽包材库建设与优化时间线汇报','period':base['period'],
            'as_of':base['as_of'],'timezone':base['timezone'],'source_head':base['source_head'],
            'base_data_sha256':hashlib.sha256(raw).hexdigest(),
            'totals':base['totals']|{'timeline_event_count':len(events)},
            'events':events,'days':[{'date':day,'event_ids':ids,'activity_summary':next((x for x in base['daily'] if x['date']==day),None)} for day,ids in sorted(days.items())],
            'daily':base['daily'],'segments':base['segments'],'pending':base['pending'],
            'image_batches':image_batches,'image_operations':image_operations,
            'image_summary':image_data['totals'],'image_method_notes':image_data['method_notes'],
            'parallel_windows':image_data['parallel_overlaps'],
            'method_notes':[
                '时间线按真实需求日志记录时间与Git提交事件时间排序，以完整日期和时:分:秒呈现，统一为北京时间。',
                '每个日期下同时展示需求、补充、重试与提交。原有114项更新作为关联成果放在对应主要需求下各一次，不在确认回复中重复。',
                '关联成果的完成状态是截至统计截止的核验结果，不表示该功能已在左列需求时刻完成。单项具体实施时刻未独立记录时，不予虚构。',
                '任务开始与结束另列真实T生命周期；活动／工具运行等待分钟另列，共用T的提示和成果不能重复加总。',
                'U条目沿用原资料归属日期作为来源信息；时间线的日期时刻来自P日志或Git，不能将来源日期当执行时刻。',
                '提交事件仅表示保存代码或档案，不等于部署；提交时间与相邻提交差均不作为工时。',
                '总时长沿用已核对的119段并行去重W区间，为AI／工具运行及处理等待，含长图像生成等待，不等于员工人工工时。',
                '后台服务持续存活、没有持续工具证据的长空档、早期ERP背景与本次报表制作不计历史投入。',
                '未同步到本机的其他设备记录及离线人工工作无法核对；没有为了每条事项显示精确时间而猜测补齐。',
                '提示目的概括脱敏，报告不含账号密码、密钥、采购价明细或本机私有连接路径。']}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(OUT),'events':len(events),'updates':sum(len(x['updates']) for x in events),'dates':len(days)},ensure_ascii=False))


if __name__=='__main__':build()
