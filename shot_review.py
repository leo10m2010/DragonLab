"""Compare independent predictions with numeric native shot paths."""
import math,time,json,pathlib
from dataclasses import replace
from physics_extensions import trajectory
from native_paths import position
from calibration_book import mobile_name
from launch_geometry import muzzle_offset
from shot_attribution import attributed_start

def interpolate(path,t):
    if not path:return None
    if t<=path[0][2]:return path[0][:2]
    for a,b in zip(path,path[1:]):
        if a[2]<=t<=b[2]:
            w=(t-a[2])/max(1e-9,b[2]-a[2]);return tuple(a[k]+w*(b[k]-a[k]) for k in (0,1))
    return path[-1][:2]

class ShotReview:
    def __init__(self,path):
        self.path=pathlib.Path(path);self.pending={};self.seen=set();self.records=[];self.latest=None
        try:self.records=json.loads(self.path.read_text(encoding='utf-8')).get('records',[])[-48:];self.latest=self.records[-1] if self.records else None
        except (OSError,ValueError,TypeError):pass
    def observe(self,state,settings):
        if state.get('status')!='live':self.pending.clear();return
        players=state.get('players',[]);hero=next((p for p in players if p.get('id')==state.get('heroId')),None)
        if not hero:return
        for shot in state.get('shots',[]):
            if not shot.get('native') or shot.get('auxiliary'):continue
            key=str(shot['id'])+':'+str(shot['start']);delay=shot.get('delay',0)
            if key in self.seen:continue
            if key not in self.pending:
                if delay:
                    parent=next((p for p in self.pending.values() if p['mobile']=='NAK' and p['shot']==1 and p['native_duration']==delay),None)
                    if shot.get('bulletId')!=36 or not parent:continue
                    info={**parent,'phase':'Salida de Nak','errors':[]}
                else:
                    attribution=attributed_start(state,shot)
                    if not attribution or not attribution['learnable'] or mobile_name(hero.get('mobile'))!=settings.mobile or attribution['shot']!=settings.selected_shot:continue
                    if not isinstance(shot.get('elapsed'),(int,float)) or shot['elapsed']>600:continue
                    distances=sorted((math.hypot(p['x']-shot['start'][0],p['y']-shot['start'][1]),p['id']) for p in players if all(isinstance(p.get(k),(int,float)) for k in ('x','y')))
                    if not distances or distances[0][1]!=hero['id'] or distances[0][0]>90 or len(distances)>1 and distances[1][0]-distances[0][0]<60:continue
                    power=attribution['power']
                    if not isinstance(power,(int,float)) or not 1<=power<=400:continue
                    snapshot=replace(settings,hero_x=hero['x'],hero_y=hero['y'],angle=hero['angle'],look=hero['look'],body_angle=hero.get('body',0),launch_offset=muzzle_offset(hero,settings.mobile,settings.selected_shot),wind=state['wind'],wind_angle=state['windAngle'],environment=dict(settings.environment))
                    info={'mobile':snapshot.mobile,'shot':snapshot.selected_shot,'power':power,'path':trajectory(snapshot,power)['projectile_paths'][0],'phase':'Guía' if snapshot.mobile=='KALSIDDON' else 'Entrada en tierra' if snapshot.mobile=='NAK' and snapshot.selected_shot==1 else 'Tiro','errors':[],'native_duration':shot.get('duration')}
                info['observed_at']=time.monotonic();self.pending[key]=info
            info=self.pending[key];elapsed=shot.get('elapsed');duration=shot.get('duration')
            if not all(isinstance(v,(int,float)) for v in (elapsed,duration)) or elapsed<delay:continue
            seconds=(elapsed-delay)/1000;t=elapsed/1000 if delay else seconds
            observed=position(shot,min(seconds,duration/1000));predicted=interpolate(info['path'],t)
            if predicted:info['errors'].append(math.dist(predicted,observed));info['errors']=info['errors'][-100:]
            if 'saved' not in info:
                actual=position(shot,duration/1000);end=interpolate(info['path'],(duration+delay)/1000)
                if end:
                    record={k:info[k] for k in ('mobile','shot','power','phase')};record.update(source='native-shot-path',endpoint_error=round(math.dist(end,actual),2),updated=time.time())
                    self.records=(self.records+[record])[-48:];self.latest=record;info['saved']=record
                    from local_storage import atomic_write
                    atomic_write(self.path,json.dumps({'schema':1,'records':self.records},indent=2).encode())
        for key,info in list(self.pending.items()):
            if time.monotonic()-info.get('observed_at',0)>8:self.seen.add(key);self.pending.pop(key,None)
        while len(self.pending)>64:
            key=next(iter(self.pending));self.seen.add(key);self.pending.pop(key)
        if len(self.seen)>4096:self.seen=set(list(self.seen)[-2048:])
