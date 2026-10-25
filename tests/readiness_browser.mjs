import {chromium} from 'playwright';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const source=await fs.readFile(new URL('../training_browser.py',import.meta.url),'utf8');
const script=source.match(/UI_JS=r"""([\s\S]*?)"""/)[1];
const browser=await chromium.launch({headless:true,...process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{}});
try {
 const page=await browser.newPage();
 await page.setContent('<div id="gameScreen" style="height:120px;width:700px"></div><button id="btnShot1">1</button><button id="btnShot2">2</button><button id="btnShotSS" class="grayscale Pressed">SS</button><button id="btnPass">Pass</button><div id="myDialog"><span id="text">Dejaste el Juego Porque te retiraste de una partida, podrás empezar tu siguiente partida en 59 Segundos.</span><button id="DragonDialogOK">OK</button></div>');
 const read=()=>page.evaluate(script);
 let state=await read();assert.deepEqual(state.shotReady,[true,true,false]);assert.equal(state.controls.btnShotSS,null);assert.equal(state.controls.btnPass.control,'btnPass');assert.equal(state.retirement.seconds,59);
 await page.locator('#btnShotSS').evaluate(e=>e.className='Pressed');assert.equal((await read()).shotReady[2],true);
 await page.locator('#btnShotSS').evaluate(e=>e.disabled=true);assert.equal((await read()).shotReady[2],false);
 await page.locator('#btnShotSS').evaluate(e=>{e.disabled=false;e.setAttribute('aria-disabled','true')});assert.equal((await read()).shotReady[2],false);
 await page.locator('#text').evaluate(e=>e.textContent='¿Estás seguro de salir de la partida?');state=await read();assert.equal(state.retirement,null);assert.equal(state.notice,null);assert.equal(state.blocked,true);
 await page.locator('#text').evaluate(e=>e.textContent='Regalo Recibido Has recibido un regalo');assert.equal((await read()).notice.kind,'gift-received');
 console.log('PASS: SS cooldown/readiness, explicit Pass, retirement wait and unknown-exit dialog distinction');
} finally {await browser.close()}
