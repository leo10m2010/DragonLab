"""Native Windows frame, DPI and process lifetime helpers.

Tk owns client geometry; Windows owns moving, sizing and Snap. Cosmetic DWM
attributes never alter window styles or force a non-client frame calculation.
"""
import os,ctypes,logging

log=logging.getLogger(__name__)

def install_custom_frame(root):
    from window_chrome import install_custom_frame as install
    return install(root)

def begin_move(root,event=None):
    from window_chrome import begin_move as move
    return move(root,event)

def enable_high_dpi():
    """Source-run fallback, called before the first Tk/Win32 window exists."""
    if os.name!='nt':return 'platform'
    try:
        user=ctypes.WinDLL('user32',use_last_error=True)
        user.SetProcessDpiAwarenessContext.argtypes=[ctypes.c_void_p]
        user.SetProcessDpiAwarenessContext.restype=ctypes.c_int
        if user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):return 'per-monitor-v2'
        # A manifest/host may already have selected the process policy.
        if ctypes.get_last_error()==5:return 'already-configured'
    except (OSError,AttributeError):pass
    try:
        result=ctypes.WinDLL('shcore').SetProcessDpiAwareness(2)
        if result==0:return 'per-monitor'
        if result in (-2147024891,0x80070005):return 'already-configured'
    except (OSError,AttributeError):pass
    try:
        if ctypes.WinDLL('user32').SetProcessDPIAware():return 'system'
    except (OSError,AttributeError):pass
    log.warning('No se pudo establecer la política DPI de arranque.')
    return 'unavailable'

def native_window_handle(root):
    from ctypes import wintypes as w
    user=ctypes.WinDLL('user32',use_last_error=True)
    user.GetAncestor.argtypes=[w.HWND,w.UINT];user.GetAncestor.restype=w.HWND
    return user.GetAncestor(root.winfo_id(),2)

def native_window_style(root):
    from ctypes import wintypes as w
    user=ctypes.WinDLL('user32',use_last_error=True)
    get=getattr(user,'GetWindowLongPtrW',user.GetWindowLongW)
    get.argtypes=[w.HWND,ctypes.c_int];get.restype=ctypes.c_ssize_t
    return get(native_window_handle(root),-16)

def style_window(root):
    if os.name!='nt':return False
    try:
        from ctypes import wintypes as w
        # Tk creates/reparents its native frame in the idle mapping pass. DWM
        # attributes applied to the earlier child HWND do not reach that frame.
        root.update_idletasks()
        hwnd=native_window_handle(root)
        dwm=ctypes.WinDLL('dwmapi');dwm.DwmSetWindowAttribute.argtypes=[w.HWND,w.DWORD,ctypes.c_void_p,w.DWORD]
        dark=ctypes.c_int(1)
        result=dwm.DwmSetWindowAttribute(hwnd,20,ctypes.byref(dark),4)
        if result:result=dwm.DwmSetWindowAttribute(hwnd,19,ctypes.byref(dark),4)
        # Optional Windows 11 cosmetics. COLORREF is BGR; charcoal is neutral.
        for attribute,value in ((33,2),(34,0x00343434),(35,0x001B1B1B),(36,0x00EEEEEE)):
            setting=ctypes.c_uint(value);dwm.DwmSetWindowAttribute(hwnd,attribute,ctypes.byref(setting),4)
        if result:log.debug('La versión de Windows no admite la barra oscura DWM: %s',result)
        return result==0
    except (OSError,AttributeError) as error:
        log.debug('Se conserva el marco nativo sin personalización DWM: %s',error)
        return False

def monitor_work_area(root):
    """Work area of the window's monitor, retaining negative desktop coords."""
    if os.name=='nt':
        try:
            from ctypes import wintypes as w
            class MonitorInfo(ctypes.Structure):
                _fields_=[('cbSize',w.DWORD),('rcMonitor',w.RECT),('rcWork',w.RECT),('dwFlags',w.DWORD)]
            user=ctypes.WinDLL('user32',use_last_error=True)
            user.MonitorFromWindow.argtypes=[w.HWND,w.DWORD];user.MonitorFromWindow.restype=w.HANDLE
            user.GetMonitorInfoW.argtypes=[w.HANDLE,ctypes.POINTER(MonitorInfo)]
            info=MonitorInfo();info.cbSize=ctypes.sizeof(info)
            if user.GetMonitorInfoW(user.MonitorFromWindow(native_window_handle(root),2),ctypes.byref(info)):
                rect=info.rcWork;return rect.left,rect.top,rect.right,rect.bottom
        except (OSError,AttributeError):pass
    return root.winfo_vrootx(),root.winfo_vrooty(),root.winfo_vrootx()+root.winfo_vrootwidth(),root.winfo_vrooty()+root.winfo_vrootheight()

def place_in_work_area(x,y,width,height,bounds,margin=8):
    left,top,right,bottom=bounds
    width=max(1,min(width,right-left-margin*2));height=max(1,min(height,bottom-top-margin*2))
    x=max(left+margin,min(x,right-width-margin));y=max(top+margin,min(y,bottom-height-margin))
    return int(x),int(y),int(width),int(height)

def drag_handle(widget,root):
    """Compatibility helper: one native move request, never a geometry loop."""
    def down(event):
        if os.name!='nt':return
        from ctypes import wintypes as w
        user=ctypes.WinDLL('user32');user.ReleaseCapture()
        user.SendMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM]
        user.SendMessageW(native_window_handle(root),0x00A1,2,0)
        return 'break'
    widget.bind('<Button-1>',down)

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
