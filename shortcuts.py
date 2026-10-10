"""Passive event-driven shortcuts for this application's connected game window.

Every event is passed onward unchanged. No key content is logged or stored.
"""
import os,threading
KEYS={'Ctrl':0x11,**{k:ord(k) for k in 'QERTYUIOPZXCVBNHJKLG'}}

def validate_bindings(target,fire):
    if target not in KEYS or fire not in KEYS or fire=='Ctrl' or target==fire:raise ValueError('Elige dos teclas diferentes; Ctrl se reserva para cambiar de objetivo.')
    return target,fire

class ShortcutState:
    CTRL={0x11,0xa2,0xa3}
    AIM={0x20,0x25,0x26,0x27,0x28,0x57,0x41,0x53,0x44}
    def __init__(self):self.controls=set();self.used=False;self.context=None
    def reset(self):self.controls.clear();self.used=False;self.context=None
    def feed(self,key,down,context,allowed,injected=False):
        if injected:return False
        if not allowed:self.reset();return False
        if self.context is not None and self.context!=context:self.reset()
        if key in self.CTRL:
            if down:
                if not self.controls:self.used=False;self.context=context
                self.controls.add(key)
                return False
            if key not in self.controls:return False
            self.controls.remove(key)
            fire=not self.controls and not self.used and self.context==context
            if not self.controls:self.used=False;self.context=None
            return fire
        if down and self.controls and key not in self.AIM:self.used=True
        return False

class GameShortcuts:
    def __init__(self,scope,emit,fire_emit=None,target_key='Ctrl',fire_key='Q'):
        self.scope=scope;self.emit=emit;self.state=ShortcutState();self.ready=False;self.error=None;self.thread_id=None;self.stop_event=threading.Event()
        self.fire_emit=fire_emit;self.pressed=set();self.set_bindings(target_key,fire_key)
    def set_bindings(self,target,fire):
        validate_bindings(target,fire);self.target_key=KEYS[target];self.fire_key=KEYS[fire];self.pressed=set();self.state.reset()
    def start(self):
        if os.name=='nt':threading.Thread(target=self.run,daemon=True).start()
    def close(self):
        self.stop_event.set()
        if self.thread_id:
            import ctypes
            ctypes.windll.user32.PostThreadMessageW(self.thread_id,0x12,0,0)
    def run(self):
        import ctypes
        from ctypes import wintypes as w
        u=ctypes.WinDLL('user32',use_last_error=True);k=ctypes.WinDLL('kernel32',use_last_error=True)
        class Key(ctypes.Structure):
            _fields_=[('vkCode',w.DWORD),('scanCode',w.DWORD),('flags',w.DWORD),('time',w.DWORD),('extra',ctypes.c_size_t)]
        callback_type=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,ctypes.c_int,w.WPARAM,w.LPARAM)
        u.SetWindowsHookExW.argtypes=(ctypes.c_int,callback_type,w.HINSTANCE,w.DWORD);u.SetWindowsHookExW.restype=w.HANDLE
        u.CallNextHookEx.argtypes=(w.HANDLE,ctypes.c_int,w.WPARAM,w.LPARAM);u.CallNextHookEx.restype=ctypes.c_ssize_t
        u.UnhookWindowsHookEx.argtypes=(w.HANDLE,);u.GetForegroundWindow.restype=w.HWND
        k.GetModuleHandleW.argtypes=(w.LPCWSTR,);k.GetModuleHandleW.restype=w.HMODULE
        k.GetCurrentThreadId.restype=w.DWORD
        self.thread_id=k.GetCurrentThreadId()
        def on_key(code,message,data):
            try:
                if code==0 and message in (0x100,0x101,0x104,0x105):
                    event=ctypes.cast(data,ctypes.POINTER(Key)).contents
                    if event.vkCode in self.state.CTRL or event.vkCode in (self.target_key,self.fire_key) or self.state.controls:
                        allowed,window,hero=self.scope()
                        foreground=u.GetForegroundWindow()
                        allowed=allowed and bool(window) and foreground==window
                        if event.flags&0x10:return u.CallNextHookEx(None,code,message,data)
                        down=message in (0x100,0x104);key=event.vkCode;fresh=key not in self.pressed
                        if down:self.pressed.add(key)
                        else:self.pressed.discard(key)
                        modifier=bool(self.state.controls) or any(u.GetAsyncKeyState(v)&0x8000 for v in (0x10,0x12,0x5b,0x5c))
                        ctrl=self.state.feed(key,down,(foreground,hero),allowed)
                        if allowed:
                            if self.target_key==0x11 and ctrl:self.emit(hero)
                            elif self.target_key!=0x11 and key==self.target_key and down and fresh and not modifier:self.emit(hero)
                            if self.fire_emit and key==self.fire_key and down and fresh and not modifier:self.fire_emit(hero)
            except Exception as error:self.error=type(error).__name__;self.state.reset()
            return u.CallNextHookEx(None,code,message,data)
        callback=callback_type(on_key);hook=None
        try:
            # Initialize the message queue before publishing the thread ID.
            message=w.MSG();u.PeekMessageW(ctypes.byref(message),None,0,0,0)
            hook=u.SetWindowsHookExW(13,callback,k.GetModuleHandleW(None),0)
            if not hook:raise ctypes.WinError(ctypes.get_last_error())
            self.ready=True
            while not self.stop_event.is_set():
                result=u.GetMessageW(ctypes.byref(message),None,0,0)
                if result<=0:break
                u.TranslateMessage(ctypes.byref(message));u.DispatchMessageW(ctypes.byref(message))
        except Exception as error:self.error=type(error).__name__+': '+str(error)[:120]
        finally:
            self.ready=False
            if hook:u.UnhookWindowsHookEx(hook)
