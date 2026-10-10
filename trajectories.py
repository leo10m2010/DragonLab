"""Persistent, non-activating trajectory drawing above the game."""
import tkinter as tk,os,time,math
from strength_guide import clickthrough
from native_paths import trail
GREEN='#72dfba';BLUE='#73bcff'

class TrajectoryOverlay:
    def __init__(self,root):
        self.win=tk.Toplevel(root);self.win.withdraw();self.win.overrideredirect(True);self.win.attributes('-topmost',True)
        self.win.configure(bg='#010203');self.win.wm_attributes('-transparentcolor','#010203')
        self.canvas=tk.Canvas(self.win,bg='#010203',highlightthickness=0);self.canvas.pack(fill='both',expand=True)
        self.lines={};self.marks={};self.key=None;self.visible=False
        self.win.update_idletasks();clickthrough(self.win)
        if os.name=='nt':self.win.wm_attributes('-disabled',True)
    def update(self,box,viewport,project,planned,observed,visible,players=(),target_id=None,hero_id=None,weather=()):
        if not visible or not box:
            if self.visible:self.win.withdraw();self.visible=False
            return
        x,y,right,bottom=box;vw,vh=viewport
        if right<=x or bottom<=y:return
        # Keep all game controls below the field uncovered.
        height=round((bottom-y)*min(1,516/vh));width=right-x
        geometry=(x,y,width,height)
        if geometry!=self.key:
            self.win.geometry(f'{width}x{height}{x:+d}{y:+d}');self.key=geometry
        wanted={}
        for i,path in enumerate(planned):wanted['aim:'+str(i)]=(path,GREEN,True)
        for key,path in observed.items():wanted['shot:'+str(key)]=(path,BLUE,False)
        for key,(path,color,dashed) in wanted.items():
            coords=[]
            step=max(1,(len(path)+399)//400)
            for point in path[::step]:
                if len(point)<2 or not all(math.isfinite(v) for v in point[:2]):continue
                px,py=project(*point[:2]);coords.extend((px*(right-x)/vw,py*(bottom-y)/vh))
            if len(coords)<4:continue
            if key not in self.lines:self.lines[key]=self.canvas.create_line(*coords,fill=color,width=2.5,dash=(6,4) if dashed else ())
            else:self.canvas.coords(self.lines[key],*coords);self.canvas.itemconfigure(self.lines[key],state='normal')
        for key in list(self.lines):
            if key not in wanted or len(wanted[key][0])<2:self.canvas.delete(self.lines.pop(key))
        annotations={}
        for p in players:
            if p.get('dead') or not all(isinstance(p.get(k),(int,float)) for k in ('x','y')):continue
            px,py=project(p['x'],p['y']);px*=width/vw;py*=(bottom-y)/vh
            if not (0<=px<=width and 0<=py<=height):continue
            color=GREEN if p.get('id')==hero_id else '#ffb86c' if p.get('id')==target_id else '#c4d1db'
            annotations['player:'+str(p.get('id'))]=([px-8,py,px+8,py,px,py,px,py-12],color)
        for i,w in enumerate(weather):
            kind=w.get('resolvedTypeId') or w.get('typeId');center=w.get('x')
            if kind not in (7,8) or not isinstance(center,(int,float)):continue
            px,_=project(center,0);px*=width/vw
            if 0<=px<=width:annotations['climate:'+str(i)]=([px,0,px,height], '#d69cfc' if kind==7 else '#7bcddb')
        for key,(coords,color) in annotations.items():
            if key not in self.marks:self.marks[key]=self.canvas.create_line(*coords,fill=color,width=1.5,dash=(3,5) if key.startswith('climate:') else ())
            else:self.canvas.coords(self.marks[key],*coords);self.canvas.itemconfigure(self.marks[key],fill=color)
        for key in list(self.marks):
            if key not in annotations:self.canvas.delete(self.marks.pop(key))
        if not self.visible:self.win.deiconify();self.visible=True
    def close(self):self.win.destroy()

class ObservedTrails:
    def __init__(self):self.paths={};self.seen={};self.measured={};self.fallback=set()
    def update(self,shots,now=None):
        now=time.monotonic() if now is None else now
        for shot in shots:
            key=shot.get('id');x,y=shot.get('x'),shot.get('y')
            if shot.get('native') and key is not None and not shot.get('auxiliary'):
                label=str(key);buffer=self.measured.setdefault(label,[])
                if all(isinstance(v,(int,float)) and math.isfinite(v) for v in (x,y)):
                    if not buffer or math.dist(buffer[-1],(x,y))>.4:buffer.append((x,y))
                    self.measured[label]=buffer[-240:]
                native=trail(shot)
                # Slow, homing or changing bullets can override the simple
                # server arc; their displayed positions remain authoritative.
                if native and buffer and math.dist(native[-1],buffer[-1])>3:self.fallback.add(label)
                if label in self.fallback and buffer:self.paths[label]=list(buffer);self.seen[label]=now;continue
                if native:self.paths[label]=native;self.seen[label]=now;continue
            if key is None or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (x,y)):continue
            path=self.paths.setdefault(str(key),[])
            if not path or math.dist(path[-1],(x,y))>.4:path.append((x,y))
            self.paths[str(key)]=path[-240:];self.seen[str(key)]=now
        for key in list(self.paths):
            if now-self.seen[key]>2:self.paths.pop(key);self.seen.pop(key);self.measured.pop(key,None);self.fallback.discard(key)
        return dict(self.paths)
    def reset(self):self.paths.clear();self.seen.clear();self.measured.clear();self.fallback.clear()
