"""Normal browser input on the verified DragonBound tab; no game function calls."""
import json,time,math,re
from cdp import CDP
from auto_fire import PowerReader
UI_JS=r"""(()=>{
 const box=e=>{if(!e)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e);if(r.width<2||r.height<2||s.visibility==='hidden'||s.display==='none')return null;
 const x=r.left+r.width/2,y=r.top+r.height/2,hit=document.elementFromPoint(x,y);return hit&&(hit===e||e.contains(hit))?{x,y}:null};
 const ids=['buttonStart1v1','lobbyButtonMobile','roomMobileSelectCancel','btnShot1','btnShot2','btnShotSS','slice_drag_button'];
 const controls=Object.fromEntries(ids.map(id=>[id,box(document.getElementById(id))]));
 const options=[...document.querySelectorAll('#roomMobileSelect .mobileSelectBtn[data-mobile]')].map(e=>({id:Number(e.dataset.mobile),name:e.querySelector('.mobileName')?.textContent,point:box(e),selected:e.classList.contains('mobileSelectCurrent')})).filter(o=>o.point);
 const alert=document.getElementById('myDialog'),ok=box(document.getElementById('DragonDialogOK'));
 const away=ok&&/Creo que estás ausente/.test(alert?.textContent||'')?ok:null;
 return {url:location.href,focused:document.hasFocus(),chat:['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)||!!document.activeElement?.isContentEditable,game:!!box(document.getElementById('gameScreen')),controls,options,away,blocked:!!ok&&!away,stop:!!window.__dragonlabTrainingStop?.stopped};
})()"""

class UnavailableShot(RuntimeError):pass

