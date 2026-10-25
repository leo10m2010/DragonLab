"""Opt-in DragonBound training with a wall-clock deadline and saved reports."""
import json,time,threading
from local_storage import atomic_write

class TrainingSession:
    def __init__(self,endpoint,target,book_path,emit,max_shots=60,max_matches=10,max_seconds=1800,continuous=False,settings_provider=None,autonomous=False,objective='calibration',background=False,allow_dual=False):
        if not 1<=max_shots<=1000 or not 1<=max_matches<=100 or not 30<=max_seconds<=86400:raise ValueError('Límites de entrenamiento inválidos')
        from pathlib import Path
        self.endpoint=endpoint;self.target=target;self.book_path=Path(book_path);self.emit=emit;self.max_shots=max_shots;self.max_matches=max_matches;self.max_seconds=max_seconds
        self.cancel=threading.Event();self.thread=None;self.running=False;self.status='Preparado';self.shots=0;self.matches=0;self.mobile_attempts={};self.history=[];self.last_error=''
        self.lab_progress={};self.errors=[];self.movements=[];self.last_timing={};self.continuous=continuous;self.settings_provider=settings_provider
        if objective not in ('calibration','evaluation','adaptive'):raise ValueError('Objetivo de entrenamiento inválido')
        if objective=='evaluation' and continuous:raise ValueError('La evaluación individual debe tener un límite')
        self.allow_dual=bool(allow_dual);self.background=bool(background);self.objective=objective;self.trial=None;self.battle=None
        self.autonomous=autonomous;self.learner=None
        self.published=None;self.published_at=0;self.started_at=None;self.started_wall=None;self.report={};self.stop_reason=''
    def start(self):
        if self.running:return
        self.cancel.clear();self.started_at=time.monotonic();self.started_wall=time.time();self.running=True;self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def stop(self):self.stop_reason='requested';self.cancel.set()
    def time_remaining(self):
        return max(0,self.max_seconds-(time.monotonic()-self.started_at)) if self.started_at is not None else self.max_seconds
    def records(self):
        try:return json.loads(self.book_path.read_text(encoding='utf-8')).get('records',{})
        except (OSError,ValueError):return {}
    def publish(self,message):
        self.status=message
        stamp=(message,self.running,self.shots,self.matches,self.last_error)
        if stamp==self.published and time.monotonic()-self.published_at<5:return
        self.published=stamp;self.published_at=time.monotonic()
        data={'active':self.running,'continuous':self.continuous,'autonomous':self.autonomous,'guided':bool(self.settings_provider) and not self.autonomous,'background':self.background,'objective':self.objective,'evaluation':self.trial.summary() if self.trial else None,'battle':self.battle.summary() if self.battle else None,'message':message,'shots':self.shots,'matches':self.matches,'limit_shots':None if self.continuous else self.max_shots,'duration_seconds':self.max_seconds,'remaining_seconds':round(self.time_remaining()),'expires_at':self.started_wall+self.max_seconds if self.started_wall is not None else None,'report':self.report,'last_error':self.last_error,'errors':self.errors[-64:],'movements':self.movements[-64:],'timing':self.last_timing,'progress':{**(self.learner.progress() if self.learner else {}),**self.lab_progress},'history':self.history[-120:],'updated':time.time()}
        data['stop_reason']=self.stop_reason
        try:atomic_write(self.book_path.parent/'entrenamiento-estado.json',json.dumps(data,allow_nan=False).encode())
        except OSError:pass
    def run(self):
        from training_controller import TrainingController
        from training_lease import TrainingLease
        try:lease=TrainingLease('data:'+str(self.book_path.parent.resolve()).casefold())
        except Exception as error:
            self.running=False;self.last_error=str(error);self.status='Entrenamiento detenido: '+str(error)
            return
        try:TrainingController(self).run()
        except Exception as error:
            self.running=False;self.last_error=str(error);self.publish('Entrenamiento detenido: '+str(error))
        finally:lease.close()
