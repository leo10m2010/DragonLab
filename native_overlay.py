"""Rust overlay adapter. Coordinates are projected before crossing the C boundary."""
import ctypes,json,math,os,threading
from native_solver import library_path
from strength_guide import guide_power,PowerGuide
from targeting import enemies
from theme import GREEN,ORANGE,MUTED,TEXT,OBSERVED
from trajectories import TrajectoryOverlay,projected_runs

class NativeScene:
    def __init__(self):
        self.dll=ctypes.CDLL(str(library_path('dragonlab_overlay').resolve()),**({'winmode':0x1100} if os.name=='nt' else {}))
        self.dll.dl_overlay_update_json.argtypes=[ctypes.c_char_p,ctypes.c_size_t];self.dll.dl_overlay_update_json.restype=ctypes.c_int
        self.dll.dl_overlay_close.argtypes=[];self.dll.dl_overlay_close.restype=None
        self.dll.dl_overlay_status.argtypes=[];self.dll.dl_overlay_status.restype=ctypes.c_uint32
        self.frame={'box':[0,0,1,1],'viewport':[1,1],'planned':[],'observed':{},'players':[],'annotations':[],'style':{},'guide':{'visible':False},'visible':False}
        self.trajectory_visible=False;self.guide_visible=False;self.last=None;self.closed=False;self.owners=set()
    def submit(self):
        if self.closed:raise RuntimeError('Guía nativa cerrada')
        self.frame['visible']=self.trajectory_visible
        payload=json.dumps(self.frame,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
        if payload==self.last:
            if not self.dll.dl_overlay_status()&1:raise RuntimeError('El hilo de dibujo Rust se detuvo')
            return
        status=self.dll.dl_overlay_update_json(payload,len(payload))
        if status not in (0,1):raise RuntimeError('La guía Rust no aceptó el dibujo')
        self.last=payload
    def clear(self,part,owner):
        self.owners.discard(owner)
        if part=='trajectory':
            self.trajectory_visible=False
            for key,value in [('planned',[]),('observed',{}),('players',[]),('annotations',[])]:self.frame[key]=value
        else:self.guide_visible=False;self.frame['guide']={'visible':False}
        if self.owners:self.submit()
        else:self.close()
    def close(self):
        if not self.closed:self.dll.dl_overlay_close();self.closed=True
    def viewable(self):return not self.closed and bool(self.dll.dl_overlay_status()&2)

_scene=None;_unavailable=False;_error='';_lock=threading.Lock()
def scene():
    global _scene,_unavailable,_error
    if os.name!='nt' or os.environ.get('DRAGONLAB_DISABLE_RUST')=='1' or os.environ.get('DRAGONLAB_DISABLE_NATIVE_OVERLAY')=='1':return None
    with _lock:
        if _unavailable:return None
        if _scene is None or _scene.closed:
            try:_scene=NativeScene()
            except (OSError,AttributeError,RuntimeError):_unavailable=True;_error='Dibujo compatible activo';return None
        return _scene

def failed(native):
    global _unavailable,_error
    native.close();_unavailable=True;_error='Dibujo compatible activo'

def diagnostics():
    return {'renderer':'rust' if _scene and not _scene.closed else 'tk','available':not _unavailable,'error':_error}

def projected_paths(paths,project):
    output=[]
    for path in paths:
        for run in projected_runs(path,project,1,1):output.append([list(run[i:i+2]) for i in range(0,len(run),2)])
    return output

class NativeTrajectory:
    def __init__(self,root,native):self.root=root;self.native=native;self.visible=False;self.fallback=None;self.closed=False;native.owners.add(self)
    def update(self,box,viewport,project,planned,observed,visible,players=(),target_id=None,hero_id=None,weather=(),style=None):
        args=(box,viewport,project,planned,observed,visible)
        kwargs={'players':players,'target_id':target_id,'hero_id':hero_id,'weather':weather,'style':style}
        if self.fallback:return self.fallback.update(*args,**kwargs)
        try:
            frame=self.native.frame;style=style or {}
            self.visible=bool(visible and box)
            self.native.trajectory_visible=self.visible
            if not self.visible:
                frame.update(planned=[],observed={},players=[],annotations=[]);self.native.submit();return
            frame['box']=list(box);frame['viewport']=list(viewport);frame['style']=style
            frame['planned']=projected_paths(planned,project)
            frame['observed']={str(key)+':'+str(i):run for key,path in observed.items() for i,run in enumerate(projected_paths([path],project))}
            numbers={p['id']:i for i,p in enumerate(enemies(players,hero_id),1)}
            frame['players']=[]
            for player in players:
                if player.get('dead'):continue
                x,y=project(player['x'],player['y'])
                frame['players'].append({'id':player['id'],'x':x,'y':y,'hero':player['id']==hero_id,'selected':player['id']==target_id,'label':('▶ ' if player['id']==target_id else '')+'ENEMIGO '+str(numbers[player['id']]) if player['id'] in numbers else 'TÚ'})
            frame['annotations']=annotations(viewport,project,weather,style,numbers,target_id)
            self.native.submit()
        except (OSError,RuntimeError,ValueError,TypeError,KeyError):
            failed(self.native);self.fallback=TrajectoryOverlay(self.root);self.fallback.update(*args,**kwargs)
    def close(self):
        if self.closed:return
        self.closed=True
        self.native.owners.discard(self)
        self.visible=False
        if self.fallback:self.fallback.close()
        elif not self.native.closed:self.native.clear('trajectory',self)

def annotations(viewport,project,weather,style,numbers,target_id):
    """Annotations are viewport coordinates, just like paths and players."""
    items=[];vw,vh=viewport;field_height=min(vh,516)
    if numbers:
        label=f'Objetivo {numbers.get(target_id,"—")}/{len(numbers)} · {style.get("target_key","Ctrl")}' if len(numbers)>1 else '1 enemigo vivo'
        items.append({'x':min(vw/2,190),'y':16,'label':label,'color':GREEN})
    if style.get('weather_name'):
        from gunbound_weather import weather_name
        items.append({'x':vw-150,'y':16,'label':'Clima: '+weather_name(style['weather_name']),'color':OBSERVED})
    names={0:'Aleatorio · sin revelar',3:'Fuerza',4:'Rayo',5:'Negro · menos daño',7:'Mirror',8:'Tornado'}
    colors={0:'#b4bdc9',3:'#ffd36c',4:'#8fbfff',5:'#a9a0b5',7:'#d69cfc',8:'#7bcddb'}
    for weather_record in weather:
        kind=0 if weather_record.get('unresolved') else weather_record.get('resolvedTypeId') or weather_record.get('typeId')
        if kind not in names or not isinstance(weather_record.get('x'),(int,float)):continue
        x,_=project(weather_record['x'],0)
        items.append({'points':[[x,0],[x,field_height]],'x':x,'y':43,'label':names[kind],'color':colors[kind],'width':1.5})
    event_names={'underground':'Entra','surface':'Sale','mirror':'Mirror · rebote','enter':'Tornado · entra','bounce':'Tornado · giro','exit':'Tornado · sale','unresolved-weather':'Aleatorio · sin revelar','force':'Fuerza','lightning':'Rayo','black-force':'Negro'}
    for event in style.get('events',[]):
        kind=event.get('kind')
        if kind not in event_names and kind!='split':continue
        x,y=project(event['x'],event['y'])
        label=f'{event.get("missiles",0)} misiles' if kind=='split' else event_names[kind]
        if kind=='split' and y<30:y=43;label='↑ Apertura · '+label
        items.append({'points':[[x-5,y],[x+5,y],[x,y-5],[x,y+5]],'x':x,'y':y-14,'label':label,'color':style.get('color',GREEN)})
    return items

class NativeGuide:
    def __init__(self,root,start,end,native):
        self.root=root;self.native=native;self.fallback=None;self.win=self;self.points=(tuple(start),tuple(end));self.last=None;self.closed=False;native.owners.add(self)
    def winfo_viewable(self):return self.fallback.win.winfo_viewable() if self.fallback else self.native.guide_visible and self.native.viewable()
    def update_position(self,start,end):
        self.points=(tuple(start),tuple(end));self.last=None
        if self.fallback:self.fallback.update_position(start,end)
    def draw(self,result,maximum,updating=False):
        if self.fallback:return self.fallback.draw(result,maximum,updating)
        try:
            power=guide_power(result);a,b=self.points
            prefix=('Q: '+result['guide_notice'][:95]+' · ') if result.get('guide_notice') else (result.get('guide_label','')+' · ') if result.get('guide_label') else ''
            if power is None:label=result.get('guide_notice') or result.get('guide_message') or ('Calculando fuerza…' if updating else 'Sin potencia válida · revisa DragonLab')
            else:label=prefix+f'{"ACTUALIZANDO" if updating else "TERRENO BLOQUEA" if result.get("blocked") else "SUELTA EN"} {power:g} / {maximum:g} · {power/maximum*100:.1f}%'
            self.native.guide_visible=True
            self.native.frame['guide']={'visible':True,'bar':[*a,*b],'power':power,'maxPower':maximum,'label':label,'updating':bool(updating),'blocked':bool(result.get('blocked')),'measured':result.get('guide_state')=='measured'}
            self.native.submit()
        except (OSError,RuntimeError,ValueError,TypeError):
            failed(self.native);self.fallback=PowerGuide(self.root,*self.points);self.fallback.draw(result,maximum,updating)
    def close(self):
        if self.closed:return
        self.closed=True
        self.native.owners.discard(self)
        if self.fallback:self.fallback.close()
        elif not self.native.closed:self.native.clear('guide',self)

def create_overlay(root):
    native=scene()
    return NativeTrajectory(root,native) if native else TrajectoryOverlay(root)

def create_guide(root,start,end):
    native=scene()
    return NativeGuide(root,start,end,native) if native else PowerGuide(root,start,end)
