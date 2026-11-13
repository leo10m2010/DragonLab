"""Low-frequency measurements of this process; never inspects other apps."""
import ctypes,os,time

def memory_usage():
    if os.name=='nt':
        from ctypes import wintypes as w
        class Counters(ctypes.Structure):
            _fields_=[('cb',w.DWORD),('PageFaultCount',w.DWORD)]+[(key,ctypes.c_size_t) for key in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetCurrentProcess.restype=w.HANDLE
        kernel.K32GetProcessMemoryInfo.argtypes=[w.HANDLE,ctypes.POINTER(Counters),w.DWORD];kernel.K32GetProcessMemoryInfo.restype=w.BOOL
        counters=Counters();counters.cb=ctypes.sizeof(counters)
        if kernel.K32GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):return counters.WorkingSetSize/1048576,counters.PagefileUsage/1048576
    else:
        try:
            with open('/proc/self/statm',encoding='ascii') as file:resident=int(file.read().split()[1])
            return resident*os.sysconf('SC_PAGE_SIZE')/1048576,None
        except (OSError,ValueError,IndexError,AttributeError):pass
    return None,None

class RuntimeMetrics:
    def __init__(self,clock=time.monotonic,cpu=time.process_time,memory=memory_usage,interval=2):
        self.clock=clock;self.cpu=cpu;self.memory=memory;self.interval=interval;self.wall=clock();self.used=cpu();self.cache={};self.presentations=None
    def sample(self,app=None,force=False):
        now=self.clock();elapsed=now-self.wall
        if self.cache and elapsed<self.interval and not force:return dict(self.cache)
        used=self.cpu();load=max(0,(used-self.used)/elapsed*100) if elapsed>0 else None
        try:working,private=self.memory()
        except (OSError,AttributeError):working,private=None,None
        from native_solver import diagnostics as solver_info
        from native_overlay import diagnostics as overlay_info
        renderer=overlay_info();native=renderer.get('counters',{});presents=native.get('presentations')
        rate=(presents-self.presentations)/elapsed if self.presentations is not None and isinstance(presents,int) and elapsed>0 and presents>=self.presentations else None
        self.presentations=presents if isinstance(presents,int) else None
        result={'cpu_one_core_percent':round(load,1) if load is not None else None,'working_set_mib':round(working,1) if working is not None else None,'private_mib':round(private,1) if private is not None else None,'overlay_presentations_hz':round(rate,1) if rate is not None else None,'solver':solver_info(),'overlay':renderer}
        if app:
            result.update(solve_ms=round(app.last_solve_seconds*1000,3) if getattr(app,'last_solve_seconds',None) is not None else None,read_ms=round(app.last_read_seconds*1000,2) if getattr(app,'last_read_seconds',None) is not None else None,source_age_s=round(max(0,now-app.last_live),1) if getattr(app,'last_live',0) else None,game=getattr(app,'clone_id',None),roster=dict(getattr(app,'roster_diagnostics',{}) or {}))
        if 'roster' in result:result['roster']={k:v for k,v in result['roster'].items() if k in ('raw','objects','missingId','invalidPosition','duplicates','valid','dead','alive','hero','ally','enemy','unknown','truncated') and isinstance(v,int) and not isinstance(v,bool) and v>=0}
        self.wall=now;self.used=used;self.cache=result
        return dict(result)
