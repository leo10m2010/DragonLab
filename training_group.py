"""Two target-pinned learners with separate books, controls and session reports."""
import json,math,threading,time,uuid
from pathlib import Path
from urllib.parse import urlsplit
from calibration_book import CalibrationBook
from local_storage import atomic_write
from training_progress import lab_summary,share_observation


def canonical_endpoint(value):
    try:
        parsed=urlsplit(value);port=parsed.port
        if parsed.scheme!='http' or parsed.hostname not in ('localhost','127.0.0.1','::1') or parsed.username is not None or parsed.password is not None or parsed.path not in ('','/') or parsed.query or parsed.fragment or port is None or not 1<=port<=65535:raise ValueError
    except (ValueError,TypeError,AttributeError):
        raise ValueError('Cada sesión necesita una conexión local HTTP con puerto explícito') from None
    return f'http://127.0.0.1:{port}'


def checked_slots(base,slots):
    if not isinstance(slots,(list,tuple)) or len(slots)!=2:raise ValueError('El entrenamiento paralelo necesita exactamente dos sesiones')
    root=Path(base).resolve();result=[];ids=set();resources=set();directories=set()
    for slot in slots:
        if not isinstance(slot,dict):raise ValueError('Configuración de sesión inválida')
        identifier=slot.get('id');target=slot.get('target')
        if identifier not in ('sesion-1','sesion-2') or identifier in ids:raise ValueError('Cada sesión necesita su identificador propio')
        if not isinstance(target,str) or not target.strip() or len(target)>200:raise ValueError('Fija la pestaña del juego antes de iniciar ambas sesiones')
        endpoint=canonical_endpoint(slot.get('endpoint'))
        try:directory=Path(slot['directory']).resolve()
        except (KeyError,TypeError,ValueError,OSError):raise ValueError('Cada sesión necesita su directorio de mediciones') from None
        if directory==root or not directory.is_relative_to(root):raise ValueError('Las mediciones paralelas deben estar separadas dentro del directorio de DragonLab')
        resource=(endpoint,target);path=str(directory).casefold()
        if resource in resources:raise ValueError('Dos sesiones no pueden controlar la misma pestaña')
        if path in directories:raise ValueError('Dos sesiones no pueden compartir el directorio de mediciones')
        ids.add(identifier);resources.add(resource);directories.add(path)
        result.append({'id':identifier,'endpoint':endpoint,'target':target,'directory':directory})
    return result


def seed_missing(source,destination):
    if destination.exists() or not source.is_file():return
    raw=source.read_bytes()
    try:
        with destination.open('xb') as stream:stream.write(raw)
    except FileExistsError:pass


