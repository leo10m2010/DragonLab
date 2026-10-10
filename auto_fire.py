"""One user-triggered shot, controlled by live UI power rather than a timer."""
import time,math
from cdp import CDP
from firing import WindowsInput

class PowerReader:
    def __init__(self,endpoint,target=None):
        self.client=CDP(endpoint,target_id=target);self.initial=self.client.sample();self.slice=None
        if self.initial.get('status')!='live':
            self.client.close();raise RuntimeError('Espera una partida activa')
        f=self.client.call('Runtime.callFunctionOn',{'objectId':self.client.game,'functionDeclaration':'function(){return Object.getOwnPropertyDescriptor(Object.getPrototypeOf(this),"OnKeyDown")?.value}'})['result'].get('objectId')
        if f:
            scopes=next((x['value']['objectId'] for x in self.client.props(f).get('internalProperties',[]) if x['name']=='[[Scopes]]'),None)
            if scopes:
                for p in self.client.props(scopes).get('result',[]):
                    value=p.get('value',{})
                    if not p['name'].isdigit() or 'Global' in value.get('description','') or not value.get('objectId'):continue
                    flag=next((p.get('value',{}).get('value') for p in self.client.props(value['objectId']).get('result',[]) if p['name']=='g_is_game_slice'),None)
                    if isinstance(flag,bool):self.slice=flag;break
        self.client.sock.settimeout(.3)
    def read(self):
        r=self.client.call('Runtime.callFunctionOn',{'objectId':self.client.game,'functionDeclaration':'''function(renderer){const own=(o,k)=>Object.getOwnPropertyDescriptor(o,k)?.value;const pick=(o,keys)=>{for(let k of keys){let v=own(o,k);if(typeof v==='number'&&Number.isFinite(v))return v}return null};let meter=own(renderer,'wind_meter');let list=own(this,'players')||[];return {turn:own(this,'turn'),hero:own(this,'my_player_number'),power:own(this,'curUIPower'),dragSens:own(this,'dragSens'),busy:!!own(this,'intervalDoSpace')||!!own(this,'isInDrag'),over:!!own(this,'isGameOver')||!!own(this,'destructed'),chat:['INPUT','TEXTAREA'].includes(document.activeElement?.tagName),shot:own(this,'selectedShot'),wind:pick(this,['windPower','wind_power','wind'])??pick(renderer,['wind_power'])??pick(meter,['value','power']),windAngle:pick(this,['windAngle','wind_angle'])??pick(renderer,['wind_angle'])??pick(meter,['angle','ang']),players:list.filter(Boolean).map(p=>({id:own(p,'n'),x:own(p,'x'),y:own(p,'y'),rawAngle:own(p,'ang'),body:own(p,'body'),look:own(p,'look'),dead:own(p,'is_alive')===false}))}}''','arguments':[{'objectId':self.client.renderer}] if self.client.renderer else [{'value':None}],'returnByValue':True})
        if r.get('exceptionDetails'):raise RuntimeError('No se pudo leer la fuerza del juego')
        return r['result']['value']
    def close(self):self.client.close()

def validate(plan,state):
    if state.get('over') or state.get('chat'):raise RuntimeError('Cierra el chat y vuelve a tu turno')
    if state.get('hero')!=plan['hero'] or state.get('turn')!=plan['hero']:raise RuntimeError('Espera tu turno')
    if state.get('shot')!=plan['shot'] or state.get('wind')!=plan['wind'] or state.get('windAngle')!=plan['windAngle']:raise RuntimeError('Los datos cambiaron; espera el nuevo cálculo')
    for ident,expected in ((plan['hero'],plan['heroState']),(plan['target'],plan['targetState'])):
        player=next((p for p in state['players'] if p['id']==ident),None)
        if not player or player.get('dead'):raise RuntimeError('El jugador o el objetivo ya no están disponibles')
        for key,value in expected.items():
            if player.get(key)!=value:raise RuntimeError('Cambió la posición o el ángulo; vuelve a calcular')

def execute(plan,reader,cancel,backend=None):
    backend=backend or WindowsInput();held=False;method=None;restore=None
    if not 1<=plan['power']<=400:raise ValueError('Fuerza inválida')
    if reader.slice is None:raise RuntimeError('No se pudo detectar el modo de tiro')
    state=reader.read();validate(plan,state)
    if state.get('busy'):raise RuntimeError('Termina el movimiento o la carga actual')
    if backend.foreground()[0]!=plan['window']:raise RuntimeError('Vuelve a la ventana del juego')
    method='space' if reader.slice else 'drag';start=time.monotonic();last_power=-1;last_change=start
    try:
        if method=='space':backend.key(True);held=True
        else:
            restore=backend.cursor();x,y=plan['barStart'];backend.move(x,y);backend.mouse(True);held=True
            # Begin with a small displacement, then measure the actual drag gain.
            dx=min(plan['power'],12)*1.5*plan.get('dpr',1);backend.move(round(x+dx),y)
        while True:
            if cancel.is_set() or backend.escaped():raise RuntimeError('Entrada liberada')
            if backend.foreground()[0]!=plan['window']:raise RuntimeError('La ventana perdió el foco')
            state=reader.read();power=state.get('power')
            # At full charge the native controller can already have released
            # and advanced the turn before our final reading arrives.
            if plan['power']>=399 and last_power>=380 and power==400 and state.get('turn')!=plan['hero']:
                return {'power':400,'method':method}
            validate(plan,state)
            if not isinstance(power,(int,float)) or not math.isfinite(power):raise RuntimeError('No se pudo medir la fuerza')
            now=time.monotonic()
            if power!=last_power:last_change=now;last_power=power
            if method=='space':
                if power>=plan['power']-1:return {'power':power,'method':method}
            else:
                if abs(power-plan['power'])<=1:return {'power':power,'method':method}
                if power>0:
                    gain=dx/power;dx+=max(-80,min(80,(plan['power']-power)*gain))
                else:dx+=8*plan.get('dpr',1)
                px=round(x+dx)
                if not plan['screenBox'][0]<px<plan['screenBox'][2]-5:raise RuntimeError('El arrastre no cabe en la ventana; usa Slice')
                backend.move(px,y)
            if now-start>5 or now-last_change>.7:raise RuntimeError('La carga no responde; entrada liberada')
            time.sleep(.015)
    finally:
        if held:
            if method=='space':backend.key(False)
            else:backend.mouse(False)
        if restore:backend.move(*restore)
