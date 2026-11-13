"""Passive action events on a dedicated loopback connection, without map polling."""
import json,select,threading,time
from cdp import CDP
from automatic import GESTURE_JS
from shortcuts import KEYS

class BrowserShotEvents:
    def __init__(self,endpoint,target,owner,get_key,emit,get_source_epoch=None):
        self.endpoint=endpoint;self.target=target;self.owner=owner;self.get_key=get_key;self.emit=emit
        self.binding='__dragonlabShot_'+owner;self.stop_event=threading.Event();self.ready=False;self.error=None;self.key=None;self.document_script=None
        self.get_source_epoch=get_source_epoch;self.source_epoch=None;self.configured_epoch=None;self.document=None;self.blocked_epoch=None;self.client=None
        self.thread=threading.Thread(target=self.run,daemon=True)
    def start(self):self.thread.start()
    def close(self):self.stop_event.set()
    def set_source_epoch(self,epoch,owner=None):
        """Reject queued old gestures immediately; the worker replaces the binding."""
        if owner is not None and owner!=self.owner:return
        if epoch!=self.source_epoch:
            self.source_epoch=epoch;self.document=None;self.ready=False
    def event(self,message):
        if message.get('method') in ('Runtime.executionContextsCleared','Page.navigatedWithinDocument') or (message.get('method')=='Page.frameNavigated' and not message.get('params',{}).get('frame',{}).get('parentId')):
            self.document=None;self.blocked_epoch=self.configured_epoch;self.ready=False
            if self.get_source_epoch is None and self.client:self.set_source_epoch(self.client.source_epoch)
            return
        if message.get('method')!='Runtime.bindingCalled':return
        p=message.get('params',{})
        if p.get('name')!=self.binding or not isinstance(p.get('payload'),str) or len(p['payload'])>512:return
        try:d=json.loads(p['payload'])
        except ValueError:return
        if not isinstance(d,dict) or d.get('owner')!=self.owner or d.get('key')!=KEYS.get(self.key):return
        if self.source_epoch is None or self.source_epoch!=self.configured_epoch or self.source_epoch==self.blocked_epoch or d.get('sourceEpoch')!=self.configured_epoch:return
        if not isinstance(d.get('document'),(int,float)) or (self.document is not None and d['document']!=self.document):return
        if not isinstance(d.get('count'),int) or isinstance(d.get('count'),bool) or not isinstance(d.get('at'),(int,float)):return
        if d['count']>0 and -.05<=time.time()-d['at']/1000<.8:self.emit(d)
    def configure(self,client,key):
        self.ready=False
        script=GESTURE_JS.replace('__OWNER__',json.dumps(self.owner)).replace('__KEY__',str(KEYS[key])).replace('__BINDING__',json.dumps(self.binding)).replace('__EPOCH__',json.dumps(self.source_epoch))
        epoch=self.source_epoch
        self.key=key
        if self.document_script:
            client.call('Page.removeScriptToEvaluateOnNewDocument',{'identifier':self.document_script})
        self.document_script=client.call('Page.addScriptToEvaluateOnNewDocument',{'source':script})['identifier']
        # Navigation events can arrive during these CDP calls. Do not publish a
        # configuration prepared for a source that has already been replaced.
        if self.source_epoch!=epoch:return
        result=client.call('Runtime.evaluate',{'expression':script,'returnByValue':True}).get('result',{}).get('value',{})
        if self.source_epoch!=epoch:return
        self.document=result.get('document');self.configured_epoch=epoch
        self.ready=self.document is not None and epoch!=self.blocked_epoch
    def run(self):
        client=None
        try:
            client=CDP(self.endpoint,target_id=self.target,hostname=None);self.client=client;client.event_handler=self.event
            self.set_source_epoch(self.get_source_epoch() if self.get_source_epoch else client.source_epoch)
            client.call('Runtime.addBinding',{'name':self.binding});self.configure(client,self.get_key())
            while not self.stop_event.is_set():
                if self.get_source_epoch:self.set_source_epoch(self.get_source_epoch())
                key=self.get_key()
                if key!=self.key or self.source_epoch!=self.configured_epoch:self.configure(client,key)
                if client.buf or select.select([client.sock],[],[],.05)[0]:client.handle_event(client.message())
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
