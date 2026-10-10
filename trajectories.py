"""Persistent, non-activating trajectory drawing above the game."""
import tkinter as tk,os,time,math
from strength_guide import clickthrough
from native_paths import trail
from targeting import enemies
GREEN='#72dfba';BLUE='#73bcff'

class TrajectoryOverlay:
    def __init__(self,root):
        self.win=tk.Toplevel(root);self.win.withdraw();self.win.overrideredirect(True);self.win.attributes('-topmost',True)
        self.win.configure(bg='#010203');self.win.wm_attributes('-transparentcolor','#010203')
        self.canvas=tk.Canvas(self.win,bg='#010203',highlightthickness=0);self.canvas.pack(fill='both',expand=True)
        self.lines={};self.marks={};self.labels={};self.key=None;self.visible=False
        self.win.update_idletasks();clickthrough(self.win)
        if os.name=='nt':self.win.wm_attributes('-disabled',True)
    def update(self,box,viewport,project,planned,observed,visible,players=(),target_id=None,hero_id=None,weather=(),style=None):
        style=style or {};aim_color=style.get('color',GREEN);line_width=style.get('width',2.5);font_size=style.get('font_size',11)
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
        for i,path in enumerate(planned):wanted['aim:'+str(i)]=(path,aim_color,True)
        for key,path in observed.items():wanted['shot:'+str(key)]=(path,BLUE,False)
        rendered=set()
        for key,(path,color,dashed) in wanted.items():
            coords=[]
            step=max(1,(len(path)+399)//400)
            for point in path[::step]:
                if len(point)<2 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in point[:2]):continue
                px,py=project(*point[:2]);coords.extend((px*(right-x)/vw,py*(bottom-y)/vh))
            if len(coords)<4:continue
            rendered.add(key)
            if key not in self.lines:self.lines[key]=self.canvas.create_line(*coords,fill=color,width=line_width,dash=(6,4) if dashed else ())
            else:self.canvas.coords(self.lines[key],*coords);self.canvas.itemconfigure(self.lines[key],state='normal',fill=color,width=line_width)
        for key in list(self.lines):
            if key not in rendered:self.canvas.delete(self.lines.pop(key))
        annotations={};labels={};outside_split=False
        for i,event in enumerate(style.get('events',[])):
            kind=event.get('kind')
            if kind not in ('underground','surface','split'):continue
            px,py=project(event['x'],event['y']);px*=width/vw;py*=(bottom-y)/vh
            if not 12<=px<=width-12 or not 30<=py<=height-25:
                if kind=='split' and py<30 and not outside_split:
                    outside_split=True;px=max(65,min(width-65,px))
                    labels['deployment-outside']=(px,43,f"↑ Apertura · {event.get('missiles',0)} misiles",aim_color)
                continue
            key='event:'+str(i);annotations[key]=([px-5,py,px+5,py,px,py-5,px,py+5],aim_color)
            labels[key]=(px,py-14,{'underground':'Entra','surface':'Sale','split':f'{event.get("missiles",0)} misiles'}[kind],aim_color)
        numbers={p['id']:i for i,p in enumerate(enemies(players,hero_id),1)}
        if numbers:
            current=numbers.get(target_id,'—')
            labels['target-status']=(min(width/2,190),16,f'Objetivo {current}/{len(numbers)} · {style.get("target_key","Ctrl")}' if len(numbers)>1 else '1 enemigo vivo',GREEN)
        for p in players:
            if p.get('dead') or not all(isinstance(p.get(k),(int,float)) for k in ('x','y')):continue
            px,py=project(p['x'],p['y']);px*=width/vw;py*=(bottom-y)/vh
            outside=not (12<=px<=width-12 and 26<=py<=height-12)
            if outside:
                if p.get('id') not in numbers and p.get('id')!=hero_id:continue
                rawx,rawy=px,py;px=max(20,min(width-20,px));py=max(35,min(height-25,py))
                direction=math.atan2(rawy-py,rawx-px)
                dx,dy=math.cos(direction),math.sin(direction)
                color='#ffb86c' if p.get('id')==target_id else '#ecf3f7'
                annotations['player:'+str(p.get('id'))]=([px-10*dx,py-10*dy,px,py,px-7*dx-4*dy,py-7*dy+4*dx,px,py,px-7*dx+4*dy,py-7*dy-4*dx],color)
                labels['player:'+str(p['id'])]=(px,py+13,(str(numbers[p['id']]) if p['id'] in numbers else 'Tú')+' fuera',color)
                continue
            color=GREEN if p.get('id')==hero_id else '#ffb86c' if p.get('id')==target_id else '#c4d1db'
            annotations['player:'+str(p.get('id'))]=([px-8,py,px+8,py,px,py,px,py-12],color)
            if p.get('id') in numbers:
                selected=p.get('id')==target_id
                labels['player:'+str(p['id'])]=(px,py-23,('▶ ' if selected else '')+str(numbers[p['id']]),'#ffb86c' if selected else '#ecf3f7')
        for i,w in enumerate(weather):
            kind=w.get('resolvedTypeId') or w.get('typeId');center=w.get('x')
            if kind not in (3,4,5,7,8) or not isinstance(center,(int,float)):continue
            px,_=project(center,0);px*=width/vw
            if 0<=px<=width:
                color={3:'#ffd36c',4:'#8fbfff',5:'#a9a0b5',7:'#d69cfc',8:'#7bcddb'}[kind]
                annotations['climate:'+str(i)]=([px,0,px,height],color)
                labels['climate:'+str(i)]=(px,16,{3:'Fuerza',4:'Rayo',5:'Negro · menos daño',7:'Mirror',8:'Tornado'}[kind],color)
        for key,(coords,color) in annotations.items():
            if key not in self.marks:self.marks[key]=self.canvas.create_line(*coords,fill=color,width=1.5,dash=(3,5) if key.startswith('climate:') else ())
            else:self.canvas.coords(self.marks[key],*coords);self.canvas.itemconfigure(self.marks[key],fill=color)
        for key in list(self.marks):
            if key not in annotations:self.canvas.delete(self.marks.pop(key))
        for key,(px,py,text,color) in labels.items():
            if key not in self.labels:self.labels[key]=self.canvas.create_text(px,py,text=text,fill=color,font=('Bahnschrift',font_size,'bold'))
            else:self.canvas.coords(self.labels[key],px,py);self.canvas.itemconfigure(self.labels[key],text=text,fill=color,font=('Bahnschrift',font_size,'bold'))
        for key in list(self.labels):
            if key not in labels:self.canvas.delete(self.labels.pop(key))
        if not self.visible:self.win.deiconify();self.visible=True
    def close(self):self.win.destroy()

