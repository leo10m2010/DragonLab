"""One released action per authoritative native turn, including consecutive turns."""
from collections import deque
import math

def turn_key(state,room):
    serial=state.get('turnSerial')
    if not isinstance(serial,(int,float)) or isinstance(serial,bool) or not math.isfinite(serial) or serial<0:return None
    hero=state.get('heroId');active=state.get('activePlayer')
    if hero is None or active is None or str(hero)!=str(active):return None
    player=next((p for p in state.get('players',[]) if str(p.get('id'))==str(hero)),None)
    if not player or player.get('dead') or state.get('over'):return None
    return (room,str(hero),serial)

class TurnLedger:
    def __init__(self):self.used=deque(maxlen=128)
    def available(self,key):return key is not None and key not in self.used
    def consume(self,key):
        if not self.available(key):raise RuntimeError('Este turno ya tiene una acción; no se repite el tiro')
        self.used.append(key)
