"""Two local browser endpoints, with an independent persistent login profile."""
import os,subprocess
from pathlib import Path
from urllib.parse import urlparse,quote
from loopback_http import get_json,get_bytes


def browser_slots(base):
    base=Path(base).resolve()
    return [{'id':f'sesion-{i}','endpoint':f'http://127.0.0.1:{9222+i}',
             'directory':base/'entrenamiento-paralelo'/f'sesion-{i}'} for i in (1,2)]


def game_target(endpoint):
    rows=get_json(endpoint,timeout=1)
    targets=[r for r in rows if r.get('type')=='page' and urlparse(r.get('url','')).hostname=='dragonbound.net']
    if len(targets)!=1:raise ValueError('Deja una sola pestaña de DragonBound abierta en cada sesión de navegador.')
    target=targets[0]
    if not isinstance(target.get('id'),str) or not target['id']:raise ValueError('La pestaña del juego todavía no está preparada.')
    return {'target':target['id'],'url':target['url']}


def ready_slots(base):
    slots=browser_slots(base)
    for i,slot in enumerate(slots,1):
        try:slot['target']=game_target(slot['endpoint'])['target']
        except (OSError,ValueError,TypeError,KeyError) as error:
            raise ValueError(f'Sesión {i}: abre su navegador y entra con su cuenta. '+str(error)) from error
    return slots


def open_second_browser(base):
    base=Path(base).resolve()
    slot=browser_slots(base)[1]
    try:
        rows=get_json(slot['endpoint'],timeout=1)
        games=[r for r in rows if r.get('type')=='page' and urlparse(r.get('url','')).hostname=='dragonbound.net' and r.get('id')]
        if games:
            get_bytes(slot['endpoint'],'/json/activate/'+quote(games[0]['id'],safe=''),timeout=1)
            return slot['endpoint']
    except (OSError,ValueError,TypeError,KeyError):pass
    candidates=[Path(os.environ.get('PROGRAMFILES','C:/Program Files'))/'Google/Chrome/Application/chrome.exe',
                Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Google/Chrome/Application/chrome.exe',
                Path(os.environ.get('LOCALAPPDATA',''))/'Google/Chrome/Application/chrome.exe',
                Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Microsoft/Edge/Application/msedge.exe']
    executable=next((path for path in candidates if path.is_file()),None)
    if executable is None:raise ValueError('Necesitas Chrome o Edge para abrir la segunda sesión.')
    profile=base/'perfiles-navegador'/'sesion-2';profile.mkdir(parents=True,exist_ok=True)
    probe=profile/'dragonlab-write-test.tmp'
    try:probe.write_bytes(b'ok')
    except OSError as error:raise ValueError('No se puede escribir el perfil de la segunda sesión. Elige una carpeta accesible.') from error
    finally:probe.unlink(missing_ok=True)
    # The user explicitly opens this interactive window to log in. No cookies,
    # passwords or browser profiles are copied from the first account.
    subprocess.Popen([str(executable),'--remote-debugging-port=9224','--remote-debugging-address=127.0.0.1',
                      '--user-data-dir='+str(profile),'--no-first-run','--no-default-browser-check',
                      '--new-window','https://dragonbound.net/'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return slot['endpoint']
