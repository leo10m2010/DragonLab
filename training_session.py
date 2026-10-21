"""Bounded autonomous DragonBound curriculum, normal UI only, opt-in per session."""
import json,time,threading
from local_storage import atomic_write

class TrainingSession:
    def __init__(self,endpoint,target,book_path,emit,max_shots=60,max_matches=10,max_seconds=1800,continuous=False,settings_provider=None,autonomous=False):
        if not 1<=max_shots<=1000 or not 1<=max_matches<=100 or not 30<=max_seconds<=21600:raise ValueError('Límites de entrenamiento inválidos')
        from pathlib import Path
        self.endpoint=endpoint;self.target=target;self.book_path=Path(book_path);self.emit=emit;self.max_shots=max_shots;self.max_matches=max_matches;self.max_seconds=max_seconds
        self.cancel=threading.Event();self.thread=None;self.running=False;self.status='Preparado';self.shots=0;self.matches=0;self.mobile_attempts={};self.history=[];self.last_error=''
        self.errors=[];self.continuous=continuous;self.settings_provider=settings_provider
        self.autonomous=autonomous;self.learner=None
        self.published=None;self.published_at=0
    def start(self):
        if self.running:return
        self.cancel.clear();self.running=True;self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def stop(self):self.cancel.set()
    def records(self):
        try:return json.loads(self.book_path.read_text(encoding='utf-8')).get('records',{})
        except (OSError,ValueError):return {}
    def publish(self,message):
        self.status=message
        stamp=(message,self.running,self.shots,self.matches,self.last_error)
        if stamp==self.published and time.monotonic()-self.published_at<5:return
        self.published=stamp;self.published_at=time.monotonic()
        data={'active':self.running,'continuous':self.continuous,'autonomous':self.autonomous,'guided':bool(self.settings_provider) and not self.autonomous,'message':message,'shots':self.shots,'matches':self.matches,'limit_shots':None if self.continuous else self.max_shots,'last_error':self.last_error,'errors':self.errors[-64:],'history':self.history[-120:],'updated':time.time()}
        try:atomic_write(self.book_path.parent/'entrenamiento-estado.json',json.dumps(data,allow_nan=False).encode())
        except OSError:pass
    def run(self):
        from training_controller import TrainingController
        TrainingController(self).run()
