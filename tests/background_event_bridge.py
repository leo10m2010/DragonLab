import sys,json,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from training_browser import TrainingBrowser
b=TrainingBrowser(sys.argv[1],sys.argv[2]);b.background=True
try:
    b.arm(focus=False);b.guard(threading.Event());b.key('up',True);b.key('up',False)
    print(json.dumps({'ok':True}))
finally:b.close()
