"""Reuse the managed game tab before opening another browser window."""
import json,urllib.request
from urllib.parse import urlparse,quote

def activate_existing_game(endpoint='http://127.0.0.1:9223',host='dragonbound.net'):
    from game_catalog import GAMES
    if host not in {g['host'] for g in GAMES.values()}:raise ValueError('Juego no disponible.')
    try:
        with urllib.request.urlopen(endpoint+'/json/list',timeout=.35) as response:targets=json.load(response)
        target=next((t for t in targets if t.get('type')=='page' and urlparse(t.get('url','')).hostname==host),None)
        if not target:return False
        with urllib.request.urlopen(endpoint+'/json/activate/'+quote(target['id'],safe=''),timeout=.35):pass
        return True
    except (OSError,ValueError,KeyError,TypeError):return False