class ObservedTrails:
    def __init__(self):self.paths={};self.seen={};self.measured={};self.fallback=set();self.render_stamps={}
    def update(self,shots,now=None):
        now=time.monotonic() if now is None else now
        for shot in shots:
            key=shot.get('id');x,y=shot.get('x'),shot.get('y')
            if shot.get('native') and key is not None and not shot.get('auxiliary'):
                label=str(key);buffer=self.measured.setdefault(label,[])
                if all(isinstance(v,(int,float)) and math.isfinite(v) for v in (x,y)):
                    if not buffer or math.dist(buffer[-1],(x,y))>.4:buffer.append((x,y))
                    self.measured[label]=buffer[-240:]
                stamp=(shot.get('elapsed'),shot.get('duration'),len(shot.get('jumps',[])))
                if self.render_stamps.get(label)==stamp and label in self.paths:self.seen[label]=now;continue
                self.render_stamps[label]=stamp
                # Keep native jump times; cap only the display sampling density.
                native=trail(shot,step=.04,max_points=400)
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
            if now-self.seen[key]>2:self.paths.pop(key);self.seen.pop(key);self.measured.pop(key,None);self.fallback.discard(key);self.render_stamps.pop(key,None)
        return dict(self.paths)
    def reset(self):self.paths.clear();self.seen.clear();self.measured.clear();self.fallback.clear();self.render_stamps.clear()
