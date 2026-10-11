"""Atomic bounded-retry writes, including transient Windows scanner locks."""
import pathlib,secrets,time

def atomic_write(path,raw):
    path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+secrets.token_hex(4)+'.tmp')
    try:
        temp.write_bytes(raw)
        for attempt in range(4):
            try:temp.replace(path);return
            except PermissionError:
                if attempt==3:raise
                time.sleep(.02*(attempt+1))
    finally:
        try:temp.unlink(missing_ok=True)
        except OSError:pass
