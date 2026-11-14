import {chromium} from 'playwright';
import {createServer} from 'node:http';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
const server=createServer((req,res)=>res.end(req.url.startsWith('/game')?'<div id="gameScreen" style="width:800px;height:600px"></div>':'<div>Sala</div>'));
await new Promise(r=>server.listen(0,'127.0.0.1',r));const origin=`http://127.0.0.1:${server.address().port}`;
const probe=createServer();await new Promise(r=>probe.listen(0,'127.0.0.1',r));const port=probe.address().port;await new Promise(r=>probe.close(r));
const profile=await mkdtemp(join(tmpdir(),'dragonlab-tab-test-'));
const chrome=spawn(process.env.CHROME_PATH||chromium.executablePath(),['--headless=new','--no-sandbox','--no-first-run','--no-default-browser-check',`--user-data-dir=${profile}`,`--remote-debugging-port=${port}`,'about:blank'],{windowsHide:true,stdio:'ignore'});
let browser,child;
try{
 const endpoint=`http://127.0.0.1:${port}`;const deadline=Date.now()+10000;while(true){try{if((await fetch(endpoint+'/json/version')).ok)break}catch{}if(chrome.exitCode!==null||Date.now()>deadline)throw Error('Fixture Chrome did not start');await new Promise(r=>setTimeout(r,30))}
 // Default CDP context with no overrides: Playwright normally makes every page
 // report focused and visible, which cannot validate real tab selection.
 browser=await chromium.connectOverCDP(endpoint,{noDefaults:true});const context=browser.contexts()[0];const lobby=await context.newPage();await lobby.goto(origin+'/lobby');const game=await context.newPage();await game.goto(origin+'/game');
 const id=async page=>{const s=await page.context().newCDPSession(page);try{return (await s.send('Target.getTargetInfo')).targetInfo.targetId}finally{await s.detach()}};const first=await id(game);
 child=spawn(process.env.PYTHON_EXE||'python',['-B','-u',fileURLToPath(new URL('tab_target_bridge.py',import.meta.url)),`http://127.0.0.1:${port}`]);let buffer='',errors='';const messages=[];
 child.stderr.on('data',d=>errors+=d);child.stdout.on('data',d=>{buffer+=d;let i;while((i=buffer.indexOf('\n'))>=0){messages.push(JSON.parse(buffer.slice(0,i)));buffer=buffer.slice(i+1)}});
 const wait=async index=>{const end=Date.now()+10000;while(messages.length<=index){if(child.exitCode!==null||Date.now()>end)throw Error(errors||'Timed out');await new Promise(r=>setTimeout(r,10))}const m=messages[index];assert(!m.error,m.error);return m};await wait(0);
 const select=async preferred=>{const n=messages.length;child.stdin.write(JSON.stringify({preferred})+'\n');return (await wait(n)).id};
 await lobby.bringToFront();assert.equal(await select(),first);
 const second=await context.newPage();await second.goto(origin+'/game2');const secondId=await id(second);await second.bringToFront();await second.waitForFunction(()=>document.hasFocus()&&document.visibilityState==='visible');assert.equal(await select(first),secondId);
 await second.close();assert.equal(await select(secondId),first);
 console.log('PASS: two same-host tabs select running game, follow focused game and recover after its tab closes.');
}finally{if(child){child.stdin.end('{"stop":true}\n');await new Promise(r=>setTimeout(r,50));if(child.exitCode===null)child.kill()}if(browser)await browser.close();if(chrome.exitCode===null)chrome.kill();await new Promise(r=>setTimeout(r,150));if(resolve(profile).startsWith(resolve(join(tmpdir(),'dragonlab-tab-test-'))))await rm(profile,{recursive:true,force:true,maxRetries:3,retryDelay:100});await new Promise(r=>server.close(r));}
