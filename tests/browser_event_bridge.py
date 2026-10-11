import sys,pathlib,json,time,threading
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from browser_shortcuts import BrowserShotEvents
key=['Q'];lock=threading.Lock()
def emit(value):
    with lock:print(json.dumps(value),flush=True)
watcher=BrowserShotEvents(sys.argv[1],sys.argv[2],'bridgefixture',lambda:key[0],lambda d:emit({'kind':'shot',**d,'received':time.time()*1000}))
watcher.start()
try:
    until=time.monotonic()+5
    while not watcher.ready and watcher.thread.is_alive() and time.monotonic()<until:time.sleep(.01)
    if not watcher.ready:raise RuntimeError(watcher.error or 'Event bridge not ready')
    emit({'kind':'ready'})
    for line in sys.stdin:
        command=json.loads(line)
        if command.get('stop'):break
        if command.get('key'):
            key[0]=command['key'];until=time.monotonic()+2
            while watcher.key!=key[0] and time.monotonic()<until:time.sleep(.01)
            time.sleep(.1);emit({'kind':'configured','key':key[0]})
finally:watcher.close();watcher.thread.join(2)
