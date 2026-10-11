"""Replay saved numeric cases without connecting to a game or sending input."""
import pathlib,json,sys
from core import Settings,solve

def replay(path):
    payload=json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
    if payload.get('schema')!=1:raise ValueError('Caso desconocido')
    result=solve(Settings(**payload['settings']));outcome=payload.get('outcome',{})
    checks={}
    if payload.get('kind')=='blocked':
        checks['blocked']=bool(result.get('blocked'))
        if 'guide_power' in outcome:checks['reference']=result.get('guide_power')==outcome['guide_power']
    expected=payload.get('expected',{})
    for key,value in expected.items():checks[key]=result.get(key)==value
    return {'case':pathlib.Path(path).name,'power':result.get('power'),'reachable':result.get('reachable'),'checks':checks,'passed':all(checks.values()) if checks else None}

if __name__=='__main__':
    root=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else pathlib.Path(__file__).parent/'casos-regresion')
    files=[root] if root.is_file() else sorted(root.glob('*.json'))
    results=[replay(p) for p in files];print(json.dumps(results,indent=2,ensure_ascii=False))
    sys.exit(1 if any(r['passed'] is False for r in results) else 0)
