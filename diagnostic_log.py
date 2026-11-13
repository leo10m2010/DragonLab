"""Bounded local event ledger containing only closed codes and numeric data."""
import json,pathlib,time
ALLOWED_CODES={'source-reset','reader-error','renderer-fallback','unknown-mobile','profile-change'}
FIELDS={'game','epoch','players','enemies','invalid','duplicates','duration_ms','version'}

def note(directory,code,**fields):
    if code not in ALLOWED_CODES:return False
    safe={'time':round(time.time(),3),'code':code}
    for key,value in fields.items():
        if key not in FIELDS:continue
        if isinstance(value,(int,float)) and not isinstance(value,bool):safe[key]=value
        elif key=='game' and value in ('dragonbound','gunbound-world','generic','manual'):safe[key]=value
        elif key=='version' and isinstance(value,str) and len(value)<=20 and all(c.isdigit() or c=='.' for c in value):safe[key]=value
    path=pathlib.Path(directory)/'diagnostico-eventos.jsonl'
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists() and path.stat().st_size>262144:path.replace(path.with_suffix('.previous.jsonl'))
        with path.open('a',encoding='utf-8') as file:file.write(json.dumps(safe,allow_nan=False,separators=(',',':'))+'\n')
        return True
    except (OSError,ValueError):return False
