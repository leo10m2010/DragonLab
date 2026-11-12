"""One manual calculation at a time, with only the newest pending snapshot."""
import threading,time
from native_solver import solve
from solve_control import SolveCancelled,check_cancel,CancellationToken

class LatestCalculation:
    def __init__(self,emit,solver=solve):
        self.emit=emit;self.solver=solver;self.condition=threading.Condition();self.pending=None;self.active=None;self.thread=None;self.closed=False
        self.submitted=0;self.completed=0;self.cancelled=0
    def invalidate(self):
        with self.condition:
            if self.active:self.active.set()
            if self.pending:self.pending[1].set();self.pending=None
    def submit(self,job):
        with self.condition:
            if self.closed:return False
            if self.active:self.active.set()
            if self.pending:self.pending[1].set()
            self.pending=(job,CancellationToken());self.submitted+=1
            if self.thread is None:
                self.thread=threading.Thread(target=self.run,daemon=True,name='DragonLab-Manual-Calculation');self.thread.start()
            self.condition.notify();return True
    def run(self):
        while True:
            with self.condition:
                while self.pending is None and not self.closed:self.condition.wait()
                if self.closed:return
                job,cancel=self.pending;self.pending=None;self.active=cancel
            event={'status':'calculated','generation':job['generation'],'context':job['context']}
            try:
                started=time.perf_counter();check_cancel(cancel)
                settings=job['settings']
                result={'reachable':False,'reason':job.get('missing_reason','Falta un perfil aplicable.')} if job.get('profile_required') else self.solver(settings,cancel=cancel)
                check_cancel(cancel)
                preview=job.get('preview_power')
                if not job.get('profile_required') and not result.get('reachable') and not result.get('blocked') and preview and not settings.environment.get('learnedLaunch'):
                    from physics_extensions import trajectory
                    traces=trajectory(settings,preview,step=.06,include_deployment=True,cancel=cancel)
                    result['preview_paths']=[[(p[0],p[1]) for p in path] for path in traces['display_paths']];result['preview_power']=preview
                check_cancel(cancel);event.update(result=result,solve_seconds=time.perf_counter()-started)
            except SolveCancelled:
                with self.condition:self.cancelled+=1
                event=None
            except Exception as error:event.update(result={},error=str(error))
            with self.condition:
                valid=not self.closed and not cancel.is_set()
                if self.active is cancel:self.active=None
                if event is not None and valid:self.completed+=1;self.emit(event)
    def close(self):
        with self.condition:
            self.closed=True
            if self.active:self.active.set()
            if self.pending:self.pending[1].set();self.pending=None
            self.condition.notify_all()
    def summary(self):
        with self.condition:return {'submitted':self.submitted,'completed':self.completed,'cancelled':self.cancelled,'pending':bool(self.pending),'active':self.active is not None}
