"""Custom client frame with native Windows moving, sizing and state changes.

The caption styles remain intact. WM_NCCALCSIZE removes their visual area;
subclassing preserves Tk's own procedure and lifecycle. No layered/color-key
window or per-motion geometry manipulation is used.
"""
import ctypes,os

_frames={}

def edge_hit(rect,x,y,border=7):
    left,top,right,bottom=rect
    if not left<=x<right or not top<=y<bottom:return 0
    a=x<left+border;b=x>=right-border;c=y<top+border;d=y>=bottom-border
    return 13 if a and c else 14 if b and c else 16 if a and d else 17 if b and d else 10 if a else 11 if b else 12 if c else 15 if d else 1

class CustomFrame:
    def __init__(self,root):
        self.root=root;self.installed=False;self.rounded_size=None
        if os.name!='nt':return
        from ctypes import wintypes as w
        from desktop_shell import native_window_handle,style_window
        self.w=w;root.update_idletasks();self.hwnd=native_window_handle(root)
        self.minimum=tuple(root.minsize());self.user=ctypes.WinDLL('user32',use_last_error=True)
        self.comctl=ctypes.WinDLL('comctl32',use_last_error=True);self.dwm=ctypes.WinDLL('dwmapi')
        self.proc_type=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,w.HWND,w.UINT,w.WPARAM,w.LPARAM,ctypes.c_size_t,ctypes.c_size_t)
        self.comctl.SetWindowSubclass.argtypes=[w.HWND,self.proc_type,ctypes.c_size_t,ctypes.c_size_t];self.comctl.SetWindowSubclass.restype=w.BOOL
        self.comctl.RemoveWindowSubclass.argtypes=[w.HWND,self.proc_type,ctypes.c_size_t];self.comctl.RemoveWindowSubclass.restype=w.BOOL
        self.comctl.DefSubclassProc.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM];self.comctl.DefSubclassProc.restype=ctypes.c_ssize_t
        self.user.GetWindowRect.argtypes=[w.HWND,ctypes.POINTER(w.RECT)];self.user.IsZoomed.argtypes=[w.HWND]
        self.user.SetWindowPos.argtypes=[w.HWND,w.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.UINT]
        self.user.ReleaseCapture.argtypes=[];self.user.SendMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM]
        try:self.user.GetDpiForWindow.argtypes=[w.HWND];self.user.GetDpiForWindow.restype=w.UINT
        except AttributeError:pass
        self.dwm.DwmSetWindowAttribute.argtypes=[w.HWND,w.DWORD,ctypes.c_void_p,w.DWORD]
        corner=ctypes.c_int(2);self.native_rounding=self.dwm.DwmSetWindowAttribute(self.hwnd,33,ctypes.byref(corner),4)==0
        self.proc=self.proc_type(self.handle);self.subclass_id=0xD12A
        if not self.comctl.SetWindowSubclass(self.hwnd,self.proc,self.subclass_id,0):raise ctypes.WinError(ctypes.get_last_error())
        self.installed=True;_frames[self.hwnd]=self
        self.user.SetWindowPos(self.hwnd,None,0,0,0,0,0x0001|0x0002|0x0004|0x0020|0x0010)
        style_window(root)
        root.bind('<Destroy>',self.destroyed,add='+')

    def work_rect(self):
        from ctypes import wintypes as w
        class Info(ctypes.Structure):_fields_=[('cbSize',w.DWORD),('rcMonitor',w.RECT),('rcWork',w.RECT),('flags',w.DWORD)]
        self.user.MonitorFromWindow.argtypes=[w.HWND,w.DWORD];self.user.MonitorFromWindow.restype=w.HANDLE
        self.user.GetMonitorInfoW.argtypes=[w.HANDLE,ctypes.POINTER(Info)]
        info=Info();info.cbSize=ctypes.sizeof(info)
        if self.user.GetMonitorInfoW(self.user.MonitorFromWindow(self.hwnd,2),ctypes.byref(info)):return info.rcWork

    def handle(self,hwnd,msg,wp,lp,subclass_id,data):
        try:
            if msg==0x0083 and wp:  # NCCALCSIZE: preserve styles, replace non-client layout.
                if self.user.IsZoomed(hwnd):
                    work=self.work_rect()
                    if work:
                        rect=ctypes.cast(lp,ctypes.POINTER(self.w.RECT)).contents
                        rect.left=max(rect.left,work.left);rect.top=max(rect.top,work.top)
                        rect.right=min(rect.right,work.right);rect.bottom=min(rect.bottom,work.bottom)
                return 0
            if msg==0x0084:  # NCHITTEST: retain native edge/corner resize.
                rect=self.w.RECT();self.user.GetWindowRect(hwnd,ctypes.byref(rect))
                x=ctypes.c_short(lp&0xffff).value;y=ctypes.c_short((lp>>16)&0xffff).value
                border=0 if self.user.IsZoomed(hwnd) else max(6,round(7*(self.user.GetDpiForWindow(hwnd) if hasattr(self.user,'GetDpiForWindow') else 96)/96))
                return edge_hit((rect.left,rect.top,rect.right,rect.bottom),x,y,border)
            if msg==0x0024:  # GETMINMAXINFO: the minimum now describes full client dimensions.
                result=self.comctl.DefSubclassProc(hwnd,msg,wp,lp)
                points=ctypes.cast(lp,ctypes.POINTER(self.w.POINT*5)).contents
                points[3].x,points[3].y=self.minimum
                return result
            if msg==0x0005 and not self.native_rounding:self.round_fallback()
            if msg==0x0082:  # NCDESTROY: never leave a Python callback on a dead HWND.
                result=self.comctl.DefSubclassProc(hwnd,msg,wp,lp);self.detach();return result
        except (OSError,ValueError,AttributeError):
            # Native processing remains available if an optional cosmetic fails.
            pass
        return self.comctl.DefSubclassProc(hwnd,msg,wp,lp)

    def round_fallback(self):
        rect=self.w.RECT();self.user.GetWindowRect(self.hwnd,ctypes.byref(rect))
        size=(rect.right-rect.left,rect.bottom-rect.top,bool(self.user.IsZoomed(self.hwnd)))
        if size==self.rounded_size or size[0]<=0 or size[1]<=0:return
        self.rounded_size=size
        self.user.SetWindowRgn.argtypes=[self.w.HWND,self.w.HRGN,self.w.BOOL]
        if size[2]:self.user.SetWindowRgn(self.hwnd,None,True);return
        gdi=ctypes.WinDLL('gdi32');gdi.CreateRoundRectRgn.argtypes=[ctypes.c_int]*6;gdi.CreateRoundRectRgn.restype=self.w.HRGN
        gdi.DeleteObject.argtypes=[self.w.HGDIOBJ]
        region=gdi.CreateRoundRectRgn(0,0,size[0]+1,size[1]+1,18,18)
        if region and not self.user.SetWindowRgn(self.hwnd,region,True):gdi.DeleteObject(region)

    def begin_move(self,event=None):
        if self.installed:
            self.user.ReleaseCapture();self.user.SendMessageW(self.hwnd,0x00A1,2,0)
        return 'break'

    def destroyed(self,event):
        if event.widget is self.root:self.detach()

    def detach(self):
        if self.installed:
            self.installed=False;self.comctl.RemoveWindowSubclass(self.hwnd,self.proc,self.subclass_id);_frames.pop(self.hwnd,None)

