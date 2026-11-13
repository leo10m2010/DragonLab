"""Small loopback-only CDP client. Never sends game actions or reads storage."""
import socket,base64,os,json,struct,hashlib,time,urllib.request,urllib.parse
from session_lifecycle import SourceLifecycle, ROSTER_HELPERS_JS, SOURCE_IDENTITY_JS

class CDP:
    def __init__(self,endpoint='http://127.0.0.1:9222',target_id=None,hostname='dragonbound.net'):
        p=urllib.parse.urlparse(endpoint)
        if p.hostname not in ('127.0.0.1','localhost','::1') or p.scheme!='http':
            raise ValueError('La conexión al navegador debe ser local')
        from loopback_http import get_json
        targets=get_json(endpoint)
        hosts=set(hostname if isinstance(hostname,(list,tuple,set)) else [hostname]) if hostname else set()
        matches=[t for t in targets if t.get('type')=='page' and (t.get('id')==target_id if target_id is not None else urllib.parse.urlparse(t.get('url','')).hostname in hosts)]
        if target_id is None and len(matches)>1:raise RuntimeError('Hay varias páginas de este juego; selecciona la pestaña exacta')
        target=matches[0] if matches else None
        if not target:raise RuntimeError('La página seleccionada no está abierta en el navegador de depuración')
        host=urllib.parse.urlparse(target.get('url','')).hostname
        if hosts and host not in hosts:raise ValueError('La pestaña seleccionada no pertenece al adaptador')
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
        self.counter=0;self.game=None;self.renderer=None;self.terrain_cache=None;self.terrain_clock=0;self.terrain_turn=None;self.terrain_inflight=False;self.endpoint=endpoint;self.event_handler=None
        self.lifecycle=SourceLifecycle(target['id'],host,getattr(self,'profile',{}).get('id','dragonbound'))
        self.source_epoch=self.lifecycle.epoch;self.allowed_hosts=hosts;self.main_frame=None;self.contexts=set();self._source_reset=False;self.discovery_clock=0;self.discovery_interval=2.;self.retired_games=[]
        self.call('Runtime.enable')
        self.call('Page.enable')
        tree=self.call('Page.getFrameTree').get('frameTree',{}).get('frame',{})
        self.main_frame=tree.get('id') or self.main_frame

    def _clear_source_cache(self):
        self.game=None;self.renderer=None;self.terrain_cache=None;self.terrain_clock=0;self.terrain_turn=None;self.terrain_inflight=False
        self.discovery_clock=0
        if hasattr(self,'controller'):self.controller=None
        self.gunbound_terrain_stamp=None;self.gunbound_terrain_clock=0

    def invalidate_source(self,reason,document=False):
        self._clear_source_cache()
        if hasattr(self,'lifecycle'):
            self.lifecycle.invalidate(reason,document);self.source_epoch=self.lifecycle.epoch
        # Native object identity and document time already distinguish sessions.
        # A second observer must not mutate the shared epoch just by connecting.
        self._source_reset=False
        if document:self.retired_games=[]

    def handle_event(self,message):
        method=message.get('method');params=message.get('params',{})
        if method=='Runtime.executionContextCreated':
            context=params.get('context',{});aux=context.get('auxData',{})
            if aux.get('isDefault') and (not self.main_frame or aux.get('frameId')==self.main_frame):self.contexts.add(context.get('id'))
        elif method=='Runtime.executionContextsCleared':
            self.contexts.clear();self.invalidate_source('contexts-cleared',True)
        elif method=='Runtime.executionContextDestroyed' and params.get('executionContextId') in self.contexts:
            self.contexts.discard(params.get('executionContextId'));self.invalidate_source('context-destroyed',True)
        elif method=='Page.frameNavigated' and not params.get('frame',{}).get('parentId'):
            frame=params['frame'];self.main_frame=frame.get('id');self.contexts.clear()
            host=urllib.parse.urlparse(frame.get('url','')).hostname
            if hasattr(self,'lifecycle'):self.lifecycle.host=host or ''
            self.invalidate_source('document-navigated',True)
        elif method=='Page.navigatedWithinDocument' and (not self.main_frame or params.get('frameId')==self.main_frame):
            self.invalidate_source('same-document-navigation',True)
        elif method in ('Inspector.detached','Target.detachedFromTarget','Target.targetDestroyed'):
            self.invalidate_source('target-detached',True)
        if self.event_handler:self.event_handler(message)

    def tag_sample(self,sample):
        if not hasattr(self,'lifecycle'):return sample
        if sample.get('sourceEpoch'):
            if self.source_epoch!=sample['sourceEpoch']:
                # Native game/hero replacement also invalidates cached map data.
                self.terrain_cache=None;self.terrain_clock=0;self.terrain_turn=None;self.terrain_inflight=False
                self.lifecycle.reason='native-source-changed'
            self.source_epoch=sample['sourceEpoch']
        else:sample['sourceEpoch']=self.source_epoch
        sample['sourceContext']={'targetId':self.lifecycle.target_id,'host':self.lifecycle.host,'adapter':self.lifecycle.adapter,'documentEpoch':self.lifecycle.document_epoch,'reason':self.lifecycle.reason}
        return sample

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
            if r.get('id')!=ident:
                self.handle_event(r)
                continue
            if 'error' in r:raise RuntimeError(r['error'].get('message','Error CDP'))
            return r.get('result',{})
    def props(self,oid):return self.call('Runtime.getProperties',{'objectId':oid,'ownProperties':True})

    def _same_object(self,left,right):
        if not left or not right:return False
        if left==right:return True
        try:return self.call('Runtime.callFunctionOn',{'objectId':left,'functionDeclaration':'function(other){return this===other}','arguments':[{'objectId':right}],'returnByValue':True}).get('result',{}).get('value') is True
        except RuntimeError:return False

    def _adopt_game(self,candidates):
        valid=[]
        for oid in dict.fromkeys(candidates):
            aliases=[getattr(self,'profile',{}).get('fields',{}).get('players','players'),'player_list']
            result=self.call('Runtime.callFunctionOn',{'objectId':oid,'functionDeclaration':'function(){'+ROSTER_HELPERS_JS+'const rows=roster(this,'+json.dumps(aliases)+''');return own(this,"destructed")!==true&&own(this,"isGameOver")!==true&&rows.some(([k,p])=>playerLike(p)&&playerId(p,k)!==null&&num(pick(p,["x","posX"]))!==null&&num(pick(p,["y","posY"]))!==null)}''','returnByValue':True})
            if result.get('result',{}).get('value') is not True:continue
            if any(self._same_object(oid,old) for old in getattr(self,'retired_games',[])):continue
            valid.append(oid)
        current=next((oid for oid in valid if self._same_object(oid,self.game)),None)
        fresh=[oid for oid in valid if not self._same_object(oid,self.game)]
        chosen=fresh[-1] if fresh else current
        if chosen and not self._same_object(chosen,self.game):
            previous=self.game
            self.invalidate_source('game-object-changed')
            if previous:
                self.retired_games.append(previous)
                if len(self.retired_games)>32:
                    old=self.retired_games.pop(0)
                    try:self.call('Runtime.releaseObject',{'objectId':old})
                    except RuntimeError:pass
            retained=self.call('Runtime.callFunctionOn',{'objectId':chosen,'functionDeclaration':'function(){return this}','objectGroup':'dragonlab-live'})
            self.game=retained.get('result',{}).get('objectId') or chosen
        elif not chosen and self.game:self.invalidate_source('no-active-game')
        return self.game

    def discover(self):
        expression='[window,document,...document.querySelectorAll("canvas")].flatMap(e=>Object.getOwnPropertyNames(e).filter(k=>k.startsWith("jQuery")).flatMap(k=>Object.entries(e[k]?.events||{}).filter(([k])=>/key/.test(k)).flatMap(([k,v])=>v.map(x=>x.handler))))'
        r=self.call('Runtime.evaluate',{'expression':expression,'objectGroup':'dragonlab-discovery','timeout':2000})
        oid=r.get('result',{}).get('objectId')
        if not oid:return None
        handles=self.props(oid).get('result',[])
        seen=set();games=[]
        for h in handles:
            if not h['name'].isdigit():continue
            fun=h.get('value',{});fid=fun.get('objectId')
            if not fid or fid in seen:continue
            seen.add(fid)
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
                        games.append(v['objectId']);continue
                    for child in pp:
                        if child['name'] not in ('game','g_game','currentGame','game_state'):continue
                        cv=child.get('value',{})
                        if not cv.get('objectId'):continue
                        nn={x['name'] for x in self.props(cv['objectId']).get('result',[])}
                        if 'players' in nn:games.append(cv['objectId'])
        result=self._adopt_game(games[:64])
        self.discovery_clock=time.monotonic()
        self.call('Runtime.releaseObjectGroup',{'objectGroup':'dragonlab-discovery'})
        return result

    def sample(self):
        if getattr(self,'allowed_hosts',None) and self.lifecycle.host not in self.allowed_hosts:
            self.invalidate_source('incompatible-host')
            return self.tag_sample({'status':'waiting','reason':'La pestaña cambió a un dominio incompatible'})
        if (not self.game or time.monotonic()-getattr(self,'discovery_clock',0)>=getattr(self,'discovery_interval',2.)) and not self.discover():
            self.call('Runtime.releaseObjectGroup',{'objectGroup':'dragonlab-discovery'})
            return self.tag_sample({'status':'waiting','reason':'Navegador conectado; esperando una partida compatible'})
        generation=self.lifecycle.revision if hasattr(self,'lifecycle') else None
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
        terrain_due=time.monotonic()-self.terrain_clock>=getattr(self,"terrain_interval",3)
        serializer='''function(renderer,readTerrain,sourceReset){
          __ROSTER_HELPERS__
          const rows=roster(this,["players","player_list"]),hid=heroId(this),href=heroObject(this,rows,hid);
          const source=(__SOURCE_IDENTITY__)(this,hid,href,sourceReset);
          const players=rows.filter(([k,p])=>playerLike(p)).map(([k,p],i)=>({
            id:playerId(p,k),name:(()=>{const v=pick(p,["name","nick"]);return typeof v==="string"?v.slice(0,60):"Jugador "+(i+1)})(),
            x:num(pick(p,["x","posX"])),y:num(pick(p,["y","posY"])),
            angle:(()=>{let a=num(pick(p,["ang"])),b=num(pick(p,["body"])),look=num(pick(p,["look"]));return a!==null&&b!==null&&look!==null?(look===0?a+b:a-b):num(pick(p,["angle","display_angle"]))})(),rawAngle:num(pick(p,["ang"])),body:num(pick(p,["body_angle","bodyAngle","body"])),
            look:num(pick(p,["look","direction"])),mobile:num(pick(p,["mobile","mobile_id"])),
            hp:num(own(p,"hp")),shield:num(own(p,"shield")),maxHp:num(own(p,"maxhp")),
            dead:flag(pick(p,["dead","is_dead","isDead"]))||[false,0].includes(pick(p,["is_alive"])),muzzles:[["aim_s1_ang","aim_s1_len"],["aim_s2_ang","aim_s2_len"],["aim_ss_ang","aim_ss_len"]].map(keys=>({angle:num(pick(p,[keys[0]])),radius:num(pick(p,[keys[1]]))})),muzzleX:num(pick(p,["aim_circle_x"])),muzzleY:num(pick(p,["aim_circle_y"])),shot:num(pick(p,["selected_shot"])),team:id(pick(p,["team"])),isHero:flag(pick(p,["is_me","isMe","is_hero"]))}));
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
              change:pick(data,["change"])?numeric(pick(data,["change"]),["at","dur","img"]):null,
              hole:Array.isArray(pick(data,["hole"]))?pick(data,["hole"]).slice(0,2).map(num):null,
              shotType:num(pick(data,["shot_type"])),metadata:{...numeric(pick(data,["start"]),["player","player_n","mobile","selectedShot","angle"]),launchSpeed:num(pick(pick(data,["start"]),["power"]))}};
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
            if(pixels&&w>0&&h>0&&w*h<=12000000){let rows=[];for(let y=0;y<h;y++){let row=[],inside=false;for(let x=0;x<w;x++){let opaque=pixels[(y*w+x)*4+3]>0;if(opaque!==inside){row.push(x);inside=opaque;}}if(inside)row.push(w);rows.push(row);}terrain={width:w,height:h,originX:0,originY:0,rows,rowsSorted:true};}
            else if(Array.isArray(surface))terrain={surface:surface.slice(0,4096).map(num),originX:num(pick(ground,["originX"]))??0,originY:num(pick(ground,["originY"]))??0};}
          return {...source,rosterDiagnostics:{raw:rows.length,objects:rows.filter(([k,p])=>playerLike(p)).length,truncated:0},status:own(this,"destructed")===true||own(this,"isGameOver")===true?"waiting":"live",players,shots,weather:weatherData,terrain,selectedShot:num(pick(this,["selectedShot","selected_shot"])),currentPower:num(pick(this,["curUIPower","power"])),wind:num(pick(this,["windPower","wind_power","wind"]))??num(pick(meter,["value","power"])),
            windAngle:num(pick(this,["windAngle","wind_angle"]))??num(pick(renderer,["wind_angle"]))??num(pick(meter,["angle","ang"])),
            rendererWind:num(pick(renderer,["wind_power"])),
            turnSerial:num(own(this,"turn_number")),over:own(this,"isGameOver")===true||own(this,"destructed")===true,turn:num(pick(this,["turn_number","turn","currentTurn"])),activePlayer:num(pick(this,["turn"])),heroId:hid,
            camera:cam?{x:num(pick(cam,["camera_x"])),y:num(pick(cam,["camera_y"])),scale:num(pick(cam,["cameraScale"])),matrix:cm,renderWidth:num(pick(engine,["width"]))??(view?num(view.width):null),renderHeight:num(pick(engine,["height"]))??(view?num(view.height):null),viewWidth:num(pick(renderer,["original_w"])),viewHeight:num(pick(renderer,["original_h"]))}:null};
        }'''.replace('__ROSTER_HELPERS__',ROSTER_HELPERS_JS).replace('__SOURCE_IDENTITY__',SOURCE_IDENTITY_JS)
        args=([{'objectId':self.renderer}] if self.renderer else [{'value':None}])+[{'value':terrain_due},{'value':getattr(self,'_source_reset',False)}]
        r=self.call('Runtime.callFunctionOn',{'objectId':self.game,'functionDeclaration':serializer,'arguments':args,'returnByValue':True,'objectGroup':'dragonlab-live'})
        if generation is not None and generation!=self.lifecycle.revision:
            return self.tag_sample({'status':'waiting','reason':'Cambio de contexto; descartando lectura anterior'})
        if 'exceptionDetails' in r:self.invalidate_source('schema-changed');raise RuntimeError('La estructura del juego cambió')
        sample=r['result'].get('value',{'status':'waiting'})
        self._source_reset=False
        sample=self.tag_sample(sample)
        if sample.get('status')!='live':
            old=self.game;self.invalidate_source('game-ended')
            if old:self.retired_games.append(old)
            self.call('Runtime.releaseObjectGroup',{'objectGroup':'dragonlab-discovery'})
            return self.tag_sample({'status':'waiting','reason':'Cambio de partida; detectando el nuevo mapa'})
        if sample.get('terrain'):
            self.terrain_cache=sample['terrain'];self.terrain_clock=time.monotonic()
        else:sample['terrain']=self.terrain_cache
        if self.terrain_turn!=sample.get('turn'):self.terrain_clock=0;self.terrain_turn=sample.get('turn')
        # Refresh once after the projectile family disappears: craters can
        # change Nak's exit before the next turn or periodic map refresh.
        inflight=bool(sample.get('shots'))
        if self.terrain_inflight and not inflight:self.terrain_clock=0
        self.terrain_inflight=inflight
        if sample.get('wind') is None:sample['wind']=sample.get('rendererWind')
        sample.pop('rendererWind',None)
        return sample
