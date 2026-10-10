"""Automatic passive capture of the selected game page; no game input or storage."""
import base64,io,ctypes,os,time
from PIL import Image

GEOMETRY_JS = r'''(()=>{
 const box=e=>{if(!e)return null;let r=e.getBoundingClientRect();return r.width>1&&r.height>1?[r.x,r.y,r.width,r.height]:null};
 let game=document.getElementById('gameScreen'),bar=document.getElementById('powerMarkArea');
 let rect=box(game),power=box(bar),fill=document.getElementById('powerBar')?.getBoundingClientRect();if(power&&fill?.height>1){power[1]=fill.y;power[3]=fill.height;}let canvas=[...document.querySelectorAll('canvas')].map(box).filter(Boolean).sort((a,b)=>b[2]*b[3]-a[2]*a[3])[0];
 return {game:rect,bar:power,canvas,active:!!rect&&getComputedStyle(game).visibility!=='hidden',focused:document.hasFocus()&&document.visibilityState==='visible',dpr:devicePixelRatio,
 screen:[screenX,screenY],outer:[outerWidth,outerHeight],inner:[innerWidth,innerHeight],title:document.title,scroll:[scrollX,scrollY]};
})()'''

def content_origin(meta):
    """Physical screen origin of Chrome's render widget, including secondary monitors."""
    if os.name!='nt':return None
    u=ctypes.windll.user32
    from ctypes import wintypes as w
    cb=ctypes.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
    u.EnumWindows.argtypes=[cb,w.LPARAM];u.EnumChildWindows.argtypes=[w.HWND,cb,w.LPARAM];u.IsWindowVisible.argtypes=[w.HWND]
    u.GetWindowRect.argtypes=[w.HWND,ctypes.POINTER(w.RECT)]
    u.GetClassNameW.argtypes=[w.HWND,w.LPWSTR,ctypes.c_int]
    u.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,ctypes.c_int]
    found=[];parent=[None];dpr=meta.get('dpr',1);expected=meta['inner']
    def child(hwnd,_):
        name=ctypes.create_unicode_buffer(256);u.GetClassNameW(hwnd,name,256)
        if name.value=='Chrome_RenderWidgetHostHWND' and u.IsWindowVisible(hwnd):
            r=w.RECT();u.GetWindowRect(hwnd,ctypes.byref(r))
            if abs((r.right-r.left)-expected[0]*dpr)<8 and abs((r.bottom-r.top)-expected[1]*dpr)<8:found.append((r.left,r.top,parent[0]))
        return True
    child_cb=cb(child)
    def window(hwnd,_):
        title=ctypes.create_unicode_buffer(512);u.GetWindowTextW(hwnd,title,512)
        name=ctypes.create_unicode_buffer(128);u.GetClassNameW(hwnd,name,128)
        if name.value.startswith('Chrome_WidgetWin') and meta.get('title') and meta['title'] in title.value:
            parent[0]=int(hwnd)
            u.EnumChildWindows(hwnd,child_cb,0)
        return True
    window_cb=cb(window);u.EnumWindows(window_cb,0)
    u.GetForegroundWindow.restype=w.HWND
    focused=[entry for entry in found if entry[2]==u.GetForegroundWindow()]
    selected=focused[0] if len(focused)==1 else found[0] if len(found)==1 else None
    if selected:meta['windowHandle']=selected[2];return selected[:2]
    return None

def screen_geometry(meta,origin):
    if not meta.get('active') or origin is None:return None,None
    dpr=meta.get('dpr',1)
    def rect(b):return tuple(round(v) for v in (origin[0]+b[0]*dpr,origin[1]+b[1]*dpr,origin[0]+(b[0]+b[2])*dpr,origin[1]+(b[1]+b[3])*dpr))
    area=rect(meta['game']);bar=meta.get('bar')
    # The DOM's mark area covers the full 0..400 range, unlike the shrinking fill.
    points=None
    if bar:
        x,y,right,bottom=rect(bar);points=((x,round((y+bottom)/2)),(right,round((y+bottom)/2)))
    return area,points

class AutoCapture:
    def __init__(self,client,clock=time.monotonic):
        self.client=client;self.clock=clock;self.last_capture=-float('inf');self.capture_interval=3
    def read(self,capture=True):
        result=self.client.call('Runtime.evaluate',{'expression':GEOMETRY_JS,'returnByValue':True,'timeout':1500})
        meta=result.get('result',{}).get('value',{})
        origin=content_origin(meta) if meta.get('active') else None
        area,points=screen_geometry(meta,origin)
        out={'geometry':meta,'screen_box':area,'guide_points':points}
        now=self.clock()
        if capture and meta.get('active') and now-self.last_capture>=self.capture_interval:
            self.last_capture=now
            try:
                # Capture the existing view without a clip/surface resize of the game.
                image=self.client.call('Page.captureScreenshot',{'format':'jpeg','quality':72,'fromSurface':True,'captureBeyondViewport':False})
                viewport=Image.open(io.BytesIO(base64.b64decode(image['data']))).convert('RGB')
                x,y,width,height=meta['game'];iw,ih=meta['inner'];sx=viewport.width/iw;sy=viewport.height/ih
                box=tuple(round(v) for v in (max(0,x)*sx,max(0,y)*sy,min(iw,x+width)*sx,min(ih,y+height)*sy))
                if box[2]>box[0] and box[3]>box[1]:out['image']=viewport.crop(box)
            except Exception as e:
                # A missed image must not tear down live game data or the guide.
                out['capture_warning']=str(e)
        return out