def install_custom_frame(root):
    existing=getattr(root,'_dragonlab_frame',None)
    if existing and existing.installed:return existing
    frame=CustomFrame(root);root._dragonlab_frame=frame;return frame

def begin_move(root,event=None):
    frame=getattr(root,'_dragonlab_frame',None)
    return frame.begin_move(event) if frame else 'break'

def tool_chrome(window,title,icon='settings',close=None):
    """Shared compact utility title bar; actions are native window operations."""
    existing=getattr(window,'_tool_header',None)
    if existing and existing.winfo_exists():return existing
    import tkinter as tk
    from icons import Icon,IconButton
    from theme import BG,TEXT,MUTED,LINE,FONT
    previous=next((child for child in window.winfo_children() if child.winfo_manager()),None)
    bar=tk.Frame(window,bg=BG);window._tool_header=bar
    options={'side':'top','fill':'x','padx':12,'pady':(6,6)}
    if previous:options['before']=previous
    bar.pack(**options)
    drag=tk.Frame(bar,bg=BG);drag.pack(side='left',fill='x',expand=True)
    mark=Icon(drag,icon,size=16);mark.pack(side='left',padx=(6,8))
    label=tk.Label(drag,text=title,bg=BG,fg=TEXT,font=(FONT,-15,'bold'));label.pack(side='left',pady=7)
    def maximize():
        try:window.state('normal' if window.state()=='zoomed' else 'zoomed')
        except tk.TclError:window.attributes('-zoomed',not bool(window.attributes('-zoomed')))
        sync()
    def sync(event=None):
        if event is None or event.widget is window:max_button.configure(icon='restore' if window.state()=='zoomed' else 'maximize')
    close_action=close or window.destroy
    for name,callback in (('minimize',window.iconify),('maximize',maximize),('close',close_action)):
        button=IconButton(bar,icon=name,icon_size=14,command=callback,bg=BG,fg=MUTED,padx=8,pady=6)
        button.pack(side='left',padx=(0,2))
        if name=='maximize':max_button=button
    for widget in (drag,mark,label):
        widget.bind('<ButtonPress-1>',lambda event:begin_move(window,event))
        widget.bind('<Double-Button-1>',lambda event:maximize())
    window.bind('<Configure>',sync,add='+')
    install_custom_frame(window)
    return bar
