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
        self.u=ctypes.windll.user32;self.u.GetForegroundWindow.restype=ctypes.c_void_p
    def foreground(self):
        h=self.u.GetForegroundWindow();pid=ctypes.c_ulong();self.u.GetWindowThreadProcessId(ctypes.c_void_p(h),ctypes.byref(pid))
        title=ctypes.create_unicode_buffer(512);self.u.GetWindowTextW(ctypes.c_void_p(h),title,512)
        return int(h or 0),int(pid.value),title.value
    def escaped(self):return bool(self.u.GetAsyncKeyState(0x1B)&0x8000)
    def key(self,down):self.u.keybd_event(0x20,0,0 if down else 2,0)
    def mouse(self,down):self.u.mouse_event(2 if down else 4,0,0,0,0)
    def move(self,x,y):self.u.SetCursorPos(int(x),int(y))
