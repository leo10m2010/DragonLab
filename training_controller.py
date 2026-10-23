"""Explicit turn state machine; bounded history, retries, and browser recovery."""
import math,time
from calibration_book import mobile_name
from training_policy import next_probe,next_mobile
from training_turns import TurnLedger,turn_key
from training_browser import TrainingBrowser,FocusPause,UnavailableShot,TurnExpired,UnconfirmedShot,TurnNotReady
from training_aim import NoAim
from training_memory import ActionMemory

def lobby_visible(ui):
    controls=ui.get('controls') or {}
    return bool(ui.get('options') or controls.get('buttonStart1v1') or controls.get('lobbyButtonMobile'))

class TrainingController:
    def __init__(self,session):
        self.s=session;self.ledger=TurnLedger();self.current=None;self.geometry=None;self.blocked=set();self.selected=False;self.queue_at=0;self.failures=0;self.in_game=False;self.power=None;self.loading_since=None;self.recovery_state={}
        self.learner=None;self.cancel=session.cancel;self.rolling=None
        if session.autonomous:
            from autonomous_learning import AutonomousLearner
            self.learner=AutonomousLearner(session.book_path.parent/'aprendizaje-autonomo.json',session.book_path);session.learner=self.learner
        self.trial=None;self.battle=None
        if session.objective in ('evaluation','adaptive'):
            if not self.learner:raise ValueError('La evaluación requiere aprendizaje autónomo')
            from training_evaluation import EvaluationTrial
            from battle_metrics import BattleMetrics
            if session.objective=='adaptive':
                from adaptive_training import AdaptiveTrial
                if session.continuous:
                    from continuous_training import RollingEvaluation
                    self.rolling=RollingEvaluation(session.book_path.parent,self.learner,session.max_shots,session.allow_dual);self.trial=self.rolling.current
                    session.report=self.rolling.report()
                else:self.trial=AdaptiveTrial(session.book_path.parent/'evaluacion-adaptativa.json',self.learner,session.max_shots,allow_dual=session.allow_dual)
            else:self.trial=EvaluationTrial(session.book_path.parent/'evaluacion-punteria.json',self.learner,session.max_shots)
            session.trial=self.trial
            self.battle=BattleMetrics(session.book_path.parent/'partidas-observadas.json',self.trial.health_result);session.battle=self.battle
        self.memory=None if session.autonomous else ActionMemory(session.book_path.parent/'estrategia-entrenamiento.json')
    def within_limits(self,started):
        s=self.s
        return not self.cancel.is_set() and time.monotonic()-started<s.max_seconds and (s.continuous or s.shots<s.max_shots)
    def run(self):
        from training_power import SleepLease
        from continuous_training import DeadlineCancel,transient_browser_error
        s=self.s;browser=None;retries=0;first=True;self.power=SleepLease()
        if getattr(s,'started_at',None) is None:s.started_at=time.monotonic()
        if getattr(s,'started_wall',None) is None:s.started_wall=time.time()
        started=s.started_at;self.cancel=DeadlineCancel(s.cancel,started+s.max_seconds)
        try:
            while self.within_limits(started):
                try:
                    if browser is None:
                        try:browser=TrainingBrowser(s.endpoint,s.target)
                        except RuntimeError as error:
                            if s.continuous and str(error)=='La página seleccionada no está abierta en el navegador de depuración':raise ConnectionError(str(error)) from error
                            raise
                        browser.recovery_state=self.recovery_state;browser.background=s.background;browser.arm(focus=first and not s.background);first=False
                        if retries:s.last_error=''
                        s.publish('Conexión recuperada' if retries else 'Entrenando en Avatar Off')
                    if self.cycle(browser) is False:break
                    retries=0
                except FocusPause as error:
                    if not s.continuous and not s.background:raise
                    self.power.hold(False)
                    s.publish(str(error));self.cancel.wait(.5)
                except (OSError,ConnectionError,TimeoutError,RuntimeError) as error:
                    if isinstance(error,RuntimeError) and not (s.continuous and transient_browser_error(error)):raise
                    if not s.continuous and not s.background:raise
                    self.power.hold(False)
                    s.last_error=str(error)
                    if browser:
                        try:browser.close()
                        except Exception:pass
                    browser=None;retries+=1
                    s.publish('Reconectando el navegador; no se repite un tiro de este turno')
                    self.cancel.wait(min(15,2**min(retries,4)))
        except Exception as error:s.last_error=str(error)
        finally:
            try:
                if self.battle:
                    if browser and not self.cancel.is_set():
                        until=time.monotonic()+15
                        while self.battle.pending and time.monotonic()<until and not self.cancel.is_set():
                            try:self.battle.observe(browser.sample())
                            except (OSError,RuntimeError,ConnectionError,TimeoutError):break
                            self.cancel.wait(.2)
                    self.battle.end()
                if self.trial:self.trial.finish()
                self.sync_report()
            except Exception as error:s.last_error=s.last_error or 'No se pudo guardar el cierre de la sesión: '+str(error)
            finally:
                self.power.close()
                if browser:
                    try:browser.close()
                    except Exception:pass
                s.running=False
            expired=time.monotonic()-started>=s.max_seconds
            if expired and s.last_error=='Entrenamiento detenido':s.last_error=''
            s.publish('Entrenamiento detenido: '+s.last_error if s.last_error else 'Tiempo de sesión completado; progreso guardado' if expired else ('Evaluación finalizada: '+self.trial.summary()['status'] if self.trial else 'Sesión finalizada; progreso guardado'))
    def sync_report(self):
        if self.rolling:
            self.s.report=self.rolling.report();self.rolling.save()
    def next_block(self,browser,ui):
        """No next charge until the old block's health callbacks have settled."""
        if self.in_game and not ui.get('game') and not lobby_visible(ui):
            self.s.publish('Esperando que reaparezca el juego; se conserva el turno reservado');self.cancel.wait(.2);return False
        if self.battle:
            if ui.get('game'):
                state=browser.sample()
                if self.learner:self.learner.track(state)
                self.battle.observe(state)
                for item in list(self.battle.pending):
                    if time.monotonic()>=item['expires']:self.battle.complete(item)
            else:self.battle.end()
            if self.battle.pending:
                self.s.publish('Completando las observaciones del bloque; el aprendizaje continuará');self.cancel.wait(.1);return False
        self.trial=self.rolling.rollover();self.s.trial=self.trial
        if self.battle:self.battle.callback=self.trial.health_result
        self.sync_report();self.s.publish(f'Aprendizaje continuo · bloque {self.rolling.block}');return True
    def cycle(self,browser):
        s=self.s;ui=browser.guard(self.cancel)
        if self.trial and self.trial.done():
            if not self.rolling:return False
            if not self.next_block(browser,ui):return
        if self.power:self.power.hold(True)
        if ui.get('loading'):
            if self.loading_since is None:self.loading_since=time.monotonic()
            if time.monotonic()-self.loading_since>60 and not s.continuous:raise RuntimeError('La carga del perfil lleva más de un minuto; revisa la conexión del juego')
            s.publish('Esperando que el juego termine de cargar el perfil');self.cancel.wait(.5);return
        self.loading_since=None
        if ui.get('blocked'):
            if not s.continuous:raise RuntimeError('Hay un aviso del juego. Ciérralo antes de volver a empezar')
            if self.power:self.power.hold(False)
            s.publish('En pausa: cierra el aviso del juego para continuar');self.cancel.wait(1);return
        if ui.get('away'):
            browser.click(ui['away'],self.cancel);self.cancel.wait(.3);return
        if ui.get('serverEntry'):
            browser.click(ui['serverEntry'],self.cancel);s.publish('Entrando a Avatar Off');self.cancel.wait(.7);return
        if ui.get('url')=='https://dragonbound.net/':
            s.publish('Esperando que cargue DragonBound y su sesión');self.cancel.wait(.5);return
        if not ui.get('game'):
            if self.in_game and not lobby_visible(ui):
                s.publish('Esperando que reaparezca el juego; se conserva el turno reservado');self.cancel.wait(.2);return
            if self.battle:self.battle.end()
            if self.learner:self.learner.pending.clear()
            if self.in_game:self.failures=0
            self.in_game=False
            self.current=None;self.blocked.clear();self.recovery_state.clear();browser.movement_turn=None;browser.client.game=None;browser.client.renderer=None
            if ui['options']:
                option=self.trial.choose_mobile(ui['options'],s.mobile_attempts) if s.objective=='adaptive' else next((o for o in ui['options'] if mobile_name(o.get('name'))=='ARMOR'),None) if self.trial else self.learner.choose_mobile(ui['options'],s.mobile_attempts) if self.learner else next_mobile(ui['options'],s.mobile_attempts)
                if not option:raise RuntimeError('No hay carros identificables en el selector')
                browser.click(option['point'],self.cancel);self.selected=True;name=mobile_name(option['name']);s.mobile_attempts[name]=s.mobile_attempts.get(name,0)+1
                s.publish('Carro elegido: '+name);self.cancel.wait(.4);return
            if ui['controls'].get('buttonStart1v1'):
                if self.queue_at and time.monotonic()-self.queue_at<20:self.cancel.wait(.5);return
                if not s.continuous and s.matches>=s.max_matches:return False
                if not self.selected and ui['controls'].get('lobbyButtonMobile'):
                    browser.click(ui['controls']['lobbyButtonMobile'],self.cancel);self.cancel.wait(.3);return
                browser.click(ui['controls']['buttonStart1v1'],self.cancel);s.matches+=1;self.queue_at=time.monotonic();self.selected=False
                s.publish('Buscando partida 1v1');self.cancel.wait(1);return
            s.publish('Esperando el lobby o la siguiente partida');self.cancel.wait(.5);return
        if not self.in_game and self.learner:self.learner.episode=str(time.time_ns())
        self.in_game=True;self.queue_at=0;state=browser.sample();key=turn_key(state,ui['url']);browser.recovery_key=key
        if self.learner:self.learner.track(state)
        if self.battle:self.battle.observe(state)
        if self.rolling:s.report=self.rolling.report()
        if key!=self.current:self.current=key;self.blocked.clear()
        if not self.ledger.available(key):
            s.publish('Esperando el próximo turno' if key in self.ledger.used else 'Esperando confirmar tu turno')
            self.cancel.wait(.10);return
        hero=next(p for p in state['players'] if str(p.get('id'))==str(state['heroId']))
        geometry=(round(hero['x']/4),round(hero['y']/4),state.get('wind'),state.get('windAngle'))
        if geometry!=self.geometry:self.blocked.clear();self.geometry=geometry
        mobile=mobile_name(hero.get('mobile'))
        if not mobile:raise RuntimeError('Carro no identificado; sesión detenida')
        if s.objective=='evaluation' and mobile!='ARMOR':s.publish('Esperando el lobby: la prueba solo usa Armor tiro 1');self.cancel.wait(.5);return
        available=[i for i,k in enumerate(('btnShot1','btnShot2','btnShotSS')) if ui['controls'].get(k) and i not in self.blocked]
        if not available:
            if self.blocked and any(ui['controls'].get(k) for k in ('btnShot1','btnShot2','btnShotSS')):
                s.publish('Esperando una posición o modalidad con tiro válido')
                if s.objective=='adaptive':self.trial.turn_skipped(key)
            self.cancel.wait(.2);return
        if s.objective=='evaluation':
            if 0 not in available:
                self.ledger.consume(key);self.trial.skip('Armor tiro 1 no está disponible');s.publish('Tiro 1 no disponible; prueba sin disparo');return
            available=[0]
        if s.objective=='adaptive':
            try:probe=self.trial.probe(mobile,state,available)
            except NoAim as error:
                error.turn_serial=key[-1];self.blocked.update(available);self.trial.skip(error);self.trial.turn_skipped(key);s.publish(str(error));self.cancel.wait(.2);return
        else:probe=self.trial.probe() if self.trial else self.learner.choose_probe(mobile,state.get('wind',0),s.shots,available) if self.learner else next_probe(s.records(),mobile,state.get('wind',0),s.shots,available)
        probe['turn_serial']=key[-1]
        if self.memory and s.shots%3==2:probe=self.memory.recommend(probe,state,available)
        stage='decidiendo con mediciones propias' if self.learner else 'calculando viento y recorrido'
        s.publish(f"Turno {key[-1]} · {mobile} · tiro {('1','2','SS')[probe['shot']]} · {stage}")
        try:
            options={'settings_provider':None if self.learner else s.settings_provider,'before_fire':lambda:self.reserve_turn(browser,key)}
            if self.learner:options['autonomous']=self.trial or self.learner
            release,observation=browser.shoot(probe,self.cancel,**options)
            self.observe(probe,release,observation);self.failures=0;s.last_error=''
        except UnavailableShot as error:
            self.blocked.add(probe['shot']);s.publish(str(error))
        except NoAim as error:
            error.turn_serial=key[-1]
            detail=str(error)
            if getattr(error,'excavation_reason',None):detail+='; abrir paso: '+error.excavation_reason
            if s.objective=='adaptive':
                self.blocked.add(probe['shot']);self.trial.skip(error)
                if isinstance(getattr(browser,'movement_events',None),list) and browser.movement_events:
                    terminal=browser.sample();player=next((p for p in terminal.get('players',[]) if str(p.get('id'))==str(terminal.get('heroId'))),None)
                    if player:self.geometry=(round(player['x']/4),round(player['y']/4),terminal.get('wind'),terminal.get('windAngle'))
                s.publish(detail+'; buscando otra modalidad en este turno')
            elif self.trial:
                if self.ledger.available(key):self.ledger.consume(key)
                self.trial.skip(error);s.publish(detail)
            else:self.blocked.add(probe['shot']);s.publish(detail+'; probando otra modalidad')
        except TurnNotReady as error:
            s.publish(str(error));self.cancel.wait(.15)
        except (TurnExpired,UnconfirmedShot) as error:
            if self.ledger.available(key):self.ledger.consume(key)
            self.failures=0;s.last_error='';self.record_error(key,str(error),'turn-ended' if isinstance(error,TurnExpired) else 'unconfirmed')
            s.publish(str(error)+'; continuará en el próximo turno')
        except (FocusPause,OSError,ConnectionError,TimeoutError):raise
        except RuntimeError as error:
            if self.cancel.is_set():raise
            from continuous_training import ObservationArchiveError,transient_browser_error
            if isinstance(error,ObservationArchiveError) or s.continuous and transient_browser_error(error):raise
            # A charge can have released partially. Never retry a control error
            # in the same native turn, even after a reconnect or missed frame.
            if self.ledger.available(key):self.ledger.consume(key)
            latest=browser.sample()
            if turn_key(latest,ui['url'])!=key:
                self.failures=0;s.last_error='';self.record_error(key,str(error),'turn-ended');s.publish('El turno terminó; continuará en el siguiente')
            else:
                s.last_error=str(error);self.failures+=1;self.record_error(key,str(error),'control');s.publish(str(error))
                if self.failures>=3:raise RuntimeError('Tres fallos de control; último: '+str(error))
        finally:
            if isinstance(getattr(browser,'last_timing',None),dict):s.last_timing=dict(browser.last_timing)
            if isinstance(getattr(browser,'movement_events',None),list) and browser.movement_events:
                s.movements.extend(browser.movement_events);s.movements=s.movements[-64:];browser.movement_events.clear()
        self.cancel.wait(.05)
    def reserve_turn(self,browser,key):
        self.ledger.consume(key)
        plan=getattr(browser,'prepared_plan',None)
        if self.trial and isinstance(plan,dict):
            reserve=getattr(self.trial,'reserve_action',None)
            if callable(reserve):reserve(plan,key)
    def record_error(self,key,reason,kind):
        self.s.errors.append({'turn':key[-1],'reason':reason,'kind':kind,'at':time.time()})
        self.s.errors=self.s.errors[-64:]
    def observe(self,probe,release,observation):
        s=self.s;s.shots+=1
        if self.rolling:self.rolling.record(probe,release,observation)
        if s.objective=='adaptive' and self.trial:self.trial.turn_recovered(self.current)
        if self.learner and not release.get('item'):self.learner.observe(probe,release,observation)
        if self.trial:
            token=self.trial.record(release,observation);self.battle.note(release,release.get('learner') or {},observation,token)
        self.sync_report()
        s.emit({'status':'training-observation','release':release,'observation':observation})
        weather=[{k:w[k] for k in ('typeId','resolvedTypeId','x','size') if isinstance(w.get(k),(int,float))} for w in observation.get('weather',[])[:32] if isinstance(w,dict)]
        lab=release.get('learner') or release.get('lab') or {};feedback={}
        try:
            if lab.get('target'):
                from native_paths import position
                from shot_attribution import attributed_start
                for bullet in observation.get('shots',[]):
                    if not (attributed_start(observation,bullet,release) or {}).get('learnable') or not isinstance(bullet.get('duration'),(int,float)):continue
                    end=position(bullet,bullet['duration']/1000)
                    if end and all(isinstance(v,(int,float)) and math.isfinite(v) for v in end):feedback={'observed_end':list(end),'target_distance':round(math.dist(end,lab['target']),2)};break
        except (ValueError,TypeError,KeyError,IndexError):pass
        try:
            if self.memory:self.memory.learn(probe,release,feedback)
        except (OSError,ValueError,TypeError):pass
        s.history.append({**probe,'timing':release.get('timing'),'item':release.get('item'),'power':lab.get('power',probe['power']),'probe_power':probe['power'],'actual_power':release.get('power'),'actual_angle':release.get('angle'),'turn_serial':release.get('turn_serial'),'movement':release.get('movement'),'angle_change':release.get('angle_change'),'lab':release.get('lab'),'learner':release.get('learner'),'feedback':feedback,'wind':release.get('wind'),'wind_angle':release.get('windAngle'),'weather':weather});s.history=s.history[-120:]
        modality=('Bala 1','Bala 2','SS')[probe['shot']]+(' + DD' if release.get('item')=='dual' else '')
        source=modality+' · '+lab.get('stage','Lab')
        s.publish(f"Tiro {s.shots} · turno {probe['turn_serial']} · {source} · fuerza {lab.get('power',probe['power'])} → real {release.get('power')}")
