"""Cloud distribution entry: server access checks run before the game observer starts."""
import copy,json,pathlib,queue,threading,time,tkinter as tk
from tkinter import messagebox
from cloud_client import CloudClient,CloudError

class CloudRuntime:
    def __init__(self,app,client):
        self.app=app;self.client=client;self.events=queue.Queue();self.stopped=False;self.last_success=time.monotonic();self.busy=False;self.last_check=0;self.next_upload=0
        import hashlib
        self.excluded_ids={hashlib.sha256((key+':'+s['sample_id']).encode()).hexdigest() for key,r in app.book.records.items() for s in r.get('samples',[]) if s.get('sample_id')}
        self.poll()
    def poll(self):
        if self.stopped:return
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='ok':
                    self.last_success=time.monotonic();self.app.cloud_profiles=value;self.app.profile_stamp=None;self.app.last_fingerprint=None;self.app.mark()
                    (self.client.directory/'published-profiles.json').write_text(json.dumps(value),encoding='utf-8')
                elif kind=='denied':
                    self.stopped=True;messagebox.showinfo('DragonLab · acceso',value);self.app.close();return
                elif kind=='error' and time.monotonic()-self.last_success>600:
                    self.stopped=True;messagebox.showinfo('DragonLab · conexión','No se pudo comprobar tu acceso durante diez minutos. Vuelve a entrar cuando tengas conexión.');self.app.close();return
                elif kind=='done':self.busy=False
        except queue.Empty:pass
        now=time.monotonic()
        if not self.busy and now-self.last_check>=60:
            self.busy=True;self.last_check=now
            snapshot=copy.deepcopy(self.app.book.records)
            def work():
                try:
                    account=self.client.status()
                    if not account or not account.get('active'):self.events.put(('denied','Tu acceso venció o está suspendido. Contacta al administrador.'));return
                    profiles=self.client.rpc('published_calibrations');self.events.put(('ok',profiles))
                    if account.get('share_measurements'):
                        from types import SimpleNamespace
                        self.client.send_new_measurements(SimpleNamespace(records=snapshot),self.excluded_ids)
                except CloudError as e:self.events.put(('error',str(e)))
                finally:self.events.put(('done',None))
            threading.Thread(target=work,daemon=True).start()
        self.app.root.after(500,self.poll)

def main():
    from launcher import main as product_main
    product_main()

if __name__=='__main__':main()
