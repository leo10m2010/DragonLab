"""Normal browser input on the verified DragonBound tab; no game function calls."""
import json,time,math,re
from cdp import CDP
from auto_fire import PowerReader
from training_drag import prepare_drag,charge_drag
from training_input import RecoverableInputError
from training_orientation import desired_look,raw_angle,up_increases_raw
from training_aim import NoAim
UI_JS=r"""(()=>{
 const box=(e,control)=>{if(!e)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e);if(r.width<2||r.height<2||s.visibility==='hidden'||s.display==='none')return null;
 const x=r.left+r.width/2,y=r.top+r.height/2,hit=document.elementFromPoint(x,y);return hit&&(hit===e||e.contains(hit))?{x,y,control:control||e.id||null}:null};
 const shotIds=['btnShot1','btnShot2','btnShotSS'];
 const usable=e=>!!e&&!e.disabled&&e.getAttribute('aria-disabled')!=='true'&&!['grayscale','disabled','Disabled'].some(k=>e.classList.contains(k));
 const ids=['buttonStart1v1','lobbyButtonMobile','roomMobileSelectCancel',...shotIds,'slice_drag_button','btnPass'];
 const controls=Object.fromEntries(ids.map(id=>[id,shotIds.includes(id)&&!usable(document.getElementById(id))?null:box(document.getElementById(id),id)]));
 const shotReady=shotIds.map(id=>!!controls[id]);
 const options=[...document.querySelectorAll('#roomMobileSelect .mobileSelectBtn[data-mobile]')].map(e=>({id:Number(e.dataset.mobile),name:e.querySelector('.mobileName')?.textContent,point:box(e,'mobile:'+e.dataset.mobile),selected:e.classList.contains('mobileSelectCurrent')})).filter(o=>o.point);
 const alert=document.getElementById('myDialog'),ok=box(document.getElementById('DragonDialogOK'),'dialog-ok');
 const loading=!!ok&&/Ingresar\.\.\. Por favor espere/.test(alert?.textContent||'')&&/Cargando/.test(alert?.textContent||'');
 const away=ok&&/Creo que estás ausente/.test(alert?.textContent||'')?ok:null;
 const retirementText=ok?(alert?.textContent||''):'';
 const retirementMatch=/Dejaste el Juego/.test(retirementText)&&/Porque te retiraste de una partida/.test(retirementText)?retirementText.match(/(?:en\s+)?(\d+)\s*Segundos?/i):null;
 const retirement=retirementMatch?{seconds:Math.min(3600,Number(retirementMatch[1])),point:ok}:null;
 const notice=ok&&/Regalo Recibido/.test(retirementText)&&/Has recibido un regalo/.test(retirementText)?{kind:'gift-received',point:ok}:null;
 const entries=location.hash===''?[...document.querySelectorAll('span,div')].filter(e=>!e.children.length&&e.textContent.trim()==='Avatar Off').map(e=>box(e,'server-avatar-off')).filter(Boolean):[];
 const dual=document.querySelector('[id^=gameItemSlot].ItemBtn.itemDual');controls.dual=box(dual,'dual');
 const selectedItems=[...document.querySelectorAll('[id^=gameItemSlot].ItemBtn.Pressed')].map(e=>({id:e.id,dual:e.classList.contains('itemDual')}));
 return {loading,retirement,notice,shotReady,dualSelected:!!dual?.classList.contains('Pressed'),selectedItems,url:location.href,serverEntry:entries.length===1?entries[0]:null,focused:document.hasFocus(),chat:['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)||!!document.activeElement?.isContentEditable,game:!!box(document.getElementById('gameScreen')),controls,options,away,blocked:!!ok&&!away,stop:!!window.__dragonlabTrainingStop?.stopped};
})()"""

class TurnExpired(RuntimeError):pass
class TurnNotReady(RuntimeError):pass
class UnconfirmedShot(RuntimeError):pass
class UnavailableShot(RuntimeError):pass
class FocusPause(RuntimeError):pass

