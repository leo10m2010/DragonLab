"""Reuse the managed game tab before opening another browser window."""
from loopback_http import get_json,get_bytes
from urllib.parse import urlparse,quote

def activate_existing_game(endpoint='http://127.0.0.1:9223',host='dragonbound.net'):
    from game_catalog import GAMES
    if host not in {g['host'] for g in GAMES.values()}:raise ValueError('Juego no disponible.')
    try:
        targets=get_json(endpoint,timeout=.35)
        target=next((t for t in targets if t.get('type')=='page' and urlparse(t.get('url','')).hostname==host),None)
        if not target:return False
        get_bytes(endpoint,'/json/activate/'+quote(target['id'],safe=''),timeout=.35)
        return True
    except (OSError,ValueError,KeyError,TypeError):return False
