"""Explicit turn state machine; bounded history, retries, and browser recovery."""
import math,time
from calibration_book import mobile_name
from training_policy import next_probe,next_mobile
from training_turns import TurnLedger,turn_key
from training_browser import TrainingBrowser,FocusPause,UnavailableShot,TurnExpired,UnconfirmedShot,TurnNotReady
from training_aim import NoAim
from training_memory import ActionMemory
from training_input import RecoverableInputError

def lobby_visible(ui):
    controls=ui.get('controls') or {}
    return bool(ui.get('options') or controls.get('buttonStart1v1') or controls.get('lobbyButtonMobile'))

class TrainingController:
    def __init__(self,session):
        self.s=session;self.ledger=TurnLedger();self.current=None;self.geometry=None;self.blocked=set();self.selected=False;self.queue_at=0;self.failures=0;self.in_game=False;self.power=None;self.loading_since=None;self.recovery_state={};self.retirement_until=None
        self.learner=None;self.cancel=session.cancel;self.rolling=None
        self.input_recovery={};session.input_recovery=self.input_recovery
        self.watchdog_token=None;self.watchdog_at=None
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
                        s.heartbeat('connecting')
                        try:browser=TrainingBrowser(s.endpoint,s.target)
                        except RuntimeError as error:
                            if s.continuous and str(error)=='La página seleccionada no está abierta en el navegador de depuración':raise ConnectionError(str(error)) from error
                            raise
                        browser.recovery_state=self.recovery_state;browser.input_recovery=self.input_recovery;browser.background=s.background;browser.arm(focus=first and not s.background);first=False
                        if retries:s.last_error=''
                        s.publish('Conexión recuperada' if retries else 'Entrenando en Avatar Off')
                    if self.cycle(browser) is False:break
                    retries=0
                except FocusPause as error:
                    if not s.continuous and not s.background:raise
                    self.power.hold(False)
                    self.suspend_watchdog()
                    s.heartbeat('paused')
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
                    s.reconnects+=1;s.heartbeat('reconnecting')
                    s.publish('Reconectando el navegador; no se repite un tiro de este turno')
                    self.cancel.wait(min(15,2**min(retries,4)))
        except Exception as error:s.last_error=str(error)
        finally:
            s.heartbeat('finishing')
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
            s.stop_reason='deadline' if expired else s.stop_reason or ('error' if s.last_error else 'cancelled' if self.cancel.is_set() else 'limits')
            s.heartbeat('error' if s.last_error else 'finished')
            s.publish('Entrenamiento detenido: '+s.last_error if s.last_error else 'Tiempo de sesión completado; progreso guardado' if expired else 'Sesión detenida por solicitud; progreso guardado' if self.cancel.is_set() else ('Evaluación finalizada: '+self.trial.summary()['status'] if self.trial else 'Sesión finalizada; progreso guardado'))
    def sync_report(self):
        if self.rolling:
            self.s.report=self.rolling.report();self.rolling.save()
    def suspend_watchdog(self):self.watchdog_token=None;self.watchdog_at=None
    def watch_native_progress(self,token):
        """Reconnect the pinned CDP only; never reload/leave a waiting game.

        A stable native view for two minutes may be a long queue rather than a
        fault. A bounded connection refresh is safe in either case and retains
        every turn reservation, model and in-flight evaluation in this object.
        """
        now=time.monotonic()
        if token!=self.watchdog_token or self.watchdog_at is None:
            self.watchdog_token=token;self.watchdog_at=now;return
        if now-self.watchdog_at<120:return
        self.watchdog_at=now;self.s.watchdog_reconnects+=1;self.s.heartbeat('reconnecting')
        raise ConnectionError('El estado nativo no cambió durante dos minutos; se revisará la conexión sin salir de la partida')
    def next_block(self,browser,ui):
        """No next charge until the old block's health callbacks have settled."""
        if self.in_game and not ui.get('game') and not lobby_visible(ui):
            self.watch_native_progress(('block-wait-game',ui.get('url')))
            self.s.heartbeat('waiting-game');self.s.publish('Esperando que reaparezca el juego; se conserva el turno reservado');self.cancel.wait(.2);return False
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
        s=self.s;s.heartbeat();ui=browser.guard(self.cancel)
        self.drain_actions(browser)
        if self.power:self.power.hold(True)
        if ui.get('loading'):
            self.suspend_watchdog()
            s.heartbeat('loading')
            if self.loading_since is None:self.loading_since=time.monotonic()
            if time.monotonic()-self.loading_since>60 and not s.continuous:raise RuntimeError('La carga del perfil lleva más de un minuto; revisa la conexión del juego')
            s.publish('Esperando que el juego termine de cargar el perfil');self.cancel.wait(.5);return
        self.loading_since=None
        retired=ui.get('retirement')
        if isinstance(retired,dict):
            self.suspend_watchdog()
            s.heartbeat('retirement')
            now=time.monotonic();seconds=retired.get('seconds',60)
            if self.retirement_until is None:
                self.retirement_until=now+max(0,min(3600,seconds))+.3
                s.retirements=getattr(s,'retirements',0)+1
                s.errors.append({'turn':None,'kind':'retirement','reason':'El juego mostró una penalización de retirada; se respeta la espera','at':time.time()});s.errors=s.errors[-64:]
            browser.retirement_until=self.retirement_until
            if now<self.retirement_until:
                s.publish(f'El juego registró una retirada · esperando {math.ceil(self.retirement_until-now)} s antes de continuar');self.cancel.wait(min(1,self.retirement_until-now));return
            browser.click(retired.get('point'),self.cancel);self.retirement_until=None;s.heartbeat('lobby',progress='retirement-cleared');self.cancel.wait(.3);return
        self.retirement_until=None
        if (ui.get('notice') or {}).get('kind')=='gift-received':
            browser.click(ui['notice']['point'],self.cancel);self.cancel.wait(.3);return
        if ui.get('blocked'):
            self.suspend_watchdog()
            s.heartbeat('blocked')
            if not s.continuous:raise RuntimeError('Hay un aviso del juego. Ciérralo antes de volver a empezar')
            if self.power:self.power.hold(False)
            s.publish('En pausa: cierra el aviso del juego para continuar');self.cancel.wait(1);return
        if ui.get('away'):
            self.suspend_watchdog()
            browser.click(ui['away'],self.cancel);self.cancel.wait(.3);return
        if ui.get('serverEntry'):
            self.suspend_watchdog()
            s.heartbeat('entering-server',progress='server-selected')
            browser.click(ui['serverEntry'],self.cancel);s.publish('Entrando a Avatar Off');self.cancel.wait(.7);return
        if ui.get('url')=='https://dragonbound.net/':
            self.suspend_watchdog()
            s.heartbeat('login')
            s.publish('Esperando que cargue DragonBound y su sesión');self.cancel.wait(.5);return
        # Modal/retirement/loading controls must still work when a block has
        # finished. Waiting for vanished game DOM before them can deadlock the
        # rollover and leave a known notice covering the lobby indefinitely.
        if self.trial and self.trial.done():
            if not self.rolling:return False
            if not self.next_block(browser,ui):return
        if not ui.get('game'):
            s.heartbeat('lobby')
            self.watch_native_progress(('lobby',ui.get('url'),bool(lobby_visible(ui)),tuple((o.get('id'),bool(o.get('selected'))) for o in ui.get('options',[])),tuple(bool(ui.get('controls',{}).get(k)) for k in ('buttonStart1v1','lobbyButtonMobile'))))
            if self.in_game and not lobby_visible(ui):
                s.heartbeat('waiting-game');s.publish('Esperando que reaparezca el juego; se conserva el turno reservado');self.cancel.wait(.2);return
            if self.battle:self.battle.end()
            if self.learner:self.learner.pending.clear()
            if self.in_game:self.failures=0
            self.in_game=False
            self.current=None;self.blocked.clear();self.recovery_state.clear();browser.movement_turn=None;browser.client.game=None;browser.client.renderer=None
            if ui['options']:
                option=self.trial.choose_mobile(ui['options'],s.mobile_attempts) if s.objective=='adaptive' else next((o for o in ui['options'] if mobile_name(o.get('name'))=='ARMOR'),None) if self.trial else self.learner.choose_mobile(ui['options'],s.mobile_attempts) if self.learner else next_mobile(ui['options'],s.mobile_attempts)
                if not option:raise RuntimeError('No hay carros identificables en el selector')
                browser.click(option['point'],self.cancel);self.selected=True;name=mobile_name(option['name']);s.mobile_attempts[name]=s.mobile_attempts.get(name,0)+1
                s.heartbeat('lobby',progress='mobile-selected')
                s.publish('Carro elegido: '+name);self.cancel.wait(.4);return
            if ui['controls'].get('buttonStart1v1'):
                if self.queue_at and time.monotonic()-self.queue_at<20:s.heartbeat('queue');self.cancel.wait(.5);return
                if not s.continuous and s.matches>=s.max_matches:return False
                if not self.selected and ui['controls'].get('lobbyButtonMobile'):
                    browser.click(ui['controls']['lobbyButtonMobile'],self.cancel);self.cancel.wait(.3);return
                browser.click(ui['controls']['buttonStart1v1'],self.cancel);s.matches+=1;self.queue_at=time.monotonic();self.selected=False
                s.heartbeat('queue',progress='queue-requested')
                s.publish('Buscando partida 1v1');self.cancel.wait(1);return
            s.publish('Esperando el lobby o la siguiente partida');self.cancel.wait(.5);return
        if not self.in_game and self.learner:self.learner.episode=str(time.time_ns())
        self.in_game=True;self.queue_at=0;state=browser.sample();key=turn_key(state,ui['url']);browser.recovery_key=key
        self.watch_native_progress(('game',ui['url'],state.get('turnSerial'),state.get('activePlayer'),state.get('heroId'),state.get('over'),state.get('wind'),state.get('windAngle'),tuple((p.get('id'),p.get('x'),p.get('y'),p.get('dead')) for p in state.get('players',[])[:32])))
        if self.learner:self.learner.track(state)
        if self.battle:self.battle.observe(state)
        if self.rolling:s.report=self.rolling.report()
        if key!=self.current:
            self.current=key;self.blocked.clear()
            if key is not None:s.heartbeat('playing',progress='native-turn')
        if not self.ledger.available(key):
            s.heartbeat('waiting-turn')
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
                try:
                    if browser.pass_turn(key,self.cancel,lambda:self.ledger.consume(key)) is True:
                        s.passed_turns=getattr(s,'passed_turns',0)+1;s.heartbeat('waiting-turn',progress='turn-passed');s.publish('Sin recorrido válido en las balas disponibles; turno pasado de forma explícita')
                except (TurnExpired,TurnNotReady):pass
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
        self.last_probe=probe
        s.heartbeat('planning')
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
        except RecoverableInputError as error:
            self.recover_input(key,error)
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
            if isinstance(getattr(browser,'click_events',None),list) and browser.click_events:
                s.ui_actions=getattr(s,'ui_actions',[])+browser.click_events;s.ui_actions=s.ui_actions[-128:];browser.click_events.clear()
        self.cancel.wait(.05)
    def recover_input(self,key,error):
        """Release already happened in the input owner; retain this controller.

        In particular, do not create a fresh ledger after an ambiguous press.
        The fallback applies only to a later, not-yet-reserved native turn.
        """
        s=self.s
        if self.ledger.available(key):self.ledger.consume(key)
        method=error.method;now=time.monotonic()
        if method=='drag':self.input_recovery['drag_disabled_until']=max(self.input_recovery.get('drag_disabled_until',0),now+180)
        s.input_recoveries+=1;s.input_recovery_counts[method]=s.input_recovery_counts.get(method,0)+1
        s.input_recovery_streak+=1;s.last_recovery_code=error.code;s.last_error='';self.failures=0
        self.record_error(key,str(error),'input-recovery');s.heartbeat('input-recovery')
        s.publish('Entrada liberada; este turno no se repite. Se usará Espacio en los próximos turnos' if method=='drag' else 'Entrada liberada; se recuperarán los controles en el próximo turno')
        self.cancel.wait(min(2,.25*2**min(s.input_recovery_streak-1,3)))
    def reserve_turn(self,browser,key):
        self.ledger.consume(key)
        plan=getattr(browser,'prepared_plan',None)
        if self.trial and isinstance(plan,dict):
            reserve=getattr(self.trial,'reserve_action',None)
            if callable(reserve):reserve(plan,key)
    def record_error(self,key,reason,kind):
        probe=getattr(self,'last_probe',{})
        self.s.errors.append({'turn':key[-1],'reason':reason,'kind':kind,'shot':probe.get('shot'),'mobile':probe.get('mobile'),'at':time.time()})
        self.s.errors=self.s.errors[-64:]
    def drain_actions(self,browser):
        actions=getattr(browser,'click_events',None)
        if isinstance(actions,list) and actions:
            self.s.ui_actions=(getattr(self.s,'ui_actions',[])+actions)[-128:];actions.clear()
    def observe(self,probe,release,observation):
        s=self.s;s.shots+=1;s.input_recovery_streak=0;s.heartbeat('playing',progress='shot-confirmed')
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
