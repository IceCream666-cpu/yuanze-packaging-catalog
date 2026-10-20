import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { PassThrough } from 'node:stream';
import { JSDOM } from 'jsdom';
import { createPreviewServer, decorateWorkspaceHTML } from '../preview-server.js';
import { installWorkspace, simpleBarePrice } from '../../internal-selection-demo/workspace.js';

const shell = '<!doctype html><html lang="zh-CN"><head><title>内部选型</title></head><body class="showroom-page catalog-workspace"><main id="main"></main><div id="modalBody"></div></body></html>';

test('preview decorates only the authenticated employee shell and keeps source app intact', () => {
  const html = decorateWorkspaceHTML(shell.replace('</body>','<script type="module" src="/app.js"></script></body>'));
  assert.match(html,/catalog-workspace immersive-workspace/);
  assert.match(html, /src="\/app.js"/);
  assert.match(html,/href="\/_workspace\/workspace.css"/);
  for (const page of ['<html><head></head><body class="client-page">客户页面</body></html>','<html><head></head><body>请登录</body></html>']) {
    assert.equal(decorateWorkspaceHTML(page),page);
  }
});

test('price presentation never discards quantities, currencies, accessories or tier conditions', () => {
  assert.equal(simpleBarePrice('普通报价：1.35'),'1.35');
  assert.equal(simpleBarePrice('普通报价：裸瓶价格1.8元'),'1.8');
  for (const value of ['普通报价：10000套：0.55元','普通报价：1.35–1.6','普通报价：USD 1.35','普通报价：1.35含运不含税','普通报价：1.35，泵头0.2元','普通报价：0.53元，一色丝印0.1元','原页：型号1.35']) {
    assert.equal(simpleBarePrice(value),null,value);
  }
});

test('enhancement retains original controls, delegated actions, raw price and updates without observer loops', async t => {
  const dom = new JSDOM(shell.replace('catalog-workspace','catalog-workspace immersive-workspace'),{pretendToBeVisual:true});
  t.after(()=>dom.window.close());
  const d = dom.window.document, main=d.querySelector('#main');
  // Background Safari can suspend animation callbacks indefinitely.
  dom.window.requestAnimationFrame = () => { throw new Error('content updates must not wait for an animation frame'); };
  main.innerHTML = `<form id="searchForm"><div class="search-box"><span>⌕</span><input name="query" id="query"></div><button type="submit">搜索</button></form>
    <article class="card"><button data-detail="existing-id">详情</button><div class="quote-preview" data-i18n-skip>普通报价：1.35</div><button class="favorite" data-favorite="existing-id" aria-label="收藏洗手液">☆</button></article>`;
  const control = d.querySelector('[data-detail]'), favourite=d.querySelector('[data-favorite]');
  let detailClicks=0, submit=0;
  control.addEventListener('click',()=>detailClicks++);
  d.querySelector('form').addEventListener('submit',event=>{event.preventDefault();submit++;});
  const cleanup = installWorkspace(d); t.after(cleanup);
  assert.equal(d.querySelector('[data-detail]'),control);
  control.click(); assert.equal(detailClicks,1);
  assert.equal(d.querySelector('[data-favorite]'),favourite);
  assert.equal(favourite.getAttribute('aria-label'),'收藏洗手液');
  assert.equal(d.querySelector('.quote-preview').dataset.wsOriginal,'普通报价：1.35');
  assert.equal(d.querySelector('.ws-price strong').textContent,'¥1.35');
  d.querySelector('[data-ws-use="精华液"]').click();
  assert.equal(submit,1); assert.equal(d.querySelector('#query').value,'精华液');
  let updates=0;
  const watch=new dom.window.MutationObserver(()=>updates++);
  watch.observe(main,{subtree:true,childList:true});
  d.documentElement.lang='en';
  await new Promise(resolve=>setTimeout(resolve,80));
  assert.equal(d.querySelector('[data-ws-price-label]').textContent,'Bare bottle');
  const settled=updates;
  await new Promise(resolve=>setTimeout(resolve,80));
  assert.equal(updates,settled,'decorator must settle instead of rendering continuously');
  watch.disconnect();
  main.innerHTML='<article class="card"><div class="quote-preview">普通报价：1.6</div></article>';
  await new Promise(resolve=>setTimeout(resolve,40));
  assert.equal(d.querySelector('.ws-price strong').textContent,'¥1.6');
  assert.equal(d.querySelectorAll('.ws-price').length,1);
});

test('HTTP overlay preserves authentication redirects, role isolation, API bytes and response headers', async t => {
  const calls = [];
  const server=createPreviewServer({upstreamRequest(url,options,callback){
    const request=new PassThrough();
    request.on('data',()=>{});
    request.on('end',()=>{
      calls.push({url,options});
      const response=new PassThrough();
      const authenticated=options.headers.cookie==='fixture=employee';
      const isAPI=url.pathname==='/api/session';
      response.statusCode=isAPI?200:authenticated?200:302;
      response.headers=isAPI?{'content-type':'application/json'}:{'content-type':'text/html; charset=utf-8','content-security-policy':"default-src 'self'; frame-ancestors 'none'",etag:'"old"','content-length':String(authenticated?Buffer.byteLength(shell):0)};
      if(!authenticated&&!isAPI)response.headers.location='/login';
      callback(response); response.end(isAPI?'{"role":"employee"}':authenticated?shell:'');
    });
    return request;
  }});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  t.after(()=>new Promise(resolve=>server.close(resolve)));
  const origin=`http://127.0.0.1:${server.address().port}`;
  const get=(route,headers={})=>new Promise((resolve,reject)=>{
    http.get(origin+route,{headers},res=>{
      let body='';res.on('data',chunk=>body+=chunk);
      res.on('end',()=>resolve({status:res.statusCode,headers:res.headers,body}));
    }).on('error',reject);
  });
  const page=await get('/',{Cookie:'fixture=employee','Accept-Encoding':'gzip','If-None-Match':'"old"'});
  assert.equal(page.status,200);
  assert.match(page.body,/immersive-workspace/);
  assert.equal(page.headers['content-length'],String(Buffer.byteLength(page.body)));
  assert.equal(page.headers.etag,undefined);
  assert.equal(page.headers['content-security-policy'],"default-src 'self'; frame-ancestors 'none'");
  assert.equal(calls[0].options.headers['accept-encoding'],'identity');
  assert.equal(calls[0].options.headers['if-none-match'],undefined);
  const anonymous=await get('/');
  assert.equal(anonymous.status,302); assert.equal(anonymous.headers.location,'/login');
  assert.equal(anonymous.body,'');
  const client=await get('/client',{Cookie:'fixture=employee'});
  assert.equal(client.body,shell,'non-workspace routes must stay byte-for-byte unchanged');
  const api=await get('/api/session');
  assert.equal(api.body,'{"role":"employee"}');
  const css=await get('/_workspace/workspace.css');
  assert.equal(css.status,200); assert.equal(css.headers['cache-control'],'no-store');
  assert.equal((await get('/_workspace/README.md')).status,404);
  assert.equal((await get('/_workspace/%2e%2e%2fpreview-server.js')).status,404);
});
