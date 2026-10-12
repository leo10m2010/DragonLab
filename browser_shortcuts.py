"""Passive action events on a dedicated loopback connection, without map polling."""
import json,select,threading,time
from cdp import CDP
from automatic import GESTURE_JS
from shortcuts import KEYS

class BrowserShotEvents:
    def __init__(self,endpoint,target,owner,get_key,emit):
        self.endpoint=endpoint;self.target=target;self.owner=owner;self.get_key=get_key;self.emit=emit
        self.binding='__dragonlabShot_'+owner;self.stop_event=threading.Event();self.ready=False;self.error=None;self.key=None;self.document_script=None
        self.thread=threading.Thread(target=self.run,daemon=True)
    def start(self):self.thread.start()
    def close(self):self.stop_event.set()
    def event(self,message):
        if message.get('method')!='Runtime.bindingCalled':return
        p=message.get('params',{})
        if p.get('name')!=self.binding or not isinstance(p.get('payload'),str) or len(p['payload'])>512:return
        try:d=json.loads(p['payload'])
        except ValueError:return
        if not isinstance(d,dict) or d.get('owner')!=self.owner or d.get('key')!=KEYS.get(self.key):return
        if not isinstance(d.get('count'),int) or not isinstance(d.get('at'),(int,float)):return
        if d['count']>0 and -.05<=time.time()-d['at']/1000<.8:self.emit(d)
    def configure(self,client,key):
        script=GESTURE_JS.replace('__OWNER__',json.dumps(self.owner)).replace('__KEY__',str(KEYS[key])).replace('__BINDING__',json.dumps(self.binding))
        self.key=key
        if self.document_script:
            client.call('Page.removeScriptToEvaluateOnNewDocument',{'identifier':self.document_script})
        self.document_script=client.call('Page.addScriptToEvaluateOnNewDocument',{'source':script})['identifier']
        client.call('Runtime.evaluate',{'expression':script,'returnByValue':True})
    def run(self):
        client=None
        try:
            client=CDP(self.endpoint,target_id=self.target);client.event_handler=self.event
            client.call('Page.enable');client.call('Runtime.addBinding',{'name':self.binding});self.configure(client,self.get_key());self.ready=True
            while not self.stop_event.is_set():
                key=self.get_key()
                if key!=self.key:self.configure(client,key)
                if client.buf or select.select([client.sock],[],[],.05)[0]:self.event(client.message())
        except Exception as e:self.error=str(e)
        finally:
            self.ready=False
            if client:
                try:
                    if self.document_script:client.call('Page.removeScriptToEvaluateOnNewDocument',{'identifier':self.document_script})
                    client.call('Runtime.evaluate',{'expression':'(()=>{const s=window.__dragonlabShotGesture;if(s?.owner==='+json.dumps(self.owner)+'){window.removeEventListener(\"keydown\",s.handler,true);delete window.__dragonlabShotGesture}})()'})
                    client.call('Runtime.removeBinding',{'name':self.binding})
                except Exception:pass
                client.close()
