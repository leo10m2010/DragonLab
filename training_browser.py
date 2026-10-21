"""Normal browser input on the verified DragonBound tab; no game function calls."""
import json,time,math,re
from cdp import CDP
from auto_fire import PowerReader
from training_orientation import desired_look,raw_angle,up_increases_raw
UI_JS=r"""(()=>{
 const box=e=>{if(!e)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e);if(r.width<2||r.height<2||s.visibility==='hidden'||s.display==='none')return null;
 const x=r.left+r.width/2,y=r.top+r.height/2,hit=document.elementFromPoint(x,y);return hit&&(hit===e||e.contains(hit))?{x,y}:null};
 const ids=['buttonStart1v1','lobbyButtonMobile','roomMobileSelectCancel','btnShot1','btnShot2','btnShotSS','slice_drag_button'];
 const controls=Object.fromEntries(ids.map(id=>[id,box(document.getElementById(id))]));
 const options=[...document.querySelectorAll('#roomMobileSelect .mobileSelectBtn[data-mobile]')].map(e=>({id:Number(e.dataset.mobile),name:e.querySelector('.mobileName')?.textContent,point:box(e),selected:e.classList.contains('mobileSelectCurrent')})).filter(o=>o.point);
 const alert=document.getElementById('myDialog'),ok=box(document.getElementById('DragonDialogOK'));
 const away=ok&&/Creo que estás ausente/.test(alert?.textContent||'')?ok:null;
 const entries=location.hash===''?[...document.querySelectorAll('span,div')].filter(e=>!e.children.length&&e.textContent.trim()==='Avatar Off').map(box).filter(Boolean):[];
 return {url:location.href,serverEntry:entries.length===1?entries[0]:null,focused:document.hasFocus(),chat:['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)||!!document.activeElement?.isContentEditable,game:!!box(document.getElementById('gameScreen')),controls,options,away,blocked:!!ok&&!away,stop:!!window.__dragonlabTrainingStop?.stopped};
})()"""

class TurnExpired(RuntimeError):pass
class UnconfirmedShot(RuntimeError):pass
class UnavailableShot(RuntimeError):pass
class FocusPause(RuntimeError):pass

