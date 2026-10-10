"""Small loopback-only CDP client. Never sends game actions or reads storage."""
import socket,base64,os,json,struct,hashlib,time,urllib.request,urllib.parse

class CDP:
    def __init__(self,endpoint='http://127.0.0.1:9222',target_id=None,hostname='dragonbound.net'):
        p=urllib.parse.urlparse(endpoint)
        if p.hostname not in ('127.0.0.1','localhost','::1') or p.scheme!='http':
            raise ValueError('La conexión al navegador debe ser local')
        with urllib.request.urlopen(endpoint+'/json/list',timeout=2) as r:targets=json.load(r)
        target=next((t for t in targets if t.get('type')=='page' and (t.get('id')==target_id if target_id is not None else urllib.parse.urlparse(t.get('url','')).hostname==hostname)),None)
        if not target:raise RuntimeError('La página seleccionada no está abierta en el navegador de depuración')
        self.target={k:target.get(k) for k in ('id','title','url')}
        p=urllib.parse.urlparse(target['webSocketDebuggerUrl'])
        if p.hostname not in ('127.0.0.1','localhost','::1'):raise ValueError('WebSocket no local')
        self.sock=socket.create_connection((p.hostname,p.port),timeout=4)
        key=base64.b64encode(os.urandom(16)).decode()
        path=p.path+('?' + p.query if p.query else '')
        self.sock.sendall((f'GET {path} HTTP/1.1\r\nHost: {p.hostname}:{p.port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        raw=b''
        while b'\r\n\r\n' not in raw:raw+=self.sock.recv(4096)
        header,self.buf=raw.split(b'\r\n\r\n',1)
        expected=base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
        if b' 101 ' not in header.split(b'\r\n')[0] or expected not in header:
            self.sock.close();raise RuntimeError('El navegador rechazó la conexión')
        self.counter=0;self.game=None;self.renderer=None;self.terrain_cache=None;self.terrain_clock=0;self.terrain_turn=None
        self.call('Runtime.enable')

    def close(self):self.sock.close()
    def read(self,n):
        while len(self.buf)<n:
            part=self.sock.recv(max(4096,n-len(self.buf)))
            if not part:raise ConnectionError('El navegador se cerró')
            self.buf+=part
        out,self.buf=self.buf[:n],self.buf[n:];return out
    def send(self,payload,opcode=1):
        mask=os.urandom(4);n=len(payload)
        header=bytes([0x80|opcode,0x80|n]) if n<126 else bytes([0x80|opcode,0x80|126])+struct.pack('!H',n) if n<65536 else bytes([0x80|opcode,0x80|127])+struct.pack('!Q',n)
        self.sock.sendall(header+mask+bytes(v^mask[i%4] for i,v in enumerate(payload)))
    def message(self):
        parts=[]
        while True:
            a,b=self.read(2);opcode=a&15;n=b&127
            if n==126:n=struct.unpack('!H',self.read(2))[0]
            elif n==127:n=struct.unpack('!Q',self.read(8))[0]
            if n>8_000_000:raise RuntimeError('Respuesta demasiado grande')
            mask=self.read(4) if b&128 else None
            body=self.read(n)
            if mask:body=bytes(v^mask[i%4] for i,v in enumerate(body))
            if opcode==8:raise ConnectionError('Conexión cerrada')
            if opcode==9:self.send(body,10);continue
            if opcode==10:continue
            parts.append(body)
            if a&128:return json.loads(b''.join(parts))
    def call(self,method,params=None):
        self.counter+=1;ident=self.counter
        self.send(json.dumps({'id':ident,'method':method,'params':params or {}}).encode())
        while True:
            r=self.message()
            if r.get('id')!=ident:continue
            if 'error' in r:raise RuntimeError(r['error'].get('message','Error CDP'))
            return r.get('result',{})
    def props(self,oid):return self.call('Runtime.getProperties',{'objectId':oid,'ownProperties':True})

    def discover(self):
        expression='[window,document,...document.querySelectorAll("canvas")].flatMap(e=>Object.getOwnPropertyNames(e).filter(k=>k.startsWith("jQuery")).flatMap(k=>Object.entries(e[k]?.events||{}).filter(([k])=>/key/.test(k)).flatMap(([k,v])=>v.map(x=>x.handler))))'
        r=self.call('Runtime.evaluate',{'expression':expression,'objectGroup':'dragonlab-discovery','timeout':2000})
        oid=r.get('result',{}).get('objectId')
        if not oid:return None
        handles=self.props(oid).get('result',[])
        seen=set()
        for h in handles:
            if not h['name'].isdigit():continue
            fun=h.get('value',{});fid=fun.get('objectId')
            if not fid or fun.get('description') in seen:continue
            seen.add(fun.get('description'))
            scopes=next((p for p in self.props(fid).get('internalProperties',[]) if p['name']=='[[Scopes]]'),None)
            if not scopes:continue
            for scope in self.props(scopes['value']['objectId']).get('result',[])[:5]:
                sv=scope.get('value',{})
                if not scope['name'].isdigit() or 'Global' in sv.get('description',''):continue
                candidates=self.props(sv['objectId']).get('result',[])
                # Consider small local closures only; never inventory page-wide account data.
                if len(candidates)>80:continue
                for c in candidates:
                    v=c.get('value',{})
                    if v.get('type')!='object' or not v.get('objectId') or v.get('subtype') in ('node','regexp','array'):continue
                    pp=self.props(v['objectId']).get('result',[])
                    names={x['name'] for x in pp}
                    if ('players' in names or 'player_list' in names) and names.intersection({'wind','windPower','wind_meter','windMeter','turn','camera','ground'}):
                        self.game=v['objectId'];return self.game
                    for child in pp:
                        if child['name'] not in ('game','g_game','currentGame','game_state'):continue
                        cv=child.get('value',{})
                        if not cv.get('objectId'):continue
                        nn={x['name'] for x in self.props(cv['objectId']).get('result',[])}
                        if 'players' in nn:self.game=cv['objectId'];return self.game
        return None

    def sample(self):
        if not self.game and not self.discover():
            self.call('Runtime.releaseObjectGroup',{'objectGroup':'dragonlab-discovery'})
            return {'status':'waiting','reason':'Navegador conectado; esperando una partida compatible'}
        if not self.renderer:
            rp=next((x for x in self.props(self.game).get('result',[]) if x['name']=='dragon2d'),None)
            if rp and rp.get('value',{}).get('objectId'):
                fp=next((x for x in self.props(rp['value']['objectId']).get('result',[]) if x['name']=='SetWind'),None)
                if fp and fp.get('value',{}).get('objectId'):
                    sp=next((x for x in self.props(fp['value']['objectId']).get('internalProperties',[]) if x['name']=='[[Scopes]]'),None)
                    if sp:
                        for scope in self.props(sp['value']['objectId']).get('result',[]):
                            sv=scope.get('value',{})
                            if not scope['name'].isdigit() or 'Global' in sv.get('description',''):continue
                            vs=self.props(sv['objectId']).get('result',[])
                            if len(vs)>100:continue
                            for v in vs:
                                vv=v.get('value',{})
                                if vv.get('description')=='Dragon2D' and vv.get('objectId'):
                                    self.renderer=vv['objectId'];break
        # Read only numeric game fields and player labels; invoke no game functions.
        terrain_due=time.monotonic()-self.terrain_clock>=1.5
        serializer='''function(renderer,readTerrain){
          const own=(o,k)=>{const d=o&&Object.getOwnPropertyDescriptor(o,k);return d&&("value"in d)?d.value:undefined};
          const pick=(o,keys)=>{for(const k of keys){let v=own(o,k);if(v!==undefined)return v}return null};
          const num=v=>typeof v==="number"&&Number.isFinite(v)?v:null;
          let list=pick(this,["players","player_list"]);let entries=list&&typeof list==="object"?Object.entries(list):[];
          const flag=v=>v===true||v===1;
          const players=entries.slice(0,16).filter(([k,p])=>p&&typeof p==="object").map(([k,p],i)=>({
            id:pick(p,["n","number","id"])??(Number.isFinite(Number(k))?Number(k):k),name:String(pick(p,["name","nick"])??("Jugador "+(i+1))).slice(0,60),
            x:num(pick(p,["x","posX"])),y:num(pick(p,["y","posY"])),
            angle:(()=>{let a=num(pick(p,["ang"])),b=num(pick(p,["body"])),look=num(pick(p,["look"]));return a!==null&&b!==null&&look!==null?(look===0?a+b:a-b):num(pick(p,["angle","display_angle"]))})(),rawAngle:num(pick(p,["ang"])),body:num(pick(p,["body_angle","bodyAngle","body"])),
            look:num(pick(p,["look","direction"])),mobile:num(pick(p,["mobile","mobile_id"])),
            dead:flag(pick(p,["dead","is_dead","isDead"]))||[false,0].includes(pick(p,["is_alive"])),muzzles:[["aim_s1_ang","aim_s1_len"],["aim_s2_ang","aim_s2_len"],["aim_ss_ang","aim_ss_len"]].map(keys=>({angle:num(pick(p,[keys[0]])),radius:num(pick(p,[keys[1]]))})),muzzleX:num(pick(p,["aim_circle_x"])),muzzleY:num(pick(p,["aim_circle_y"])),shot:num(pick(p,["selected_shot"])),team:pick(p,["team"]),isHero:flag(pick(p,["is_me","isMe","is_hero"]))}));
          let meter=pick(renderer,["wind_meter","windMeter"]),cam=renderer;
          const numeric=(o,keys)=>Object.fromEntries(keys.map(k=>[k,num(own(o,k))]).filter(x=>x[1]!==null));
          const container=pick(renderer,["camera_container"]),matrix=pick(container,["worldTransform"]),engine=pick(renderer,["renderer"]),view=pick(engine,["view"])??pick(renderer,["view"]);
          const cm=matrix?numeric(matrix,["a","b","c","d","tx","ty"]):null;
          const worldPosition=(shot)=>{
            const anim=pick(shot,["anim_container"]),pos=pick(anim,["position"]),px=num(pick(pos,["x"])),py=num(pick(pos,["y"]));
            if(px!==null&&py!==null)return [px,py];
            const trace=pick(shot,["trace_divs"]);if(Array.isArray(trace)&&trace.length){let x=num(pick(trace[0],["x"])),y=num(pick(trace[0],["y"]));if(x!==null&&y!==null)return [x,y];}
            let child=anim;if(!child){let children=pick(shot,["children"]);child=Array.isArray(children)?children[0]:null;}
            const m=pick(child,["worldTransform"]),x=num(pick(m,["tx"])),y=num(pick(m,["ty"]));
            if(!cm||x===null||y===null)return null;
            const det=cm.a*cm.d-cm.b*cm.c;if(!Number.isFinite(det)||Math.abs(det)<1e-9)return null;
            return [(cm.d*(x-cm.tx)-cm.c*(y-cm.ty))/det,(-cm.b*(x-cm.tx)+cm.a*(y-cm.ty))/det];
          };
          let rawShots=pick(this,["bullets","projectiles","shots","bullet_list"]);
          let shots=(Array.isArray(rawShots)?rawShots:[]).slice(0,64).map((s,i)=>{
            let data=pick(s,["shot"]),start=pick(data,["s"]),position=worldPosition(s);
            if(Array.isArray(start)&&start.length>=6&&start.slice(0,6).every(v=>typeof v==='number'&&Number.isFinite(v)))return {
              native:true,id:num(pick(s,["_dragonclock_id"]))??start.slice(0,6).join('/'),start:start.slice(0,6),
              elapsed:num(pick(s,["total_elapsed_time"])),duration:num(pick(data,["time"])),
              x:position?position[0]:null,y:position?position[1]:null,
              jumps:(pick(data,["jumps"])||[]).slice(0,128).filter(j=>Array.isArray(j)&&j.length>=5).map(j=>j.slice(0,8).map(num)),
              orbit:Array.isArray(pick(data,["orbit"]))?pick(data,["orbit"]).slice(0,4).map(num):null,wave:num(pick(data,["wave"])),path:Array.isArray(pick(data,["path"]))?pick(data,["path"]).slice(0,12000).map(num):null,
              bulletId:num(pick(data,["img"])),delay:num(start[6])??0,auxiliary:!!pick(data,["is_lightning"])||!!pick(data,["thor"]),
              shotType:num(pick(data,["shot_type"])),metadata:numeric(pick(data,["start"]),["power","player","player_n","mobile","selectedShot","angle"])};
            return numeric(s,["id","x","y","vx","vy","ax","ay","angle","power","mobile","bullet_id","time","time_ms"]);
          });
          // Rendered columns describe the present turn; after_shot_* can already
          // contain the following turn while a bullet is flying.
          let columns=pick(renderer,["weathers"]),weatherData=[];
          if(Array.isArray(columns))weatherData=columns.slice(0,32).map(w=>({typeId:num(pick(w,["weather_type"])),x:num(pick(pick(w,["position"]),["x"]))??num(pick(w,["x"])),size:num(pick(w,["size"]))})).filter(w=>w.typeId!==null&&w.x!==null&&w.size!==null);
          else{let weather=pick(this,["after_shot_active_weathers","active_weathers"]);if(Array.isArray(weather))weatherData=weather.slice(0,32).filter(Array.isArray).map(w=>({typeId:num(w[0]),x:num(w[1]),size:num(w[2]),resolvedTypeId:num(w[3])})).filter(w=>w.x!==null&&w.typeId!==null);}
          let ground=pick(this,["terrain","ground"]),surface=pick(ground,["heights","heightmap","surface"]);
          let terrain=null;
          if(readTerrain&&ground){let image=pick(ground,["imageData"]),pixels=image?.data,w=num(pick(ground,["w","width"]))??image?.width,h=num(pick(ground,["h","height"]))??image?.height;
            if(pixels&&w>0&&h>0&&w*h<=4000000){let rows=[];for(let y=0;y<h;y++){let row=[],inside=false;for(let x=0;x<w;x++){let opaque=pixels[(y*w+x)*4+3]>0;if(opaque!==inside){row.push(x);inside=opaque;}}if(inside)row.push(w);rows.push(row);}terrain={width:w,height:h,originX:0,originY:0,rows};}
            else if(Array.isArray(surface))terrain={surface:surface.slice(0,4096).map(num),originX:num(pick(ground,["originX"]))??0,originY:num(pick(ground,["originY"]))??0};}
          return {status:pick(this,["destructed"])===true?"waiting":"live",players,shots,weather:weatherData,terrain,selectedShot:num(pick(this,["selectedShot","selected_shot"])),currentPower:num(pick(this,["curUIPower","power"])),wind:num(pick(this,["windPower","wind_power","wind"]))??num(pick(meter,["value","power"])),
            windAngle:num(pick(this,["windAngle","wind_angle"]))??num(pick(renderer,["wind_angle"]))??num(pick(meter,["angle","ang"])),
            rendererWind:num(pick(renderer,["wind_power"])),
            turn:num(pick(this,["turn_number","turn","currentTurn"])),activePlayer:num(pick(this,["turn"])),heroId:pick(this,["my_player","myPlayerNumber","my_player_number"]),
            camera:cam?{x:num(pick(cam,["camera_x"])),y:num(pick(cam,["camera_y"])),scale:num(pick(cam,["cameraScale"])),matrix:cm,renderWidth:num(pick(engine,["width"]))??(view?num(view.width):null),renderHeight:num(pick(engine,["height"]))??(view?num(view.height):null),viewWidth:num(pick(renderer,["original_w"])),viewHeight:num(pick(renderer,["original_h"]))}:null};
        }'''
        args=([{'objectId':self.renderer}] if self.renderer else [{'value':None}])+[{'value':terrain_due}]
        r=self.call('Runtime.callFunctionOn',{'objectId':self.game,'functionDeclaration':serializer,'arguments':args,'returnByValue':True,'objectGroup':'dragonlab-live'})
        if 'exceptionDetails' in r:self.game=None;self.renderer=None;raise RuntimeError('La estructura del juego cambió')
        sample=r['result'].get('value',{'status':'waiting'})
        if sample.get('status')!='live':
            self.game=None;self.renderer=None;self.terrain_cache=None;self.terrain_clock=0
            self.call('Runtime.releaseObjectGroup',{'objectGroup':'dragonlab-discovery'})
            return {'status':'waiting','reason':'Cambio de partida; detectando el nuevo mapa'}
        if sample.get('terrain'):
            self.terrain_cache=sample['terrain'];self.terrain_clock=time.monotonic()
        else:sample['terrain']=self.terrain_cache
        if self.terrain_turn!=sample.get('turn'):self.terrain_clock=0;self.terrain_turn=sample.get('turn')
        if sample.get('wind') is None:sample['wind']=sample.get('rendererWind')
        sample.pop('rendererWind',None)
        return sample
