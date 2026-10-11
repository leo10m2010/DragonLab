"""One user-triggered shot, controlled by live UI power rather than a timer."""
import time,math
from cdp import CDP
from firing import WindowsInput

DRAG_POINT = r"""(()=>{
 const game=document.getElementById('gameScreen');if(!game)return null;
 const r=game.getBoundingClientRect();
 for(const fy of [.28,.12,.42]){
  const x=r.left+16,y=r.top+Math.min(r.height*.75,516)*fy,hit=document.elementFromPoint(x,y);
  if(hit&&game.contains(hit)&&!hit.closest('#gameui,#touch_ui,button,input,textarea,select,a,[role="button"]'))return [x,y];
 }return null;
})()"""

class PowerReader:
    def __init__(self,endpoint,target=None):
        self.client=CDP(endpoint,target_id=target)
        try:self.initial=self.client.sample()
        except Exception:
            self.client.close();raise
        if self.initial.get('status')!='live':
            self.client.close();raise RuntimeError('Espera una partida activa')
        # The visible mode button is authoritative and updates immediately.
        # A closure flag from a particular prototype version is not a stable API.
        self.client.sock.settimeout(.3)
    def read(self):
        r=self.client.call('Runtime.callFunctionOn',{'objectId':self.client.game,'functionDeclaration':r'''function(renderer){const own=(o,k)=>o&&Object.getOwnPropertyDescriptor(o,k)?.value;const pick=(o,keys)=>{for(let k of keys){let v=own(o,k);if(typeof v==='number'&&Number.isFinite(v))return v}return null};let meter=own(renderer,'wind_meter');let list=own(this,'players')||[];let mode=document.getElementById('slice_drag_button'),mark=document.getElementById('powerMarkArea')?.getBoundingClientRect(),fill=document.getElementById('powerBar')?.getBoundingClientRect();let id=v=>typeof v==='string'&&/^\d+$/.test(v)?Number(v):v;return {turn:id(own(this,'turn')),hero:id(own(this,'my_player_number')),power:mark?.width>0&&fill?Math.round(Math.max(0,Math.min(400,400*fill.width/mark.width))):pick(this,['curUIPower']),mode:mode?(mode.classList.contains('drag')?'drag':'space'):null,focused:document.hasFocus()&&document.visibilityState==='visible',moving:['intervalDoLeft','intervalDoRight','intervalDoUp','intervalDoDown'].some(k=>!!own(this,k)),dragSens:own(this,'dragSens'),dragStartX:own(this,'drag_start_x'),dragUpdates:Array.isArray(own(this,'stat'))&&Array.isArray(own(this,'stat')[0])?Math.max(0,own(this,'stat').length-1):null,dragPointX:Array.isArray(own(this,'stat'))&&Array.isArray(own(this,'stat').at(-1))?own(this,'stat').at(-1)[1]:null,busy:!!own(this,'intervalDoSpace')||!!own(this,'isInDrag'),over:!!own(this,'isGameOver')||!!own(this,'destructed'),chat:['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)||!!document.activeElement?.isContentEditable,shot:own(this,'selectedShot'),wind:pick(this,['windPower','wind_power','wind'])??pick(renderer,['wind_power'])??pick(meter,['value','power']),windAngle:pick(this,['windAngle','wind_angle'])??pick(renderer,['wind_angle'])??pick(meter,['angle','ang']),players:list.filter(Boolean).map(p=>({id:id(own(p,'n')),x:own(p,'x'),y:own(p,'y'),rawAngle:own(p,'ang'),body:own(p,'body'),look:own(p,'look'),dead:own(p,'is_alive')===false}))}}''','arguments':[{'objectId':self.client.renderer}] if self.client.renderer else [{'value':None}],'returnByValue':True})
        if r.get('exceptionDetails'):raise RuntimeError('No se pudo leer la fuerza del juego')
        return r['result']['value']
    def drag_start(self,window):
        from automatic import GEOMETRY_JS,content_origin,screen_geometry
        meta=self.client.call('Runtime.evaluate',{'expression':GEOMETRY_JS,'returnByValue':True})['result']['value']
        origin=content_origin(meta)
        point=self.client.call('Runtime.evaluate',{'expression':DRAG_POINT,'returnByValue':True})['result'].get('value')
        if not origin or meta.get('windowHandle')!=window or not point or not meta.get('focused'):
            raise RuntimeError('No se encontró una zona libre para arrastrar en el juego')
        self.drag_box,_=screen_geometry(meta,origin)
        return tuple(round(origin[i]+point[i]*meta.get('dpr',1)) for i in (0,1))
    def close(self):self.client.close()

