"""Bounded local numeric regression cases; no account or chat data."""
import json,pathlib,hashlib,threading
from dataclasses import asdict
from local_storage import atomic_write

class ReplayStore:
    def __init__(self,path,limit=8,max_bytes=512*1024):
        self.path=pathlib.Path(path);self.limit=limit;self.max_bytes=max_bytes;self.seen=set();self.index=0;self.lock=threading.Lock()
        files=sorted(self.path.glob('case-*.json'),key=lambda p:p.stat().st_mtime) if self.path.exists() else []
        for p in files[:-limit]:p.unlink()
        if files:self.index=(int(files[-1].stem.split('-')[-1])+1)%limit
    def record(self,settings,kind,outcome):
        with self.lock:return self._record(settings,kind,outcome)
    def _record(self,settings,kind,outcome):
        if kind not in ('blocked','mismatch','unconfirmed','ambiguous'):return False
        data={'schema':1,'kind':kind,'settings':asdict(settings),'outcome':{k:outcome[k] for k in ('status','power','actualPower','requestedPower','blocked','guide_power','reason') if k in outcome}}
        # Environments are produced by our numeric serializer; keep only the
        # simulation inputs so unrelated data cannot enter exported fixtures.
        allowed=('terrain','activeWeathers','hitTolerance','players','targetId','mapHeight','nakUndergroundGravity','observedAcceleration')
        data['settings']['environment']={k:v for k,v in data['settings']['environment'].items() if k in allowed}
        data['settings']['environment']['players']=[{k:p[k] for k in ('id','x','y','dead') if k in p} for p in data['settings']['environment'].get('players',[])]
        data['settings']['environment']['activeWeathers']=[{k:w[k] for k in ('typeId','resolvedTypeId','x','y','size','width','height','angle','power','direction') if k in w} for w in data['settings']['environment'].get('activeWeathers',[])]
        raw=json.dumps(data,sort_keys=True,allow_nan=False).encode();key=hashlib.sha256(raw).hexdigest()
        if key in self.seen or len(raw)>self.max_bytes:return False
        self.seen.add(key)
        if len(self.seen)>128:self.seen={key}
        dest=self.path/f'case-{self.index}.json'
        atomic_write(dest,raw);self.index=(self.index+1)%self.limit
        return True