class TrainingBrowser:
    def __init__(self,endpoint,target=None):
        self.client=CDP(endpoint,target_id=target);self.client.sock.settimeout(.5);self.reader=None
    def ui(self):
        state=self.client.call('Runtime.evaluate',{'expression':UI_JS,'returnByValue':True}).get('result',{}).get('value',{})
        if not re.fullmatch(r'https://dragonbound\.net/#server-8(?:/room-\d+)?/?',state.get('url','')):raise RuntimeError('El entrenamiento solo está habilitado en Avatar Off, servidor 8')
        return state
    def guard(self,cancel):
        if cancel.is_set():raise RuntimeError('Entrenamiento detenido')
        ui=self.ui()
        if ui.get('stop'):cancel.set();raise RuntimeError('Esc: entrenamiento detenido')
        if not ui.get('focused') or ui.get('chat'):raise RuntimeError('Entrenamiento pausado: vuelve al juego y cierra el chat')
        return ui
    def click(self,point,cancel):
        self.guard(cancel)
        if not point or not all(isinstance(point.get(k),(int,float)) and math.isfinite(point[k]) for k in ('x','y')):raise RuntimeError('Control no disponible')
        args={'x':point['x'],'y':point['y'],'button':'left','clickCount':1}
        try:self.client.call('Input.dispatchMouseEvent',{'type':'mousePressed',**args})
        finally:self.client.call('Input.dispatchMouseEvent',{'type':'mouseReleased',**args})
    def key(self,key,down):
        codes={'space':(' ',32,'Space'),'up':('ArrowUp',38,'ArrowUp'),'down':('ArrowDown',40,'ArrowDown')}
        name,vk,code=codes[key]
        self.client.call('Input.dispatchKeyEvent',{'type':'keyDown' if down else 'keyUp','key':name,'code':code,'windowsVirtualKeyCode':vk,'nativeVirtualKeyCode':vk})
    def arm(self):
        self.client.call('Page.bringToFront')
        self.client.call('Runtime.evaluate',{'expression':"(()=>{const old=window.__dragonlabTrainingStop;if(old?.handler)window.removeEventListener('keydown',old.handler,true);const s={stopped:false};s.handler=e=>{if(e.isTrusted&&e.key==='Escape')s.stopped=true};window.addEventListener('keydown',s.handler,true);window.__dragonlabTrainingStop=s})()"})
    def sample(self):return self.client.sample()
    def shoot(self,probe,cancel):
        self.reader=PowerReader(self.client.endpoint,self.client.target['id']);reader=self.reader
        held=None
        try:
            ui=self.guard(cancel);s=reader.read()
            if s.get('over') or s.get('turn')!=s.get('hero') or s.get('busy') or s.get('moving'):raise RuntimeError('Esperando tu turno sin movimiento')
            hero_id=s['hero'];target_shot=probe['shot']
            if s.get('shot')!=target_shot:
                self.click(ui['controls'].get(('btnShot1','btnShot2','btnShotSS')[target_shot]),cancel);time.sleep(.08);s=reader.read()
                if s.get('shot')!=target_shot:raise UnavailableShot('Tiro no disponible; esperando recarga')
            # Slice has a readable live bar and does not move the user's pointer.
            if s.get('mode')!='space':
                self.click(self.guard(cancel)['controls'].get('slice_drag_button'),cancel);time.sleep(.08);s=reader.read()
                if s.get('mode')!='space':raise RuntimeError('No se pudo activar Slice')
            started=time.monotonic()
            for _ in range(40):
                self.guard(cancel);s=reader.read()
                if s.get('turn')!=hero_id:raise RuntimeError('Cambió el turno')
                hero=next((p for p in s['players'] if p['id']==hero_id),None)
                if not hero:raise RuntimeError('Jugador sin posición')
                angle=hero.get('rawAngle');delta=probe['angle']-angle if isinstance(angle,(int,float)) else 0
                if abs(delta)<=2 or time.monotonic()-started>2:break
                held='up' if delta>0 else 'down';self.key(held,True);time.sleep(.045);self.key(held,False);held=None
            s=reader.read();hero=next(p for p in s['players'] if p['id']==hero_id)
            release={'hero':hero_id,'x':hero['x'],'y':hero['y'],'shot':target_shot,'angle':hero.get('rawAngle'),'wind':s.get('wind'),'windAngle':s.get('windAngle'),'baseline':[]}
            from shot_attribution import identity,attributed_start
            release['baseline']=[identity(p) for p in self.sample().get('shots',[])]
            self.guard(cancel);held='space';self.key('space',True);start=time.monotonic();charging=False
            while time.monotonic()-start<4:
                self.guard(cancel);s=reader.read()
                if s.get('turn')!=hero_id or s.get('over') or s.get('shot')!=target_shot:raise RuntimeError('Cambió el contexto del tiro')
                current=next((p for p in s.get('players',[]) if p.get('id')==hero_id),None)
                if not current or s.get('moving') or math.hypot(current['x']-release['x'],current['y']-release['y'])>1 or s.get('wind')!=release['wind'] or s.get('windAngle')!=release['windAngle']:raise RuntimeError('Cambió la posición o el viento durante la carga')
                if s.get('busy'):charging=True
                elif charging:raise RuntimeError('La carga terminó antes de tiempo')
                power=s.get('power')
                if charging and isinstance(power,(int,float)) and power>=probe['power']-1:
                    release['power']=power;break
                time.sleep(.01)
            else:raise RuntimeError('La barra no confirmó la fuerza')
            self.key('space',False);held=None
            # Capture observed starts while their own-shooter attribution is fresh.
            until=time.monotonic()+.6;observed=None
            while time.monotonic()<until:
                observed=self.sample()
                if any(identity(p) not in release['baseline'] and (attributed_start(observed,p,release) or {}).get('learnable') for p in observed.get('shots',[])):return release,observed
                time.sleep(.025)
            raise RuntimeError('Tiro liberado, pero sin salida propia confirmada; no se usará para calibrar')
        finally:
            try:
                if held:self.key(held,False)
            finally:reader.close();self.reader=None
    def close(self):
        try:self.client.call('Runtime.evaluate',{'expression':"(()=>{const s=window.__dragonlabTrainingStop;if(s?.handler)window.removeEventListener('keydown',s.handler,true);delete window.__dragonlabTrainingStop})()"})
        except Exception:pass
        self.client.close()