def validate(plan,state):
    if state.get('over') or state.get('chat') or state.get('focused') is not True:raise RuntimeError('Cierra el chat y vuelve a tu turno')
    if state.get('moving'):raise RuntimeError('Suelta las teclas de movimiento y ángulo antes de disparar')
    if state.get('mode') not in ('space','drag'):raise RuntimeError('No se pudo detectar Slice / Drag')
    if state.get('hero')!=plan['hero'] or state.get('turn')!=plan['hero']:raise RuntimeError('Espera tu turno')
    if state.get('shot')!=plan['shot'] or state.get('wind')!=plan['wind'] or state.get('windAngle')!=plan['windAngle']:raise RuntimeError('Los datos cambiaron; espera el nuevo cálculo')
    for ident,expected in ((plan['hero'],plan['heroState']),(plan['target'],plan['targetState'])):
        player=next((p for p in state['players'] if p['id']==ident),None)
        if not player or player.get('dead'):raise RuntimeError('El jugador o el objetivo ya no están disponibles')
        for key,value in expected.items():
            if player.get(key)!=value:raise RuntimeError('Cambió la posición o el ángulo; vuelve a calcular')

def execute(plan,reader,cancel,backend=None,trace=None):
    backend=backend or WindowsInput();held=False;method=None
    def report(stage,**data):
        if trace:
            try:trace({'stage':stage,**data})
            except Exception:pass
    if not isinstance(plan['power'],(int,float)) or not math.isfinite(plan['power']) or not 1<=plan['power']<=400:raise ValueError('Fuerza inválida')
    state=reader.read();validate(plan,state)
    if state.get('busy') or backend.input_busy():raise RuntimeError('Termina el movimiento o la carga actual')
    if backend.foreground()[0]!=plan['window']:raise RuntimeError('Vuelve a la ventana del juego')
    method=state['mode'];start=time.monotonic();last_power=-1;last_change=start
    charging=False;last_cursor=None;window_rect=backend.window_rect(plan['window']);expected_drag_x=None;move_revision=None;move_started=None
    def check():
        if cancel.is_set() or backend.escaped():raise RuntimeError('Entrada liberada; el juego puede lanzar con fuerza parcial')
        if backend.foreground()[0]!=plan['window']:raise RuntimeError('La ventana perdió el foco; entrada liberada')
        if backend.window_rect(plan['window'])!=window_rect:raise RuntimeError('La ventana cambió de posición; vuelve a calcular')
        if method=='drag' and last_cursor and math.dist(backend.cursor(),last_cursor)>3:raise RuntimeError('Moviste el mouse; entrada liberada')
    check()
    try:
        if method=='space':backend.key(True);held=True
        else:
            x,y=reader.drag_start(plan['window']);check();backend.move(x,y);last_cursor=(x,y)
            if not backend.point_in_window(x,y,plan['window']):raise RuntimeError('Otra ventana cubre la zona de arrastre')
            backend.mouse(True);held=True
            # UIDragStart assigns a fresh sensitivity. Never reuse a previous
            # value or move the pointer to discover it with a probe charge.
            while True:
                check();fresh=reader.read();check();validate(plan,fresh)
                if fresh.get('mode')!=method:raise RuntimeError('Cambió Slice / Drag; vuelve a pulsar el atajo')
                if fresh.get('busy'):break
                if time.monotonic()-start>.5:raise RuntimeError('El juego no inició la carga; no se repite el tiro')
                time.sleep(.005)
            sensitivity=fresh.get('dragSens');dpr=plan.get('dpr',1)
            if not isinstance(sensitivity,(int,float)) or not math.isfinite(sensitivity) or not 0<sensitivity<=10:
                raise RuntimeError('No se pudo leer la sensibilidad de este arrastre; entrada liberada')
            if not isinstance(dpr,(int,float)) or not math.isfinite(dpr) or not 0<dpr<=8:
                raise RuntimeError('Cambió la escala de pantalla; vuelve a calcular')
            drag_origin=fresh.get('dragStartX');move_revision=fresh.get('dragUpdates')
            if not isinstance(drag_origin,(int,float)) or not math.isfinite(drag_origin) or not isinstance(move_revision,int):
                raise RuntimeError('No se pudo confirmar el origen del arrastre; entrada liberada')
            dx=plan['power']*sensitivity*dpr;px=round(x+dx)
            if not getattr(reader,'drag_box',plan['screenBox'])[0]+5<px<getattr(reader,'drag_box',plan['screenBox'])[2]-5:
                raise RuntimeError('El arrastre no cabe en la ventana; usa Slice')
            expected_drag_x=drag_origin+(px-x)/dpr;move_started=time.monotonic()
            report('drag-start',requested=plan['power'],sensitivity=sensitivity,previousPower=fresh.get('power'))
            last_cursor=(px,y);backend.move(*last_cursor);charging=True
        while True:
            check()
            state=reader.read();check();power=state.get('power')
            # At full charge the native controller can already have released
            # and advanced the turn before our final reading arrives.
            full_drag_confirmed=(method=='drag' and state.get('dragStartX')==drag_origin and state.get('dragSens')==sensitivity and isinstance(state.get('dragUpdates'),int) and state['dragUpdates']>move_revision and isinstance(state.get('dragPointX'),(int,float)) and abs(state['dragPointX']-expected_drag_x)<=1)
            if plan['power']==400 and power==400 and state.get('turn')!=plan['hero'] and (full_drag_confirmed or method=='space' and last_power>=380):
                return {'power':400,'method':method}
            validate(plan,state)
            if state['mode']!=method:raise RuntimeError('Cambió Slice / Drag; vuelve a pulsar el atajo')
            if not isinstance(power,(int,float)) or not math.isfinite(power):raise RuntimeError('No se pudo medir la fuerza')
            now=time.monotonic()
            if method=='drag':
                if state.get('dragStartX')!=drag_origin or state.get('dragSens')!=sensitivity:
                    raise RuntimeError('Cambió el arrastre; entrada liberada')
                observed_x=state.get('dragPointX');revision=state.get('dragUpdates')
                confirmed=isinstance(revision,int) and revision>move_revision and isinstance(observed_x,(int,float)) and math.isfinite(observed_x) and abs(observed_x-expected_drag_x)<=1
                if not confirmed:
                    if now-move_started>.7:raise RuntimeError('El juego no confirmó el movimiento del mouse; entrada liberada')
                    time.sleep(.01);continue
                report('drag-confirmed',power=power,updates=revision)
            if not charging:
                if not state.get('busy'):
                    if now-start>.5:raise RuntimeError('El juego no inició la carga; no se repite el tiro')
                    time.sleep(.005);continue
                charging=True
            elif not state.get('busy'):raise RuntimeError('La carga terminó antes de alcanzar la fuerza')
            if power!=last_power:last_change=now;last_power=power
            if method=='space':
                if power>=plan['power']-1:return {'power':power,'method':method}
            else:
                if power==plan['power']:
                    report('release',power=power);return {'power':power,'method':method}
                if power>0:
                    dx+=max(-80,min(80,(plan['power']-power)*sensitivity*dpr))
                else:dx+=8*plan.get('dpr',1)
                px=round(x+dx)
                if not getattr(reader,'drag_box',plan['screenBox'])[0]+5<px<getattr(reader,'drag_box',plan['screenBox'])[2]-5:raise RuntimeError('El arrastre no cabe en la ventana; usa Slice')
                move_revision=revision;expected_drag_x=drag_origin+(px-x)/dpr;move_started=now
                last_cursor=(px,y);backend.move(*last_cursor)
            if now-start>5 or now-last_change>.7:raise RuntimeError('La carga no responde; entrada liberada')
            time.sleep(.004 if method=='space' else .015)
    finally:
        # SendInput queues the release. Restoring through SetCursorPos before
        # Chrome consumes mouseup can reset the shot to minimum force.
        if held:
            if method=='space':backend.key(False)
            else:backend.mouse(False)
