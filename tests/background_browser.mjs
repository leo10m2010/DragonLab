import {chromium} from 'playwright';
import {createServer} from 'node:net';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
const server=createServer();await new Promise(r=>server.listen(0,'127.0.0.1',r));const port=server.address().port;await new Promise(r=>server.close(r));
const browser=await chromium.launch({headless:false,args:[`--remote-debugging-port=${port}`],...process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{}});
try {
 const context=await browser.newContext();const page=await context.newPage();await page.route('https://dragonbound.net/**',route=>route.fulfill({contentType:'text/html',body:'<div id="gameScreen" style="width:800px;height:600px"></div><script>window.keys=[];addEventListener("keydown",e=>window.keys.push(e.key))</script>'}));
 await page.goto('https://dragonbound.net/#server-8');
 const other=await context.newPage();await other.goto('data:text/html,<h1>Other task</h1>');await other.evaluate(()=>{window.keys=[];addEventListener('keydown',e=>window.keys.push(e.key))});await other.bringToFront();
 await (await context.newCDPSession(page)).send('Emulation.setFocusEmulationEnabled',{enabled:false});
 await (await context.newCDPSession(other)).send('Emulation.setFocusEmulationEnabled',{enabled:false});
 await other.bringToFront();
 await page.waitForFunction(()=>!document.hasFocus(),null,{timeout:3000});
 assert.equal(await page.evaluate(()=>document.hasFocus()),false);
 const targets=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();const id=targets.find(t=>t.url==='https://dragonbound.net/#server-8').id;
 const python=process.env.PYTHON||'python';const child=spawn(python,['-B',fileURLToPath(new URL('./background_event_bridge.py',import.meta.url)),`http://127.0.0.1:${port}`,id]);let output='';child.stdout.on('data',b=>output+=b);child.stderr.on('data',b=>output+=b);
 const code=await new Promise(resolve=>child.on('close',resolve));assert.equal(code,0,output);
 assert.deepEqual(await page.evaluate(()=>window.keys),['ArrowUp']);assert.deepEqual(await other.evaluate(()=>window.keys),[]);
 // Chromium may focus the receiving renderer for dispatched input; the user's active page must keep focus.
 assert.equal(await other.evaluate(()=>document.hasFocus()),true);
 console.log('PASS: background CDP input reaches only its bound target; active tab keeps focus.');
} finally {await browser.close()}
