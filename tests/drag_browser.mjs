import {chromium} from 'playwright';
import {createServer} from 'node:net';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';

const server=createServer();
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const port=server.address().port;
await new Promise(resolve=>server.close(resolve));
const browser=await chromium.launch({headless:true,args:[`--remote-debugging-port=${port}`],...process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{}});

function fixture(power,sensitivity,previousSensitivity){
 return `<!doctype html><style>html,body{margin:0}#gameScreen{width:1000px;height:600px;background:#123}</style><div id="gameScreen"></div><script>
 const requested=${power},freshSensitivity=${sensitivity};
 window.fixture={state:{turn:0,hero:0,turnNumber:1,shot:0,mode:'drag',over:false,moving:false,busy:false,power:requested,dragSens:${previousSensitivity},dragStartX:null,dragUpdates:0,dragPointX:null,awaitingAck:false},events:[],releases:[]};
 const f=window.fixture;
 for(const type of ['mousedown','mousemove','mouseup','keydown'])addEventListener(type,event=>{
  f.events.push({type,trusted:event.isTrusted,x:event.clientX,y:event.clientY,pageX:event.pageX,buttons:event.buttons,at:performance.now()});
  if(type==='mousedown'){
   if(!event.isTrusted||event.button!==0||event.target.id!=='gameScreen')throw Error('Unexpected drag start');
   f.state.busy=true;f.state.dragSens=freshSensitivity;f.state.dragStartX=event.pageX;f.state.dragPointX=event.pageX;f.state.dragUpdates=0;
  }else if(type==='mousemove'&&f.state.busy){
   if(!event.isTrusted||event.buttons!==1)throw Error('Drag move is not trusted or not held');
   const x=event.pageX;
   // Previous force intentionally equals the requested value. Native feedback
   // acknowledges this trusted movement only later, never on dispatch alone.
   f.state.awaitingAck=true;
   setTimeout(()=>{if(!f.state.busy)return;f.state.dragPointX=x;f.state.dragUpdates++;f.state.power=Math.round((x-f.state.dragStartX)/f.state.dragSens);f.state.awaitingAck=false},90);
  }else if(type==='mouseup'){
   f.releases.push({x:event.pageX,power:f.state.power,updates:f.state.dragUpdates,busy:f.state.busy});f.state.busy=false;
  }
 });
 </script>`;
}

try{
 const context=await browser.newContext({viewport:{width:1100,height:720}});
 const first=await context.newPage();
 await first.route('https://dragonbound.net/**',route=>route.fulfill({contentType:'text/html',body:fixture(150,1.37,1.65)}));
 await first.goto('https://dragonbound.net/#server-8/room-1');
 const second=await context.newPage();
 await second.route('https://dragonbound.net/**',route=>route.fulfill({contentType:'text/html',body:fixture(280,1.63,1.30)}));
 await second.goto('https://dragonbound.net/#server-8/room-2');
 const other=await context.newPage();
 await other.goto('data:text/html,<h1>Other task</h1>');
 await other.evaluate(()=>{window.inputs=[];for(const name of ['mousedown','mousemove','mouseup','keydown'])addEventListener(name,event=>window.inputs.push(event.type))});
 await other.bringToFront();
 assert.equal(await other.evaluate(()=>document.hasFocus()),true);
 const targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
 const firstId=targets.find(target=>target.url==='https://dragonbound.net/#server-8/room-1').id;
 const secondId=targets.find(target=>target.url==='https://dragonbound.net/#server-8/room-2').id;
 assert.notEqual(firstId,secondId);
 const python=process.env.PYTHON||'python';
 const child=spawn(python,['-B',fileURLToPath(new URL('./drag_event_bridge.py',import.meta.url)),`http://127.0.0.1:${port}`,firstId,secondId]);
 let output='';child.stdout.on('data',data=>output+=data);child.stderr.on('data',data=>output+=data);
 const code=await new Promise(resolve=>child.on('close',resolve));
 assert.equal(code,0,output);
 const results=JSON.parse(output).results;
 assert.deepEqual(results.map(result=>result.target),[firstId,secondId]);
 assert.deepEqual(results.map(result=>result.power),[150,280]);
 for(const [page,requested] of [[first,150],[second,280]]){
  const data=await page.evaluate(()=>window.fixture);
  assert.equal(data.releases.length,1);
  assert.equal(data.releases[0].power,requested);
  assert.ok(data.releases[0].updates>=1,'Mouse released before native movement acknowledgement');
  assert.equal(data.state.busy,false);
  assert.equal(data.events.filter(event=>event.type==='mousedown').length,1);
  assert.ok(data.events.every(event=>event.trusted));
  assert.equal(data.events.at(-1).type,'mouseup');
  assert.equal(data.events.at(-1).buttons,0);
  const finalMove=data.events.findLast(event=>event.type==='mousemove');
  assert.equal(data.events.at(-1).x,finalMove.x,'Mouseup must stay at the last drag position');
  assert.equal(data.events.filter(event=>event.type==='keydown').length,0);
 }
 assert.deepEqual(await other.evaluate(()=>window.inputs),[]);
 assert.equal(await other.evaluate(()=>document.hasFocus()),true);
 console.log('PASS: concurrent trusted Drag stays on each pinned target, waits for native power and releases at its final point; active tab remains untouched.');
}finally{await browser.close()}
