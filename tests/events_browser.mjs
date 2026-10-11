import {chromium} from 'playwright';
import {createServer} from 'node:net';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
const server=createServer();await new Promise(r=>server.listen(0,'127.0.0.1',r));
const port=server.address().port;await new Promise(r=>server.close(r));
const browser=await chromium.launch({headless:true,args:[`--remote-debugging-port=${port}`],...process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{}});
let child;
try {
 const page=await browser.newPage();const html='<div id="gameScreen" style="width:800px;height:600px"></div><input id="chat">';
 await page.goto('data:text/html,'+encodeURIComponent(html));await page.bringToFront();
 const session=await page.context().newCDPSession(page);const {targetInfo}=await session.send('Target.getTargetInfo');
 child=spawn(process.env.PYTHON_EXE||'python',['-B','-u',fileURLToPath(new URL('browser_event_bridge.py',import.meta.url)),`http://127.0.0.1:${port}`,targetInfo.targetId]);
 const messages=[];let buffer='',errors='';
 child.stderr.on('data',d=>errors+=d);
 child.stdout.on('data',d=>{buffer+=d;let i;while((i=buffer.indexOf('\n'))>=0){messages.push(JSON.parse(buffer.slice(0,i)));buffer=buffer.slice(i+1);}});
 const wait=async predicate=>{const deadline=Date.now()+5000;while(Date.now()<deadline){const found=messages.find(predicate);if(found)return found;if(child.exitCode!==null)throw Error(errors);await new Promise(r=>setTimeout(r,5));}throw Error(`Timed out: ${errors}`)};
 await wait(m=>m.kind==='ready');await page.keyboard.press('q');
 const first=await wait(m=>m.kind==='shot');const latency=first.received-first.at;
 assert.equal(first.key,81);assert.equal(first.count,1);assert(latency>=-50&&latency<750);
 await page.keyboard.press('Control+q');await page.locator('#chat').focus();await page.keyboard.press('q');
 await new Promise(r=>setTimeout(r,80));assert.equal(messages.filter(m=>m.kind==='shot').length,1);
 child.stdin.write(JSON.stringify({key:'R'})+'\n');await wait(m=>m.kind==='configured');
 await page.locator('#chat').evaluate(e=>e.blur());await page.keyboard.press('q');await page.keyboard.press('r');
 const custom=await wait(m=>m.kind==='shot'&&m.key===82);assert.equal(custom.count,1);
 await page.reload();await page.keyboard.press('r');
 await wait(m=>m.kind==='shot'&&m.key===82&&m.at>custom.at);
 console.log(`Python/CDP shortcut, custom key, chat, modifiers and reload passed; event latency ${latency.toFixed(1)} ms`);
} finally {
 if(child){child.stdin.end(JSON.stringify({stop:true})+'\n');await new Promise(r=>setTimeout(r,150));if(child.exitCode===null)child.kill();}
 await browser.close();
}
