"""One explicit shortcut shot through native Windows controls, with live checks."""
import math,time
from adapters import AdapterClient
from auto_fire import validate
from firing import WindowsInput
from automatic import GEOMETRY_JS,content_origin,screen_geometry

class GunBoundPowerReader:
    def __init__(self,endpoint,target=None):
        self.client=AdapterClient(endpoint,target,'gunbound-world')
        self.initial=self.client.sample()
        if self.initial.get('status')!='live':self.close();raise RuntimeError('Espera una partida activa')
        self.client.sock.settimeout(.4)
    def read(self):
        script="""function(){const s=this.room.state,p=s.players.get(this.myId),rear=['nak','aduka'].includes(p?.mobileId),right=(p?.facing==='right')!==rear;
        return {hero:this.myId,turn:s.activePlayerId,power:this.drag?.power??this.power,lastPower:this.lastPower,mode:this.inputMode==='slice'?'space':this.inputMode==='drag'?'drag':null,
        focused:document.hasFocus()&&document.visibilityState==='visible',over:this.destroyed||s.phase==='GAME_OVER'||s.phase==='LOBBY',blocked:this.gameInputBlocked||!this.roomConnected||this.observer||this.renderSurface!=='live'||s.phase!=='TURN',
        chat:['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)||!!document.activeElement?.isContentEditable,moving:!!this.moveHeld||!!this.touchAimHeld||!!this.keyboardMoveKeys?.size,
        busy:!!this.charging||!!this.drag,shot:({shot1:0,shot2:1,ss:2})[this.shot],wind:s.windPower,windAngle:s.windAngleDeg,armedItem:!!p?.armedItem,
        sensitivity:this.graphicsSettings?.dragSensitivity,canvasWidth:this.app.canvas.getBoundingClientRect().width,stageWidth:this.stageSize.width,
        players:[...s.players.$items.entries()].map(([id,p])=>({id,x:p.x,y:p.y,rawAngle:id===this.myId?this.angle:p.aimAngle,body:p.bodyTilt,look:p.facing==='right'?1:0,dead:p.alive===false||p.hp<=0}))}}
        """
        result=self.client.call('Runtime.callFunctionOn',{'objectId':self.client.controller,'functionDeclaration':script,'returnByValue':True})
        if result.get('exceptionDetails'):raise RuntimeError('No se pudo confirmar la fuerza del juego')
        return result['result']['value']
    def drag_start(self,window):
        meta=self.client.call('Runtime.evaluate',{'expression':GEOMETRY_JS,'returnByValue':True})['result']['value'];origin=content_origin(meta)
        script="""(()=>{const c=document.querySelector('canvas.gb-battle-canvas');if(!c)return null;const r=c.getBoundingClientRect();for(const fraction of [.15,.25,.4]){const x=r.left+r.width*.12,y=r.top+r.height*fraction;if(document.elementFromPoint(x,y)===c)return [x,y]}return null})()"""
        point=self.client.call('Runtime.evaluate',{'expression':script,'returnByValue':True})['result'].get('value')
        if not origin or meta.get('windowHandle')!=window or not point or not meta.get('focused'):raise RuntimeError('No hay una zona libre para arrastrar')
        self.drag_box,_=screen_geometry(meta,origin)
        return tuple(round(origin[i]+point[i]*meta.get('dpr',1)) for i in (0,1))
    def close(self):self.client.close()

def execute_gunbound(plan,reader,cancel,backend=None,trace=None):
    if not isinstance(plan['power'],(int,float)) or not math.isfinite(plan['power']) or not 3<=plan['power']<=100:raise ValueError('Fuerza fuera de rango')
    backend=backend or WindowsInput();state=reader.read();validate(plan,state)
    if state.get('blocked') or state.get('armedItem'):raise RuntimeError('Espera tu turno y desactiva el ítem antes de disparar')
    if state.get('busy') or backend.input_busy():raise RuntimeError('Termina la carga actual')
    method=state['mode'];held=False;cursor=None;rect=backend.window_rect(plan['window']);start=time.monotonic();last=-1;changed=start;charging=False;move_sent=False
    def check():
        if cancel.is_set() or backend.escaped():raise RuntimeError('Entrada liberada; puede salir un tiro parcial')
        if backend.foreground()[0]!=plan['window'] or backend.window_rect(plan['window'])!=rect:raise RuntimeError('La ventana cambió; entrada liberada')
        if cursor and math.dist(backend.cursor(),cursor)>3:raise RuntimeError('Moviste el mouse; entrada liberada')
    check()
    try:
        if method=='space':backend.key(True);held=True
        else:
            x,y=reader.drag_start(plan['window']);check();backend.move(x,y);cursor=(x,y)
            if not backend.point_in_window(x,y,plan['window']):raise RuntimeError('Otra ventana cubre el arrastre')
            backend.mouse(True);held=True
        while True:
            check();state=reader.read();check();power=state.get('power')
            if charging and plan['power']==100 and not state.get('busy') and state.get('lastPower')==100 and (method=='space' or move_sent):return {'power':100,'method':method}
            validate(plan,state)
            if state.get('blocked') or state.get('armedItem') or state['mode']!=method:raise RuntimeError('Cambió el turno, modo o ítem; entrada liberada')
            if not isinstance(power,(int,float)) or not math.isfinite(power):raise RuntimeError('No se pudo leer la fuerza')
            now=time.monotonic()
            if not state.get('busy'):
                if charging or now-start>.6:raise RuntimeError('La carga no está activa; no se repite el tiro')
                time.sleep(.01);continue
            charging=True
            if power!=last:last=power;changed=now
            if method=='space':
                if power>=plan['power']-.25:return {'power':power,'method':method}
            elif abs(power-plan['power'])<=.4:return {'power':power,'method':method}
            elif not move_sent:
                sensitivity=state.get('sensitivity');sensitivity=round(max(50,min(150,sensitivity))) if isinstance(sensitivity,(int,float)) and math.isfinite(sensitivity) else 100
                scale=state['canvasWidth']/state['stageWidth']*plan.get('dpr',1)
                dx=plan['power']*2.5*100/sensitivity*scale;box=getattr(reader,'drag_box',plan['screenBox'])
                direction=1 if x+dx<box[2]-8 else -1
                px=round(x+direction*dx)
                if not box[0]+8<px<box[2]-8:raise RuntimeError('El arrastre no cabe; usa Slice')
                if not backend.point_in_window(px,y,plan['window']):raise RuntimeError('Otra ventana cubre el arrastre')
                cursor=(px,y);backend.move(*cursor);move_sent=True
            if now-start>5 or now-changed>.8:raise RuntimeError('La barra no confirmó la fuerza; entrada liberada')
            time.sleep(.004 if method=='space' else .01)
    finally:
        if held:
            if method=='space':backend.key(False)
            else:backend.mouse(False)
