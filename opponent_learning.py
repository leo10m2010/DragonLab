"""Passive anonymous opponent observations; never a source of shot calibration."""
import hashlib,json,math,time,statistics
from collections import deque
from pathlib import Path
from calibration_book import mobile_name
from local_storage import atomic_write


def number(value):return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)
def point(player):
    return [float(player['x']),float(player['y'])] if isinstance(player,dict) and all(number(player.get(k)) and abs(player[k])<=1e6 for k in ('x','y')) else None
def health(player):
    return player['hp']+player['shield'] if isinstance(player,dict) and all(number(player.get(k)) and player[k]>=0 for k in ('hp','shield')) else None
def digest(value):return hashlib.sha256(str(value).encode('utf-8')).hexdigest()[:24]
def identifier(value):return None if value is None or isinstance(value,(dict,list,bool)) else str(value)
def serial(value):return int(value) if number(value) and 0<=value<=1e12 and value==int(value) else None
def mobile(player):return mobile_name(player.get('mobile')) if isinstance(player,dict) else None
def mode(value):return int(value) if number(value) and value in (0,1,2) else None

def weather_key(state):
    rows=state.get('weather')
    if not isinstance(rows,list) or len(rows)>32:return None
    result=[]
    for row in rows:
        if not isinstance(row,dict) or not all(number(row.get(k)) for k in ('typeId','x','size')):return None
        result.append(tuple(row.get(k) if number(row.get(k)) else None for k in ('typeId','x','size','resolvedTypeId')))
    return tuple(result)


def enemy(player,hero):
    return identifier(player.get('id'))!=identifier(hero.get('id')) and (hero.get('team') is None or player.get('team')!=hero['team'])


def primary(shot):
    start=shot.get('start') if isinstance(shot,dict) else None
    return bool(isinstance(shot,dict) and shot.get('native') and not shot.get('auxiliary') and not shot.get('delay') and isinstance(start,list) and len(start)==6 and all(number(v) for v in start) and number(shot.get('elapsed')) and 0<=shot['elapsed']<=600)


def owner_of(shot):
    metadata=shot.get('metadata') if isinstance(shot.get('metadata'),dict) else {}
    a=identifier(metadata.get('player_n'));b=identifier(metadata.get('player'))
    return None if a is not None and b is not None and a!=b else a if a is not None else b


