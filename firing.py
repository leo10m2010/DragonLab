"""Explicitly armed, one-shot Windows input. Dry-run is the default.
Never chooses a target or fires autonomously. Each shot requires a new arm action.
"""
import ctypes,os,time,threading,math
from dataclasses import dataclass

@dataclass
class FirePlan:
    power:float
    max_power:float=400
    method:str='space'
    full_power_ms:float=1800
    bar_start:tuple=None
    bar_end:tuple=None
    data_time:float=0
    max_age:float=8
    countdown:float=3
    target_hwnd:int=0
    target_pid:int=0

class FireController:
    def __init__(self,backend=None):
        self.backend=backend or WindowsInput();self.cancel_event=threading.Event();self.armed=False
    def capture_target(self):return self.backend.foreground()
    def arm(self):self.armed=True;self.cancel_event.clear()
    def cancel(self):self.cancel_event.set();self.armed=False
    def fire(self,plan,dry_run=True,progress=None):
        if not self.armed:raise ValueError('Debes habilitar este disparo primero')
        self.armed=False
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (plan.power,plan.max_power,plan.full_power_ms,plan.data_time,plan.max_age,plan.countdown)):raise ValueError('El plan contiene valores inválidos')
        if not 0<=plan.power<=plan.max_power or plan.max_power<=0:raise ValueError('Potencia inválida')
        if plan.method not in ('space','bar'):raise ValueError('Método inválido')
        if not 50<=plan.full_power_ms<=10000:raise ValueError('Calibra la duración máxima entre 50 y 10000 ms')
        if not plan.target_hwnd or not plan.target_pid or plan.target_pid==os.getpid():raise ValueError('Selecciona primero la ventana del juego')
        if not 0<=plan.countdown<=10:raise ValueError('Cuenta regresiva inválida')
        if plan.method=='bar' and (not plan.bar_start or not plan.bar_end):raise ValueError('Configura los extremos de la barra')
        if plan.method=='bar' and any(len(p)!=2 or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in p) for p in (plan.bar_start,plan.bar_end)):raise ValueError('Coordenadas de barra inválidas')
        def check():
            if self.cancel_event.is_set() or self.backend.escaped():raise RuntimeError('Disparo cancelado')
            if time.monotonic()-plan.data_time>plan.max_age:raise RuntimeError('Solución caducada: vuelve a calcular')
        until=time.monotonic()+plan.countdown
        while time.monotonic()<until:
            check()
            if progress:progress('Cuenta regresiva %.1f s · Esc cancela'%max(0,until-time.monotonic()))
            time.sleep(.03)
        check()
        hwnd,pid,title=self.backend.foreground()
        if hwnd!=plan.target_hwnd or pid!=plan.target_pid:raise RuntimeError('La ventana elegida debe estar en primer plano')
        fraction=plan.power/plan.max_power
        action={'method':plan.method,'power':plan.power,'fraction':fraction,'window':title,'dry_run':dry_run}
        if plan.method=='space':action['hold_ms']=fraction*plan.full_power_ms
        else:action['point']=[round(a+(b-a)*fraction) for a,b in zip(plan.bar_start,plan.bar_end)]
        if dry_run:return action
        held=False
        try:
            if plan.method=='space':
                self.backend.key(True);held=True;end=time.monotonic()+action['hold_ms']/1000
                while time.monotonic()<end:
                    check()
                    if self.backend.foreground()[:2]!=(plan.target_hwnd,plan.target_pid):raise RuntimeError('La ventana perdió el foco; entrada liberada')
                    time.sleep(.005)
            else:
                self.backend.move(*plan.bar_start);self.backend.mouse(True);held=True
                check();self.backend.move(*action['point']);time.sleep(.03)
        finally:
            if held:
                if plan.method=='space':self.backend.key(False)
                else:self.backend.mouse(False)
        return action

class WindowsInput:
    def __init__(self):
        if os.name!='nt':raise RuntimeError('La entrada de disparo requiere Windows')
        self.u=ctypes.WinDLL('user32',use_last_error=True);self.u.GetForegroundWindow.restype=ctypes.c_void_p
        from ctypes import wintypes as w
        class Mouse(ctypes.Structure):
            _fields_=[('dx',w.LONG),('dy',w.LONG),('mouseData',w.DWORD),('flags',w.DWORD),('time',w.DWORD),('extra',ctypes.c_size_t)]
        class Key(ctypes.Structure):
            _fields_=[('vk',w.WORD),('scan',w.WORD),('flags',w.DWORD),('time',w.DWORD),('extra',ctypes.c_size_t)]
        class Union(ctypes.Union):
            _fields_=[('mouse',Mouse),('key',Key)]
        class Input(ctypes.Structure):
            _anonymous_=('data',)
            _fields_=[('type',w.DWORD),('data',Union)]
        self.Input=Input;self.Key=Key;self.Mouse=Mouse
        self.u.SendInput.argtypes=[w.UINT,ctypes.POINTER(Input),ctypes.c_int];self.u.SendInput.restype=w.UINT
        self.u.GetWindowRect.argtypes=[w.HWND,ctypes.POINTER(w.RECT)]
        self.u.WindowFromPoint.argtypes=[w.POINT];self.u.WindowFromPoint.restype=w.HWND
        self.u.GetAncestor.argtypes=[w.HWND,w.UINT];self.u.GetAncestor.restype=w.HWND
    def foreground(self):
        h=self.u.GetForegroundWindow();pid=ctypes.c_ulong();self.u.GetWindowThreadProcessId(ctypes.c_void_p(h),ctypes.byref(pid))
        title=ctypes.create_unicode_buffer(512);self.u.GetWindowTextW(ctypes.c_void_p(h),title,512)
        return int(h or 0),int(pid.value),title.value
    def escaped(self):return bool(self.u.GetAsyncKeyState(0x1B)&0x8000)
    def input_busy(self):
        return any(self.u.GetAsyncKeyState(k)&0x8000 for k in (0x01,0x20,0x10,0x11,0x12,0x25,0x26,0x27,0x28,0x57,0x41,0x53,0x44,0x5b,0x5c))
    def window_rect(self,window):
        from ctypes import wintypes as w
        r=w.RECT()
        if not self.u.GetWindowRect(window,ctypes.byref(r)):raise RuntimeError('La ventana del juego ya no está disponible')
        return r.left,r.top,r.right,r.bottom
    def point_in_window(self,x,y,window):
        from ctypes import wintypes as w
        child=self.u.WindowFromPoint(w.POINT(x,y))
        return bool(child) and self.u.GetAncestor(child,2)==window
    def send(self,event):
        if self.u.SendInput(1,ctypes.byref(event),ctypes.sizeof(self.Input))!=1:
            raise RuntimeError('Windows no aceptó la entrada. Abre el juego y DragonLab con el mismo nivel de permisos.')
    def key(self,down):
        e=self.Input();e.type=1;e.key=self.Key(0x20,0,0 if down else 2,0,0);self.send(e)
    def mouse(self,down):
        e=self.Input();e.type=0;e.mouse=self.Mouse(0,0,0,2 if down else 4,0,0);self.send(e)
    def move(self,x,y):
        if not self.u.SetCursorPos(int(x),int(y)):raise RuntimeError('Windows no pudo mover el cursor')
    def cursor(self):
        from ctypes import wintypes
        point=wintypes.POINT();self.u.GetCursorPos(ctypes.byref(point));return point.x,point.y
