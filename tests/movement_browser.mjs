import {chromium} from 'playwright';
import {createServer} from 'node:net';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
const server=createServer();await new Promise(r=>server.listen(0,'127.0.0.1',r));const port=server.address().port;await new Promise(r=>server.close(r));
const browser=await chromium.launch({headless:true,args:[`--remote-debugging-port=${port}`],...process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{}});
const html=start=>`<div id="gameScreen" style="width:1000px;height:600px"></div><script>
 window.movement={state:{hero:0,turn:0,turnNumber:1,players:[{id:0,x:${start},y:100,body:0}]},events:[],held:false};
 const m=window.movement;
 addEventListener('keydown',e=>{m.events.push({type:e.type,key:e.key,trusted:e.isTrusted});if(e.key==='ArrowRight')m.held=true});
 addEventListener('keyup',e=>{m.events.push({type:e.type,key:e.key,trusted:e.isTrusted});if(e.key==='ArrowRight')m.held=false});
 let before=performance.now();setInterval(()=>{const now=performance.now(),dt=Math.min(.05,(now-before)/1000);before=now;if(m.held)m.state.players[0].x+=42*dt},8);
</script>`;
try{
 const context=await browser.newContext();const pages=[];
 for(const [index,start] of [[1,100],[2,700]]){const page=await context.newPage();await page.route('https://dragonbound.net/**',route=>route.fulfill({contentType:'text/html',body:html(start)}));await page.goto(`https://dragonbound.net/#server-8/room-${index}`);pages.push(page)}
 const other=await context.newPage();await other.goto('data:text/html,<h1>Other task</h1>');await other.evaluate(()=>{window.keys=[];addEventListener('keydown',e=>window.keys.push(e.key));addEventListener('keyup',e=>window.keys.push(e.key))});await other.bringToFront();
 const targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();const ids=[1,2].map(i=>targets.find(t=>t.url===`https://dragonbound.net/#server-8/room-${i}`).id);
 const child=spawn(process.env.PYTHON||'python',['-B',fileURLToPath(new URL('./movement_event_bridge.py',import.meta.url)),`http://127.0.0.1:${port}`,...ids]);let output='';child.stdout.on('data',b=>output+=b);child.stderr.on('data',b=>output+=b);
 const code=await new Promise(r=>child.on('close',r));assert.equal(code,0,output);const results=JSON.parse(output);
 for(const [index,distance] of [[0,4],[1,36]]){const data=await pages[index].evaluate(()=>window.movement);assert.equal(data.held,false);assert.deepEqual(data.events.map(e=>[e.type,e.key,e.trusted]),[['keydown','ArrowRight',true],['keyup','ArrowRight',true]]);assert.equal(results[index].stop,'distance-reached');assert.ok(results[index].actual_distance>=distance-2&&results[index].actual_distance<=distance+3,JSON.stringify(results[index]))}
 assert.ok(results[1].duration_ms>results[0].duration_ms);assert.deepEqual(await other.evaluate(()=>window.keys),[]);assert.equal(await other.evaluate(()=>document.hasFocus()),true);
 console.log('PASS: short and long native-position walks use trusted isolated keys, stop at actual distance and release both targets.');
}finally{await browser.close()}