def context(state,hero,rival,hero_position=None):
    """Exact vehicles/wind, explicitly clear weather, coarse relative geometry."""
    a=hero_position or point(hero);b=point(rival);wind=state.get('wind');angle=state.get('windAngle')
    if not a or not b or not mobile(hero) or not mobile(rival) or not number(wind) or not 0<=wind<=100 or not number(angle) or state.get('weather')!=[]:return None
    dx,dy=a[0]-b[0],a[1]-b[1]
    return [mobile(hero),mobile(rival),round(wind,2),round(angle%360,2) if wind else 0,1 if dx>=0 else -1,int(abs(dx)//80),math.floor(dy/40)]


def wilson(rows):
    n=len(rows);hits=sum(row.get('hero_health_drop',0)>0 for row in rows);p=hits/n;z=1.959963984540054
    den=1+z*z/n;center=(p+z*z/(2*n))/den;radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return {'estimate':p,'low':max(0,center-radius),'high':min(1,center+radius),'samples':n,'episodes':len({row['episode'] for row in rows})}


class OpponentLearner:
    def __init__(self,path,max_cases=256):
        if isinstance(max_cases,bool) or not isinstance(max_cases,int) or not 1<=max_cases<=4096:raise ValueError('Límite de observaciones inválido')
        self.path=Path(path);self.max_cases=max_cases;self.cases=[];self.positions=[];self.storage_error='';self._load_failed=False
        self.totals={k:0 for k in ('opponent_turns','opponent_shots','opponent_inferred_shots','position_samples','known_health_windows')}
        self._seen_turns=deque(maxlen=max_cases*4);self._seen_projectiles=deque(maxlen=max_cases*8);self._seen_cases=set();self._seen_positions=set();self._episode=None;self._turns={};self._active=None;self._pending=[];self._last_state=None;self._last_observed_at=None;self._dirty=False;self._last_save=time.monotonic()
        try:
            if self.path.exists():
                if self.path.stat().st_size>8_000_000:raise ValueError('oversized')
                saved=json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(saved,dict) or saved.get('schema')!=1:raise ValueError('schema')
                self.cases=[self._clean_case(row) for row in saved.get('cases',[])[-max_cases:]]
                self.positions=[self._clean_position(row) for row in saved.get('positions',[])[-max_cases:]]
                self.cases=[row for row in self.cases if row];self.positions=[row for row in self.positions if row]
                for k in self.totals:
                    value=(saved.get('totals') or {}).get(k,0)
                    if not isinstance(value,int) or isinstance(value,bool) or not 0<=value<=10**12:raise ValueError('counter')
                    self.totals[k]=value
                self._seen_turns.extend(v for v in saved.get('seen_turns',[])[-max_cases*4:] if self._hash(v))
                self._seen_projectiles.extend(v for v in saved.get('seen_projectiles',[])[-max_cases*8:] if self._hash(v))
        except (OSError,ValueError,TypeError,AttributeError):
            self.cases=[];self.positions=[];self.totals={k:0 for k in self.totals};self._seen_turns.clear();self._seen_projectiles.clear()
            self.storage_error='No se pudo cargar el aprendizaje de rivales; se conserva el archivo original';self._load_failed=True
        self._seen_cases={row['id'] for row in self.cases};self._seen_positions={row['id'] for row in self.positions}
    @staticmethod
    def _hash(value):return isinstance(value,str) and len(value)==24 and all(c in '0123456789abcdef' for c in value)
    @classmethod
    def _clean_case(cls,row):
        if not isinstance(row,dict) or not cls._hash(row.get('id')) or not cls._hash(row.get('episode')):return None
        if row.get('enemy_mobile') is not None and mobile_name(row['enemy_mobile'])!=row['enemy_mobile']:return None
        if row.get('hero_mobile') is not None and mobile_name(row['hero_mobile'])!=row['hero_mobile']:return None
        result={k:row.get(k) for k in ('id','episode','enemy_mobile','hero_mobile')};result['shot']=mode(row.get('shot'))
        result['power']=None
        for k in ('enemy_position','hero_position','observed_displacement'):
            value=row.get(k);result[k]=list(value) if isinstance(value,list) and len(value)==2 and all(number(v) and abs(v)<=1e6 for v in value) else None
        for k in ('launch_angle','launch_speed','enemy_raw_angle','wind','wind_angle'):
            result[k]=row.get(k) if number(row.get(k)) else None
        result['movement_ambiguous']=row.get('movement_ambiguous') is True;result['health_known']=row.get('health_known') is True
        drop=row.get('hero_health_drop');result['hero_health_drop']=drop if result['health_known'] and number(drop) and drop>=0 else None
        ctx=row.get('context');valid=isinstance(ctx,list) and len(ctx)==7 and ctx[:2]==[result['hero_mobile'],result['enemy_mobile']] and all(number(v) for v in ctx[2:])
        result['context']=list(ctx) if valid else None
        result['owner_source']=row.get('owner_source') if row.get('owner_source') in ('native-owner','observed-turn-origin') else 'native-owner'
        if result['owner_source']=='observed-turn-origin':result['context']=None;result['health_known']=False;result['hero_health_drop']=None
        if result['hero_health_drop'] is None:result['health_known']=False
        return result
    @classmethod
    def _clean_position(cls,row):
        if not isinstance(row,dict) or not cls._hash(row.get('id')) or not cls._hash(row.get('episode')):return None
        result={k:row.get(k) for k in ('id','episode')};result['enemy_mobile']=mobile_name(row.get('enemy_mobile'));result['movement_ambiguous']=row.get('movement_ambiguous') is True
        for k in ('from','to','observed_displacement'):
            value=row.get(k)
            if not isinstance(value,list) or len(value)!=2 or not all(number(v) and abs(v)<=1e6 for v in value):return None
            result[k]=list(value)
        reference=row.get('hero_position');result['hero_position']=list(reference) if isinstance(reference,list) and len(reference)==2 and all(number(v) and abs(v)<=1e6 for v in reference) else None
        return result
    def save(self,force=False):
        if not self._dirty:return not bool(self.storage_error)
        if self._load_failed:return False
        now=time.monotonic()
        if not force and now-self._last_save<5:return True
        try:
            atomic_write(self.path,json.dumps({'schema':1,'totals':self.totals,'cases':self.cases[-self.max_cases:],'positions':self.positions[-self.max_cases:],'seen_turns':list(self._seen_turns),'seen_projectiles':list(self._seen_projectiles)},allow_nan=False,separators=(',',':')).encode('utf-8'))
            self._last_save=now;self._dirty=False;self.storage_error='';return True
        except (OSError,ValueError,TypeError):self._last_save=now;self.storage_error='No se pudo guardar el aprendizaje de rivales';return False
    def _position(self,turn,player=None):
        if turn['id'] in self._seen_positions:return
        final=point(player) or turn['last'];start=turn['position']
        if not final:return
        changed=health(player) is not None and turn['enemy_health'] is not None and health(player)!=turn['enemy_health']
        row={'id':turn['id'],'episode':self._episode,'enemy_mobile':turn['mobile'],'from':start,'to':final,'hero_position':turn.get('hero_position'),'observed_displacement':[final[0]-start[0],final[1]-start[1]],'movement_ambiguous':bool(turn['ambiguous'] or changed)}
        self.positions.append(row);self.positions=self.positions[-self.max_cases:];self._seen_positions={r['id'] for r in self.positions};self.totals['position_samples']+=1;self._dirty=True
    def _finish(self,pending,state=None,allow_known=False):
        if pending not in self._pending:return
        self._pending.remove(pending);row=pending['row']
        hero=next((p for p in (state or {}).get('players',[]) if identifier(p.get('id'))==pending['hero']),None)
        after=health(hero);before=pending['before']
        known=allow_known and not pending['ambiguous'] and before is not None and after is not None and after<=before
        row['health_known']=bool(known);row['hero_health_drop']=before-after if known else None
        if known:self.totals['known_health_windows']+=1
        self._dirty=True
    def end(self):
        for pending in list(self._pending):self._finish(pending)
        if self._active:self._position(self._active)
        self._episode=None;self._active=None;self._turns={};self._last_state=None;self._last_observed_at=None;self.save(force=True)
    def _temporal_owner(self,state,shot,players,hero):
        """Observed correlation only; it can never authorize HP/risk evidence."""
        metadata=shot.get('metadata') if isinstance(shot.get('metadata'),dict) else {}
        if any(k in metadata for k in ('player','player_n')) or not primary(shot) or shot['elapsed']>150 or mode(shot.get('shotType')) is None:return None
        previous=self._last_state;now=time.monotonic()
        if not previous or self._last_observed_at is None or not 0<=now-self._last_observed_at<=.35:return None
        if serial(state.get('turnSerial'))!=previous['turnSerial']:return None
        owner=identifier(previous['activePlayer']);current=identifier(state.get('activePlayer'))
        if owner in (None,'-1') or current not in (owner,'-1') or identifier(state.get('heroId'))!=identifier(previous['heroId']):return None
        rival=next((p for p in players if identifier(p.get('id'))==owner),None)
        old_rival=next((p for p in previous['players'] if identifier(p.get('id'))==owner),None)
        old_hero=next((p for p in previous['players'] if identifier(p.get('id'))==identifier(state.get('heroId'))),None)
        if not rival or not old_rival or not old_hero or not enemy(rival,hero) or rival.get('dead') or not mobile(hero) or not mobile(rival):return None
        if mobile(hero)!=mobile(old_hero) or mobile(rival)!=mobile(old_rival) or hero.get('team')!=old_hero.get('team') or rival.get('team')!=old_rival.get('team'):return None
        if not all(number(state.get(k)) and state.get(k)==previous.get(k) for k in ('wind','windAngle')):return None
        if weather_key(state) is None or weather_key(state)!=previous['weather_key']:return None
        raw=state.get('players')
        if not isinstance(raw,(list,tuple)) or any(not isinstance(p,dict) or not point(p) for p in raw[:16]):return None
        if math.dist(point(hero),point(old_hero))>1 or math.dist(shot['start'][:2],point(old_rival))>60:return None
        distances=sorted((math.dist(shot['start'][:2],point(p)),identifier(p['id'])) for p in players)
        if not distances or distances[0][1]!=owner or distances[0][0]>60 or len(distances)>1 and distances[1][0]-distances[0][0]<60:return None
        return owner
    def observe(self,state,episode):
        if not isinstance(state,dict):return
        ep=digest(episode)
        if self._episode!=ep:
            self.end();self._episode=ep
        if state.get('status')!='live':self.save();return
        raw_players=state.get('players');raw_players=raw_players if isinstance(raw_players,(list,tuple)) else []
        players=[p for p in raw_players[:16] if isinstance(p,dict) and identifier(p.get('id')) is not None and point(p)]
        hero=next((p for p in players if identifier(p.get('id'))==identifier(state.get('heroId'))),None)
        if not hero:self.save();return
        rivals=[p for p in players if enemy(p,hero)];alive=[p for p in players if not p.get('dead')]
        unique=len(alive)==2 and sum(enemy(p,hero) for p in alive)==1
        if state.get('over') and len(players)==2 and sum(enemy(p,hero) for p in players)==1:unique=True
        raw_shots=state.get('shots');raw_shots=raw_shots if isinstance(raw_shots,(list,tuple)) else []
        shots=[s for s in raw_shots[:64] if isinstance(s,dict)]
        # Delayed families are not new primary volleys, but can still alter HP.
        # Include every native family when checking interference/unknown owners.
        owners={owner_of(s) for s in shots if s.get('native')}
        # Fallback visual entries do not prove a native family/owner, even if
        # their arbitrary metadata happens to name the expected player.
        if any(not s.get('native') for s in shots):owners.add(None)
        active=identifier(state.get('activePlayer'));turn_serial=serial(state.get('turnSerial'));by_id={identifier(p['id']):p for p in players}
        for pending in list(self._pending):
            if not unique or any(o!=pending['owner'] for o in owners) or any(s.get('auxiliary') for s in shots):pending['ambiguous']=True
            if mobile(hero)!=pending['hero_mobile'] or mobile(by_id.get(pending['owner']))!=pending['enemy_mobile']:pending['ambiguous']=True
            if turn_serial!=pending['turn'] and any(primary(s) and digest((ep,s.get('id'),s['start'])) not in pending['families'] for s in shots):pending['ambiguous']=True
            hero_point=point(hero)
            if hero_point is None or math.dist(hero_point,pending['hero_position'])>1:pending['ambiguous']=True
            finished=bool(state.get('over') or turn_serial is not None and turn_serial!=pending['turn'] and active not in (None,'-1'))
            expired=time.monotonic()>=pending['expires']
            if finished or expired:self._finish(pending,state,allow_known=finished)
        rival=next((p for p in rivals if identifier(p['id'])==active and not p.get('dead')),None)
        key=digest((ep,active,turn_serial)) if rival is not None and turn_serial is not None else None
        if self._active and self._active['id']!=key:
            self._position(self._active,by_id.get(self._active['owner']));self._active=None
        if key is not None:
            if self._active is None:
                self._active={'id':key,'owner':active,'serial':turn_serial,'position':point(rival),'last':point(rival),'mobile':mobile(rival),'enemy_health':health(rival),'hero_health':health(hero),'hero_position':point(hero),'hero_mobile':mobile(hero),'wind':state.get('wind'),'wind_angle':state.get('windAngle'),'state_context':context(state,hero,rival),'ambiguous':False,'pre_shot':False}
                self._turns[active]=self._active
                if key not in self._seen_turns:self._seen_turns.append(key);self.totals['opponent_turns']+=1;self._dirty=True
            self._active['last']=point(rival)
            if health(rival)!=self._active['enemy_health'] or health(hero)!=self._active['hero_health'] or any(o!=active for o in owners):self._active['ambiguous']=True
            if not any(owner_of(s)==active and primary(s) for s in shots):self._active['pre_shot']=True
        for shot in shots:
            if not primary(shot):continue
            owner=owner_of(shot);source='native-owner'
            if owner is None:
                owner=self._temporal_owner(state,shot,players,hero);source='observed-turn-origin'
            rival=by_id.get(owner)
            if owner is None or not rival or not enemy(rival,hero):continue
            projectile=digest((ep,shot.get('id'),shot['start']))
            if projectile in self._seen_projectiles:continue
            turn=self._turns.get(owner)
            if not turn or turn['id'] in self._seen_cases:continue
            metadata=shot.get('metadata') or {}
            if metadata.get('mobile') is not None and mobile_name(metadata['mobile'])!=mobile(rival):continue
            kind=mode(shot.get('shotType'));alternate=mode(metadata.get('selectedShot'))
            if kind is not None and alternate is not None and kind!=alternate:continue
            kind=kind if kind is not None else alternate
            if kind is None:continue
            self._seen_projectiles.append(projectile)
            start=shot['start'];now=time.monotonic();rival_position=point(rival);self._position(turn,rival)
            row={'id':turn['id'],'episode':ep,'enemy_mobile':mobile(rival),'hero_mobile':mobile(hero),'shot':kind,'power':None,'launch_angle':start[2],'launch_speed':start[3],'enemy_raw_angle':rival.get('rawAngle') if number(rival.get('rawAngle')) else None,'enemy_position':rival_position,'hero_position':point(hero),'observed_displacement':[rival_position[i]-turn['position'][i] for i in (0,1)],'movement_ambiguous':bool(turn['ambiguous']),'wind':turn['wind'] if number(turn['wind']) else None,'wind_angle':turn['wind_angle'] if number(turn['wind_angle']) else None,'context':None,'health_known':False,'hero_health_drop':None,'owner_source':source}
            # Risk evidence needs an observed pre-shot window, unchanged hero,
            # one live enemy and no active weather. It is not an impact claim.
            ctx=context(state,hero,rival)
            context_unchanged=turn['state_context'] is not None and ctx is not None and ctx[:5]==turn['state_context'][:5]
            unambiguous=source=='native-owner' and unique and turn['pre_shot'] and not turn['ambiguous'] and all(o==owner for o in owners) and math.dist(point(hero),turn['hero_position'])<=1 and context_unchanged
            row['context']=ctx if unambiguous else None
            self.cases.append(row);self.cases=self.cases[-self.max_cases:];self._seen_cases={r['id'] for r in self.cases};self.totals['opponent_shots']+=1;self._dirty=True
            if source=='observed-turn-origin':self.totals['opponent_inferred_shots']+=1
            duration=shot.get('duration');duration=duration/1000 if number(duration) and duration>=0 else 2
            families={digest((ep,s.get('id'),s['start'])) for s in shots if primary(s) and owner_of(s)==owner}
            self._pending.append({'row':row,'owner':owner,'hero':identifier(hero['id']),'turn':turn['serial'],'before':turn['hero_health'],'hero_position':point(hero),'hero_mobile':mobile(hero),'enemy_mobile':mobile(rival),'families':families,'expires':now+min(20,duration+2),'ambiguous':not unambiguous})
        self._last_state={'heroId':state.get('heroId'),'activePlayer':state.get('activePlayer'),'turnSerial':turn_serial,'wind':state.get('wind'),'windAngle':state.get('windAngle'),'weather_key':weather_key(state),'players':[{k:p.get(k) for k in ('id','mobile','team','x','y','dead')} for p in players]}
        self._last_observed_at=time.monotonic()
        if state.get('over'):
            if self._active:self._position(self._active,by_id.get(self._active['owner']))
            for pending in list(self._pending):self._finish(pending,state,allow_known=True)
            self.save(force=True)
        else:self.save()
    def _groups(self):
        groups={}
        for row in self.cases:
            if row.get('health_known') and row.get('context') is not None and number(row.get('hero_health_drop')):groups.setdefault(tuple(row['context']),[]).append(row)
        return groups
    def summary(self):
        groups=self._groups();ready=sum(len(rows)>=8 and len({r['episode'] for r in rows})>=2 for rows in groups.values())
        behavior={}
        for name in sorted({row['enemy_mobile'] for row in self.positions+self.cases if row.get('enemy_mobile')}):
            positions=[row for row in self.positions if row.get('enemy_mobile')==name];clear=[row for row in positions if not row['movement_ambiguous'] and row.get('hero_position')]
            toward=away=still=0;distances=[]
            for row in clear:
                distance=math.dist(row['from'],row['to']);distances.append(distance)
                difference=math.dist(row['to'],row['hero_position'])-math.dist(row['from'],row['hero_position'])
                if distance<=2:still+=1
                elif difference<-3:toward+=1
                elif difference>3:away+=1
            shots=[row for row in self.cases if row.get('enemy_mobile')==name]
            behavior[name]={'position_samples':len(positions),'usable_position_samples':len(clear),'toward':toward,'away':away,'stationary':still,'median_displacement':round(statistics.median(distances),2) if distances else None,'weapon_counts':{str(mode):sum(row['shot']==mode for row in shots) for mode in (0,1,2)},'inferred_shots':sum(row.get('owner_source')=='observed-turn-origin' for row in shots)}
        return {**self.totals,'profiles':len({(row['enemy_mobile'],row['shot']) for row in self.cases}),'behavior_profiles':behavior,'risk_ready_contexts':ready,'storage_error':self.storage_error}
    def risk_for_position(self,state,position,target_id=None):
        if not isinstance(state,dict) or state.get('status')!='live' or state.get('over') or not isinstance(position,(list,tuple)) or len(position)!=2 or not all(number(v) for v in position):return None
        raw_players=state.get('players')
        if not isinstance(raw_players,(list,tuple)):return None
        players=[p for p in raw_players if isinstance(p,dict) and point(p) and not p.get('dead')]
        hero=next((p for p in players if identifier(p.get('id'))==identifier(state.get('heroId'))),None)
        if not hero or len(players)!=2:return None
        rivals=[p for p in players if enemy(p,hero)]
        if len(rivals)!=1:return None
        rival=rivals[0]
        if target_id is not None and identifier(rival['id'])!=identifier(target_id):return None
        ctx=context(state,hero,rival,list(position))
        if ctx is None:return None
        rows=self._groups().get(tuple(ctx),[])
        return wilson(rows) if len(rows)>=8 and len({row['episode'] for row in rows})>=2 else None
