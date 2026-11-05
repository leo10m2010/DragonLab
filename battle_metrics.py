"""Observe health windows and completed 1v1 outcomes; unknown is never a loss."""
import json,math,time,uuid
from local_storage import atomic_write

def health(player):
    if not isinstance(player,dict):return None
    hp=player.get('hp');shield=player.get('shield')
    if not all(health_value(v) is not None for v in (hp,shield)):return None
    return health_value(hp+shield)


def health_value(value):
    try:return value if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>=0 else None
    except OverflowError:return None


def reward_projectile_unknown(shot,hero,players):
    """Unresolved/foreign projectiles cannot supply a policy reward."""
    if not isinstance(shot,dict) or shot.get('native') is not True:return True
    metadata=shot.get('metadata') or {}
    if not isinstance(metadata,dict):return True
    a,b=metadata.get('player_n'),metadata.get('player')
    if a is not None and b is not None and str(a)!=str(b):return True
    owner=a if a is not None else b
    if owner is not None:return isinstance(owner,bool) or str(owner)!=str(hero)
    start=shot.get('start')
    if shot.get('auxiliary') or not isinstance(start,list) or len(start)<2:return True
    if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in start[:2]):return True
    near=sorted((math.hypot(p['x']-start[0],p['y']-start[1]),str(p['id'])) for p in players if all(isinstance(p.get(k),(int,float)) and not isinstance(p[k],bool) and math.isfinite(p[k]) for k in ('x','y')))
    return not near or near[0][0]>90 or near[0][1]!=str(hero) or len(near)>1 and near[1][0]-near[0][0]<60

