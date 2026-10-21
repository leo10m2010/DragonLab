"""Bounded online action memory; reward is endpoint proximity, never claimed damage."""
import json,math,hashlib,time
from pathlib import Path
from local_storage import atomic_write
from calibration_book import mobile_name

def context(mobile,origin,target,wind,wind_angle):
    values=[*origin,*target,wind,wind_angle]
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in values):raise ValueError('Contexto no finito')
    if not mobile_name(mobile) or wind<0:raise ValueError('Carro o viento inválido')
    dx=target[0]-origin[0];dy=target[1]-origin[1]
    return ':'.join(map(str,(mobile_name(mobile),min(10,int(wind//10)),int((wind_angle%360)//45),min(10,int(math.hypot(dx,dy)//250)),1 if dx>=0 else -1,0 if abs(dy)<50 else 1 if dy>0 else -1)))

class ActionMemory:
    def __init__(self,path,limit=512):
        self.path=Path(path);self.limit=limit;self.cells={};self.seen=[]
        try:
            data=json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data,dict):return
            if data.get('schema')==1:
                cells=data.get('cells',{})
                if isinstance(cells,dict):
                    self.cells=dict((k,c) for k,c in list(cells.items())[-limit:] if isinstance(c,dict) and isinstance(c.get('context'),str) and c.get('shot') in (0,1,2) and isinstance(c.get('angle'),(int,float)) and math.isfinite(c['angle']) and -180<=c['angle']<=180 and isinstance(c.get('count'),int) and 1<=c['count']<=200 and isinstance(c.get('mean'),(int,float)) and math.isfinite(c['mean']) and 0<=c['mean']<=1)
                if isinstance(data.get('seen'),list):self.seen=[v for v in data['seen'][-256:] if isinstance(v,str)]
        except (OSError,ValueError,TypeError):pass
    def learn(self,probe,release,feedback):
        lab=release.get('learner') or release.get('lab') or {};miss=feedback.get('target_distance')
        if lab.get('action','apuntar')=='abrir paso' or not lab.get('target') or not isinstance(miss,(int,float)) or not math.isfinite(miss) or miss<0:return False
        angle=lab.get('angle');origin=(release.get('x'),release.get('y'));shot=release.get('shot')
        if not isinstance(angle,(int,float)) or not math.isfinite(angle) or shot not in (0,1,2):return False
        try:bucket=context(probe['mobile'],origin,lab['target'],release.get('wind'),release.get('windAngle'))
        except (ValueError,TypeError,KeyError):return False
        distance=math.dist(origin,lab['target'])
        if distance<60:return False
        ident=hashlib.sha256(json.dumps([probe.get('turn_serial'),origin,release.get('power'),release.get('wind'),lab['target'],feedback.get('observed_end')],sort_keys=True).encode()).hexdigest()[:24]
        if ident in self.seen:return False
        self.seen=(self.seen+[ident])[-256:]
        key=bucket+':'+str(shot)+':'+str(round(angle/10)*10)
        previous=self.cells.get(key,{});count=min(200,previous.get('count',0)+1);reward=max(0,1-miss/distance)
        self.cells.pop(key,None)
        self.cells[key]={'context':bucket,'shot':shot,'angle':round(angle/10)*10,'count':count,'mean':previous.get('mean',0)+(reward-previous.get('mean',0))/count,'source':'native-endpoint-distance','updated':time.time()}
        self.cells=dict(list(self.cells.items())[-self.limit:])
        atomic_write(self.path,json.dumps({'schema':1,'cells':self.cells,'seen':self.seen},allow_nan=False).encode());return True
    def recommend(self,probe,state,available):
        hero=next((p for p in state.get('players',[]) if p.get('id')==state.get('heroId')),None)
        if not hero:return probe
        enemies=[p for p in state.get('players',[]) if p.get('id')!=hero['id'] and not p.get('dead') and (hero.get('team') is None or p.get('team')!=hero['team'])]
        try:
            target=min(enemies,key=lambda p:math.dist((hero['x'],hero['y']),(p['x'],p['y'])))
            bucket=context(probe['mobile'],(hero['x'],hero['y']),(target['x'],target['y']),state.get('wind'),state.get('windAngle'))
        except (ValueError,TypeError,KeyError):return probe
        choices=[c for c in self.cells.values() if c.get('context')==bucket and c.get('count',0)>=2 and c.get('shot') in available and isinstance(c.get('mean'),(int,float)) and 0<=c['mean']<=1]
        if not choices:return probe
        best=max(choices,key=lambda c:c['mean']-.1/math.sqrt(c['count']))
        return {**probe,'shot':best['shot'],'angle':best['angle'],'purpose':'mejor alcance observado'}
