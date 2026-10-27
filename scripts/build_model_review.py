"""Build the local, review-only index from the featured inventory and verified model status."""
import html,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'docs/client-motion-demo'
items=json.loads((ROOT/'src/featured.json').read_text())
posters={p['id']:p for p in json.loads((ROOT/'src/posters.json').read_text())}
status=json.loads((ROOT/'model-review-status.json').read_text())
esc=lambda s:html.escape(str(s),quote=True)
ready=sum(status.get(p['id'],{}).get('state') in ('complete','published') for p in items)
cards=[]
for p in items:
 id=p['id'];r=status.get(id,{'state':'working'});done=r['state'] in ('complete','published');photos=r.get('screenshots',{})
 image=photos.get('closed',posters[id]['thumb']);tag='已上线' if r['state']=='published' else '已完成 · 本地预览' if done else '逐款制作中'
 card=f'''<article data-name="{esc(p['name']+' '+p['kind']['zh'])}" data-state="{r['state']}"><div class="visual" style="--paper:{r.get('background',p['background'])}"><img loading="lazy" src="{image}" data-closed="{photos.get('closed',posters[id]['thumb'])}" data-open="{photos.get('open',posters[id]['thumb'])}" data-poster="{posters[id]['image']}" alt="{esc(p['name'])} {'模型合拢预览' if photos else '原海报参考'}"></div><div class="meta"><span class="status {r['state']}">{tag}</span><span>{len(r.get('components',[])) or ''}{' 层' if r.get('components') else ''}</span></div><h2>{esc(p['name'])}</h2><p>{esc(p['kind']['zh'])}</p><div class="links">'''
 if done:card+=f'<a href="/?model={id}" target="_blank" rel="noopener">打开交互模型 <span aria-hidden="true">↗</span></a>'
 else:card+='<span class="pending">校准材质与比例</span>'
 card+=f'<a href="{posters[id]["original"]}" target="_blank" rel="noopener">原海报</a></div></article>'
 cards.append(card)
page='''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>源泽 · '''+str(len(items))+'''款包材结构陈列</title><link rel="stylesheet" href="/model-review.css"></head><body><main><header><div class="top"><img src="/assets/yuanze-mark-compact.webp" alt="源泽"><a href="/" target="_blank" rel="noopener">客户端预览 ↗</a></div><h1>包材结构陈列</h1><div class="intro"><p>从原海报到可拆解的包装。逐款对照轮廓、材质与印刷，拖动旋转模型，滑动展开部件与文字。</p><p class="progress">READY / <strong>'''+str(ready)+'''</strong> / '''+str(len(items))+'''</p></div><div class="toolbar"><label><span class="sr-only">查找产品</span><input type="search" placeholder="查找名称或品类…" id="search"></label><div class="views" role="group" aria-label="预览图片"><button aria-pressed="true" data-view="closed">合拢</button><button aria-pressed="false" data-view="open">展开</button><button aria-pressed="false" data-view="poster">原海报</button></div></div></header><section aria-label="'''+str(len(items))+'''款精选包材">'''+''.join(cards)+'''</section><p id="empty" hidden>没有匹配的产品，请试试其他名称。</p><footer><p>本页汇集全部本地模型。标为“已上线”的款式已独立发布；其余完成款供本地查看。每款内均可打开原海报对照。</p><p>空包材展示不含料液与场景道具。隐藏结构、壁厚与尺寸由图片推定，生产前需结合实物校准。</p></footer></main><script src="/model-review.js"></script></body></html>'''
(ROOT/'public/model-review.html').write_text(page)
print(f'Review index: {ready}/{len(items)} verified models')
