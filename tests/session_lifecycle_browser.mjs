// Controlled synthetic lifecycle/roster exercise; no real game, account or input.
import {chromium} from 'playwright';
import {createServer} from 'node:http';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';

const html=`<!doctype html><canvas></canvas><script>
window.fixtureRows=()=>Object.fromEntries([...Array.from({length:25},(_,i)=>['metadata'+i,{value:i}]),...Array.from({length:32},(_,i)=>['actor'+i,{n:i,x:i*20,y:100,team:i<4?1:2,is_me:i===0}])]);
window.fixtureGame={players:fixtureRows(),my_player_number:0,wind:3,windAngle:0,turn:0,ground:{surface:[1,2,3]},isGameOver:false,destructed:false};
fixtureGame.my_player=fixtureGame.players.actor0;
window.makeFixtureListener=game=>function fixtureListener(){return game.wind};
window.jQueryFixture={events:{keydown:[{handler:makeFixtureListener(fixtureGame)}]}};
</script>`;
const server=createServer((request,response)=>{response.setHeader('Content-Type','text/html');response.end(html)});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const origin=`http://127.0.0.1:${server.address().port}`;
// The debugging socket is separate from the synthetic HTTP page.
const probe=createServer();await new Promise(r=>probe.listen(0,'127.0.0.1',r));
const debugPort=probe.address().port;await new Promise(r=>probe.close(r));
const browser=await chromium.launch({headless:true,args:[`--remote-debugging-port=${debugPort}`],...process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{}});
let child;
try {
 const page=await browser.newPage();await page.goto(origin);
 const session=await page.context().newCDPSession(page);const {targetInfo}=await session.send('Target.getTargetInfo');
 child=spawn(process.env.PYTHON_EXE||'python',['-B','-u',fileURLToPath(new URL('session_event_bridge.py',import.meta.url)),`http://127.0.0.1:${debugPort}`,targetInfo.targetId]);
 const messages=[];let buffer='',errors='';
 child.stderr.on('data',data=>errors+=data);
 child.stdout.on('data',data=>{buffer+=data;let i;while((i=buffer.indexOf('\n'))>=0){messages.push(JSON.parse(buffer.slice(0,i)));buffer=buffer.slice(i+1)}});
 const wait=async predicate=>{const end=Date.now()+10000;while(Date.now()<end){const result=messages.find(predicate);if(result)return result;if(child.exitCode!==null)throw Error(errors);await new Promise(r=>setTimeout(r,10))}throw Error(`Timed out: ${errors}`)};
 await wait(m=>m.ready);
 const sample=async()=>{const before=messages.length;child.stdin.write('{"sample":true}\n');const message=await wait(m=>messages.indexOf(m)>=before);assert(!message.error,message.error);return message};
 const first=await sample();assert.equal(first.sample.status,'live');assert.equal(first.sample.players.length,32);
 assert.equal(first.sample.heroId,0);assert.equal(first.sample.rosterDiagnostics.raw,57);assert.equal(first.sample.rosterDiagnostics.enemy,28);
 assert.equal(first.sample.sourceEpoch,first.validation.sourceEpoch);
 const again=await sample();assert.equal(again.sample.sourceEpoch,first.sample.sourceEpoch);
 // Relogin can reuse the same native ID in the same game object/document.
 await page.evaluate(()=>{const hero={...fixtureGame.players.actor0,x:999};fixtureGame.players.actor0=hero;fixtureGame.my_player=hero});
 const relogin=await sample();assert.notEqual(relogin.sample.sourceEpoch,first.sample.sourceEpoch);assert.equal(relogin.sample.heroId,0);
 assert.equal(relogin.sample.sourceEpoch,relogin.validation.sourceEpoch);
 // A stale, non-destructed game remains reachable through an identical closure.
 await page.evaluate(()=>{fixtureGame.isGameOver=true;const fresh={...fixtureGame,players:new Map(Array.from({length:16},(_,i)=>[i,{id:i,x:i*10,y:200,team:i<4?1:2}])),isGameOver:false};fresh.my_player=fresh.players.get(0);window.fixtureGame=fresh;jQueryFixture.events.keydown.push({handler:makeFixtureListener(fresh)})});
 const replaced=await sample();assert.equal(replaced.sample.players.length,16);assert.equal(replaced.sample.status,'live');assert.equal(replaced.sample.heroId,0);
 assert.notEqual(replaced.sample.sourceObject,relogin.sample.sourceObject);assert.equal(replaced.sample.sourceEpoch,replaced.validation.sourceEpoch);
 // Same-document SPA navigation must invalidate even when all actor IDs match.
 await page.evaluate(()=>history.pushState({},'', '/next'));
 const spa=await sample();assert.notEqual(spa.sample.sourceEpoch,replaced.sample.sourceEpoch);assert.equal(spa.sample.sourceEpoch,spa.validation.sourceEpoch);
 await page.reload();const reload=await sample();assert.equal(reload.sample.players.length,32);assert.notEqual(reload.sample.sourceDocument,spa.sample.sourceDocument);
 // An accessor in the roster is never invoked, even before the valid actors.
 await page.evaluate(()=>{window.fixtureGetterCalls=0;Object.defineProperty(fixtureGame.players,'trap',{enumerable:true,get(){fixtureGetterCalls++;throw Error('getter executed')}})});
 const trapped=await sample();assert.equal(trapped.sample.players.length,32);assert.equal(await page.evaluate(()=>fixtureGetterCalls),0);
 console.log('Controlled CDP lifecycle passed: 32 metadata-prefixed actors, real Map, hero object ID 0 reuse, identical closures, stale game-over object, SPA navigation, reload, independent-reader epoch, no getters.');
} finally {
 if(child){child.stdin.end('{"stop":true}\n');await new Promise(r=>setTimeout(r,100));if(child.exitCode===null)child.kill()}
 await browser.close();await new Promise(r=>server.close(r));
}
