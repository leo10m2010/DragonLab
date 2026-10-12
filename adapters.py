"""Explicit, read-only browser adapters. A registered URL is not a compatibility claim."""
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from cdp import CDP

PROFILES = [
    {'id': 'dragonbound', 'name': 'DragonBound', 'hosts': ['dragonbound.net'],
     'mode': 'dragonbound', 'compatibility': 'Lectura observada; física requiere calibración'},
    {'id': 'gunbound-world', 'name': 'GunBound World', 'hosts': ['play.gunbound.world'],
     'mode': 'generic', 'state_paths': ['game', 'g_game', 'currentGame', 'game_state'],
     'fields': {'wind':'windPower','windAngle':'windAngleDeg','turn':'turnNumber','heroId':'activePlayerId'},
     'compatibility': 'Experimental: posiciones observadas; física pendiente de calibración'},
    {'id': 'generic', 'name': 'Clon configurable', 'hosts': [], 'mode': 'generic',
     'state_paths': ['game', 'g_game', 'currentGame', 'game_state'],
     'compatibility': 'Requiere configurar rutas y física de este clon'},
    {'id': 'manual', 'name': 'Captura manual / cualquier ventana', 'hosts': [], 'mode': 'manual',
     'compatibility': 'Selección manual de posiciones; física calibrada por usuario'},
]


def built_in_profiles():
    return json.loads(json.dumps(PROFILES))


def list_browser_pages(endpoint='http://127.0.0.1:9222'):
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('La conexión al navegador debe ser local')
    with urllib.request.urlopen(endpoint.rstrip('/') + '/json/list', timeout=2) as response:
        targets = json.load(response)
    return [{k: t.get(k, '') for k in ('id', 'title', 'url')} for t in targets
            if t.get('type') == 'page' and t.get('webSocketDebuggerUrl')]


def load_profiles(path):
    """Load data, never executable expressions. User profiles can override builtin IDs."""
    loaded = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(loaded, list):
        raise ValueError('Los adaptadores deben ser una lista JSON')
    profiles = {p['id']: p for p in built_in_profiles()}
    for profile in loaded:
        _validate(profile)
        profiles[profile['id']] = profile
    return list(profiles.values())


def _validate(profile):
    if not isinstance(profile, dict) or not isinstance(profile.get('id'), str):
        raise ValueError('Adaptador sin identificador')
    if profile.get('mode', 'generic') not in ('generic', 'dragonbound', 'manual'):
        raise ValueError('Modo de adaptador desconocido')
    paths = list(profile.get('state_paths', [])) + list(profile.get('fields', {}).values())
    for path in paths:
        if not isinstance(path, str) or not re.fullmatch(r'[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*|\.\d+)*', path):
            raise ValueError('Usa rutas de propiedades, por ejemplo game.players; no expresiones')
        if any(p in ('__proto__', 'prototype', 'constructor') for p in path.split('.')):
            raise ValueError('Ruta de prototipo no permitida')


