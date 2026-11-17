// Run with ego-browser nodejs < this-file; set an existing TaskSpace ID and baseline/candidate.
const t=await taskSpace(48),p=t.page('p1');
const fs=await import('node:fs/promises');
const variant='candidate',port=variant==='baseline'?8881:8882,results=[];
await p.cdp('Network.enable');await p.cdp('Network.setCacheDisabled',{cacheDisabled:true});
await p.cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
try {
 for(let run=1;run<=3;run++) {
  await p.cdp('Network.emulateNetworkConditions',{offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1});
  await p.goto(`http://127.0.0.1:${port}/client`);
  await p.click('loc=css:button[aria-label="Moisture Shampoo"]');
  await p.waitForFunction(()=>document.querySelector('.colour-copy')?.dataset.productId==='poster-049');
  await p.evaluate(()=>{const b=document.querySelector('.colour-poster'); b.addEventListener('pointerenter',()=>window.__intentAt=performance.now(),{once:true});b.addEventListener('click',()=>window.__clickAt=performance.now(),{once:true});});
  await p.cdp('Network.emulateNetworkConditions',{offline:false,latency:80,downloadThroughput:500000,uploadThroughput:250000,connectionType:'cellular4g'});
  await p.hover('text="查看产品详情"');
  await p.waitForTimeout(500);
  await p.click('text="查看产品详情"');
  await p.waitForFunction(()=>window.__packagingLoadMetrics?.some(m=>m.timings.firstFrame),undefined,{timeout:45000});
  const data=await p.evaluate(()=>{const m=window.__packagingLoadMetrics.findLast(m=>m.timings.firstFrame);const started=performance.getEntriesByName(`packaging:${m.id}:start`)[0].startTime;return {leadMs:window.__clickAt-window.__intentAt,clickToFrameMs:started+m.timings.firstFrame-window.__clickAt,metrics:window.__packagingLoadMetrics,models:performance.getEntriesByType('resource').filter(r=>r.name.endsWith('.glb')).map(r=>({url:r.name,duration:r.duration,encodedBytes:r.encodedBodySize,transferBytes:r.transferSize})),scene:document.querySelector('.packaging-model').__packagingScene.getState()};});
  results.push({run,...data});console.log({variant,run,leadMs:data.leadMs,clickToFrameMs:data.clickToFrameMs,requests:data.models.length});
 }
 await fs.writeFile(`/Users/icecream/Documents/Codex/2026-10-22/gen/work/body-care-duo/docs/client-motion-demo/review-evidence/loading-20261117/${variant}-controlled.json`,JSON.stringify({variant,conditions:{latencyMs:80,downloadBytesPerSecond:500000,cacheDisabled:true,viewport:'1440x1000',hoverWaitMs:500,scope:'model open only; main page loaded unthrottled; loopback gzip server'},results},null,2));
} finally {await p.cdp('Network.setCacheDisabled',{cacheDisabled:false});await p.cdp('Network.emulateNetworkConditions',{offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1});}
