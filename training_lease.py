"""Cross-process exclusive ownership of training controls and mutable data."""
import hashlib,os,tempfile
from pathlib import Path

class TrainingLease:
    def __init__(self,resource):
        directory=Path(tempfile.gettempdir())/'DragonLab-training-locks';directory.mkdir(exist_ok=True)
        self.file=open(directory/(hashlib.sha256(resource.encode()).hexdigest()+'.lock'),'a+b')
        self.file.seek(0);self.file.write(b'0');self.file.flush();self.file.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.file.close();self.file=None
            raise RuntimeError('Otra sesión de entrenamiento ya controla esta pestaña o sus datos') from None
    def close(self):
        if self.file:
            self.file.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(),fcntl.LOCK_UN)
            self.file.close();self.file=None
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