class TrainingGroup:
    """One launcher facade; an individual worker failure does not stop its peer."""
    def __init__(self,base,slots,emit,max_shots=40,max_seconds=86400,continuous=True,session_factory=None):
        # Validate every slot and common limit before writing files or workers.
        self.base=Path(base).resolve();self.slots=checked_slots(self.base,slots)
        if isinstance(max_shots,bool) or not isinstance(max_shots,int) or not 1<=max_shots<=1000 or isinstance(max_seconds,bool) or not isinstance(max_seconds,(int,float)) or not math.isfinite(max_seconds) or not 30<=max_seconds<=86400:raise ValueError('Límites de entrenamiento inválidos')
        if session_factory is None:
            from training_session import TrainingSession
            session_factory=TrainingSession
        self.group_run_id=uuid.uuid4().hex;self.emit=emit;self.continuous=bool(continuous);self.autonomous=True;self.background=True
        self.cancel=threading.Event();self._monitor_stop=threading.Event();self._monitor=None;self._selected=0
        self._observation_lock=threading.Lock();self._write_lock=threading.Lock();self._started=False;self.monitor_error=''
        self.books={};self.sessions=[];self.thread=self
        for slot in self.slots:
            slot['directory'].mkdir(parents=True,exist_ok=True)
            for name in ('calibraciones.json','aprendizaje-autonomo.json'):seed_missing(self.base/name,slot['directory']/name)
            identifier=slot['id'];book=CalibrationBook(slot['directory']/'calibraciones.json');self.books[identifier]=book
            def forward(event,session_id=identifier):
                if not isinstance(event,dict):return
                tagged={**event,'session_id':session_id,'group_run_id':self.group_run_id}
                if isinstance(event.get('release'),dict):tagged['release']={**event['release'],'measurement_session':self.group_run_id+':'+session_id}
                self.emit(tagged)
            session=session_factory(slot['endpoint'],slot['target'],book.path,forward,max_shots=max_shots,max_matches=6,max_seconds=max_seconds,continuous=self.continuous,autonomous=True,objective='adaptive',background=True,allow_dual=True)
            session.session_id=identifier;session.lab_progress=lab_summary(book);self.sessions.append(session)

    @property
    def selected(self):return self._selected
    @selected.setter
    def selected(self,value):
        if isinstance(value,bool) or value not in (0,1):raise ValueError('Selecciona la sesión 1 o la sesión 2')
        self._selected=int(value)
    def __getattr__(self,name):
        sessions=self.__dict__.get('sessions')
        if not sessions or name.startswith('__'):raise AttributeError(name)
        return getattr(sessions[self._selected],name)
    @property
    def running(self):return any(session.running for session in self.sessions)
    @property
    def shots(self):return sum(session.shots for session in self.sessions)
    @property
    def matches(self):return sum(session.matches for session in self.sessions)
    @property
    def status(self):return ' · '.join(f"Sesión {index+1}: {session.status}" for index,session in enumerate(self.sessions))
    @property
    def last_error(self):return ' · '.join(f"Sesión {index+1}: {session.last_error}" for index,session in enumerate(self.sessions) if session.last_error)
    @property
    def lab_progress(self):return self.sessions[self._selected].lab_progress
    @lab_progress.setter
    def lab_progress(self,value):self.sessions[self._selected].lab_progress=value

    def start(self):
        if self._started:return self
        self._started=True;self.cancel.clear();self._monitor_stop.clear()
        for session in self.sessions:
            try:session.start()
            except Exception as error:
                session.running=False;session.last_error=str(error);session.status='No se pudo iniciar esta sesión'
        self.publish_overview()
        self._monitor=threading.Thread(target=self._watch,name='DragonLab-dual-monitor',daemon=True);self._monitor.start()
        return self
    def stop(self):
        self.cancel.set()
        for session in self.sessions:session.stop()
        # Keep the monitor until the workers actually release their controls.
        # A Stop click need not call join(), and must still get a final snapshot.
        self.publish_overview()
    def join(self,timeout=None):
        self._monitor_stop.set();until=None if timeout is None else time.monotonic()+max(0,timeout)
        for session in self.sessions:
            thread=session.thread
            if thread and thread is not threading.current_thread():thread.join(None if until is None else max(0,until-time.monotonic()))
        if self._monitor and self._monitor is not threading.current_thread():self._monitor.join(None if until is None else max(0,until-time.monotonic()))
        self.publish_overview()
    def is_alive(self):return self.running or bool(self._monitor and self._monitor.is_alive())
    def observe(self,event):
        if not isinstance(event,dict) or event.get('group_run_id')!=self.group_run_id or event.get('session_id') not in self.books:raise ValueError('La observación no pertenece a esta sesión paralela')
        if event.get('status')!='training-observation' or not isinstance(event.get('observation'),dict) or not isinstance(event.get('release'),dict):raise ValueError('La observación de entrenamiento está incompleta')
        identifier=event['session_id'];index=next(i for i,slot in enumerate(self.slots) if slot['id']==identifier)
        with self._observation_lock:
            progress=share_observation(self.books[identifier],event['observation'],event['release'])
            self.sessions[index].lab_progress=progress
        return progress
    def overview(self):
        rows=[]
        for slot,session in zip(self.slots,self.sessions):
            state='stopping' if session.running and self.cancel.is_set() else 'active' if session.running else 'error' if session.last_error else 'finished' if self._started else 'prepared'
            rows.append({'id':slot['id'],'state':state,'active':bool(session.running),'shots':session.shots,'matches':session.matches,'remaining_seconds':round(session.time_remaining()),'block':(session.report or {}).get('block'),'error':bool(session.last_error),'error_count':len(session.errors)})
        return {'schema':1,'group_run_id':self.group_run_id,'active':self.running,'continuous':self.continuous,'stopping':self.cancel.is_set(),'shots':self.shots,'matches':self.matches,'sessions':rows,'updated':time.time()}
    def publish_overview(self):
        try:
            with self._write_lock:atomic_write(self.base/'entrenamiento-paralelo-estado.json',json.dumps(self.overview(),allow_nan=False).encode())
            self.monitor_error=''
        except (OSError,TypeError,ValueError):self.monitor_error='No se pudo guardar el estado del entrenamiento paralelo'
    def _watch(self):
        try:
            while not self._monitor_stop.wait(2):
                self.publish_overview()
                if not self.running:self._monitor_stop.set();break
        finally:self.publish_overview()
