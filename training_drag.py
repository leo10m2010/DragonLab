"""Measured Drag through the pinned CDP target; never moves the desktop cursor."""
import math,time
from training_input import RecoverableInputError

# Observed DragonBound UIDragStart chooses random(130,170)/100, afresh on
# every press. Reserve space for that entire range BEFORE starting a charge.
MAX_SENSITIVITY=1.7
DRAG_GEOMETRY_JS=r"""(()=>{
 const game=document.getElementById('gameScreen');if(!game)return null;
 const r=game.getBoundingClientRect(),right=Math.min(r.right,innerWidth)-6;
 const bad='#gameui,#touch_ui,#gameChatHtml,#gameChat .scrollbar,#howtoplay,button,input,textarea,select,a,[role="button"]';
 const free=(x,y)=>{const e=document.elementFromPoint(x,y);return !!e&&game.contains(e)&&!e.closest(bad)};
 let best=null;for(const fy of [.28,.12,.42]){
  const x=Math.max(6,r.left+16),y=r.top+Math.min(r.height*.75,516)*fy;
  if(y<6||y>Math.min(innerHeight,r.bottom)-6||!free(x,y))continue;
  let end=x;for(let xx=x;xx<=right;xx+=8){if(!free(xx,y))break;end=xx}
  if(end>x&&(!best||end-x>best.right-best.x))best={x,y,right:end,left:r.left,top:r.top,width:r.width,height:r.height,scrollX,scrollY,viewportWidth:innerWidth,viewportHeight:innerHeight};
 }return best;
})()"""

def number(value):return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)

def prepare_drag(client,power):
    if not number(power) or not 1<=power<=400:raise ValueError('Fuerza inválida')
    value=client.call('Runtime.evaluate',{'expression':DRAG_GEOMETRY_JS,'returnByValue':True}).get('result',{}).get('value')
    fields=('x','y','right','left','top','width','height','scrollX','scrollY','viewportWidth','viewportHeight')
    if not isinstance(value,dict) or not all(number(value.get(k)) for k in fields):return None
    if value['width']<=0 or value['height']<=0 or value['right']-value['x']<math.ceil(power*MAX_SENSITIVITY)+3:return None
    return {k:value[k] for k in fields}

def charge_drag(client,reader,geometry,power,cancel,guard,validate,on_press):
    """One reserved attempt. No fallback/retry after mousePressed, even on error.

    validate checks native turn/pose/wind. Full power may release itself before
    the final read; allow_released is only used with a proven fresh native move.
    """
    held=False;x,y=geometry['x'],geometry['y'];px=x;started=time.monotonic();expected=None;move_started=None
    def layout():
        fresh=prepare_drag(client,power)
        if not fresh or any(abs(fresh[k]-v)>.5 for k,v in geometry.items()):raise RecoverableInputError('Cambió la zona de arrastre; no se repite este tiro',method='drag',code='layout-changed')
    def send(kind,down):
        client.call('Input.dispatchMouseEvent',{'type':kind,'x':px,'y':y,'button':'left' if kind!='mouseMoved' else 'none','buttons':1 if down else 0,**({'clickCount':1} if kind!='mouseMoved' else {})})
    def read():
        guard(cancel)
        if cancel.is_set():raise RuntimeError('Arrastre detenido; entrada liberada')
        return reader.read()
    try:
        layout();initial=read();validate(initial)
        if initial.get('busy') or initial.get('moving'):raise RecoverableInputError('Ya hay otra carga o movimiento; no se inicia el arrastre',method='drag',code='input-busy')
        send('mouseMoved',False)
        before=read();validate(before)
        if before.get('busy') or before.get('moving'):raise RecoverableInputError('Ya hay otra carga o movimiento; no se inicia el arrastre',method='drag',code='input-busy')
        # Mark BEFORE dispatch: a timeout can occur after Chrome accepted input.
        on_press();held=True;started=time.monotonic();send('mousePressed',True)
        while True:
            state=read();validate(state)
            if state.get('busy'):break
            if time.monotonic()-started>.5:raise RecoverableInputError('El juego no inició el arrastre; no se repite el tiro',method='drag',code='drag-not-started')
            cancel.wait(.005)
        sensitivity=state.get('dragSens');origin=state.get('dragStartX');revision=state.get('dragUpdates')
        if not number(sensitivity) or not 1.3<=sensitivity<=MAX_SENSITIVITY or not number(origin) or not isinstance(revision,int):raise RecoverableInputError('No se confirmó la sensibilidad de este arrastre; entrada liberada',method='drag',code='drag-contract-changed')
        # Native pageX differs from CDP CSS x only by the document scroll.
        if abs(origin-(x+geometry['scrollX']))>1:raise RecoverableInputError('El juego registró otro origen de arrastre; entrada liberada',method='drag',code='drag-origin-changed')
        corrections=0
        def move(delta):
            nonlocal px,expected,move_started
            layout();px=round(x+delta,2)
            if not x<=px<=geometry['right']:raise RecoverableInputError('El arrastre sale del juego; entrada liberada',method='drag',code='drag-out-of-bounds')
            expected=origin+(px-x);move_started=time.monotonic();send('mouseMoved',True)
        move(power*sensitivity)
        while True:
            state=read();actual=state.get('power');native_x=state.get('dragPointX');updated=state.get('dragUpdates')
            same=state.get('dragStartX')==origin and state.get('dragSens')==sensitivity
            confirmed=same and isinstance(updated,int) and updated>revision and number(native_x) and abs(native_x-expected)<=1
            full=power==400 and actual==400 and confirmed
            validate(state,allow_released=full)
            if not same:raise RecoverableInputError('Cambió el arrastre; entrada liberada',method='drag',code='drag-origin-changed')
            now=time.monotonic()
            if now-started>1.5:raise RecoverableInputError('El arrastre no confirmó la fuerza a tiempo; entrada liberada',method='drag',code='drag-power-timeout')
            if not confirmed:
                if now-move_started>.65:raise RecoverableInputError('El juego no confirmó el movimiento; entrada liberada',method='drag',code='drag-move-timeout')
                cancel.wait(.01);continue
            if not number(actual) or not 1<=actual<=400:raise RecoverableInputError('Fuerza nativa inválida; entrada liberada',method='drag',code='invalid-power')
            if not state.get('busy') and not full:raise RecoverableInputError('El arrastre terminó antes de tiempo',method='drag',code='drag-ended-early')
            if abs(actual-power)<=1:
                layout()
                return {'power':actual,'method':'drag','charge_ms':round((now-started)*1000,2),'sensitivity':sensitivity,'corrections':corrections,'power_error':actual-power}
            if corrections>=4:raise RecoverableInputError('La fuerza no converge; entrada liberada',method='drag',code='drag-power-diverged')
            revision=updated;corrections+=1
            move(px-x+max(-80,min(80,(power-actual)*sensitivity)))
    finally:
        # Release on this target at the LAST coordinates, including transport
        # failure/cancellation. Moving back before mouseup changes native force.
        if held:send('mouseReleased',False)
