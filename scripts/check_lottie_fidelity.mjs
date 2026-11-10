// Run only against the disposable Chrome started by check_lottie_fidelity.py.
import {readFile, writeFile} from 'node:fs/promises';
import {dirname, join} from 'node:path';

const [port, manifest] = process.argv.slice(2);
const {player, cases} = JSON.parse(await readFile(manifest, 'utf8'));
const bundle = await readFile(player, 'utf8');
const origin = `http://127.0.0.1:${Number(port)}`;
const version = await (await fetch(`${origin}/json/version`)).json();
const target = await (await fetch(`${origin}/json/new?about:blank`, {method:'PUT'})).json();
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {socket.onopen=resolve; socket.onerror=reject;});
let nextId = 0;
const pending = new Map();
socket.onmessage = ({data}) => {
  const message = JSON.parse(data), item = pending.get(message.id);
  if (!item) return;
  pending.delete(message.id); clearTimeout(item.timer);
  if (message.error) item.reject(new Error(JSON.stringify(message.error)));
  else item.resolve(message.result);
};
function call(method, params={}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => {pending.delete(id); reject(new Error(`CDP timeout: ${method}`));}, 15000);
    pending.set(id, {resolve,reject,timer});
    socket.send(JSON.stringify({id, method, params}));
  });
}
async function evaluate(expression) {
  const result = await call('Runtime.evaluate', {expression,awaitPromise:true,returnByValue:true});
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
const results=[];
try {
  await call('Page.enable'); await call('Runtime.enable');
  await evaluate(`document.documentElement.innerHTML='<head></head><body style="margin:0;background:transparent"></body>'`);
  await call('Network.enable');
  await call('Network.setBlockedURLs', {urls:['http://*','https://*']});
  await evaluate(bundle);
  const playerVersion=await evaluate('lottie.version');
  for (const item of cases) {
    await call('Emulation.setDeviceMetricsOverride', {
      width:item.width,height:item.height,deviceScaleFactor:1,mobile:false,
    });
    await call('Emulation.setDefaultBackgroundColorOverride',{color:{r:0,g:0,b:0,a:0}});
    const payload=JSON.parse(await readFile(item.payload,'utf8'));
    if(item.control==='blank')payload.layers=[];
    const frame=item.control==='frozen'?0:item.frame;
    const observed=await evaluate(`(async()=>{
      if(window.animation)window.animation.destroy();
      document.body.innerHTML='<div id="stage" style="width:${item.width}px;height:${item.height}px"></div>';
      const animation=lottie.loadAnimation({
        container:document.getElementById('stage'),renderer:${JSON.stringify(item.renderer)},
        loop:false,autoplay:false,animationData:${JSON.stringify(payload)},
        rendererSettings:{preserveAspectRatio:'xMinYMin meet',clearCanvas:true},
      });
      window.animation=animation;
      await new Promise((resolve,reject)=>{
        const timer=setTimeout(()=>reject(new Error('Player load timeout')),5000);
        animation.addEventListener('data_failed',()=>{clearTimeout(timer);reject(new Error('Player data failed'));});
        animation.addEventListener('DOMLoaded',()=>{clearTimeout(timer);resolve();});
      });
      animation.setSubframe(false);
      animation.goToAndStop(${frame},true);
      await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
      const box=document.getElementById('stage').getBoundingClientRect();
      return {width:box.width,height:box.height,dpr:devicePixelRatio,
        current_frame:animation.currentFrame,total_frames:animation.totalFrames};
    })()`);
    if(observed.width!==item.width || observed.height!==item.height || observed.dpr!==1
      || Math.abs(observed.current_frame-frame)>0.00001)
      throw new Error(`Unexpected stage or clock: ${JSON.stringify(observed)}`);
    const {data}=await call('Page.captureScreenshot',{format:'png',fromSurface:true,
      clip:{x:0,y:0,width:item.width,height:item.height,scale:1}});
    const screenshot=join(dirname(manifest),`${item.name}-player.png`);
    await writeFile(screenshot,Buffer.from(data,'base64'));
    results.push({name:item.name,screenshot,observed});
  }
  console.log(JSON.stringify({browser:version.Browser,node:process.version,
    player_version:playerVersion,renderers:[...new Set(cases.map(item=>item.renderer))],cases:results}));
} finally {
  await call('Page.close').catch(()=>{});
  socket.close();
}
