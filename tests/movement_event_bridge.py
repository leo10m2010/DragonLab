"""Real target-specific keyboard events against controlled movement fixtures."""
import concurrent.futures,json,sys,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from training_browser import TrainingBrowser

class Reader:
    def __init__(self,client):self.client=client
    def read(self):return self.client.call('Runtime.evaluate',{'expression':'window.movement.state','returnByValue':True})['result']['value']

def run(endpoint,target,distance):
    browser=TrainingBrowser(endpoint,target);browser.background=True
    try:
        browser.arm(focus=False);browser.seconds_left=lambda:20;browser.movement_mobile='ARMOR'
        return browser.walk(Reader(browser.client),{'direction':'right','distance':distance,'max_drop':14},threading.Event(),1)
    finally:browser.close()

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(run,sys.argv[1],sys.argv[2],4);second=pool.submit(run,sys.argv[1],sys.argv[3],36)
        print(json.dumps([first.result(timeout=10),second.result(timeout=10)]))
