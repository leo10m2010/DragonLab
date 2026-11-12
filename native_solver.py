"""Optional Rust acceleration for the manual guide; original engine is fallback."""
import ctypes,json,os,pathlib,sys,threading
from dataclasses import asdict
from core import finite_settings,solve as reference_solve
from solve_control import SolveCancelled,check_cancel

class NativeUnsupported(Exception):pass

def library_path(name):
    base=pathlib.Path(getattr(sys,'_MEIPASS',pathlib.Path(__file__).parent))
    extension='.dll' if os.name=='nt' else '.so'
    return base/'native'/'bin'/((name if os.name=='nt' else 'lib'+name)+extension)

class NativeSolver:
    def __init__(self,path=None):
        path=pathlib.Path(path or library_path('dragonlab_core')).resolve()
        self.dll=ctypes.CDLL(str(path),**({'winmode':0x1100} if os.name=='nt' else {}))
        self.dll.dl_core_version.argtypes=[];self.dll.dl_core_version.restype=ctypes.c_uint32
        if self.dll.dl_core_version()!=1:raise OSError('ABI del motor Rust incompatible')
        self.dll.dl_cancel_new.argtypes=[];self.dll.dl_cancel_new.restype=ctypes.c_void_p
        for name in ('dl_cancel_set','dl_cancel_free','dl_string_free'):
            function=getattr(self.dll,name);function.argtypes=[ctypes.c_void_p];function.restype=None
        self.dll.dl_solve_json.argtypes=[ctypes.c_char_p,ctypes.c_size_t,ctypes.c_void_p];self.dll.dl_solve_json.restype=ctypes.c_void_p
    def solve(self,settings,cancel=None):
        finite_settings(settings);check_cancel(cancel)
        if cancel is not None and not hasattr(cancel,'subscribe'):raise NativeUnsupported('non-native cancellation token')
        request=json.dumps(asdict(settings),ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
        handle=self.dll.dl_cancel_new();unregister=None;response=None
        if not handle:raise RuntimeError('No se pudo crear cancelación Rust')
        try:
            if cancel is not None:unregister=cancel.subscribe(lambda:self.dll.dl_cancel_set(handle))
            response=self.dll.dl_solve_json(request,len(request),handle)
            if not response:raise RuntimeError('El motor Rust no devolvió un resultado')
            data=json.loads(ctypes.string_at(response))
            check_cancel(cancel)
            error=data.get('error')
            if error=='cancelled':raise SolveCancelled()
            if isinstance(error,str) and error.startswith('unsupported:'):raise NativeUnsupported(error)
            if error:raise RuntimeError(error)
            result=data.get('result')
            if not isinstance(result,dict) or not isinstance(result.get('reachable'),bool):raise RuntimeError('Respuesta Rust inválida')
            return result
        finally:
            if unregister:unregister()
            if response:self.dll.dl_string_free(response)
            self.dll.dl_cancel_free(handle)

_lock=threading.Lock();_backend=None;_attempted=False
_stats={'engine':'python','native_completed':0,'fallbacks':0,'error':''}

def backend():
    global _backend,_attempted
    with _lock:
        if not _attempted:
            _attempted=True
            if os.environ.get('DRAGONLAB_DISABLE_RUST')!='1':
                try:_backend=NativeSolver();_stats['engine']='rust+python'
                except (OSError,AttributeError):_stats['error']='Motor Rust no disponible; se utiliza el motor compatible.'
        return _backend

def solve(settings,cancel=None):
    native=backend()
    if native:
        try:
            result=native.solve(settings,cancel)
            with _lock:_stats['native_completed']+=1
            return result
        except NativeUnsupported:pass
        except SolveCancelled:raise
        except (OSError,RuntimeError,ValueError,TypeError) as error:
            with _lock:_stats['error']='Motor compatible activo: '+str(error)[:120]
    with _lock:_stats['fallbacks']+=1
    return reference_solve(settings,cancel=cancel)

def diagnostics():
    with _lock:return dict(_stats)
