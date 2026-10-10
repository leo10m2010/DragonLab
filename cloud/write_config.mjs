import fs from 'node:fs';
const supabaseUrl=process.env.SUPABASE_URL,publicKey=process.env.SUPABASE_PUBLIC_KEY;
if(!/^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(supabaseUrl||''))throw Error('Configure SUPABASE_URL');
if(!publicKey||publicKey.startsWith('sb_secret_'))throw Error('Only a public publishable/anon key is allowed');
if(!publicKey.startsWith('sb_publishable_')){try{if(JSON.parse(Buffer.from(publicKey.split('.')[1],'base64url')).role!=='anon')throw Error();}catch{throw Error('Only the anon key is allowed');}}
fs.writeFileSync(new URL('./frontend/public/config.json',import.meta.url),JSON.stringify({supabaseUrl,publicKey,githubRepo:'leo10m2010/DragonLab'},null,2));
console.log('Public panel configuration generated.');
