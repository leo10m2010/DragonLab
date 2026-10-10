"""Stable enemy order and a passive, combination-safe Control tap reader."""
import os

def enemies(players,hero_id):
    hero=next((p for p in players if p.get('id')==hero_id),None)
    if hero is None:return []
    return sorted((p for p in players if p.get('id')!=hero_id and not p.get('dead') and
                   (hero.get('team') is None or p.get('team')!=hero.get('team'))),key=lambda p:str(p.get('id')))

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
        down=bool(user.GetAsyncKeyState(0x11)&0x8000)
        # Include the since-last-read bit to catch combinations between polls.
        states=[user.GetAsyncKeyState(k)&0x8001 for k in range(1,256) if k not in (0x11,0xa2,0xa3)] if allowed else []
        other=any(states) if down or self.held else False
        return self.feed(down,other,window,allowed)
