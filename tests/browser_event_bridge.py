import sys,pathlib,json,time,threading
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from browser_shortcuts import BrowserShotEvents
key=['Q'];lock=threading.Lock()
def emit(value):
    with lock:print(json.dumps(value),flush=True)
watcher=BrowserShotEvents(sys.argv[1],sys.argv[2],'bridgefixture',lambda:key[0],lambda d:emit({'kind':'shot',**d,'received':time.time()*1000}))

def wait_ready(previous_epoch=None,document=None):
    until=time.monotonic()+5
    while watcher.thread.is_alive() and time.monotonic()<until:
        if (watcher.ready and watcher.key==key[0] and watcher.configured_epoch==watcher.source_epoch
                and (previous_epoch is None or watcher.source_epoch!=previous_epoch)
                and (document is None or watcher.document==document)):
            return {'key':watcher.key,'sourceEpoch':watcher.source_epoch,'document':watcher.document}
        time.sleep(.005)
    raise RuntimeError(watcher.error or 'Event bridge not ready')

watcher.start()
try:
    emit({'kind':'ready',**wait_ready()})
    for line in sys.stdin:
        command=json.loads(line)
        if command.get('stop'):break
        if command.get('key'):
            key[0]=command['key'];emit({'kind':'configured',**wait_ready()})
        if command.get('waitReady'):
            emit({'kind':'rearmed',**wait_ready(command.get('previousEpoch'),command.get('document'))})
finally:watcher.close();watcher.thread.join(2)