class AdapterClient(CDP):
    def __init__(self, endpoint='http://127.0.0.1:9222', target_id=None,
                 profile_id='dragonbound', config=None):
        self.profile = config or next((p for p in built_in_profiles() if p['id'] == profile_id), None)
        if self.profile is None:
            raise ValueError('Adaptador desconocido')
        _validate(self.profile)
        self.manual = self.profile.get('mode') == 'manual'
        self.controller=None
        if self.manual:
            return
        if target_id is None:
            hosts = self.profile.get('hosts', [])
            matches = [p for p in list_browser_pages(endpoint)
                       if urllib.parse.urlparse(p['url']).hostname in hosts]
            if not matches:
                raise RuntimeError('Selecciona una página abierta para este adaptador')
            target_id = matches[0]['id']
        super().__init__(endpoint, target_id=target_id)

    def close(self):
        if not self.manual:
            super().close()

    def discover(self):
        if self.profile.get('mode') == 'dragonbound':
            return super().discover()
        # Follow only explicit own data properties; getters and game functions are never invoked.
        paths = self.profile.get('state_paths', [])
        expression = '''(function(paths){for(const path of paths){let o=window;
          for(const k of path.split('.')){let d=o&&Object.getOwnPropertyDescriptor(o,k);o=d&&('value'in d)?d.value:null;}
          if(o&&typeof o==='object')return o;}return null;})(%s)''' % json.dumps(paths)
        result = self.call('Runtime.evaluate', {'expression': expression,
                            'objectGroup': 'dragonlab-discovery', 'timeout': 2000})
        value = result.get('result', {})
        self.game = value.get('objectId') if value.get('subtype') != 'null' else None
        if not self.game and self.profile['id']=='gunbound-world':self.game=self._discover_controller()
        return self.game

    def _discover_controller(self):
        # CDP omits listener handles unless the debugger domain is enabled.
        # No pause, breakpoint, game event or input is issued.
        self.call('Debugger.enable')
        try:
            sid=self._discover_listener_controller()
            if not sid:self.call('Runtime.releaseObjectGroup',{'objectGroup':'dragonlab-discovery'})
            return sid
        finally:
            self.call('Debugger.disable')

    def _controller_state(self, cid):
        result=self.call('Runtime.callFunctionOn',{'objectId':cid,'functionDeclaration':'function(){if(this.destroyed===true||this.renderSurface&&this.renderSurface!=="live")return null;return this.room?.state??this.room?.serializer?.state??this.room?.serializer?.decoder?.state??null}', 'objectGroup':'dragonlab-discovery'})
        sid=result.get('result',{}).get('objectId')
        if sid and 'players' in {p['name'] for p in self.props(sid).get('result',[])}:
            self.controller=cid
            return sid
        return None

    def _discover_listener_controller(self):
        """Inspect keyboard-listener closures for the observed game's controller.

        Follows a bounded set of local object descriptors, never account storage.
        GunBound's selected state getter is a passive room-state read.
        """
        window=self.call('Runtime.evaluate',{'expression':'window','objectGroup':'dragonlab-discovery'})['result']['objectId']
        listeners=self.call('DOMDebugger.getEventListeners',{'objectId':window,'depth':1}).get('listeners',[])
        seen=set()
        for listener in listeners:
            if listener.get('type') not in ('keydown','keyup'):continue
            handler=listener.get('originalHandler',listener.get('handler',{}));oid=handler.get('objectId')
            if not oid or oid in seen:continue
            seen.add(oid);properties=self.props(oid);candidates=[]
            for internal in properties.get('internalProperties',[]):
                if internal['name']=='[[BoundThis]]':candidates.append(internal.get('value',{}))
                if internal['name']=='[[Scopes]]':
                    for scope in self.props(internal['value']['objectId']).get('result',[])[:6]:
                        value=scope.get('value',{})
                        if 'Global' in value.get('description','') or not value.get('objectId'):continue
                        local=self.props(value['objectId']).get('result',[])
                        if len(local)>80:
                            # Class-field arrows do not expose their lexical this.
                            # Match the observed battle class signature, then inspect
                            # only its instances; never traverse account objects.
                            if value.get('description')=='Module' and 'onKeyDown' in handler.get('description',''):
                                for prop in local:
                                    ctor=prop.get('value',{})
                                    desc=ctor.get('description','')
                                    if ctor.get('type')!='function' or not desc.startswith('class') or 'room;myId;hud;' not in desc[:120]:continue
                                    prototype=next((p.get('value',{}).get('objectId') for p in self.props(ctor['objectId']).get('result',[]) if p['name']=='prototype'),None)
                                    if not prototype:continue
                                    instances=self.call('Runtime.queryObjects',{'prototypeObjectId':prototype,'objectGroup':'dragonlab-discovery'}).get('objects',{}).get('objectId')
                                    if not instances:continue
                                    instances=self.call('Runtime.callFunctionOn',{'objectId':instances,'functionDeclaration':'function(){return this.filter(v=>v&&v.destroyed!==true&&v.renderSurface==="live").slice(0,8)}','objectGroup':'dragonlab-discovery'}).get('result',{}).get('objectId')
                                    if not instances:continue
                                    for item in self.props(instances).get('result',[])[:8]:
                                        if not item['name'].isdigit():continue
                                        cid=item.get('value',{}).get('objectId')
                                        if cid:
                                            sid=self._controller_state(cid)
                                            if sid:return sid
                            continue
                        candidates.extend(p.get('value',{}) for p in local if p.get('value',{}).get('type')=='object')
            for candidate in candidates[:40]:
                cid=candidate.get('objectId')
                if not cid:continue
                names={p['name'] for p in self.props(cid).get('result',[])}
                if 'room' not in names or not names.intersection({'stageSize','power','geometry','cameraX','keydown'}):continue
                sid=self._controller_state(cid)
                if sid:return sid
        return None

    def sample(self):
        if self.manual:
            return {'status': 'manual', 'reason': 'Selecciona posiciones en la captura y calibra la física'}
        if self.profile.get('mode') == 'dragonbound':
            result = super().sample()
        else:
            result = self._generic_sample()
        result['adapter'] = self.profile['id']
        # Measured projectile acceleration uses the game's angle directly.
        result['compatibility'] = self.profile.get('compatibility', 'Experimental')
        return result

    def _generic_sample(self):
        if not self.game and not self.discover():
            return {'status': 'waiting', 'reason': 'Estado inaccesible: configura state_paths o usa captura manual'}
        fields = {'players': 'players', 'heroId': 'my_player_number', 'wind': 'wind_power',
                  'windAngle': 'wind_angle', 'turn': 'turn', 'shots': 'projectiles',
                  'weather': 'weather', 'terrain': 'terrain', 'camera': 'camera'}
        fields.update(self.profile.get('fields', {}))
        serializer = '''function(fields,gunbound){
          const own=(o,k)=>{const d=o&&Object.getOwnPropertyDescriptor(o,k);if(d&&('value'in d))return d.value;if(gunbound&&o)try{return o[k]??null}catch{}return null};
          const path=(o,p)=>p.split('.').reduce(own,o);
          const n=v=>typeof v==='number'&&Number.isFinite(v)?v:null,id=v=>typeof v==='string'?v.slice(0,80):n(v);
          const values=o=>Array.isArray(o)?o:(gunbound&&o&&o.$items instanceof Map?[...o.$items.values()]:o instanceof Map?[...o.values()]:o&&typeof o==='object'?Object.getOwnPropertyNames(o).slice(0,64).map(k=>own(o,k)):[]);
          const limited=(o,keys)=>Object.fromEntries(keys.map(k=>[k,n(own(o,k))]).filter(x=>x[1]!==null));
          const collection=path(this,fields.players), entries=gunbound&&collection?.$items instanceof Map?[...collection.$items.entries()]:values(collection).map((p,i)=>[i,p]);
          const players=entries.slice(0,16).filter(([k,p])=>p&&typeof p==='object').map(([key,p],i)=>({
            id:id(own(p,'actorId'))??id(own(p,'userId'))??id(own(p,'id'))??n(own(p,'n'))??id(key)??i,x:n(own(p,'x')),y:n(own(p,'y')),
            name:typeof (own(p,'username')??own(p,'name'))==='string'?(own(p,'username')??own(p,'name')).slice(0,60):'Jugador '+(i+1),
            angle:n(own(p,'aimAngle'))??n(own(p,'angle'))??n(own(p,'ang')),mobile:id(own(p,'mobileId'))??n(own(p,'mobile')),look:n(own(p,'look'))??(own(p,'facing')==='right'?1:own(p,'facing')==='left'?0:null),
            dead:own(p,'alive')===false||n(own(p,'hp'))===0,body:n(own(p,'bodyTilt'))??n(own(p,'bodyAngle'))??n(own(p,'body_angle')),team:id(own(p,'team')),isHero:own(p,'isMe')===true}));
          const camera=path(this,fields.camera),terrain=path(this,fields.terrain),surface=own(terrain,'heights');
          return {status:players.length?'live':'waiting',phase:gunbound?own(this,'phase'):null,players,heroId:gunbound?null:id(path(this,fields.heroId)),
            wind:n(path(this,fields.wind)),windAngle:n(path(this,fields.windAngle)),turn:n(path(this,fields.turn)),
            camera:camera?limited(camera,['x','y','scale']):null,
            shots:values(path(this,fields.shots)).slice(0,64).map(s=>limited(s,['id','x','y','vx','vy','ax','ay','time','power','angle'])),
            weather:values(path(this,fields.weather)).slice(0,32).map(w=>limited(w,['type','id','x','y','width','height','power','angle'])),
            terrain:terrain?{...limited(terrain,['width','height','originX','originY']),surface:Array.isArray(surface)?surface.slice(0,4096).map(n):null}:null};
        }'''
        result = self.call('Runtime.callFunctionOn', {'objectId': self.game, 'functionDeclaration': serializer,
                            'arguments': [{'value': fields},{'value':self.profile['id']=='gunbound-world'}], 'returnByValue': True})
        if result.get('exceptionDetails'):
            self.game = None
            return {'status': 'waiting', 'reason': 'El estado cambió; esperando una estructura compatible'}
        sample=result.get('result', {}).get('value', {'status': 'waiting'})
        if self.profile['id']=='gunbound-world' and self.controller:
            info=self.call('Runtime.callFunctionOn',{'objectId':self.controller,'functionDeclaration':'''function(){const s=this.room?.state,p=s?.players?.get(this.myId),m=this.world?.worldTransform,z=this.stageSize,rear=['nak','aduka'].includes(p?.mobileId),right=(p?.facing==='right')!==rear,world=(right?this.angle:180-this.angle)-(p?.bodyTilt??0);return {heroId:this.myId,activePlayer:s?.activePlayerId,currentPower:this.power,rawAngle:this.angle,localAngle:right?world:180-world,muzzles:p?.mobileId==='armor'?[{angle:52,radius:33}]:[],selectedShot:({shot1:0,shot2:1,ss:2})[p?.selectedShot],camera:m&&z?{matrix:{a:m.a,b:m.b,c:m.c,d:m.d,tx:m.tx,ty:m.ty},renderWidth:z.width,renderHeight:z.height}:null}}''','returnByValue':True}).get('result',{}).get('value',{})
            sample.update(info)
            import time
            stamp=(self.controller,sample.get('turn'))
            if sample.get('phase') in ('TURN','RESOLVING') and (stamp!=getattr(self,'gunbound_terrain_stamp',None) or time.monotonic()-getattr(self,'gunbound_terrain_clock',0)>5):
                ground=self.call('Runtime.callFunctionOn',{'objectId':self.controller,'functionDeclaration':'''function(){const c=this.terrain?.canvas,ctx=this.terrain?.ctx;if(!c||!ctx||!c.width||!c.height||c.width*c.height>12000000)return null;const w=c.width,h=c.height,p=ctx.getImageData(0,0,w,h).data,rows=[];for(let y=0;y<h;y++){let row=[],inside=false;for(let x=0;x<w;x++){const opaque=p[(y*w+x)*4+3]>0;if(opaque!==inside){row.push(x);inside=opaque}}if(inside)row.push(w);rows.push(row)}return {width:w,height:h,originX:0,originY:0,rows,rowsSorted:true}}''','returnByValue':True}).get('result',{}).get('value')
                if ground:self.terrain_cache=ground
                self.gunbound_terrain_stamp=stamp;self.gunbound_terrain_clock=time.monotonic()
            sample['terrain']=self.terrain_cache
            hero=next((p for p in sample.get('players',[]) if p.get('id')==info.get('heroId')),None)
            if hero and isinstance(info.get('localAngle'),(int,float)):
                hero['angle']=info['localAngle']
                hero['isHero']=True
                hero['muzzles']=info.get('muzzles',[])
                hero['rawAngle']=info.get('rawAngle')
            if sample.get('phase') not in ('TURN','RESOLVING'):
                sample['status']='waiting'
                sample['reason']='Esperando una partida activa de GunBound World'
                self.game=None;self.controller=None;self.terrain_cache=None
                self.call('Runtime.releaseObjectGroup',{'objectGroup':'dragonlab-discovery'})
        return sample
