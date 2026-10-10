const headers={'Content-Type':'application/json','Access-Control-Allow-Origin':Deno.env.get('PANEL_ORIGIN')||'https://configure-your-panel.invalid','Access-Control-Allow-Headers':'authorization,apikey,content-type','Access-Control-Allow-Methods':'POST,OPTIONS','Vary':'Origin'};
Deno.serve(async request=>{
 if(request.method==='OPTIONS')return new Response(null,{headers});
 if(request.method!=='POST')return new Response(JSON.stringify({error:'Método inválido'}),{status:405,headers});
 const url=Deno.env.get('SUPABASE_URL')!,key=Deno.env.get('SUPABASE_ANON_KEY')!,service=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
 const authorization=request.headers.get('authorization')||'';
 try{
  const admin=await fetch(url+'/rest/v1/rpc/is_admin',{method:'POST',headers:{apikey:key,Authorization:authorization,'Content-Type':'application/json'},body:'{}'});
  if(!admin.ok||await admin.json()!==true)return new Response(JSON.stringify({error:'Solo administrador'}),{status:403,headers});
  const body=await request.json();
  if(typeof body.email!=='string'||!/^\S+@\S+\.\S+$/.test(body.email)||typeof body.password!=='string'||body.password.length<12||!Number.isInteger(body.months)||body.months<1||body.months>24)return new Response(JSON.stringify({error:'Correo, contraseña o meses inválidos'}),{status:400,headers});
  const created=await fetch(url+'/auth/v1/admin/users',{method:'POST',headers:{apikey:service,Authorization:'Bearer '+service,'Content-Type':'application/json'},body:JSON.stringify({email:body.email,password:body.password,email_confirm:true})});
  const user=await created.json();if(!created.ok)return new Response(JSON.stringify({error:'No se pudo crear la cuenta. Comprueba si ya existe.'}),{status:400,headers});
  const granted=await fetch(url+'/rest/v1/rpc/admin_grant',{method:'POST',headers:{apikey:key,Authorization:authorization,'Content-Type':'application/json'},body:JSON.stringify({target:user.id,months:body.months,request_id:body.request_id})});
  if(!granted.ok){await fetch(url+'/auth/v1/admin/users/'+user.id,{method:'DELETE',headers:{apikey:service,Authorization:'Bearer '+service}});return new Response(JSON.stringify({error:'No se pudo activar el acceso; la cuenta creada se retiró.'}),{status:400,headers});}
  return new Response(JSON.stringify({id:user.id,...await granted.json()}),{headers});
 }catch{return new Response(JSON.stringify({error:'No se pudo completar la creación.'}),{status:500,headers});}
});
