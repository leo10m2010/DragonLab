"""Explicit turn state machine; bounded history, retries, and browser recovery."""
import math,time
from calibration_book import mobile_name
from training_policy import next_probe,next_mobile
from training_turns import TurnLedger,turn_key
from training_browser import TrainingBrowser,FocusPause,UnavailableShot,TurnExpired,UnconfirmedShot,TurnNotReady
from training_aim import NoAim
from training_memory import ActionMemory

class TrainingController:
    def __init__(self,session):
        self.s=session;self.ledger=TurnLedger();self.current=None;self.blocked=set();self.selected=False;self.queue_at=0;self.failures=0;self.in_game=False;self.power=None
        self.learner=None
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
                self.trial=AdaptiveTrial(session.book_path.parent/'evaluacion-adaptativa.json',self.learner,session.max_shots,allow_dual=session.allow_dual)
            else:self.trial=EvaluationTrial(session.book_path.parent/'evaluacion-punteria.json',self.learner,session.max_shots)
            session.trial=self.trial
            self.battle=BattleMetrics(session.book_path.parent/'partidas-observadas.json',self.trial.health_result);session.battle=self.battle
        self.memory=None if session.autonomous else ActionMemory(session.book_path.parent/'estrategia-entrenamiento.json')
    def within_limits(self,started):
        s=self.s
        return not s.cancel.is_set() and (s.continuous or s.shots<s.max_shots and time.monotonic()-started<s.max_seconds)
    def run(self):
        from training_power import SleepLease
        s=self.s;browser=None;started=time.monotonic();retries=0;first=True;self.power=SleepLease()
        try:
            while self.within_limits(started):
                try:
                    if browser is None:
                        browser=TrainingBrowser(s.endpoint,s.target);browser.background=s.background;browser.arm(focus=first and not s.background);first=False
                        if retries:s.last_error=''
                        s.publish('Conexión recuperada' if retries else 'Entrenando en Avatar Off')
                    if self.cycle(browser) is False:break
                    retries=0
                except FocusPause as error:
                    if not s.continuous and not s.background:raise
                    self.power.hold(False)
                    s.publish(str(error));s.cancel.wait(.5)
                except (OSError,ConnectionError,TimeoutError) as error:
                    if not s.continuous and not s.background:raise
                    self.power.hold(False)
                    s.last_error=str(error)
                    if browser:
                        try:browser.close()
                        except Exception:pass
                    browser=None;retries+=1
                    s.publish('Reconectando el navegador; no se repite un tiro de este turno')
                    s.cancel.wait(min(15,2**min(retries,4)))
        except Exception as error:s.last_error=str(error)
        finally:
            if self.battle:
                if browser and not s.cancel.is_set():
                    until=time.monotonic()+15
                    while self.battle.pending and time.monotonic()<until and not s.cancel.is_set():
                        try:self.battle.observe(browser.sample())
                        except (OSError,RuntimeError,ConnectionError,TimeoutError):break
                        s.cancel.wait(.2)
                self.battle.end()
            if self.trial:self.trial.finish()
            self.power.close()
            if browser:
                try:browser.close()
                except Exception:pass
            s.running=False
            s.publish('Entrenamiento detenido: '+s.last_error if s.last_error else ('Evaluación finalizada: '+self.trial.summary()['status'] if self.trial else 'Sesión finalizada; progreso guardado'))
    def cycle(self,browser):
        s=self.s;ui=browser.guard(s.cancel)
        if self.trial and self.trial.done():return False
        if self.power:self.power.hold(True)
        if ui.get('blocked'):raise RuntimeError('Hay un aviso del juego. Ciérralo antes de volver a empezar')
        if ui.get('away'):
            browser.click(ui['away'],s.cancel);s.cancel.wait(.3);return
        if ui.get('serverEntry'):
            browser.click(ui['serverEntry'],s.cancel);s.publish('Entrando a Avatar Off');s.cancel.wait(.7);return
        if ui.get('url')=='https://dragonbound.net/':
            s.publish('Esperando que cargue DragonBound y su sesión');s.cancel.wait(.5);return
        if not ui.get('game'):
            if self.battle:self.battle.end()
            if self.learner:self.learner.pending.clear()
            if self.in_game:self.ledger=TurnLedger();self.failures=0
            self.in_game=False
            self.current=None;self.blocked.clear();browser.client.game=None;browser.client.renderer=None
            if ui['options']:
                option=self.trial.choose_mobile(ui['options'],s.mobile_attempts) if s.objective=='adaptive' else next((o for o in ui['options'] if mobile_name(o.get('name'))=='ARMOR'),None) if self.trial else self.learner.choose_mobile(ui['options'],s.mobile_attempts) if self.learner else next_mobile(ui['options'],s.mobile_attempts)
                if not option:raise RuntimeError('No hay carros identificables en el selector')
                browser.click(option['point'],s.cancel);self.selected=True;name=mobile_name(option['name']);s.mobile_attempts[name]=s.mobile_attempts.get(name,0)+1
                s.publish('Carro elegido: '+name);s.cancel.wait(.4);return
            if ui['controls'].get('buttonStart1v1'):
                if self.queue_at and time.monotonic()-self.queue_at<20:s.cancel.wait(.5);return
                if not s.continuous and s.matches>=s.max_matches:return False
                if not self.selected and ui['controls'].get('lobbyButtonMobile'):
                    browser.click(ui['controls']['lobbyButtonMobile'],s.cancel);s.cancel.wait(.3);return
                browser.click(ui['controls']['buttonStart1v1'],s.cancel);s.matches+=1;self.queue_at=time.monotonic();self.selected=False
                s.publish('Buscando partida 1v1');s.cancel.wait(1);return
            s.publish('Esperando el lobby o la siguiente partida');s.cancel.wait(.5);return
        if not self.in_game and self.learner:self.learner.episode=str(time.time_ns())
        self.in_game=True;self.queue_at=0;state=browser.sample();key=turn_key(state,ui['url'])
        if self.learner:self.learner.track(state)
        if self.battle:self.battle.observe(state)
        if key!=self.current:self.current=key;self.blocked.clear()
        if not self.ledger.available(key):
            s.publish('Esperando el próximo turno' if key in self.ledger.used else 'Esperando confirmar tu turno')
            s.cancel.wait(.35);return
        hero=next(p for p in state['players'] if str(p.get('id'))==str(state['heroId']))
        mobile=mobile_name(hero.get('mobile'))
        if not mobile:raise RuntimeError('Carro no identificado; sesión detenida')
        if s.objective=='evaluation' and mobile!='ARMOR':s.publish('Esperando el lobby: la prueba solo usa Armor tiro 1');s.cancel.wait(.5);return
        available=[i for i,k in enumerate(('btnShot1','btnShot2','btnShotSS')) if ui['controls'].get(k) and i not in self.blocked]
        if not available:
            if self.blocked:
                self.ledger.consume(key);s.publish('Sin modalidad disponible o tiro seguro en este turno')
                if s.objective=='adaptive':self.trial.turn_skipped(key)
            s.cancel.wait(.2);return
        if s.objective=='evaluation':
            if 0 not in available:
                self.ledger.consume(key);self.trial.skip('Armor tiro 1 no está disponible');s.publish('Tiro 1 no disponible; prueba sin disparo');return
            available=[0]
        if s.objective=='adaptive':
            try:probe=self.trial.probe(mobile,state,available)
            except NoAim as error:self.ledger.consume(key);self.trial.skip(error);self.trial.turn_skipped(key);s.publish(str(error));return
        else:probe=self.trial.probe() if self.trial else self.learner.choose_probe(mobile,state.get('wind',0),s.shots,available) if self.learner else next_probe(s.records(),mobile,state.get('wind',0),s.shots,available)
        probe['turn_serial']=key[-1]
        if self.memory and s.shots%3==2:probe=self.memory.recommend(probe,state,available)
        stage='decidiendo con mediciones propias' if self.learner else 'calculando viento y recorrido'
        s.publish(f"Turno {key[-1]} · {mobile} · tiro {('1','2','SS')[probe['shot']]} · {stage}")
        try:
            options={'settings_provider':None if self.learner else s.settings_provider,'before_fire':lambda:self.ledger.consume(key)}
            if self.learner:options['autonomous']=self.trial or self.learner
            release,observation=browser.shoot(probe,s.cancel,**options)
            self.observe(probe,release,observation);self.failures=0;s.last_error=''
        except UnavailableShot as error:
            self.blocked.add(probe['shot']);s.publish(str(error))
        except NoAim as error:
            if s.objective=='adaptive':
                self.blocked.add(probe['shot']);self.trial.skip(error);s.publish(str(error)+'; buscando otra modalidad en este turno')
            elif self.trial:
                if self.ledger.available(key):self.ledger.consume(key)
                self.trial.skip(error);s.publish(str(error))
            else:self.blocked.add(probe['shot']);s.publish(str(error)+'; probando otra modalidad')
        except TurnNotReady as error:
            s.publish(str(error));s.cancel.wait(.15)
        except (TurnExpired,UnconfirmedShot) as error:
            if self.ledger.available(key):self.ledger.consume(key)
            self.failures=0;s.last_error='';self.record_error(key,str(error),'turn-ended' if isinstance(error,TurnExpired) else 'unconfirmed')
            s.publish(str(error)+'; continuará en el próximo turno')
        except (FocusPause,OSError,ConnectionError,TimeoutError):raise
        except RuntimeError as error:
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
        s.cancel.wait(.15)
    def record_error(self,key,reason,kind):
        self.s.errors.append({'turn':key[-1],'reason':reason,'kind':kind,'at':time.time()})
        self.s.errors=self.s.errors[-64:]
    def observe(self,probe,release,observation):
        s=self.s;s.shots+=1
        if self.learner and not release.get('item'):self.learner.observe(probe,release,observation)
        if self.trial:
            token=self.trial.record(release,observation);self.battle.note(release,release.get('learner') or {},observation,token)
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
        source=lab.get('stage','Lab')
        s.publish(f"Tiro {s.shots} · turno {probe['turn_serial']} · {source} · fuerza {lab.get('power',probe['power'])} → real {release.get('power')}")
