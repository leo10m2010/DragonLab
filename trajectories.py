"""Persistent, non-activating trajectory drawing above the game."""
import tkinter as tk,os,time,math,heapq
from tkinter import font as tkfont
from strength_guide import clickthrough
from native_paths import trail
from targeting import enemies,find_hero,player_role
from theme import GREEN,OBSERVED,BG,LINE,ORANGE,TEXT,MUTED


def actor_label_layout(actors,width,height,font_pixels,line_height=None):
    """Pack labels without changing actor IDs or dropping crowded targets.

    Each actor belongs to one label; a full field groups the overflow and keeps
    the selected actor's ID visible. Markers remain at their actual edge/point.
    """
    if not actors or width<=0 or height<=0:return []
    padding=min(6,width/4,height/4)
    header=min(58,height*.15)
    cell_width=220 if len(actors)<=6 else max(64,min(144,font_pixels*8+16))
    # Fallback fonts can be taller than the requested pixels. Include actual
    # line spacing and the label background/outline in each occupied row.
    row_height=max(24,(line_height if line_height is not None else font_pixels*2)+12)
    columns=max(1,int((width-2*padding)//cell_width));rows=max(1,int((height-header-2*padding)//row_height))
    cell_width=(width-2*padding)/columns;cell_height=(height-header-2*padding)/rows
    free=set(range(columns*rows));queue=list(range(columns*rows));groups={}
    for actor in actors:
        column=min(columns-1,max(0,int((actor['x']-padding)//cell_width)))
        row=min(rows-1,max(0,int((actor['y']-23-header-padding)//cell_height)))
        preferred=row*columns+column
        if preferred in free:cell=preferred
        else:
            while queue and queue[0] not in free:heapq.heappop(queue)
            cell=queue[0] if queue else preferred
        free.discard(cell);groups.setdefault(cell,[]).append(actor)
    labels=[]
    for cell,members in groups.items():
        members.sort(key=lambda actor:not actor['selected']);actor=members[0]
        text=actor['short']+' · +'+str(len(members)-1) if len(members)>1 else actor['short'] if len(actors)>6 else actor['label']
        labels.append({'key':actor['key'],'members':tuple(member['id'] for member in members),
            'x':padding+(cell%columns+.5)*cell_width,'y':header+padding+(cell//columns+.5)*cell_height,
            'width':cell_width,'text':text,'color':actor['color']})
    return labels

def projected_runs(path,project,x_scale,y_scale):
    """Project the supplied geometry without smoothing, skipping or bridging gaps."""
    runs=[];coords=[]
    for point in path:
        if not isinstance(point,(list,tuple)) or len(point)<2 or not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in point[:2]):
            if len(coords)>=4:runs.append(tuple(coords))
            coords=[];continue
        px,py=project(*point[:2])
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (px,py)):
            if len(coords)>=4:runs.append(tuple(coords))
            coords=[];continue
        coords.extend((px*x_scale,py*y_scale))
    if len(coords)>=4:runs.append(tuple(coords))
    return runs

class TrajectoryOverlay:
    def __init__(self,root):
        self.win=tk.Toplevel(root);self.win.withdraw();self.win.overrideredirect(True);self.win.attributes('-topmost',True)
        self.win.configure(bg='#010203');self.win.wm_attributes('-transparentcolor','#010203')
        self.canvas=tk.Canvas(self.win,bg='#010203',highlightthickness=0);self.canvas.pack(fill='both',expand=True)
        self.lines={};self.marks={};self.labels={};self.label_backgrounds={};self.key=None;self.visible=False
        self.line_stamps={};self.mark_stamps={};self.label_stamps={}
        self.win.update_idletasks();clickthrough(self.win)
        if os.name=='nt':self.win.wm_attributes('-disabled',True)
    def update(self,box,viewport,project,planned,observed,visible,players=(),target_id=None,hero_id=None,weather=(),style=None):
        style=style or {};aim_color=style.get('color',GREEN);line_width=style.get('width',2.5);font_size=style.get('font_size',11)
        if not visible or not box:
            if self.visible:self.win.withdraw();self.visible=False
            return
        x,y,right,bottom=box;vw,vh=viewport
        if right<=x or bottom<=y or vw<=0 or vh<=0:return
        # Keep all game controls below the field uncovered.
        height=round((bottom-y)*min(1,516/vh));width=right-x
        geometry=(x,y,width,height)
        if geometry!=self.key:
            self.win.geometry(f'{width}x{height}{x:+d}{y:+d}');self.key=geometry
        wanted={}
        for i,path in enumerate(planned):wanted['aim:'+str(i)]=(path,aim_color,line_width)
        for key,path in observed.items():wanted['shot:'+str(key)]=(path,style.get('observed_color',OBSERVED),max(1.5,line_width*.7))
        rendered=set()
        for base,(path,color,stroke) in wanted.items():
            for index,coords in enumerate(projected_runs(path,project,(right-x)/vw,(bottom-y)/vh)):
                key=base if index==0 else base+':segment:'+str(index);rendered.add(key)
                stamp=(coords,color,stroke)
                if key not in self.lines:self.lines[key]=self.canvas.create_line(*coords,fill=color,width=stroke,dash=(),capstyle='round',joinstyle='round')
                else:
                    previous=self.line_stamps.get(key)
                    if previous is None or previous[0]!=coords:self.canvas.coords(self.lines[key],*coords)
                    if previous is None or previous[1:]!=stamp[1:]:self.canvas.itemconfigure(self.lines[key],state='normal',fill=color,width=stroke,dash=(),capstyle='round',joinstyle='round')
                self.line_stamps[key]=stamp
        for key in list(self.lines):
            if key not in rendered:self.canvas.delete(self.lines.pop(key));self.line_stamps.pop(key,None)
        annotations={};labels={};outside_split=False
        for i,event in enumerate(style.get('events',[])):
            kind=event.get('kind')
            if kind not in ('underground','surface','split','mirror','enter','bounce','exit','force','lightning','black-force','unresolved-weather'):continue
            px,py=project(event['x'],event['y']);px*=width/vw;py*=(bottom-y)/vh
            if not 12<=px<=width-12 or not 30<=py<=height-25:
                if kind=='split' and py<30 and not outside_split:
                    outside_split=True;px=max(65,min(width-65,px))
                    labels['deployment-outside']=(px,43,f"↑ Apertura · {event.get('missiles',0)} misiles",aim_color)
                continue
            key='event:'+str(i);annotations[key]=([px-5,py,px+5,py,px,py-5,px,py+5],aim_color)
            labels[key]=(px,py-14,{'underground':'Entra','surface':'Sale','mirror':'Mirror · rebote','enter':'Tornado · entra','bounce':'Tornado · giro','exit':'Tornado · sale','unresolved-weather':'Aleatorio · sin revelar','force':'Fuerza','lightning':'Rayo','black-force':'Negro','split':f'{event.get("missiles",0)} misiles'}[kind],aim_color)
        numbers={p['id']:i for i,p in enumerate(enemies(players,hero_id),1)}
        if numbers:
            current=numbers.get(target_id,'—')
            labels['target-status']=(min(width/2,190),16,f'Objetivo {current}/{len(numbers)} · {style.get("target_key","Ctrl")}' if len(numbers)>1 else '1 enemigo vivo',GREEN)
        hero=find_hero(players,hero_id);actors=[]
        physical_font=max(10,min(15,round(font_size*max(.75,min(1.25,width/vw)))))
        if players and getattr(self,'actor_font_size',None)!=physical_font:
            self.actor_font_size=physical_font
            self.actor_font=tkfont.Font(self.canvas,family='Bahnschrift',size=-physical_font,weight='bold')
            self.actor_line_height=self.actor_font.metrics('linespace')
        for player_index,p in enumerate(players):
            if p.get('dead') or not all(isinstance(p.get(k),(int,float)) and not isinstance(p[k],bool) and math.isfinite(p[k]) for k in ('x','y')):continue
            px,py=project(p['x'],p['y']);px*=width/vw;py*=(bottom-y)/vh
            if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (px,py)):continue
            role=player_role(p,hero);selected=p.get('id')==target_id
            color=ORANGE if selected else GREEN if role=='hero' else '#7BCBDB' if role=='ally' else OBSERVED if role=='enemy' else MUTED
            number=numbers.get(p.get('id'));prefix='▶ ' if selected else ''
            text='TÚ' if role=='hero' else 'ALIADO' if role=='ally' else ('ENEMIGO ' if role=='enemy' else 'OBJETIVO ')+str(number or '')
            short=prefix+('TÚ' if role=='hero' else 'A' if role=='ally' else 'E' if role=='enemy' else '?')+(str(number) if number else str(player_index+1) if role!='hero' else '')
            outside=not (12<=px<=width-12 and 26<=py<=height-12)
            if outside:
                rawx,rawy=px,py;px=max(20,min(width-20,px));py=max(35,min(height-25,py))
                direction=math.atan2(rawy-py,rawx-px)
                dx,dy=math.cos(direction),math.sin(direction)
                annotations['player:'+str(p.get('id'))]=([px-10*dx,py-10*dy,px,py,px-7*dx-4*dy,py-7*dy+4*dx,px,py,px-7*dx+4*dy,py-7*dy-4*dx],color)
            else:annotations['player:'+str(p.get('id'))]=([px-8,py,px+8,py,px,py,px,py-12],color)
            actors.append({'id':p.get('id'),'key':'player:'+str(p.get('id')),'x':px,'y':py,'label':prefix+text+(' · fuera de vista' if outside else ''),'short':short,'color':color,'selected':selected})
        actor_layout=actor_label_layout(actors,width,height,physical_font,getattr(self,'actor_line_height',physical_font*2))
        self.actor_label_groups={item['key']:item['members'] for item in actor_layout}
        positions={actor['id']:actor for actor in actors}
        for item in actor_layout:
            key=item['key'];labels[key]=(item['x'],item['y'],item['text'],item['color'])
            for ident in item['members']:
                actor=positions[ident]
                if math.hypot(actor['x']-item['x'],actor['y']-item['y'])>35:
                    annotations['leader:'+str(ident)]=([actor['x'],actor['y'],item['x'],item['y']],actor['color'])
        if style.get('weather_name'):
            from gunbound_weather import weather_name
            labels['current-weather']=(width-150,16,'Clima: '+weather_name(style['weather_name']),OBSERVED)
        for i,w in enumerate(weather):
            kind=w.get('resolvedTypeId') or w.get('typeId');center=w.get('x')
            if w.get('unresolved'):kind=0
            if kind not in (0,3,4,5,7,8) or not isinstance(center,(int,float)):continue
            px,_=project(center,0);px*=width/vw
            if 0<=px<=width:
                color={0:'#b4bdc9',3:'#ffd36c',4:'#8fbfff',5:'#a9a0b5',7:'#d69cfc',8:'#7bcddb'}[kind]
                annotations['climate:'+str(i)]=([px,0,px,height],color)
                labels['climate:'+str(i)]=(px,43,{0:'Aleatorio · sin revelar',3:'Fuerza',4:'Rayo',5:'Negro · menos daño',7:'Mirror',8:'Tornado'}[kind],color)
        for key,(coords,color) in annotations.items():
            stamp=(tuple(coords),color,3 if key.startswith('player:') else 1.5)
            if key not in self.marks:self.marks[key]=self.canvas.create_line(*coords,fill=color,width=stamp[2],dash=(),capstyle='round',joinstyle='round')
            elif self.mark_stamps.get(key)!=stamp:
                self.canvas.coords(self.marks[key],*coords);self.canvas.itemconfigure(self.marks[key],fill=color,width=stamp[2])
            self.mark_stamps[key]=stamp
        for key in list(self.marks):
            if key not in annotations:self.canvas.delete(self.marks.pop(key));self.mark_stamps.pop(key,None)
        for key,(px,py,text,color) in labels.items():
            label_font=-physical_font if key.startswith('player:') else font_size
            stamp=(px,py,text,color,label_font,width)
            if key in self.labels and self.label_stamps.get(key)==stamp:continue
            if key not in self.labels:self.labels[key]=self.canvas.create_text(px,py,text=text,fill=color,font=('Bahnschrift',label_font,'bold'))
            else:self.canvas.coords(self.labels[key],px,py);self.canvas.itemconfigure(self.labels[key],text=text,fill=color,font=('Bahnschrift',label_font,'bold'))
            bounds=self.canvas.bbox(self.labels[key])
            if bounds:
                shift=max(0,4-bounds[0])-max(0,bounds[2]-(width-4))
                if shift:self.canvas.move(self.labels[key],shift,0);bounds=self.canvas.bbox(self.labels[key])
                l,t,r,b=bounds;l-=4;t-=2;r+=4;b+=2;radius=5
                shape=[l+radius,t,r-radius,t,r,t,r,b-radius,r,b,r-radius,b,l+radius,b,l,b,l,t+radius,l,t]
                if key not in self.label_backgrounds:self.label_backgrounds[key]=self.canvas.create_polygon(*shape,smooth=True,fill=BG,outline=LINE)
                else:self.canvas.coords(self.label_backgrounds[key],*shape)
                self.canvas.tag_lower(self.label_backgrounds[key],self.labels[key])
            self.label_stamps[key]=stamp
        for key in list(self.labels):
            if key not in labels:
                self.canvas.delete(self.labels.pop(key));self.canvas.delete(self.label_backgrounds.pop(key,None));self.label_stamps.pop(key,None)
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
