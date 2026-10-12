import {chromium} from 'playwright';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const source=await fs.readFile(new URL('../gunbound_weather.py',import.meta.url),'utf8');
const expression=source.match(/WEATHER_ZONES_JS=r"""([\s\S]*?)"""/)[1];
const browser=await chromium.launch({headless:true,...process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{}});
try {
 const page=await browser.newPage();
 const evaluate=value=>page.evaluate(({expression,value})=>{window.s={weatherZones:value};return eval(expression)},{expression,value});
 assert.deepEqual(await evaluate(JSON.stringify([{kind:'tornado',x:764,size:122}])),[{kind:'tornado',x:764,size:122}]);
 assert.deepEqual(await evaluate(JSON.stringify([{kind:'mirror',x:400,size:92}])),[{kind:'mirror',x:400,size:92}]);
 assert.deepEqual(await evaluate('not JSON'),[]);assert.deepEqual(await evaluate('{}'),[]);
 assert.deepEqual(await evaluate('[]'),[]);assert.deepEqual(await evaluate([{kind:'mirror',x:200,size:100}]),[{kind:'mirror',x:200,size:100}]);
 assert.deepEqual(await evaluate(JSON.stringify([{kind:'mirror',x:'200'}])),[]);
 assert.deepEqual(await evaluate(JSON.stringify([{kind:'random',x:500,size:128,variant:'mirror',revealed:false}])),[{kind:'random',x:500,size:128,variant:'mirror',revealed:false}]);
 console.log('PASS: real weatherZones JSON shape, arrays, malformed input and numeric positions');
}finally{await browser.close()}
