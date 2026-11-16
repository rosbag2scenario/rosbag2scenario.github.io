// Optional browser QA: start tools/serve.py first; requires Playwright Chromium.
const {chromium}=require(process.env.PLAYWRIGHT_PACKAGE || 'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});const page=await browser.newPage({viewport:{width:1440,height:1000}});let errors=[],external=[];
 page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(!r.url().startsWith('http://127.0.0.1:8765')&&!r.url().startsWith('data:'))external.push(r.url())});
 await page.goto('http://127.0.0.1:8765',{waitUntil:'networkidle'});await page.waitForFunction(()=>document.querySelector('#gap-case').options.length===4);
 assert.equal(await page.locator('source[src="media/d1-submission.mp4"]').count(),1);
 assert.equal(await page.locator('#gap-case').inputValue(),'R01');assert(!await page.locator('#gallery-browser').getAttribute('open'));
 assert(await page.evaluate(()=>document.querySelector('#regression').offsetTop<document.querySelector('#results').offsetTop));
 assert(await page.evaluate(()=>document.querySelector('.reconstruction-intro').offsetTop<document.querySelector('#gap-explorer').offsetTop));
 await page.click('#browse-gaps');
 assert(await page.locator('video').evaluateAll(vs=>vs.every(v=>v.paused)));
 for(const kind of ['real','benchmark']){
  await page.selectOption('#gap-kind',kind);let ids=await page.locator('#gap-case option').evaluateAll(os=>os.map(o=>o.value));
  assert.equal(ids.length,kind==='real'?4:111);
  for(const id of ids){await page.selectOption('#gap-case',id);for(const chart of ['gap-xy','gap-speed','gap-direction'])assert(!await page.locator('#'+chart).evaluate(n=>/NaN|Infinity/.test(n.innerHTML)),id+' '+chart);}
 }
 await page.selectOption('#gap-motion','near_stationary');assert.equal(await page.locator('#gap-case option').count(),55);
 await page.selectOption('#gap-motion','moving');assert.equal(await page.locator('#gap-case option').count(),56);
 assert.equal(await page.locator('#equal-scale, #download-case').count(),0);
 await page.selectOption('#gap-motion','all');
 while(await page.locator('#gallery-more').isVisible())await page.click('#gallery-more');
 assert.equal(await page.locator('.gap-card').count(),111);
 await page.locator('.gap-card[data-case="T042"]').click();assert.equal(await page.locator('#gap-case').inputValue(),'T042');
 await page.locator('#alignment').screenshot({path:'/tmp/rosbag-v2-alignment.png'});
 for(const c of ['D1','D2','D7','Empty road']){await page.selectOption('#map-case',c);assert(await page.locator('#alignment-map path').count()>10);}
 assert.equal(await page.locator('#map-zoom, #map-position, #gap-time, #motion-time, #compare-play, #comparison-dialog').count(),0);
 for(const v of ['speed','acceleration','steering','components']){await page.selectOption('#motion-view',v);assert(!await page.locator('#motion-command').evaluate(n=>/NaN|Infinity/.test(n.innerHTML)));}
 await page.selectOption('#motion-view','speed');
 await page.locator('summary').filter({hasText:'Why sometimes'}).click();
 await page.locator('#ambiguity-time').fill('0');await page.locator('#ambiguity-time').dispatchEvent('input');assert((await page.locator('#ambiguity-status').textContent()).includes('1a5f'));
 await page.locator('#ambiguity-timeline').screenshot({path:'/tmp/rosbag-v2-ambiguity.png'});

 await page.click('#browse-gaps');await page.selectOption('#gap-kind','real');await page.locator('#gallery-browser summary').click();await page.locator('#gap-explorer').screenshot({path:'/tmp/rosbag-final-explorer.png'});
 assert.equal(await page.locator('#gap-direction [data-cursor] line').count(),0);
 const headingPaths=await page.locator('#gap-direction > path').count();await page.locator('#gap-methods input[value=ours]').uncheck();assert.equal(await page.locator('#gap-direction > path').count(),headingPaths-1);await page.locator('#gap-methods input[value=ours]').check();
 assert.equal(await page.locator('[data-motion-case]').count(),7);assert.equal(await page.locator('.motion-grid img').count(),28);
 for(const detail of await page.locator('.motion-details').all()){await detail.locator('summary').click();await detail.locator('img').first().scrollIntoViewIfNeeded();await detail.locator('summary').click();}
 await page.locator('#case-notes > summary').click();
 for(const clip of await page.locator('.case-clip').all()){await clip.locator('summary').click();const v=clip.locator('video');await v.evaluate(async n=>{n.load();await new Promise((resolve,reject)=>{n.onloadedmetadata=resolve;n.onerror=reject});n.currentTime=12;await new Promise(resolve=>n.onseeked=resolve);});assert.equal(await v.evaluate(n=>n.videoWidth),1920);assert.equal(await v.evaluate(n=>n.videoHeight),1470);assert(Math.abs(await v.evaluate(n=>n.duration)-17.1)<.05);await clip.locator('.encounter-motion').scrollIntoViewIfNeeded();assert(await clip.locator('.motion-grid img').evaluateAll(imgs=>imgs.every(i=>i.complete && i.naturalWidth>0)));if(await clip.locator('[data-motion-case=d3]').count())await clip.screenshot({path:'/tmp/rosbag-standard-d3-case.png'});await clip.locator('summary').click();}
 await page.locator('#case-notes > summary').click();
 const video=page.locator('#comparison-video');await video.scrollIntoViewIfNeeded();
 assert.equal(await page.locator('#comparison video').count(),1);assert(await video.evaluate(v=>v.controls));
 await video.evaluate(async v=>{v.load();await new Promise((resolve,reject)=>{v.onloadedmetadata=resolve;v.onerror=reject;});v.currentTime=12;await new Promise(resolve=>v.onseeked=resolve);});
 assert.deepEqual(await video.evaluate(v=>[v.videoWidth,v.videoHeight,v.duration]),[3840,1470,22.2]);
 await video.evaluate(v=>v.play());await page.waitForTimeout(700);assert(await video.evaluate(v=>!v.paused && v.currentTime>12));await video.evaluate(v=>v.pause());
 await video.evaluate(v=>v.requestFullscreen());assert(await page.evaluate(()=>document.fullscreenElement?.id==='comparison-video'));await page.evaluate(()=>document.exitFullscreen());
 await page.locator('#regression').screenshot({path:'/tmp/rosbag-native-comparison.png'});
 for(const width of [320,390,768]){await page.setViewportSize({width,height:844});await page.waitForTimeout(150);console.log('Viewport',width,await page.evaluate(()=>[document.body.scrollWidth,innerWidth]));assert(await page.evaluate(()=>document.body.scrollWidth<=innerWidth),`overflow ${width}`);}
 await page.setViewportSize({width:390,height:844});await page.locator('#gap-explorer').screenshot({path:'/tmp/rosbag-final-mobile-explorer.png'});
 await page.setViewportSize({width:1440,height:1000});await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:'/tmp/rosbag-final-hero.png'});
 await page.emulateMedia({colorScheme:'dark'});await page.locator('#gap-explorer').screenshot({path:'/tmp/rosbag-v2-dark-gallery.png'});await page.emulateMedia({colorScheme:'light'});
 console.log('Layout',await page.evaluate(()=>({height:document.body.scrollHeight,regressionTop:document.querySelector('#regression').offsetTop})));
 const nojs=await browser.newPage({javaScriptEnabled:false});await nojs.goto('http://127.0.0.1:8765');assert(await nojs.locator('#gap-explorer noscript').isVisible());assert(await nojs.locator('#results table').count()===3);
 assert.equal(errors.length,0);assert.equal(external.length,0);console.log('PASS: all 115 cases, both motion filters, one D1 player, collapsed gallery, 111 scaled thumbnails, native comparison playback/seek/fullscreen, full-encounter maps, command views, temporal ambiguity, 320/390/768 widths, no-JS fallback, no page errors or external requests.');await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
