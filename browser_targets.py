"""Choose a game tab using public visibility/game presence, never account data."""
from urllib.parse import urlparse

class NoGamePage(RuntimeError):pass
class AmbiguousGamePages(RuntimeError):pass
class FollowGameTab(RuntimeError):pass

STATE_JS="""(()=>{const g=location.hostname==='play.gunbound.world'?document.querySelector('canvas.gb-battle-canvas'):document.getElementById('gameScreen');const s=g&&getComputedStyle(g);return {focused:document.hasFocus(),visible:document.visibilityState==='visible',game:!!g&&!!g.getClientRects().length&&s.visibility!=='hidden'&&s.display!=='none'}})()"""

def choose_page(pages,states,preferred=None):
    known=[p for p in pages if p['id'] in states]
    for predicate in (
        lambda s:s.get('focused') and s.get('game'),
        lambda s:s.get('game'),
        lambda s:s.get('focused'),
        lambda s:s.get('visible') and s.get('game'),
        lambda s:s.get('visible'),
    ):
        matches=[p for p in known if predicate(states[p['id']])]
        if len(matches)==1:return matches[0]['id']
    if preferred in {p['id'] for p in known}:return preferred
    if known and not any(states[p['id']].get('game') for p in known):return known[0]['id']
    raise AmbiguousGamePages('Activa la pestaña del juego para conectar la guía.')

def resolve_game_target(endpoint,hosts,preferred=None,pages=None):
    if pages is None:
        from loopback_http import get_json
        pages=get_json(endpoint)
    matches=[p for p in pages if p.get('type')=='page' and urlparse(p.get('url','')).hostname in hosts]
    if not matches:raise NoGamePage('Abre el juego en el navegador conectado.')
    if len(matches)==1:return matches[0]['id']
    from cdp import CDP
    states={}
    for page in matches:
        client=None
        try:
            client=CDP(endpoint,target_id=page['id'],hostname=hosts)
            client.sock.settimeout(.5)
            state=client.call('Runtime.evaluate',{'expression':STATE_JS,'returnByValue':True}).get('result',{}).get('value')
            if isinstance(state,dict):states[page['id']]=state
        except (OSError,RuntimeError,ValueError):pass
        finally:
            if client:client.close()
    return choose_page(matches,states,preferred)