class TrainingBrowser:
    def __init__(self,endpoint,target=None):
        self.client=CDP(endpoint,target_id=target);self.client.sock.settimeout(.5);self.client.terrain_interval=4;self.reader=None
    def ui(self):
        state=self.client.call('Runtime.evaluate',{'expression':UI_JS,'returnByValue':True}).get('result',{}).get('value',{})
        if not re.fullmatch(r'https://dragonbound\.net/#server-8(?:/room-\d+)?/?',state.get('url','')) and not (state.get('url')=='https://dragonbound.net/' and state.get('serverEntry')):raise RuntimeError('El entrenamiento solo está habilitado en Avatar Off, servidor 8')
        return state
    def guard(self,cancel):
        if cancel.is_set():raise RuntimeError('Entrenamiento detenido')
        ui=self.ui()
        if ui.get('stop'):cancel.set();raise RuntimeError('Esc: entrenamiento detenido')
        if not ui.get('focused') or ui.get('chat'):raise FocusPause('En pausa: vuelve al juego y cierra el chat para continuar')
        return ui
    def click(self,point,cancel):
        self.guard(cancel)
        if not point or not all(isinstance(point.get(k),(int,float)) and math.isfinite(point[k]) for k in ('x','y')):raise RuntimeError('Control no disponible')
        args={'x':point['x'],'y':point['y'],'button':'left','clickCount':1}
        try:self.client.call('Input.dispatchMouseEvent',{'type':'mousePressed',**args})
        finally:self.client.call('Input.dispatchMouseEvent',{'type':'mouseReleased',**args})
    def key(self,key,down):
        codes={'space':(' ',32,'Space'),'up':('ArrowUp',38,'ArrowUp'),'down':('ArrowDown',40,'ArrowDown'),'left':('ArrowLeft',37,'ArrowLeft'),'right':('ArrowRight',39,'ArrowRight')}
        name,vk,code=codes[key]
        self.client.call('Input.dispatchKeyEvent',{'type':'keyDown' if down else 'keyUp','key':name,'code':code,'windowsVirtualKeyCode':vk,'nativeVirtualKeyCode':vk})
    def arm(self,focus=True):
        if focus:self.client.call('Page.bringToFront')
        self.client.call('Runtime.evaluate',{'expression':"(()=>{const old=window.__dragonlabTrainingStop;if(old?.handler)window.removeEventListener('keydown',old.handler,true);const s={stopped:false};s.handler=e=>{if(e.isTrusted&&e.key==='Escape')s.stopped=true};window.addEventListener('keydown',s.handler,true);window.__dragonlabTrainingStop=s})()"})
    def sample(self):return self.client.sample()
    def seconds_left(self):
        deadline=getattr(self,'turn_deadline',None)
        return max(0,deadline-time.monotonic()) if deadline is not None else 120
    def require_charge_time(self):
        if self.seconds_left()<4.5:raise TurnExpired('Queda poco tiempo para confirmar la carga; esperando otro turno')
    def adjust_angle(self,reader,target,cancel,expected_serial=None):
        state=reader.read();hero_id=state.get('hero');serial=state.get('turnNumber')
        if expected_serial is not None and serial!=expected_serial:raise TurnExpired('Cambió el turno antes de ajustar ángulo')
        hero=next((p for p in state.get('players',[]) if p.get('id')==hero_id),{})
        initial=hero.get('rawAngle')
        if not isinstance(initial,(int,float)) or not math.isfinite(initial):raise RuntimeError('Ángulo sin lectura; no se dispara')
        if not hasattr(self,'angle_limits'):self.angle_limits={}
        key=(getattr(self,'angle_mobile',None),hero.get('body'),hero.get('look'))
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
            raise RuntimeError('La flecha no cambió el ángulo; no se dispara')
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
            self.guard(cancel);self.key(direction,True);cancel.wait(.08)
        finally:self.key(direction,False)
        hero=next(p for p in reader.read()['players'] if p['id']==state['hero'])
        if hero['look']!=desired:raise RuntimeError('El carro no confirmó la orientación de salida')
        return hero
    def plan_with_reposition(self,reader,autonomous,probe,target_x,serial,cancel):
        """At most two supported steps; every attempt replans from the actual pose."""
        from training_aim import NoAim
        from training_movement import walking_step
        movements=[];avoid=None
        for attempt in range(3):
            self.guard(cancel)
            fresh=reader.read()
            if fresh.get('turnNumber')!=serial or fresh.get('turn')!=fresh.get('hero'):raise TurnExpired('Cambió el turno al buscar un ángulo')
            player=next(p for p in fresh['players'] if p['id']==fresh['hero'])
            state=self.sample()
            try:
                result=autonomous.plan(state,player,probe)
                return result,({'steps':movements,'from':movements[0]['from'],'to':movements[-1]['to']} if movements else None)
            except NoAim as error:
                if not error.reposition or attempt==2 or self.seconds_left()<8:raise
                step=walking_step(state,target_x,avoid=avoid)
                if not step:raise NoAim(str(error)+'; no hay suelo seguro para cambiar de posición') from error
                movement=self.walk(reader,step,cancel,expected_serial=serial);movements.append(movement)
                if abs(movement['to'][0]-movement['from'][0])<.5:avoid=step['direction']
                self.orient(reader,target_x>=movement['to'][0],serial,cancel)
        raise NoAim('No se encontró un ángulo tras dos pasos')
    def shoot(self,probe,cancel,settings_provider=None,before_fire=None,autonomous=None):
        self.reader=PowerReader(self.client.endpoint,self.client.target['id']);reader=self.reader
        held=None
        try:
            ui=self.guard(cancel);s=reader.read()
            if s.get('over') or s.get('turn')!=s.get('hero') or s.get('busy') or s.get('moving'):raise RuntimeError('Esperando tu turno sin movimiento')
            hero_id=s['hero'];serial=s.get('turnNumber');target_shot=probe['shot']
            remaining=s.get('turnSeconds');self.turn_deadline=time.monotonic()+(remaining if isinstance(remaining,(int,float)) and math.isfinite(remaining) else 8.5)
            self.require_charge_time()
            if probe.get('turn_serial',serial)!=serial:raise RuntimeError('El turno cambió antes de preparar el tiro')
            if s.get('shot')!=target_shot:
                self.click(ui['controls'].get(('btnShot1','btnShot2','btnShotSS')[target_shot]),cancel);time.sleep(.08);s=reader.read()
                if s.get('shot')!=target_shot:raise UnavailableShot('Tiro no disponible; esperando recarga')
            # Slice has a readable live bar and does not move the user's pointer.
            if s.get('mode')!='space':
                self.click(self.guard(cancel)['controls'].get('slice_drag_button'),cancel);time.sleep(.08);s=reader.read()
                if s.get('mode')!='space':raise RuntimeError('No se pudo activar Slice')
            lab=None;independent=None;planned_angle=probe['angle'];movement=None
            if autonomous:
                state=self.sample();hero=next(p for p in state['players'] if str(p['id'])==str(state['heroId']))
                targets=[p for p in state['players'] if str(p['id'])!=str(hero['id']) and not p.get('dead') and (hero.get('team') is None or p.get('team')!=hero['team'])]
                if not targets:raise RuntimeError('Sin objetivo vivo')
                target=min(targets,key=lambda p:math.hypot(p['x']-hero['x'],p['y']-hero['y']))
                self.orient(reader,target['x']>=hero['x'],serial,cancel)
                fresh=reader.read();player=next(p for p in fresh['players'] if p['id']==hero_id)
                independent,movement=self.plan_with_reposition(reader,autonomous,probe,target['x'],serial,cancel);planned_angle=independent['raw_angle']
                if independent.get('needs_move') and self.seconds_left()>12:
                    from training_movement import walking_step
                    plan=walking_step(self.sample(),target['x'])
                    if plan:
                        movement=self.walk(reader,plan,cancel,expected_serial=serial)
                        self.orient(reader,target['x']>=next(p for p in reader.read()['players'] if p['id']==hero_id)['x'],serial,cancel)
                        player=next(p for p in reader.read()['players'] if p['id']==hero_id)
                        independent=autonomous.plan(self.sample(),player,probe);planned_angle=independent['raw_angle']
            elif settings_provider:
                from training_aim import choose_aim,actual_solution,NoAim
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
            self.angle_mobile=probe.get('mobile');angle_change=self.adjust_angle(reader,planned_angle,cancel,expected_serial=serial)
            if autonomous:
                fresh=reader.read();player=next(p for p in fresh['players'] if p['id']==hero_id)
                independent=autonomous.plan(self.sample(),player,probe,actual=True,previous=independent);probe={**probe,'power':independent['power']}
            elif settings_provider:
                settings=settings_provider(self.sample(),cancel);lab=actual_solution(settings,allow_blocked=lab.get('training_action') in ('abrir paso','aproximar'))
                probe={**probe,'power':lab['power']}
            s=reader.read();hero=next(p for p in s['players'] if p['id']==hero_id)
            release={'hero':hero_id,'x':hero['x'],'y':hero['y'],'shot':target_shot,'angle':hero.get('rawAngle'),'wind':s.get('wind'),'windAngle':s.get('windAngle'),'baseline':[]}
            release['pose']={k:hero.get(k) for k in ('look','body','minAngle','maxAngle')}
            release['angle_change']=angle_change
            release['movement']=movement;release['turn_serial']=serial
            if independent:release['learner']=independent
            if lab:release['lab']={'power':lab['power'],'angle':settings.angle,'target':[settings.target_x,settings.target_y],'end':lab.get('end'),'action':lab.get('training_action','apuntar'),'approximate':lab.get('approximate',False)}
            from shot_attribution import identity,attributed_start
            before_state=self.sample()
            from battle_metrics import health
            release['health_before']={str(p['id']):health(p) for p in before_state.get('players',[])}
            release['baseline']=[identity(p) for p in before_state.get('shots',[])]
            self.guard(cancel)
            fresh=reader.read()
            if fresh.get('turn')!=hero_id or fresh.get('turnNumber')!=serial:raise TurnExpired('Cambió el turno antes de cargar')
            remaining=fresh.get('turnSeconds')
            if isinstance(remaining,(int,float)) and math.isfinite(remaining):self.turn_deadline=min(self.turn_deadline,time.monotonic()+remaining)
            self.require_charge_time()
            if before_fire:before_fire()
            held='space';self.key('space',True);start=time.monotonic();charging=False
            while time.monotonic()-start<4:
                self.guard(cancel);s=reader.read()
                if s.get('turn')!=hero_id or s.get('turnNumber')!=serial or s.get('over'):raise TurnExpired('Terminó el turno durante la carga')
                if s.get('shot')!=target_shot:raise RuntimeError('Cambió la modalidad durante la carga')
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
            self.client.terrain_clock=time.monotonic()
            until=time.monotonic()+1.2;observed=None
            while time.monotonic()<until:
                observed=self.sample()
                if any(identity(p) not in release['baseline'] and (attributed_start(observed,p,release) or {}).get('learnable') for p in observed.get('shots',[])):return release,observed
                time.sleep(.025)
            raise UnconfirmedShot('Tiro liberado, pero sin salida propia confirmada; no se usará para calibrar')
        finally:
            try:
                if held:self.key(held,False)
            finally:reader.close();self.reader=None
    def close(self):
        try:self.client.call('Runtime.evaluate',{'expression':"(()=>{const s=window.__dragonlabTrainingStop;if(s?.handler)window.removeEventListener('keydown',s.handler,true);delete window.__dragonlabTrainingStop})()"})
        except Exception:pass
        self.client.close()
