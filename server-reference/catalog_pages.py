"""Versioned server-side pages, using the same JS search rules as the browser."""
import csv
import io
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import threading
import time
from urllib.parse import parse_qs


class CatalogBusy(Exception):
    pass


def catalog_revision(store):
    with store.connection() as conn:
        records = tuple(conn.execute('SELECT COUNT(*),COALESCE(SUM(version),0),COALESCE(SUM(archived),0) FROM admin_records').fetchone())
        config = tuple((r['resource'],r['version']) for r in conn.execute('SELECT resource,version FROM admin_config ORDER BY resource'))
        audit = conn.execute("SELECT COALESCE(MAX(id),0) FROM admin_audit WHERE resource IN ('records','settings','taxonomy')").fetchone()[0]
    return records, config, audit


def search_options(query, store, username):
    values = parse_qs(query, max_num_fields=512)
    result = {'q':values.get('q',[''])[0], 'page':int(values.get('page',['1'])[0]),
              'pageSize':int(values.get('pageSize',['20'])[0]), 'filters':{}}
    if len(result['q'])>200 or result['page']<1 or result['pageSize'] not in {20,40,80}:
        raise ValueError('Invalid pagination')
    for key in ['kind','section','category','material','capacity','capacityBand','bottle','use','quote','source','imageStatus']:
        selected=values.get(key,[])
        if len(selected)>64 or any(len(v)>240 for v in selected):raise ValueError('Invalid filters')
        result['filters'][key]=selected
    if 'imageIds' in values:
        if len(values['imageIds'])>256 or any(len(v)>200 for v in values['imageIds']):raise ValueError('Invalid image results')
        result['imageIds']=values['imageIds']
    result['favorites']=values.get('favorites')==['1']
    if result['favorites']:
        with store.connection() as conn:
            row=conn.execute('SELECT content FROM preferences WHERE username=?',(username,)).fetchone()
        result['favoriteIds']=json.loads(row[0]).get('favorites',[]) if row else []
    return result


class CatalogPages:
    def __init__(self, store, root):
        self.store,self.root=store,Path(root)
        self.node=os.environ.get('NODE_BIN') or shutil.which('node')
        self.enabled=bool(self.node)
        self.gate=threading.Lock()
        self.process=None
        self.revision=None
        self.metadata={}

    def close(self):
        if self.process:
            self.process.terminate()
            try:self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
            for stream in [self.process.stdin,self.process.stdout]:
                if stream:stream.close()
        self.process=None;self.revision=None

    def _exchange(self, job):
        if not self.process or self.process.poll() is not None:
            raise CatalogBusy()
        # Stream initialization rather than constructing another 33 MB string.
        json.dump(job,self.process.stdin,ensure_ascii=False,separators=(',',':'))
        self.process.stdin.write('\n');self.process.stdin.flush()
        result=bytearray();deadline=time.monotonic()+25
        with selectors.DefaultSelector() as select:
            select.register(self.process.stdout,selectors.EVENT_READ)
            while time.monotonic()<deadline:
                if not select.select(max(0,deadline-time.monotonic())):break
                chunk=os.read(self.process.stdout.fileno(),65536)
                if not chunk:break
                result.extend(chunk)
                if len(result)>128_000_000:break
                if result.endswith(b'\n'):
                    value=json.loads(result)
                    if 'error' in value:raise CatalogBusy()
                    return value
        raise CatalogBusy()

    def _load(self):
        stamp=catalog_revision(self.store)
        if self.process and self.process.poll() is None and stamp==self.revision:return
        self.close()
        catalog=self.store.catalog()
        self.metadata={key:catalog[key] for key in ('meta','settings','taxonomy')}
        self.process=subprocess.Popen([self.node,'--max-old-space-size=384',str(self.root/'catalog_worker.mjs')],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',bufsize=1)
        self._exchange({'action':'load','catalog':catalog})
        self.revision=stamp

    def request(self, action, **arguments):
        if not self.enabled or not self.gate.acquire(timeout=15):raise CatalogBusy()
        try:
            self._load()
            return {**self._exchange({'action':action,**arguments}),**self.metadata}
        except (OSError,ValueError,BrokenPipeError,CatalogBusy):
            self.close();raise CatalogBusy() from None
        finally:self.gate.release()

    def warm(self):
        return self.request('query',options={'filters':{'kind':['package']},'page':1,'pageSize':20})


def internal_csv(records):
    kinds={'package':'包材','source_page':'图册与图片线索','process_rule':'工艺与价格参考','semi_finished':'料体与半成品','service':'检测与服务','requirement':'需求资料','uncertain':'待分类'}
    headers=['产品编号','内部记录ID','名称','类型','材料原文','规格原文','供应商原文','报价口径','普通报价原文','普通起订数量','普通交期','定制报价原文','定制起订数量','定制交期','样品费原文','开模费原文','来源','资料用途','参考用途（选型参考）']
    fields=['productCode','id','name','kind','materialRaw','specificationRaw','supplierRaw','quoteHeader','quoteRaw','moqRaw','leadTimeRaw','customQuoteRaw','customMoqRaw','customLeadTimeRaw','sampleFeeRaw','moldFeeRaw']
    output=io.StringIO();output.write('\ufeff');writer=csv.writer(output);writer.writerow(headers)
    def safe(value):
        value=value if isinstance(value,str) else '' if value is None else json.dumps(value,ensure_ascii=False,separators=(',',':'))
        return "'"+value if value.lstrip().startswith(('=','+','-','@','\t','\r','\n')) else value
    for record in records:
        source=record.get('source') or {};file=str(source.get('workbook') or '')
        note=record.get('sourceNote') or (f'{file} · 第 {source["page"]} 页' if source.get('page') else (file+' · ' if file else '')+str(source.get('sheet') or '原始表格')+' · 第 '+str(source.get('row','?'))+' 行') if source or record.get('sourceNote') else '管理员维护'
        # The worker supplies derived display values for this employee report.
        # Keep the report heading distinct from the editable import-template
        # field, whose missing/automatic/disabled states carry write intent.
        def usage_text(key):
            values = record.get(key)
            return ' / '.join(value for value in values if isinstance(value, str)) if isinstance(values, list) else ''
        row=[kinds.get(record.get('kind'),'待分类') if k=='kind' else record.get(k) for k in fields]+[note,usage_text('uses'),usage_text('referenceUses')]
        writer.writerow([safe(v) for v in row])
    return output.getvalue().encode('utf-8')
