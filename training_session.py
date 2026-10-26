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
        self.retirements=0;self.passed_turns=0;self.ui_actions=[]
        self.phase='prepared';self.heartbeat_at=None;self.last_progress_at=None;self.last_progress_kind='';self.confirmed_shot_at=None
        self.input_recovery={};self.input_recoveries=0;self.input_recovery_counts={};self.input_recovery_streak=0;self.last_recovery_code='';self.reconnects=0;self.watchdog_reconnects=0
        self.status_write_error=''
        self.opponent_progress={};self.opponent_error=''
    def start(self):
        if self.running:return
        self.cancel.clear();self.started_at=time.monotonic();self.started_wall=time.time();self.running=True;self.heartbeat('starting',progress='started');self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def stop(self):self.stop_reason='requested';self.cancel.set()
    def time_remaining(self):
        return max(0,self.max_seconds-(time.monotonic()-self.started_at)) if self.started_at is not None else self.max_seconds
    def heartbeat(self,phase=None,progress=None):
        now=time.monotonic();self.heartbeat_at=now
        if phase is not None:self.phase=phase
        if progress is not None:self.last_progress_at=now;self.last_progress_kind=progress
        if progress=='shot-confirmed':self.confirmed_shot_at=now
    def health(self):
        now=time.monotonic();progress_at=self.last_progress_at if self.last_progress_at is not None else self.started_at
        age=lambda stamp:None if stamp is None else round(max(0,now-stamp),2)
        retry=self.input_recovery.get('drag_disabled_until',0)
        return {'phase':self.phase,'heartbeat_age_seconds':age(self.heartbeat_at),'progress_age_seconds':age(progress_at),'shot_age_seconds':age(self.confirmed_shot_at if self.confirmed_shot_at is not None else self.started_at),'last_progress_kind':self.last_progress_kind,'input_recoveries':self.input_recoveries,'input_recovery_counts':dict(self.input_recovery_counts),'last_recovery_code':self.last_recovery_code,'drag_retry_after_seconds':round(max(0,retry-now),2),'reconnects':self.reconnects,'watchdog_reconnects':self.watchdog_reconnects,'status_write_error':bool(self.status_write_error)}
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
        data['health']=self.health()
        data['opponents']={**self.opponent_progress,'observer_error':bool(self.opponent_error)}
        data.update(retirements=self.retirements,passed_turns=self.passed_turns,ui_actions=self.ui_actions[-128:])
        try:
            atomic_write(self.book_path.parent/'entrenamiento-estado.json',json.dumps(data,allow_nan=False).encode());self.status_write_error=''
        except OSError:self.status_write_error='No se pudo guardar el estado del entrenamiento'
    def run(self):
        from training_controller import TrainingController
        from training_lease import TrainingLease
        try:lease=TrainingLease('data:'+str(self.book_path.parent.resolve()).casefold())
        except Exception as error:
            self.running=False;self.last_error=str(error);self.stop_reason='error';self.heartbeat('error');self.status='Entrenamiento detenido: '+str(error)
            return
        try:TrainingController(self).run()
        except Exception as error:
            self.running=False;self.last_error=str(error);self.stop_reason='error';self.heartbeat('error');self.publish('Entrenamiento detenido: '+str(error))
        finally:lease.close()
