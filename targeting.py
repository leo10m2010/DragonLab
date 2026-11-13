"""Stable enemy order and a passive, combination-safe Control tap reader."""
import os
import math
import time
from collections import Counter
from session_lifecycle import primitive_id

class PlayerTracker:
    def __init__(self):self.cache={};self.source_epoch=None;self.diagnostics={}
    def reset(self):self.cache.clear();self.source_epoch=None;self.diagnostics={}
    def update(self,players,now=None,source_epoch=None):
        if source_epoch is not None and source_epoch!=self.source_epoch:self.reset();self.source_epoch=source_epoch
        now=time.monotonic() if now is None else now;present=set();result=[]
        valid_players=normalize_players(players,diagnostics=self.diagnostics,require_coordinates=False)
        duplicates={identity(p.get('id')) for p in players if isinstance(p,dict)}-{p['id'] for p in valid_players}
        for ident in duplicates:self.cache.pop(ident,None)
        for raw in valid_players:
            ident=identity(raw.get('id'))
            if ident is None:continue
            present.add(ident);prior=self.cache.get(ident)
            if raw.get('dead'):self.cache.pop(ident,None);result.append(raw);continue
            valid=valid_coordinates(raw)
            if valid:
                player={**(prior[0] if prior else {}),**{k:v for k,v in raw.items() if v is not None},'id':ident,'team':raw.get('team'),'stale':False};self.cache[ident]=(player,now);result.append(player)
            elif prior and now-prior[1]<=.8:result.append({**prior[0],**{k:v for k,v in raw.items() if k not in ('x','y') and v is not None},'team':raw.get('team'),'stale':True})
        for ident,(player,last) in list(self.cache.items()):
            if now-last>.8:self.cache.pop(ident,None)
            elif ident not in present and ident not in duplicates:result.append({**player,'stale':True})
        self.diagnostics['stale']=sum(bool(p.get('stale')) for p in result)
        return normalize_players(result)

def identity(value):
    return primitive_id(value)


def valid_coordinates(player):
    return all(not isinstance(player.get(k),bool) and isinstance(player.get(k),(int,float)) and math.isfinite(player[k]) for k in ('x','y'))

def normalize_players(players,diagnostics=None,require_coordinates=True):
    players=players if isinstance(players,(list,tuple)) else []
    counts=Counter(identity(p.get('id')) for p in players if isinstance(p,dict))
    result=[];stats={'raw':len(players),'objects':0,'missingId':0,'invalidPosition':0,'duplicates':0,'valid':0,'dead':0,'alive':0,'hero':0,'ally':0,'enemy':0,'unknown':0,'truncated':0}
    for p in players:
        if not isinstance(p,dict):continue
        stats['objects']+=1
        q=dict(p);q['id']=identity(q.get('id'))
        if q['id'] is None:stats['missingId']+=1;continue
        if counts[q['id']]>1:stats['duplicates']+=1;continue
        if not valid_coordinates(q):
            stats['invalidPosition']+=1
            if require_coordinates:continue
        q['team']=identity(q.get('team'));result.append(q)
    stats['valid']=sum(valid_coordinates(p) for p in result)
    stats['dead']=sum(bool(p.get('dead')) for p in result);stats['alive']=len(result)-stats['dead']
    if diagnostics is not None:diagnostics.clear();diagnostics.update(stats)
    return result


def player_role(player,hero):
    if not hero:return 'unknown'
    if identity(player.get('id'))==identity(hero.get('id')):return 'hero'
    own_team,other_team=identity(hero.get('team')),identity(player.get('team'))
    if own_team is None or other_team is None:return 'unknown'
    return 'ally' if own_team==other_team else 'enemy'


def roster_diagnostics(players,hero_id,acquisition=None):
    stats={};valid=normalize_players(players,stats);hero=find_hero(valid,hero_id)
    for p in valid:
        if not p.get('dead'):stats[player_role(p,hero)]+=1
    if isinstance(acquisition,dict):
        for key in ('raw','objects','truncated'):
            value=acquisition.get(key)
            if isinstance(value,int) and not isinstance(value,bool) and value>=0:stats[key]=value
    return stats

def find_hero(players,hero_id):
    matches=[p for p in players if p.get('isHero')]
    if len(matches)==1:return matches[0]
    return next((p for p in players if p.get('id')==identity(hero_id)),None)

def enemies(players,hero_id):
    hero_id=identity(hero_id);hero=next((p for p in players if p.get('id')==hero_id),None)
    if hero is None:return []
    # Unknown teams remain selectable but retain an explicit unknown role. A
    # missing team never becomes a claim that the actor is an enemy.
    return sorted(({**p,'role':player_role(p,hero)} for p in players if p.get('id')!=hero_id and not p.get('dead') and player_role(p,hero)!='ally'),key=lambda p:(not isinstance(p.get('id'),(int,float)),p.get('id') if isinstance(p.get('id'),(int,float)) else str(p.get('id'))))

def next_target(players,hero_id,current):
    ids=[p['id'] for p in enemies(players,hero_id)]
    if not ids:return None
    return ids[(ids.index(current)+1)%len(ids)] if current in ids else ids[0]

class ControlTap:
    def __init__(self):self.held=False;self.used=False;self.window=None
    def feed(self,down,other,window,allowed):
        if not allowed:self.held=False;self.used=False;self.window=None;return False
        if down:
            if not self.held:self.used=False;self.window=window
            self.held=True;self.used|=other or window!=self.window
            return False
        fire=self.held and not self.used and not other and self.window==window
        self.held=False;self.used=False;self.window=None
        return fire
    def poll(self,allowed):
        if os.name!='nt':return False
        import ctypes
        user=ctypes.windll.user32
        user.GetForegroundWindow.restype=ctypes.c_void_p
        user.GetWindowTextW.argtypes=(ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_int)
        title=ctypes.create_unicode_buffer(512)
        window=user.GetForegroundWindow();user.GetWindowTextW(window,title,512)
        allowed=allowed and 'dragonbound' in title.value.lower()
        state=user.GetAsyncKeyState(0x11);down=bool(state&0x8000)
        # Include the since-last-read bit to catch combinations between polls.
        # Ignore mouse buttons and stale prior key events on the initial press.
        mask=0x8001 if self.held else 0x8000
        states=[user.GetAsyncKeyState(k)&mask for k in range(8,256) if k not in (0x11,0xa2,0xa3)] if allowed and (down or self.held or state&1) else []
        other=any(states) if down or self.held else False
        if allowed and state&1 and not down and not self.held:
            return not any(states) # very short press/release between reads
        return self.feed(down,other,window,allowed)