class TrainingBrowser:
    def __init__(self,endpoint,target=None):
        self.client=CDP(endpoint,target_id=target)
        from training_lease import TrainingLease
        try:self.control_lease=TrainingLease('target:'+self.client.endpoint+':'+self.client.target['id'])
        except Exception:self.client.close();raise
        self.movement_events=[];self.client.sock.settimeout(.5);self.client.terrain_interval=4;self.reader=None
    def ui(self):
        state=self.client.call('Runtime.evaluate',{'expression':UI_JS,'returnByValue':True}).get('result',{}).get('value',{})
        if not re.fullmatch(r'https://dragonbound\.net/#server-8(?:/room-\d+)?/?',state.get('url','')) and state.get('url')!='https://dragonbound.net/':raise RuntimeError('El entrenamiento solo está habilitado en Avatar Off, servidor 8')
        return state
    def guard(self,cancel):
        if cancel.is_set():raise RuntimeError('Entrenamiento detenido')
        ui=self.ui()
        if ui.get('stop'):cancel.set();raise RuntimeError('Esc: entrenamiento detenido')
        if ui.get('blocked') and getattr(self,'reader',None) is not None:raise FocusPause('En pausa: apareció un aviso durante la preparación del tiro')
        if ui.get('chat') or not getattr(self,'background',False) and not ui.get('focused'):raise FocusPause('En pausa: vuelve al juego y cierra el chat para continuar')
        return ui
    def click(self,point,cancel):
        ui=self.guard(cancel)
        role=point.get('control') if isinstance(point,dict) else None
        if ui.get('blocked') and role!='dialog-ok':raise TurnNotReady('Hay un aviso sobre el juego; no se pulsa el control anterior')
        if role:
            current=(ui.get('controls') or {}).get(role)
            if role.startswith('mobile:'):current=next((o.get('point') for o in ui.get('options',[]) if 'mobile:'+str(o.get('id'))==role),None)
            elif role=='server-avatar-off':current=ui.get('serverEntry')
            elif role=='dialog-ok':
                current=ui.get('away') or (ui.get('notice') or {}).get('point')
                retired=ui.get('retirement') or {}
                if not current and retired and time.monotonic()>=getattr(self,'retirement_until',math.inf):current=retired.get('point')
            if not current:raise TurnNotReady('El control cambió; se recalculará sin pulsar otra zona')
            point=current
        if not point or not all(isinstance(point.get(k),(int,float)) and math.isfinite(point[k]) for k in ('x','y')):raise RuntimeError('Control no disponible')
        actions=getattr(self,'click_events',[]);actions.append({'control':role or 'legacy-point','at':time.time()});self.click_events=actions[-64:]
        args={'x':point['x'],'y':point['y'],'button':'left','clickCount':1}
        try:self.client.call('Input.dispatchMouseEvent',{'type':'mousePressed',**args})
        finally:self.client.call('Input.dispatchMouseEvent',{'type':'mouseReleased',**args})
    def key(self,key,down):
        codes={'space':(' ',32,'Space'),'up':('ArrowUp',38,'ArrowUp'),'down':('ArrowDown',40,'ArrowDown'),'left':('ArrowLeft',37,'ArrowLeft'),'right':('ArrowRight',39,'ArrowRight')}
        name,vk,code=codes[key]
        self.client.call('Input.dispatchKeyEvent',{'type':'keyDown' if down else 'keyUp','key':name,'code':code,'windowsVirtualKeyCode':vk,'nativeVirtualKeyCode':vk})
    def arm(self,focus=True):
        if getattr(self,'background',False):self.client.call('Emulation.setFocusEmulationEnabled',{'enabled':True})
        if focus and not getattr(self,'background',False):self.client.call('Page.bringToFront')
        self.client.call('Runtime.evaluate',{'expression':"(()=>{const old=window.__dragonlabTrainingStop;if(old?.handler)window.removeEventListener('keydown',old.handler,true);const s={stopped:false};s.handler=e=>{if(e.isTrusted&&e.key==='Escape')s.stopped=true};window.addEventListener('keydown',s.handler,true);window.__dragonlabTrainingStop=s})()"})
    def sample(self):return self.client.sample()
    def seconds_left(self):
        deadline=getattr(self,'turn_deadline',None)
        return max(0,deadline-time.monotonic()) if deadline is not None else 120
    def require_charge_time(self):
        if self.seconds_left()<4.5:raise TurnExpired('Queda poco tiempo para confirmar la carga; esperando otro turno')
    @staticmethod
    def require_shot_ready(ui,shot):
        ready=ui.get('shotReady')
        if isinstance(ready,list) and (shot not in (0,1,2) or len(ready)<=shot or not ready[shot]):
            raise UnavailableShot('SS está recargando; se buscará una bala normal' if shot==2 else 'Esta bala no está disponible todavía')
    def pass_turn(self,key,cancel,before_pass):
        from training_turns import turn_key
        ui=self.guard(cancel)
        if ui.get('blocked') or not ui.get('game'):return False
        if turn_key(self.sample(),ui.get('url'))!=key:raise TurnExpired('Cambió el turno antes de pasarlo')
        point=(ui.get('controls') or {}).get('btnPass')
        if not point:return False
        before_pass();self.click(point,cancel)
        until=time.monotonic()+.4
        while time.monotonic()<until:
            if turn_key(self.sample(),ui.get('url'))!=key:return True
            if cancel.wait(.025):break
        return False
    def confirm_setting(self,reader,serial,field,value,cancel):
        """Wait for the actual game setting, without assuming one render frame."""
        until=time.monotonic()+.45
        while True:
            self.guard(cancel);state=reader.read()
            if state.get('over') or state.get('turnNumber')!=serial or state.get('turn')!=state.get('hero'):raise TurnExpired('Cambió el turno al confirmar los controles')
            if state.get(field)==value:return state
            if time.monotonic()>=until:break
            if cancel.wait(.02):raise RuntimeError('Selección cancelada')
        raise UnavailableShot('El juego todavía no confirmó la modalidad' if field=='shot' else 'No se pudo confirmar el modo de carga')
    def prepare_charge(self,reader,serial,power,cancel):
        recovery=getattr(self,'input_recovery',{})
        geometry=prepare_drag(self.client,power) if time.monotonic()>=recovery.get('drag_disabled_until',0) else None
        method='drag' if geometry else 'space'
        state=reader.read()
        if state.get('mode')!=method:
            self.click(self.guard(cancel)['controls'].get('slice_drag_button'),cancel)
            self.confirm_setting(reader,serial,'mode',method,cancel)
        # Toggling the mode may change the available DOM area. Fallback is
        # permitted here only, before ledger reservation or any charge input.
        if method=='drag':
            geometry=prepare_drag(self.client,power)
            if not geometry:
                self.click(self.guard(cancel)['controls'].get('slice_drag_button'),cancel)
                self.confirm_setting(reader,serial,'mode','space',cancel);method='space'
        return method,geometry
    def validate_charge(self,state,release,allow_released=False):
        if state.get('over') or not allow_released and (state.get('turn')!=release['hero'] or state.get('turnNumber')!=release['turn_serial']):raise TurnExpired('Terminó el turno durante la carga')
        if state.get('shot')!=release['shot'] or state.get('mode')!=release['method']:raise RecoverableInputError('Cambió la modalidad durante la carga',method=release['method'],code='input-state-changed')
        current=next((p for p in state.get('players',[]) if p.get('id')==release['hero']),None)
        if not current or state.get('moving') or math.hypot(current['x']-release['x'],current['y']-release['y'])>1 or any(current.get(k)!=release.get('pose',{}).get(k) for k in ('look','body')) or current.get('rawAngle')!=release.get('angle') or state.get('wind')!=release['wind'] or state.get('windAngle')!=release['windAngle']:raise RecoverableInputError('Cambió la posición, el ángulo o el viento durante la carga',method=release['method'],code='input-state-changed')
    def verify_release(self,reader,release,cancel):
        """Last native check before reserving a turn or starting either input."""
        ui=self.guard(cancel);self.require_shot_ready(ui,release['shot']);state=reader.read()
        if state.get('over') or state.get('turnNumber')!=release['turn_serial'] or state.get('turn')!=release['hero']:raise TurnExpired('Cambió el turno antes de cargar')
        player=next((p for p in state.get('players',[]) if p.get('id')==release['hero']),None)
        if not player or state.get('busy') or state.get('moving') or state.get('shot')!=release['shot'] or state.get('mode')!=release.get('method','space'):raise TurnNotReady('Los controles cambiaron; recalculando antes de cargar')
        if math.hypot(player['x']-release['x'],player['y']-release['y'])>1 or any(player.get(k)!=release.get('pose',{}).get(k) for k in ('look','body')) or player.get('rawAngle')!=release.get('angle') or state.get('wind')!=release.get('wind') or state.get('windAngle')!=release.get('windAngle'):raise TurnNotReady('Cambió la posición, el ángulo o el viento; recalculando')
        target=release.get('target_before')
        planned=(release.get('learner') or {}).get('target')
        if target and planned and math.hypot(target['x']-planned[0],target['y']-planned[1])>3:raise TurnNotReady('El objetivo cambió durante el cálculo; recalculando')
        if target:
            current=next((p for p in state.get('players',[]) if str(p.get('id'))==str(target['id'])),None)
            if not current or current.get('dead') or math.hypot(current['x']-target['x'],current['y']-target['y'])>3:raise TurnNotReady('El objetivo cambió; recalculando antes de cargar')
        remaining=state.get('turnSeconds')
        if isinstance(remaining,(int,float)) and math.isfinite(remaining):self.turn_deadline=min(self.turn_deadline,time.monotonic()+remaining)
        self.require_charge_time()
    def adjust_angle(self,reader,target,cancel,expected_serial=None):
        state=reader.read();hero_id=state.get('hero');serial=state.get('turnNumber')
        if expected_serial is not None and serial!=expected_serial:raise TurnExpired('Cambió el turno antes de ajustar ángulo')
        hero=next((p for p in state.get('players',[]) if p.get('id')==hero_id),{})
        initial=hero.get('rawAngle')
        if not isinstance(initial,(int,float)) or not math.isfinite(initial):raise RuntimeError('Ángulo sin lectura; no se dispara')
        if not hasattr(self,'angle_limits'):self.angle_limits={}
        key=(getattr(self,'angle_mobile',None),getattr(self,'angle_shot',None),hero.get('body'),hero.get('look'))
        bounds=self.angle_limits.get(key,{})
        for source,destination in (('minAngle','low'),('maxAngle','high')):
            if isinstance(hero.get(source),(int,float)) and math.isfinite(hero[source]):bounds[destination]=hero[source]
        requested=target;target=max(bounds.get('low',-180),min(bounds.get('high',180),target))
        if abs(target-initial)<=1:return {'before':initial,'after':initial,'requested':requested,'reached':abs(requested-initial)<=1,'limited':target!=requested}
        if not hasattr(self,'angle_key_direction'):self.angle_key_direction={}
        control_key=getattr(self,'angle_mobile',None)
        increases=self.angle_key_direction.get(control_key,up_increases_raw(hero))
        direction='up' if (target>initial)==increases else 'down';last=initial;changed=time.monotonic();start=changed;stalled=False;switched=False
        try:
            self.guard(cancel);self.key(direction,True)
            while time.monotonic()-start<3 and self.seconds_left()>5:
                if cancel.wait(.025):raise RuntimeError('Entrenamiento detenido')
                self.guard(cancel);state=reader.read()
                if state.get('turn')!=hero_id or state.get('turnNumber')!=serial or state.get('over'):raise TurnExpired('Cambió el turno al ajustar ángulo')
                value=next((p.get('rawAngle') for p in state.get('players',[]) if p.get('id')==hero_id),None)
                if not isinstance(value,(int,float)) or not math.isfinite(value):raise RuntimeError('Se perdió la lectura del ángulo')
                if value!=last:
                    observed_increase=value>last
                    self.angle_key_direction[control_key]=observed_increase if direction=='up' else not observed_increase
                    if (target-initial)*(value-last)<0:
                        if switched:raise RuntimeError('Las teclas no confirman un ajuste estable; no se dispara')
                        self.key(direction,False);direction='down' if direction=='up' else 'up';self.key(direction,True);switched=True
                        last=value;changed=time.monotonic();continue
                    last=value;changed=time.monotonic()
                if abs(target-value)<=1 or (target-initial)*(target-value)<0:break
                if time.monotonic()-changed>.65:stalled=True;break
        finally:self.key(direction,False)
        # A limit is acceptable only after observing actual movement. Replan at it.
        if abs(last-initial)<.5:
            if self.seconds_left()<=5:raise TurnExpired('Se agotó el tiempo para ajustar el ángulo')
            raise NoAim('La flecha no cambió el ángulo; no se dispara',reason='angle-unavailable')
        if stalled:
            bounds['high' if last>initial else 'low']=last;self.angle_limits[key]=bounds
            if len(self.angle_limits)>64:self.angle_limits={key:bounds}
        return {'before':initial,'after':last,'requested':requested,'reached':abs(last-requested)<=1,'limited':stalled}
    def walk(self,reader,plan,cancel,expected_serial=None):
        state=reader.read();hero_id=state['hero'];serial=state.get('turnNumber')
        if expected_serial is not None and serial!=expected_serial:raise RuntimeError('Cambió el turno antes de caminar')
        p=next(p for p in state['players'] if p['id']==hero_id);origin=(p['x'],p['y']);last=p['x'];changed=time.monotonic();start=changed
        if state.get('turn')!=hero_id or state.get('busy') or state.get('over'):raise RuntimeError('No se puede caminar fuera de un turno disponible')
        try:
            self.guard(cancel);self.key(plan['direction'],True)
            while time.monotonic()-start<.65:
                if cancel.wait(.025):raise RuntimeError('Movimiento detenido')
                self.guard(cancel);state=reader.read()
                if state.get('turn')!=hero_id or state.get('turnNumber')!=serial or state.get('over'):raise TurnExpired('Cambió el turno al caminar')
                p=next(p for p in state['players'] if p['id']==hero_id)
                if p['y']-origin[1]>plan.get('max_drop',14):break
                if p['x']!=last:last=p['x'];changed=time.monotonic()
                if abs(p['x']-origin[0])>=plan['distance'] or time.monotonic()-changed>.25:break
        finally:self.key(plan['direction'],False)
        return {'from':list(origin),'to':[p['x'],p['y']],'direction':plan['direction']}
    def orient(self,reader,right,serial,cancel):
        state=reader.read();hero=next(p for p in state['players'] if p['id']==state['hero'])
        desired=desired_look(hero,right)
        if hero['look']==desired:return hero
        if state.get('turn')!=state['hero'] or state.get('turnNumber')!=serial:raise TurnExpired('Cambió el turno antes de orientar')
        direction='right' if desired else 'left'
        try:
            self.guard(cancel);self.key(direction,True)
            until=time.monotonic()+.6
            while time.monotonic()<until:
                if cancel.wait(.025):raise RuntimeError('Orientación detenida')
                self.guard(cancel);fresh=reader.read()
                if fresh.get('turn')!=state['hero'] or fresh.get('turnNumber')!=serial:raise TurnExpired('Cambió el turno al orientar')
                hero=next(p for p in fresh['players'] if p['id']==state['hero'])
                if hero['look']==desired:return hero
        finally:self.key(direction,False)
        raise NoAim('El carro no confirmó la orientación de salida',reason='orientation-unconfirmed')
    def plan_with_reposition(self,reader,autonomous,probe,target_x,serial,cancel):
        """At most two supported steps; every attempt replans from the actual pose."""
        from training_aim import NoAim
        from training_movement import choose_reposition
        movements=[];avoid=None;event=None
        recovery=getattr(self,'recovery_state',None)
        if not isinstance(recovery,dict):recovery={};self.recovery_state=recovery
        key=getattr(self,'recovery_key',serial)
        if recovery.get('key')!=key:recovery.clear();recovery.update(key=key,steps=0,visited=[])
        self.movement_turn=serial;self.turn_steps=recovery['steps'];self.visited_positions=recovery['visited']
        if not hasattr(self,'movement_events'):self.movement_events=[]
        for attempt in range(3):
            self.guard(cancel)
            fresh=reader.read()
            if fresh.get('turnNumber')!=serial or fresh.get('turn')!=fresh.get('hero'):raise TurnExpired('Cambió el turno al buscar un ángulo')
            player=next(p for p in fresh['players'] if p['id']==fresh['hero'])
            state=self.sample()
            try:
                result=self.timed_plan(autonomous,state,player,probe)
                if event:event.update(trajectory_found=True,reason='solution-found')
                return result,({'steps':movements,'from':movements[0]['from'],'to':movements[-1]['to']} if movements else None)
            except NoAim as error:
                if event:event.update(trajectory_found=False,reason=error.reason)
                if not error.reposition or self.turn_steps>=2 or attempt==2 or self.seconds_left()<8:
                    recover=getattr(autonomous,'excavate',None)
                    candidate=recover(state,player,probe,error) if callable(recover) and self.seconds_left()>=5 else None
                    if isinstance(candidate,dict):return candidate,({'steps':movements,'from':movements[0]['from'],'to':movements[-1]['to']} if movements else None)
                    raise
                def evaluate(hypothetical,step):
                    simulated={**player,'x':step['expected_to'][0],'y':step['expected_to'][1],'body':step['expected_body']}
                    try:
                        candidate=self.timed_plan(autonomous,hypothetical,simulated,probe)
                        return candidate.get('stage') in ('evaluación con modelo congelado','calibración dirigida provisional')
                    except NoAim:return False
                escape=(error.recovery or {}).get('weather_escape_x') if isinstance(error.recovery,dict) else None
                walk_target=escape if error.reason=='unknown-weather' and isinstance(escape,(int,float)) and math.isfinite(escape) else target_x
                step=choose_reposition(state,walk_target,error.reason,avoid=avoid,evaluate=evaluate,visited=self.visited_positions)
                if not step:
                    recover=getattr(autonomous,'excavate',None);candidate=recover(state,player,probe,error) if callable(recover) else None
                    if isinstance(candidate,dict):return candidate,({'steps':movements,'from':movements[0]['from'],'to':movements[-1]['to']} if movements else None)
                    blocked=NoAim(str(error)+'; no hay suelo seguro para cambiar de posición',reason='unsafe-ground')
                    blocked.excavation_reason=getattr(error,'excavation_reason',None)
                    raise blocked from error
                # Hypothetical plans can take time; reserve enough for angle
                # adjustment and charge again immediately before walking.
                if self.seconds_left()<8:raise NoAim('Se conserva el tiempo restante para otra modalidad',reason='recovery-time-budget')
                self.turn_steps+=1;recovery['steps']=self.turn_steps
                self.visited_positions.append([player['x'],player['y']])
                movement=self.walk(reader,step,cancel,expected_serial=serial);movements.append(movement)
                event={'selection':step.get('selection'),'turn':serial,'from':movement['from'],'to':movement['to'],'direction':movement['direction'],'trajectory_found':None,'reason':'awaiting-replan'}
                self.movement_events.append(event);self.movement_events=self.movement_events[-64:]
                if abs(movement['to'][0]-movement['from'][0])<.5:avoid=step['direction']
                self.orient(reader,target_x>=movement['to'][0],serial,cancel)
        raise NoAim('No se encontró un ángulo tras dos pasos')
    def timed_plan(self,autonomous,*args,**kwargs):
        started=time.perf_counter()
        try:return autonomous.plan(*args,**kwargs)
        finally:self.planning_ms=getattr(self,'planning_ms',0)+(time.perf_counter()-started)*1000
    def select_dual(self,reader,serial,cancel):
        self.require_charge_time();state=reader.read();ui=self.guard(cancel)
        if state.get('turnNumber')!=serial or state.get('turn')!=state.get('hero') or state.get('shot') not in (0,1):raise TurnExpired('DD requiere el mismo turno y bala 1 o 2')
        if any(not item.get('dual') for item in ui.get('selectedItems',[])):raise NoAim('Hay otro ítem seleccionado',reason='active-item')
        if not ui.get('controls',{}).get('dual'):return False
        if not ui.get('dualSelected'):
            self.dual_selected_here=True
            self.click(ui['controls']['dual'],cancel)
        for _ in range(6):
            fresh=reader.read()
            if fresh.get('turnNumber')!=serial or fresh.get('turn')!=fresh.get('hero'):raise TurnExpired('Cambió el turno al seleccionar DD')
            if self.guard(cancel).get('dualSelected'):return True
            if cancel.wait(.025):raise RuntimeError('Selección DD cancelada')
        raise NoAim('El juego no confirmó DD; no se carga',reason='item-unconfirmed')
    def shoot(self,probe,cancel,settings_provider=None,before_fire=None,autonomous=None):
        self.prepared_plan=None
        self.reader=PowerReader(self.client.endpoint,self.client.target['id']);reader=self.reader
        held=None;dual_selected_here=False;self.dual_selected_here=False;charge_started=False;serial=None;self.planning_ms=0;preparing_at=time.perf_counter()
        try:
            ui=self.guard(cancel);s=reader.read()
            if s.get('over') or s.get('turn')!=s.get('hero') or s.get('busy') or s.get('moving'):raise TurnNotReady('Esperando que termine el movimiento o la animación del turno')
            hero_id=s['hero'];serial=s.get('turnNumber');target_shot=probe['shot']
            self.require_shot_ready(ui,target_shot)
            remaining=s.get('turnSeconds');self.turn_deadline=time.monotonic()+(remaining if isinstance(remaining,(int,float)) and math.isfinite(remaining) else 8.5)
            self.require_charge_time()
            if probe.get('turn_serial',serial)!=serial:raise RuntimeError('El turno cambió antes de preparar el tiro')
            if s.get('shot')!=target_shot:
                point=ui['controls'].get(('btnShot1','btnShot2','btnShotSS')[target_shot])
                if not point:raise UnavailableShot('Tiro no disponible; esperando recarga')
                self.click(point,cancel);s=self.confirm_setting(reader,serial,'shot',target_shot,cancel)
            lab=None;independent=None;planned_angle=probe['angle'];movement=None
            if autonomous:
                state=self.sample();hero=next(p for p in state['players'] if str(p['id'])==str(state['heroId']))
                targets=[p for p in state['players'] if str(p['id'])!=str(hero['id']) and not p.get('dead') and (hero.get('team') is None or p.get('team')!=hero['team'])]
                if not targets:raise RuntimeError('Sin objetivo vivo')
                target=min(targets,key=lambda p:math.hypot(p['x']-hero['x'],p['y']-hero['y']))
                self.orient(reader,target['x']>=hero['x'],serial,cancel)
                fresh=reader.read();player=next(p for p in fresh['players'] if p['id']==hero_id)
                independent,movement=self.plan_with_reposition(reader,autonomous,probe,target['x'],serial,cancel);planned_angle=independent['raw_angle']
            elif settings_provider:
                from training_aim import choose_aim,actual_solution
                settings=settings_provider(self.sample(),cancel)
                player=next(p for p in reader.read()['players'] if p['id']==hero_id)
                desired=desired_look(player,settings.target_x>=settings.hero_x)
                if settings.look!=desired:
                    if reader.read().get('turnNumber')!=serial:raise TurnExpired('Cambió el turno antes de orientar')
                    held='right' if desired else 'left';self.guard(cancel);self.key(held,True);cancel.wait(.08);self.key(held,False);held=None
                    settings=settings_provider(self.sample(),cancel)
                    if settings.look!=desired:raise RuntimeError('El carro no confirmó su orientación al objetivo')
                hero=next(p for p in reader.read()['players'] if p['id']==hero_id)
                body_offset=hero.get('body',0)*(1 if hero.get('look')==0 else -1)
                limits=(hero['minAngle']+body_offset,hero['maxAngle']+body_offset) if all(isinstance(hero.get(k),(int,float)) for k in ('minAngle','maxAngle')) else None
                preferred=probe['angle'] if desired==int(settings.target_x>=settings.hero_x) else 180-probe['angle']
                try:planned_angle,lab=choose_aim(settings,preferred,limits)
                except NoAim:
                    from training_movement import walking_step
                    plan=walking_step(self.sample(),settings.target_x)
                    if plan:
                        movement=self.walk(reader,plan,cancel,expected_serial=serial);settings=settings_provider(self.sample(),cancel)
                        if abs(movement['to'][0]-movement['from'][0])<.5:
                            alternative=walking_step(self.sample(),settings.target_x,avoid=plan['direction'])
                            if alternative:movement=self.walk(reader,alternative,cancel,expected_serial=serial);settings=settings_provider(self.sample(),cancel)
                        player=next(p for p in reader.read()['players'] if p['id']==hero_id)
                        desired=desired_look(player,settings.target_x>=settings.hero_x)
                        if settings.look!=desired:
                            if reader.read().get('turnNumber')!=serial:raise TurnExpired('Cambió el turno antes de orientar')
                            held='right' if desired else 'left';self.guard(cancel);self.key(held,True);cancel.wait(.08);self.key(held,False);held=None
                            settings=settings_provider(self.sample(),cancel)
                            if settings.look!=desired:raise RuntimeError('El carro no confirmó su orientación tras caminar')
                        hero=next(p for p in reader.read()['players'] if p['id']==hero_id)
                        body_offset=hero.get('body',0)*(1 if hero.get('look')==0 else -1)
                        limits=(hero['minAngle']+body_offset,hero['maxAngle']+body_offset) if all(isinstance(hero.get(k),(int,float)) for k in ('minAngle','maxAngle')) else None
                    preferred=probe['angle'] if desired==int(settings.target_x>=settings.hero_x) else 180-probe['angle']
                    planned_angle,lab=choose_aim(settings,preferred,limits,allow_blocked=True)
                planned_angle+=hero.get('body',0)*(1 if hero.get('look')==1 else -1)
            self.angle_mobile=probe.get('mobile');self.angle_shot=target_shot;angle_change=self.adjust_angle(reader,planned_angle,cancel,expected_serial=serial)
            if autonomous:
                fresh=reader.read();player=next(p for p in fresh['players'] if p['id']==hero_id)
                independent=self.timed_plan(autonomous,self.sample(),player,probe,actual=True,previous=independent);probe={**probe,'power':independent['power']}
            elif settings_provider:
                settings=settings_provider(self.sample(),cancel);lab=actual_solution(settings,allow_blocked=lab.get('training_action') in ('abrir paso','aproximar'))
                probe={**probe,'power':lab['power']}
            s=reader.read();hero=next(p for p in s['players'] if p['id']==hero_id)
            release={'hero':hero_id,'x':hero['x'],'y':hero['y'],'shot':target_shot,'angle':hero.get('rawAngle'),'wind':s.get('wind'),'windAngle':s.get('windAngle'),'baseline':[]}
            release['timing']={'planning_ms':round(self.planning_ms,2),'preparation_ms':round((time.perf_counter()-preparing_at)*1000,2)}
            release['pose']={k:hero.get(k) for k in ('look','body','minAngle','maxAngle')}
            release['angle_change']=angle_change
            release['movement']=movement;release['turn_serial']=serial
            if independent:release['learner']=independent
            if lab:release['lab']={'power':lab['power'],'angle':settings.angle,'target':[settings.target_x,settings.target_y],'end':lab.get('end'),'action':lab.get('training_action','apuntar'),'approximate':lab.get('approximate',False)}
            from shot_attribution import identity,attributed_start
            before_state=self.sample()
            from battle_metrics import health
            release['health_before']={str(p['id']):health(p) for p in before_state.get('players',[])}
            from weapon_policy import enemy_for
            target_before=enemy_for(before_state,(release.get('learner') or release.get('lab') or {}).get('target'))
            if target_before:release['target_before']={k:target_before[k] for k in ('id','x','y')}
            release['baseline']=[identity(p) for p in before_state.get('shots',[])]
            self.guard(cancel)
            fresh=reader.read()
            if fresh.get('turn')!=hero_id or fresh.get('turnNumber')!=serial:raise TurnExpired('Cambió el turno antes de cargar')
            remaining=fresh.get('turnSeconds')
            if isinstance(remaining,(int,float)) and math.isfinite(remaining):self.turn_deadline=min(self.turn_deadline,time.monotonic()+remaining)
            self.require_charge_time()
            wants_dual=bool(independent and independent.get('use_dual'))
            selected=self.guard(cancel).get('selectedItems') or []
            if selected and not wants_dual:raise NoAim('Hay un ítem activo fuera del plan',reason='active-item')
            if wants_dual and self.select_dual(reader,serial,cancel):release['item']='dual';dual_selected_here=not selected
            release['method'],drag_geometry=self.prepare_charge(reader,serial,probe['power'],cancel)
            release['requested_power']=probe['power']
            self.verify_release(reader,release,cancel)
            self.prepared_plan=independent
            if before_fire:before_fire()
            def started():
                nonlocal charge_started
                charge_started=True
            if release['method']=='drag':
                result=charge_drag(self.client,reader,drag_geometry,probe['power'],cancel,self.guard,lambda state,**kw:self.validate_charge(state,release,**kw),started)
                release['power']=result['power'];release['drag']={k:v for k,v in result.items() if k not in ('power','method','charge_ms')}
                release['timing']['charge_ms']=result['charge_ms']
            else:
                held='space';started();start=time.monotonic();self.key('space',True);charging=False
                while time.monotonic()-start<4:
                    self.guard(cancel);s=reader.read();self.validate_charge(s,release)
                    if s.get('busy'):charging=True
                    elif charging:raise RecoverableInputError('La carga terminó antes de tiempo',method='space',code='space-ended-early')
                    power=s.get('power')
                    if charging and isinstance(power,(int,float)) and math.isfinite(power) and power>=probe['power']-1:
                        release['power']=power;break
                    time.sleep(.01)
                else:raise RecoverableInputError('La barra no confirmó la fuerza',method='space',code='space-power-timeout')
                self.key('space',False);held=None
                release['timing']['charge_ms']=round((time.monotonic()-start)*1000,2)
            release['timing']['input_method']=release['method']
            # Capture observed starts while their own-shooter attribution is fresh.
            self.client.terrain_clock=time.monotonic()
            until=time.monotonic()+1.2;observed=None
            while time.monotonic()<until:
                observed=self.sample()
                if any(identity(p) not in release['baseline'] and (attributed_start(observed,p,release) or {}).get('learnable') for p in observed.get('shots',[])):return release,observed
                time.sleep(.025)
            raise UnconfirmedShot('Tiro liberado, pero sin salida propia confirmada; no se usará para calibrar')
        finally:
            self.last_timing={'planning_ms':round(self.planning_ms,2),'attempt_ms':round((time.perf_counter()-preparing_at)*1000,2)}
            try:
                if held:self.key(held,False)
            finally:
                if (dual_selected_here or self.dual_selected_here) and not charge_started and not cancel.is_set():
                    try:
                        current=reader.read();ui=self.guard(cancel)
                        if current.get('turnNumber')==serial and current.get('turn')==current.get('hero') and ui.get('dualSelected'):self.click(ui['controls']['dual'],cancel)
                    except (RuntimeError,OSError,ConnectionError,TimeoutError):pass
                reader.close();self.reader=None
    def close(self):
        if getattr(self,'background',False):
            try:self.client.call('Emulation.setFocusEmulationEnabled',{'enabled':False})
            except Exception:pass
        try:self.client.call('Runtime.evaluate',{'expression':"(()=>{const s=window.__dragonlabTrainingStop;if(s?.handler)window.removeEventListener('keydown',s.handler,true);delete window.__dragonlabTrainingStop})()"})
        except Exception:pass
        try:self.client.close()
        finally:
            if getattr(self,'control_lease',None):self.control_lease.close()
