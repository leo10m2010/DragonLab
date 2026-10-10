import {chromium} from 'playwright';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const source=await fs.readFile(new URL('../automatic.py',import.meta.url),'utf8');
const template=source.match(/GESTURE_JS = r'''([\s\S]*?)'''/)[1];
const script=template.replace('__OWNER__','"fixture"').replace('__KEY__','81');
const browser=await chromium.launch({headless:true,...process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{}});
try {
 const page=await browser.newPage();
 await page.setContent('<div id="gameScreen" style="width:800px;height:600px"><canvas></canvas></div><input id="chat">');
 await page.bringToFront();
 const state=()=>page.evaluate(script);
 assert.equal((await state()).count,0);
 await page.keyboard.press('q');assert.equal((await state()).count,1);
 await page.evaluate(()=>window.dispatchEvent(new KeyboardEvent('keydown',{key:'q',keyCode:81})));
 assert.equal((await state()).count,1);
 await page.keyboard.press('Control+q');assert.equal((await state()).count,1);
 await page.keyboard.down('q');await page.keyboard.down('q');await page.keyboard.up('q');assert.equal((await state()).count,2);
 await page.locator('#chat').focus();await page.keyboard.press('q');assert.equal((await state()).count,2);
 await page.locator('#chat').evaluate(e=>e.blur());
 const custom=script.replace('key=81','key=82');
 await page.evaluate(custom);await page.keyboard.press('q');assert.equal((await page.evaluate(custom)).count,0);
 await page.keyboard.press('r');assert.equal((await page.evaluate(custom)).count,1);
 await page.locator('#gameScreen').evaluate(e=>e.style.display='none');
 await page.keyboard.press('r');assert.equal((await page.evaluate(custom)).count,1);
 console.log('PASS: trusted Q once; no repeat, synthetic event, modifiers/chat/lobby; custom R replaces Q.');
}finally{await browser.close();}
