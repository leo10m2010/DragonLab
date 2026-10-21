"""Observe health windows and completed 1v1 outcomes; unknown is never a loss."""
import json,math,time,uuid
from local_storage import atomic_write

def health(player):
    hp=player.get('hp');shield=player.get('shield')
    if not all(isinstance(v,(int,float)) and math.isfinite(v) and v>=0 for v in (hp,shield)):return None
    return hp+shield

class BattleMetrics:
    def __init__(self,path,callback=lambda row:None):
        self.path=path;self.callback=callback;self.pending=[];self.games=[];self.windows=[];self.game=None;self.last=None
    def save(self):
        atomic_write(self.path,json.dumps({'schema':1,'games':self.games[-100:],'health_windows':self.windows[-300:]},allow_nan=False).encode())
    def begin(self,state):
        self.game={'id':uuid.uuid4().hex,'hero':state.get('heroId'),'outcome':'unknown','source':None,'started':time.time()};self.last=state
    def note(self,release,plan,state,token):
        if not self.game:self.begin(state)
        hero=release['hero'];target=plan.get('target_id')
        players=state.get('players',[])
        if target is None and plan.get('target'):
            others=[p for p in players if str(p.get('id'))!=str(hero) and not p.get('dead')]
            if others:target=min(others,key=lambda p:(p['x']-plan['target'][0])**2+(p['y']-plan['target'][1])**2)['id']
        before=release.get('health_before') or {str(p['id']):health(p) for p in players}
        durations=[s.get('duration',0)/1000 for s in state.get('shots',[]) if s.get('native')]
        self.pending.append({'token':token,'hero':hero,'target':target,'turn':release.get('turn_serial'),'before':before,'expires':time.monotonic()+min(20,max(durations,default=2)+2),'ambiguous':False,'baseline':release.get('baseline',[])})
    def observe(self,state):
        if state.get('status')!='live':return
        if not self.game:
            if state.get('over'):return
            self.begin(state)
        self.last=state;players=state.get('players',[])
        for item in list(self.pending):
            # If another shooter's family is already present, HP attribution is unknown.
            for shot in state.get('shots',[]):
                from shot_attribution import identity
                if identity(shot) in item.get('baseline',[]):continue
                start=shot.get('start')
                if not shot.get('native') or shot.get('auxiliary') or not isinstance(start,list) or len(start)<2:continue
                near=sorted((math.hypot(p['x']-start[0],p['y']-start[1]),str(p['id'])) for p in players if isinstance(p.get('x'),(int,float)) and isinstance(p.get('y'),(int,float)))
                if near and near[0][0]<90 and near[0][1]!=str(item['hero']):item['ambiguous']=True
            serial=state.get('turnSerial');active=state.get('activePlayer')
            finished=state.get('over') or time.monotonic()>=item['expires'] or serial is not None and serial!=item['turn'] and active not in (None,-1)
            if finished:self.complete(item,state)
        if state.get('over'):self.end(state)
    def complete(self,item,state=None):
        if item not in self.pending:return
        self.pending.remove(item);after={str(p['id']):health(p) for p in (state or {}).get('players',[])}
        target=str(item['target']);before=item['before'].get(target);current=after.get(target)
        known=not item['ambiguous'] and before is not None and current is not None
        row={'token':item['token'],'game':self.game['id'] if self.game else None,'known':known,'enemy_health_drop':max(0,before-current) if known else None,'attribution':'own-shot-window' if known else 'unknown','confirmed_impact':False}
        self.windows.append(row);self.windows=self.windows[-300:];self.callback(row);self.save()
    def end(self,state=None):
        if not self.game:return
        state=state or self.last or {}
        for item in list(self.pending):self.complete(item,state if state.get('over') else None)
        hero=next((p for p in state.get('players',[]) if str(p.get('id'))==str(self.game['hero'])),None)
        enemies=[p for p in state.get('players',[]) if str(p.get('id'))!=str(self.game['hero'])]
        if state.get('over') and hero and len(enemies)==1:
            if hero.get('dead') and not enemies[0].get('dead'):self.game.update(outcome='loss',source='native-survival-at-gameover')
            elif not hero.get('dead') and enemies[0].get('dead'):self.game.update(outcome='win',source='native-survival-at-gameover')
        self.game['finished']=time.time();self.games.append(self.game);self.games=self.games[-100:];self.game=None;self.save()
    def summary(self):
        wins=sum(g['outcome']=='win' for g in self.games);losses=sum(g['outcome']=='loss' for g in self.games)
        return {'wins':wins,'losses':losses,'unknown_results':len(self.games)-wins-losses,'win_rate':round(wins*100/(wins+losses),1) if wins+losses else None,'known_health_windows':sum(w['known'] for w in self.windows)}
