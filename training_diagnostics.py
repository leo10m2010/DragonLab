"""Read-only packaged browser diagnostic; no account inventory or inputs."""
import json,traceback,tempfile
from pathlib import Path

def connection_check(path):
    report={};client=None
    try:
        report['stage']='connect'
        from cdp import CDP
        client=CDP('http://127.0.0.1:9223')
        report['stage']='ui'
        from training_browser import UI_JS
        ui=client.call('Runtime.evaluate',{'expression':UI_JS,'returnByValue':True}).get('result',{}).get('value',{})
        report['ui']={k:ui.get(k) for k in ('game','blocked','loading')}
        report['stage']='sample';state=client.sample();report['state']=state.get('status')
        report['stage']='storage'
        from training_lease import TrainingLease
        with TrainingLease('diagnostic-only'):pass
        from local_storage import atomic_write
        atomic_write(path.with_suffix('.probe'),b'ok');path.with_suffix('.probe').unlink()
        report['stage']='ok'
    except Exception:report['traceback']=traceback.format_exc()
    finally:
        if client:client.close()
        path.write_text(json.dumps(report),encoding='utf-8')
