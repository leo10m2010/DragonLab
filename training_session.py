"""Bounded autonomous DragonBound curriculum, normal UI only, opt-in per session."""
import json,time,threading
from training_policy import next_probe,next_mobile
from calibration_book import mobile_name
from local_storage import atomic_write

class TrainingSession:
    def __init__(self,endpoint,target,book_path,emit,max_shots=60,max_matches=10,max_seconds=1800):
        if not 1<=max_shots<=1000 or not 1<=max_matches<=100 or not 30<=max_seconds<=21600:raise ValueError('Límites de entrenamiento inválidos')
        from pathlib import Path
        self.endpoint=endpoint;self.target=target;self.book_path=Path(book_path);self.emit=emit;self.max_shots=max_shots;self.max_matches=max_matches;self.max_seconds=max_seconds
        self.cancel=threading.Event();self.thread=None;self.running=False;self.status='Preparado';self.shots=0;self.matches=0;self.mobile_attempts={};self.history=[];self.last_error=''
    def start(self):
        if self.running:return
        self.cancel.clear();self.running=True;self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def stop(self):self.cancel.set()
    def records(self):
        try:return json.loads(self.book_path.read_text(encoding='utf-8')).get('records',{})
        except (OSError,ValueError):return {}
    def publish(self,message):
        self.status=message
        data={'active':self.running,'message':message,'shots':self.shots,'matches':self.matches,'limit_shots':self.max_shots,'last_error':self.last_error,'history':self.history[-120:],'updated':time.time()}
        try:atomic_write(self.book_path.parent/'entrenamiento-estado.json',json.dumps(data,allow_nan=False).encode())
        except OSError:pass
    def run(self):
        from training_browser import TrainingBrowser,UnavailableShot
        browser=None;started=time.monotonic();selected=False;queue_at=0;consumed=False;failures=0;last_hero=None;blocked_modes=set()
        try:
            browser=TrainingBrowser(self.endpoint,self.target);browser.arm();self.publish('Entrenando en Avatar Off')
            while not self.cancel.is_set() and self.shots<self.max_shots and time.monotonic()-started<self.max_seconds:
                ui=browser.guard(self.cancel)
                if ui.get('blocked'):raise RuntimeError('Hay un aviso del juego. Ciérralo antes de volver a empezar')
                if ui.get('away'):
                    browser.click(ui['away'],self.cancel);self.cancel.wait(.3);continue
                if not ui.get('game'):
                    consumed=False;last_hero=None;browser.client.game=None;browser.client.renderer=None
                    if ui['options']:
                        option=next_mobile(ui['options'],self.mobile_attempts)
                        if not option:raise RuntimeError('No hay carros identificables en el selector')
                        browser.click(option['point'],self.cancel);selected=True;name=mobile_name(option['name']);self.mobile_attempts[name]=self.mobile_attempts.get(name,0)+1
                        self.publish('Carro elegido: '+name);self.cancel.wait(.4);continue
                    if ui['controls'].get('buttonStart1v1'):
                        if queue_at and time.monotonic()-queue_at<20:self.cancel.wait(.5);continue
                        if self.matches>=self.max_matches:break
                        if not selected and ui['controls'].get('lobbyButtonMobile'):
                            browser.click(ui['controls']['lobbyButtonMobile'],self.cancel);self.cancel.wait(.3);continue
                        browser.click(ui['controls']['buttonStart1v1'],self.cancel);self.matches+=1;queue_at=time.monotonic();selected=False;self.publish('Buscando partida 1v1');self.cancel.wait(1);continue
                    self.publish('Esperando el lobby o la siguiente partida');self.cancel.wait(.5);continue
                queue_at=0
                state=browser.sample();hero_id=state.get('heroId');active=state.get('activePlayer')
                if active is not None and active not in (-1,hero_id):consumed=False;blocked_modes.clear()
                if last_hero is not None and last_hero!=hero_id:consumed=False
                last_hero=hero_id
                hero=next((p for p in state.get('players',[]) if p.get('id')==hero_id),None)
                if not hero or hero.get('dead') or active!=hero_id or consumed:
                    self.status='Esperando tu turno';self.cancel.wait(.25);continue
                mobile=mobile_name(hero.get('mobile'))
                if not mobile:raise RuntimeError('Carro no identificado; sesión detenida')
                available=[i for i,key in enumerate(('btnShot1','btnShot2','btnShotSS')) if ui['controls'].get(key) and i not in blocked_modes]
                if not available:self.cancel.wait(.2);continue
                probe=next_probe(self.records(),mobile,state.get('wind',0),self.shots,available)
                self.publish(f"{mobile} · tiro {('1','2','SS')[probe['shot']]} · fuerza de prueba {probe['power']}")
                try:
                    release,observation=browser.shoot(probe,self.cancel);consumed=True;self.shots+=1;failures=0;self.last_error=''
                    self.emit({'status':'training-observation','release':release,'observation':observation})
                    weather=[{k:w[k] for k in ('typeId','resolvedTypeId','x','size') if isinstance(w.get(k),(int,float))} for w in observation.get('weather',[])[:32] if isinstance(w,dict)]
                    self.history.append({**probe,'actual_power':release.get('power'),'actual_angle':release.get('angle'),'wind':release.get('wind'),'wind_angle':release.get('windAngle'),'weather':weather})
                    self.publish(f"Tiro {self.shots} registrado; esperando medición")
                except UnavailableShot as error:
                    blocked_modes.add(probe['shot']);self.publish(str(error));self.cancel.wait(.1);continue
                except RuntimeError as error:
                    self.last_error=str(error);failures+=1;self.publish(str(error))
                    # Never repeat a failed charge: it may have released a partial shot.
                    consumed=True
                    if failures>=3:raise RuntimeError('Tres intentos sin confirmar; revisa la sesión antes de continuar')
                self.cancel.wait(.25)
        except Exception as error:
            self.last_error=str(error);self.publish(str(error))
        finally:
            self.running=False
            if browser:browser.close()
            self.publish('Entrenamiento detenido: '+self.last_error if self.last_error else 'Sesión finalizada; progreso guardado')
