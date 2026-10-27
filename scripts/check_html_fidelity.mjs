// Fixture driver for the task-owned Chrome started by check_html_fidelity.py.
import {readFile, writeFile} from 'node:fs/promises';

const [port, manifest] = process.argv.slice(2);
const cases = JSON.parse(await readFile(manifest, 'utf8'));
const origin = `http://127.0.0.1:${Number(port)}`;
const version = await (await fetch(`${origin}/json/version`)).json();
const target = await (await fetch(`${origin}/json/new?about:blank`, {method:'PUT'})).json();
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {socket.onopen=resolve; socket.onerror=reject;});
let nextId = 0;
const pending = new Map(), events = [];
socket.onmessage = ({data}) => {
  const message = JSON.parse(data);
  if (!message.id) {events.push(message); return;}
  const item = pending.get(message.id);
  if (!item) return;
  pending.delete(message.id); clearTimeout(item.timer);
  if (message.error) item.reject(new Error(JSON.stringify(message.error)));
  else item.resolve(message.result);
};
function call(method, params={}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => {pending.delete(id); reject(new Error(`CDP timeout: ${method}`));}, 10000);
    pending.set(id, {resolve,reject,timer});
    socket.send(JSON.stringify({id, method, params}));
  });
}
async function evaluate(expression) {
  const result = await call('Runtime.evaluate', {expression,awaitPromise:true,returnByValue:true});
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
async function event(method) {
  for (let retry=0;retry<200;retry++) {
    const index=events.findIndex(item=>item.method===method);
    if(index>=0)return events.splice(index,1)[0].params;
    await new Promise(resolve=>setTimeout(resolve,10));
  }
  throw new Error(`Missing browser event: ${method}`);
}
async function settledStage(index) {
  await evaluate(`(async()=>{
    const stage=document.querySelectorAll('.qt-stage')[${index}];
    const deadline=performance.now()+3000;
    while(stage.hidden || stage.style.willChange) {
      if(performance.now()>deadline)throw new Error('Slide did not settle');
      await new Promise(resolve=>setTimeout(resolve,10));
    }
    await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
  })()`);
}
const results=[];
try {
  await call('Page.enable'); await call('Runtime.enable'); await call('Animation.enable');
  for (const item of cases) {
    await call('Emulation.setDeviceMetricsOverride', {
      width:item.width,height:item.height,deviceScaleFactor:1,mobile:false,
    });
    await call('Emulation.setDefaultBackgroundColorOverride',{color:{r:0,g:0,b:0,a:0}});
    await call('Animation.setPlaybackRate',{playbackRate:0});
    events.length=0;
    await call('Page.navigate',{url:item.url});
    await event('Page.loadEventFired');
    await evaluate(`(async()=>{
      await document.fonts.ready;
      await Promise.all(Array.from(document.images, image=>image.decode()));
      await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
    })()`);
    await settledStage(0);
    for(let index=0;index<item.slide;index++) {
      await evaluate(`document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}))`);
      await settledStage(index+1);
    }
    let seek=null;
    if(item.time!==null) {
      events.length=0;
      await evaluate(`document.body.click()`);
      const {animation}=await event('Animation.animationStarted');
      if(animation.type!=='CSSAnimation')throw new Error(`Expected a real CSS animation: ${animation.type}`);
      await call('Animation.seekAnimations',{animations:[animation.id],currentTime:item.time*1000});
      seek={animation_id:animation.id,seconds:item.time,method:'Animation.seekAnimations'};
    }
    await evaluate(`new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))`);
    if(item.omit) {
      await evaluate(`(()=>{
        const stage=document.querySelectorAll('.qt-stage')[${item.slide}];
        const element=stage.querySelector('[data-qt-motion-key="${item.omit}"]');
        if(!element)throw new Error('Missing negative-control target');
        element.remove();
      })()`);
      await evaluate(`new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))`);
    }
    const observed=await evaluate(`(()=>{
      const stage=document.querySelectorAll('.qt-stage')[${item.slide}];
      const box=stage.getBoundingClientRect();
      return {x:box.x,y:box.y,width:box.width,height:box.height,dpr:devicePixelRatio,
        fonts_status:document.fonts.status,
        font_faces:Array.from(document.fonts,face=>({family:face.family,status:face.status})),
        stage_count:document.querySelectorAll('.qt-stage').length,
        visibility:getComputedStyle(stage).visibility};
    })()`);
    if(observed.dpr!==1 || Math.abs(observed.width-item.width)>0.01 || Math.abs(observed.height-item.height)>0.01)
      throw new Error(`Stage is scaled or stretched: ${JSON.stringify(observed)}`);
    if(item.expects_embedded_font && (!observed.font_faces.length || observed.font_faces.some(face=>face.status!=='loaded')))
      throw new Error(`Embedded font did not load: ${JSON.stringify(observed.font_faces)}`);
    const {data}=await call('Page.captureScreenshot',{format:'png',fromSurface:true,
      clip:{x:observed.x,y:observed.y,width:item.width,height:item.height,scale:1}});
    await writeFile(item.screenshot,Buffer.from(data,'base64'));
    results.push({name:item.name,screenshot:item.screenshot,observed,seek});
  }
  console.log(JSON.stringify({browser:{product:version.Browser,protocol:version['Protocol-Version'],user_agent:version['User-Agent']},node:process.version,cases:results}));
} finally {
  await call('Page.close').catch(()=>{});
  socket.close();
}
