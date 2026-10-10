"""Stable enemy order and a passive, combination-safe Control tap reader."""
import os
import math
import time

class PlayerTracker:
    def __init__(self):self.cache={}
    def reset(self):self.cache.clear()
    def update(self,players,now=None):
        now=time.monotonic() if now is None else now;present=set();result=[]
        for raw in players:
            if not isinstance(raw,dict):continue
            ident=identity(raw.get('id'))
            if ident is None:continue
            present.add(ident);prior=self.cache.get(ident)
            if raw.get('dead'):self.cache.pop(ident,None);result.append(raw);continue
            valid=all(isinstance(raw.get(k),(int,float)) and math.isfinite(raw[k]) for k in ('x','y'))
            if valid:
                player={**(prior[0] if prior else {}),**{k:v for k,v in raw.items() if v is not None},'id':ident,'stale':False};self.cache[ident]=(player,now);result.append(player)
            elif prior and now-prior[1]<=.8:result.append({**prior[0],'stale':True})
        for ident,(player,last) in list(self.cache.items()):
            if now-last>.8:self.cache.pop(ident,None)
            elif ident not in present:result.append({**player,'stale':True})
        return normalize_players(result)

def identity(value):
    if isinstance(value,str) and value.strip().lstrip('-').isdigit():return int(value)
    return value

def normalize_players(players):
    result={}
    for p in players:
        if not isinstance(p,dict) or not all(isinstance(p.get(k),(int,float)) and math.isfinite(p[k]) for k in ('x','y')):continue
        q=dict(p);q['id']=identity(q.get('id'))
        if q['id'] is None:continue
        q['team']=identity(q.get('team'));result[q['id']]=q
    return list(result.values())

def find_hero(players,hero_id):
    matches=[p for p in players if p.get('isHero')]
    if len(matches)==1:return matches[0]
    return next((p for p in players if p.get('id')==identity(hero_id)),None)

def enemies(players,hero_id):
    hero=next((p for p in players if p.get('id')==hero_id),None)
    if hero is None:return []
    return sorted((p for p in players if p.get('id')!=hero_id and not p.get('dead') and
                   (hero.get('team') is None or p.get('team')!=hero.get('team'))),key=lambda p:(not isinstance(p.get('id'),int),p.get('id') if isinstance(p.get('id'),int) else str(p.get('id'))))

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