class BattleMetrics:
    def __init__(self,path,callback=lambda row:None,outcome_callback=lambda row:None,episode_provider=None):
        self.path=path;self.callback=callback;self.outcome_callback=outcome_callback;self.pending=[];self.games=[];self.windows=[];self.game=None;self.last=None;self.completed_tokens=[]
        # These totals belong to this controller run, not the retained 100-game
        # display window and not a mixture of earlier installation sessions.
        self.run_totals={'games':0,'wins':0,'losses':0,'unknown_results':0}
        self.episode_provider=episode_provider
    def save(self):
        atomic_write(self.path,json.dumps({'schema':1,'games':self.games[-100:],'health_windows':self.windows[-300:],'run_totals':self.run_summary()},allow_nan=False).encode())
    def begin(self,state):
        self.game={'id':uuid.uuid4().hex,'hero':state.get('heroId'),'outcome':'unknown','source':None,'started':time.time()};self.last=state
        episode=self.episode_provider() if callable(self.episode_provider) else None
        if isinstance(episode,str) and 0<len(episode)<=200:self.game['strategy_episode']=episode
    def note(self,release,plan,state,token):
        if token in self.completed_tokens or any(p['token']==token for p in self.pending):return
        if not self.game:self.begin(state)
        hero=release['hero'];target=plan.get('target_id')
        players=state.get('players',[])
        if target is None and plan.get('target'):
            others=[p for p in players if str(p.get('id'))!=str(hero) and not p.get('dead')]
            if others:target=min(others,key=lambda p:(p['x']-plan['target'][0])**2+(p['y']-plan['target'][1])**2)['id']
        before=release.get('health_before') or {str(p['id']):health(p) for p in players}
        before={str(k):health_value(v) for k,v in before.items()} if isinstance(before,dict) else {}
        durations=[s['duration']/1000 for s in state.get('shots',[]) if isinstance(s,dict) and s.get('native') and health_value(s.get('duration')) is not None]
        overlapping=bool(self.pending)
        for item in self.pending:item['reward_ambiguous']=True
        self.pending.append({'token':token,'hero':hero,'target':target,'turn':release.get('turn_serial'),'before':before,'last_health':dict(before),'expires':time.monotonic()+min(20,max(durations,default=2)+2),'ambiguous':False,'reward_ambiguous':overlapping,'healing_observed':False,'terrain_impact':plan.get('expected_terrain_impact'),'baseline':release.get('baseline',[])})
    def observe(self,state):
        if state.get('status')!='live':return
        if not self.game:
            if state.get('over'):return
            self.begin(state)
        self.last=state;players=state.get('players',[])
        for item in list(self.pending):
            if 'last_health' not in item:
                item['last_health']=dict(item.get('before') or {});item['reward_ambiguous']=True
            measured={str(p['id']):health(p) for p in players}
            for ident in (str(item['hero']),str(item['target'])):
                previous=item['last_health'].get(ident);current=measured.get(ident)
                if previous is not None and current is not None and current>previous:item['healing_observed']=True
                if current is not None:item['last_health'][ident]=current
            # If another shooter's family is already present, HP attribution is unknown.
            for shot in state.get('shots',[]):
                from shot_attribution import identity
                if not isinstance(shot,dict):item['reward_ambiguous']=True;continue
                if identity(shot) in item.get('baseline',[]):
                    duration=health_value(shot.get('duration'));elapsed=health_value(shot.get('elapsed'))
                    if duration is None or elapsed is None or elapsed<duration:
                        if reward_projectile_unknown(shot,item['hero'],players):item['reward_ambiguous']=True
                    continue
                if reward_projectile_unknown(shot,item['hero'],players):item['reward_ambiguous']=True
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
        # Direct end()/complete() calls must obey the same reward exclusions
        # as an ordinary observation tick; a final frame can contain the
        # first visible foreign or unresolved projectile.
        from shot_attribution import identity
        players=(state or {}).get('players',[])
        for shot in (state or {}).get('shots',[]):
            if isinstance(shot,dict) and identity(shot) in item.get('baseline',[]):
                duration=health_value(shot.get('duration'));elapsed=health_value(shot.get('elapsed'))
                if duration is not None and elapsed is not None and elapsed>=duration:continue
            if reward_projectile_unknown(shot,item['hero'],players):item['reward_ambiguous']=True
        self.pending.remove(item);after={str(p['id']):health(p) for p in (state or {}).get('players',[])}
        self.completed_tokens=(self.completed_tokens+[item['token']])[-512:]
        target=str(item['target']);before=health_value(item['before'].get(target));current=health_value(after.get(target))
        known=not item['ambiguous'] and before is not None and current is not None
        own_before=health_value(item['before'].get(str(item['hero'])));own_after=health_value(after.get(str(item['hero'])))
        own_known=own_before is not None and own_after is not None
        healing=item.get('healing_observed',False) or before is not None and current is not None and current>before or own_known and own_after>own_before
        reason='unknown-attribution' if not known else 'unknown-own-health' if not own_known else 'ambiguous-health-window' if item.get('reward_ambiguous') else 'healing-observed' if healing else None
        row={'token':item['token'],'game':self.game['id'] if self.game else None,'known':known,'enemy_health_drop':max(0,before-current) if known else None,'own_health_drop':max(0,own_before-own_after) if own_known else None,'enemy_health_before':before,'enemy_health_after':current,'own_health_before':own_before,'own_health_after':own_after,'reward_eligible':reason is None,'reward_rejection':reason,'attribution':'own-shot-window' if known else 'unknown','confirmed_impact':False}
        impact=item.get('terrain_impact');row['terrain_opened']=None
        if known and impact and (state or {}).get('terrain'):
            from autonomous_learning import occupied
            row['terrain_opened']=not occupied(state['terrain'],*impact)
        self.windows.append(row);self.windows=self.windows[-300:];self.callback(row);self.save()
    def end(self,state=None):
        if not self.game:return
        state=state or self.last or {}
        for item in list(self.pending):self.complete(item,state if state.get('over') else None)
        hero=next((p for p in state.get('players',[]) if str(p.get('id'))==str(self.game['hero'])),None)
        enemies=[p for p in state.get('players',[]) if str(p.get('id'))!=str(self.game['hero'])]
        if state.get('over') is True and hero and len(enemies)==1 and isinstance(hero.get('dead'),bool) and isinstance(enemies[0].get('dead'),bool):
            if hero['dead'] and not enemies[0]['dead']:self.game.update(outcome='loss',source='native-survival-at-gameover')
            elif not hero['dead'] and enemies[0]['dead']:self.game.update(outcome='win',source='native-survival-at-gameover')
        self.game['finished']=time.time();self.game['outcome_known']=self.game['outcome'] in ('win','loss')
        finished=dict(self.game);self.games.append(finished);self.games=self.games[-100:];self.game=None
        self.run_totals['games']+=1
        self.run_totals[{'win':'wins','loss':'losses','unknown':'unknown_results'}[finished['outcome']]]+=1
        self.save();self.outcome_callback(dict(finished))
    def run_summary(self):
        totals=dict(self.run_totals);known=totals['wins']+totals['losses']
        return {**totals,'win_rate':round(totals['wins']*100/known,1) if known else None,'scope':'current-controller-run'}
    def summary(self):
        wins=sum(g['outcome']=='win' for g in self.games);losses=sum(g['outcome']=='loss' for g in self.games)
        return {'wins':wins,'losses':losses,'unknown_results':len(self.games)-wins-losses,'win_rate':round(wins*100/(wins+losses),1) if wins+losses else None,'known_health_windows':sum(w['known'] for w in self.windows),'recent_games':len(self.games),'recent_limit':100,'run_totals':self.run_summary()}
