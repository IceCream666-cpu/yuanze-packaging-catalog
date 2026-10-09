"""Bounded CSV/XLSX import reader. It never writes business data or evaluates formulas."""
import base64
import binascii
import csv
import io
import json
import math
from pathlib import Path
import re
import zipfile

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_BODY_BYTES = ((MAX_FILE_BYTES + 2) // 3) * 4 + 4096
MAX_ROWS = 2000
FIELDS = {
    '记录编号':'id', '产品编号':'productCode', '版本':'version', '名称':'name', '资料类型':'kind',
    '分类':'category', '瓶型':'bottleType', '材质':'materials', '容量ml':'capacityMl',
    '规格':'specificationRaw', '系列':'series', '型号':'model', '用途':'uses', '参考用途':'referenceUses',
    '供应商':'supplierRaw', 'MOQ':'moqRaw', '单价':'quoteRaw', '货期':'leadTimeRaw',
    '报价口径':'quoteHeader', '定制报价':'customQuoteRaw', '定制MOQ':'customMoqRaw',
    '定制货期':'customLeadTimeRaw', '描述':'description', '备注':'remarksRaw',
    '来源说明':'sourceNote', '材质原文':'materialRaw',
}
KIND = {'包材':'package', '料体与半成品':'semi_finished', '检测与服务':'service',
        '需求资料':'requirement', '待分类':'uncertain'}

def template_csv():
    output = io.StringIO(newline='')
    csv.writer(output).writerow(FIELDS)
    return ('\ufeff' + output.getvalue()).encode('utf-8')

def parse_import(data):
    if not isinstance(data, dict) or set(data) != {'filename','content'}:
        raise ValueError('请提交文件名与文件内容')
    name, encoded = data['filename'], data['content']
    if not isinstance(name,str) or len(name)>255 or not isinstance(encoded,str) or len(encoded)>MAX_BODY_BYTES:
        raise ValueError('文件信息无效或文件过大')
    try:
        binary = base64.b64decode(encoded, validate=True)
    except (ValueError,binascii.Error) as error:
        raise ValueError('文件编码无效') from error
    if not binary or len(binary)>MAX_FILE_BYTES:
        raise ValueError('导入文件不能为空或超过10MB')
    extension = Path(name).suffix.lower()
    warnings = []
    if extension == '.csv':
        try:
            contents = binary.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                contents = binary.decode('gb18030')
            except UnicodeDecodeError as error:
                raise ValueError('CSV请保存为UTF-8编码') from error
        try:
            rows = []
            for row in csv.reader(io.StringIO(contents)):
                rows.append(row)
                if len(rows)>MAX_ROWS+1:
                    raise ValueError('每次最多导入2000行，请拆分文件')
        except csv.Error as error:
            raise ValueError('CSV格式无法读取，请检查引号和字段长度') from error
    elif extension == '.xlsx':
        try:
            with zipfile.ZipFile(io.BytesIO(binary)) as archive:
                infos=archive.infolist()
                if len(infos)>1500 or sum(x.file_size for x in infos)>25*1024*1024:
                    raise ValueError('Excel解压后过大，请使用简化的导入模板')
                if any('vbaProject' in x.filename or x.filename.startswith('xl/externalLinks/') for x in infos):
                    raise ValueError('导入文件不可含宏或外部工作簿链接')
                if any(x.filename.startswith('xl/media/') for x in infos):
                    warnings.append('表格内嵌图片不参与本次导入，请在产品编辑页单独上传。')
            from openpyxl import load_workbook
            workbook=load_workbook(io.BytesIO(binary),read_only=True,data_only=False,keep_links=False)
            try:
                if len(workbook.worksheets)!=1:
                    raise ValueError('请使用仅含一个工作表的导入文件，避免漏导其他工作表')
                sheet=workbook.worksheets[0]
                sheet.reset_dimensions()
                rows=[]
                for cells in sheet.iter_rows():
                    if len(cells)>80:
                        raise ValueError('最多允许80列，请使用导入模板')
                    if any(cell.data_type=='f' for cell in cells):
                        raise ValueError('Excel含公式，请复制并粘贴为数值后再导入')
                    rows.append([cell.value for cell in cells])
                    if len(rows)>MAX_ROWS+1:
                        raise ValueError('每次最多导入2000行，请拆分文件')
            finally:
                workbook.close()
        except (zipfile.BadZipFile,KeyError) as error:
            raise ValueError('无法读取Excel，请使用有效的.xlsx模板') from error
        except ImportError as error:
            raise ValueError('Excel读取组件暂不可用，可先使用CSV模板') from error
    else:
        raise ValueError('仅支持.csv或.xlsx文件')
    if not rows:
        raise ValueError('文件为空')
    headers=[str(x or '').strip() for x in rows[0]]
    mapping={**FIELDS, **{v:v for v in FIELDS.values()}}
    if len(headers)>80 or len(set(x for x in headers if x))!=len([x for x in headers if x]):
        raise ValueError('列名重复或列数超过限制')
    unknown=[x for x in headers if x and x not in mapping]
    if unknown:
        raise ValueError('不支持的列名：'+ '、'.join(unknown[:8])+'；请使用导入模板')
    fields=[mapping.get(x) for x in headers]
    known_fields=[x for x in fields if x]
    if len(set(known_fields))!=len(known_fields):raise ValueError('同一字段重复出现，请勿同时使用中英文列名')
    if 'name' not in fields:
        raise ValueError('缺少名称列，请使用导入模板')
    result=[];errors=[];source_rows=[]
    for row_number,row in enumerate(rows[1:],2):
        if not any(x is not None and str(x).strip() for x in row):
            continue
        if len(row)>len(headers) and any(x not in (None,'') for x in row[len(headers):]):
            errors.append({'row':row_number,'message':'数据列多于表头'})
            continue
        record={}
        try:
            for key, value in zip(fields,row):
                if key is None:
                    if value not in (None,''): raise ValueError('存在没有列名的数据')
                    continue
                value='' if value is None else str(value).strip()
                if len(value)>10000: raise ValueError('单元格内容超过10000字')
                if key == 'referenceUses':
                    # An empty cell makes no change to an existing override.
                    if not value:
                        continue
                    if value.casefold() in ('自动', 'auto', 'automatic'):
                        record[key] = None
                    elif value.startswith('['):
                        values = json.loads(value)
                        if not isinstance(values, list) or any(not isinstance(x, str) or not x.strip() for x in values):
                            raise ValueError('参考用途须为文字列表、[]或自动')
                        record[key] = values
                    else:
                        record[key] = [x.strip() for x in re.split('[、,，;；|]', value) if x.strip()]
                elif key in ('materials','uses'):
                    record[key]=[x.strip() for x in re.split('[、,，;；|]',value) if x.strip()]
                elif key=='capacityMl':
                    record[key]=float(value) if value else None
                    if record[key] is not None and (not math.isfinite(record[key]) or record[key]<=0):
                        raise ValueError('容量必须为正数或留空')
                elif key=='version':
                    if value: record[key]=int(value)
                elif key=='id':
                    if value: record[key]=value
                elif key=='productCode':
                    # Empty cells mean no assertion; new product codes are
                    # always assigned by the store, never supplied by a file.
                    if value: record[key]=value
                elif key=='kind':
                    if value: record[key]=KIND.get(value,value)
                else:
                    record[key]=value
            if not record.get('name'): raise ValueError('名称不能为空')
            result.append(record)
            # Preserve the spreadsheet's physical row number. Empty and invalid
            # rows are omitted above, so the store's list index is not a sheet row.
            source_rows.append(row_number)
        except (ValueError,TypeError) as error:
            errors.append({'row':row_number,'message':str(error)})
    if not result and not errors:
        raise ValueError('只有表头，没有可导入记录')
    if len(json.dumps(result,ensure_ascii=False).encode())>2*1024*1024:
        raise ValueError('本批文字资料过多，请拆分为更小文件')
    return {'rows':result,'sourceRows':source_rows,'errors':errors,'warnings':warnings,'count':len(result)}
