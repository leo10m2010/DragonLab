"""Windows chrome and process lifetime helpers for the local launcher."""
import os,ctypes

def style_window(root):
    if os.name!='nt':return
    try:
        from ctypes import wintypes as w
        u=ctypes.WinDLL('user32',use_last_error=True)
        u.GetAncestor.argtypes=[w.HWND,w.UINT];u.GetAncestor.restype=w.HWND
        hwnd=u.GetAncestor(root.winfo_id(),2)
        get=u.GetWindowLongPtrW;put=u.SetWindowLongPtrW
        get.argtypes=[w.HWND,ctypes.c_int];get.restype=ctypes.c_ssize_t
        put.argtypes=[w.HWND,ctypes.c_int,ctypes.c_ssize_t];put.restype=ctypes.c_ssize_t
        put(hwnd,-16,get(hwnd,-16)&~(0x00C00000|0x00040000))
        u.SetWindowPos.argtypes=[w.HWND,w.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.UINT]
        u.SetWindowPos(hwnd,None,0,0,0,0,0x27)
        dwm=ctypes.WinDLL('dwmapi');dwm.DwmSetWindowAttribute.argtypes=[w.HWND,w.DWORD,ctypes.c_void_p,w.DWORD]
        rounded=ctypes.c_int(2);dwm.DwmSetWindowAttribute(hwnd,33,ctypes.byref(rounded),4)
        border=ctypes.c_uint(0xfffffffe);dwm.DwmSetWindowAttribute(hwnd,34,ctypes.byref(border),4)
        dark=ctypes.c_int(1);dwm.DwmSetWindowAttribute(hwnd,20,ctypes.byref(dark),4)
    except (OSError,AttributeError):pass

def drag_handle(widget,root):
    def down(e):root._drag=(e.x_root-root.winfo_x(),e.y_root-root.winfo_y())
    def move(e):
        if hasattr(root,'_drag'):
            x=max(-root.winfo_width()+80,min(root.winfo_screenwidth()-80,e.x_root-root._drag[0]))
            y=max(0,min(root.winfo_screenheight()-45,e.y_root-root._drag[1]))
            root.geometry(f'{x:+d}{y:+d}')
    widget.bind('<Button-1>',down);widget.bind('<B1-Motion>',move)

class SingleInstance:
    def __init__(self,name):
        self.handle=None;self.primary=True
        if os.name!='nt':return
        from ctypes import wintypes as w
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.CreateMutexW.argtypes=[ctypes.c_void_p,w.BOOL,w.LPCWSTR];self.kernel.CreateMutexW.restype=w.HANDLE
        self.kernel.CloseHandle.argtypes=[w.HANDLE]
        ctypes.set_last_error(0);self.handle=self.kernel.CreateMutexW(None,False,'Local\\'+name)
        if not self.handle:raise OSError('No se pudo proteger la instancia de DragonLab.')
        self.primary=ctypes.get_last_error()!=183
    def close(self):
        if self.handle:self.kernel.CloseHandle(self.handle);self.handle=None

def restore_launcher():
    if os.name!='nt':return
    from ctypes import wintypes as w
    u=ctypes.WinDLL('user32')
    u.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,ctypes.c_int]
    u.ShowWindow.argtypes=[w.HWND,ctypes.c_int];u.SetForegroundWindow.argtypes=[w.HWND]
    @ctypes.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
    def visit(hwnd,param):
        text=ctypes.create_unicode_buffer(300);u.GetWindowTextW(hwnd,text,300)
        if text.value.startswith('DragonLab ·') and 'Launcher' in text.value:
            u.ShowWindow(hwnd,9);u.SetForegroundWindow(hwnd);return False
        return True
    u.EnumWindows(visit,0)
