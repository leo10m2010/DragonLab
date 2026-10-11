"""Run the capture engine inside the product's single main window."""
import tkinter as tk

class EngineWindow(tk.Toplevel):
    def __init__(self,parent):
        self.jobs=set();self.dead=False;super().__init__(parent);self.withdraw()
    def after(self,ms,func=None,*args):
        if func is None:return super().after(ms)
        slot=[]
        def run():
            if slot:self.jobs.discard(slot[0])
            if not self.dead:func(*args)
        identifier=super().after(ms,run);slot.append(identifier);self.jobs.add(identifier);return identifier
    def destroy(self):
        self.dead=True
        for identifier in list(self.jobs):
            try:self.after_cancel(identifier)
            except tk.TclError:pass
        self.jobs.clear();super().destroy()

class EngineHost:
    def __init__(self,parent,directory,client=None):
        import app as module
        directory.mkdir(parents=True,exist_ok=True);module.BASE=directory
        self.window=EngineWindow(parent);self.closed=False
        try:self.app=module.App(self.window,embedded=True)
        except Exception:self.window.destroy();raise
        self.app.ui_parent=parent;self.app.embedded=True;self.app.draw=lambda:None
        if client:
            from cloud_runtime import CloudRuntime
            self.app.cloud_runtime=CloudRuntime(self.app,client)
    def start(self,clone):
        from game_catalog import game_by_id
        if not game_by_id(clone):raise ValueError('Juego no disponible.')
        self.app.clone_id=clone;self.app.adapter_config=None;self.app.browser_target=None
        self.app.change_mobile();self.app.persist_preferences()
        return self.app.open_game_browser()
    def settings(self):return self.app.open_settings()
    def stop(self):
        if self.closed:return
        self.closed=True
        for name in ('settings_window','diagnostics_window'):
            win=getattr(self.app,name,None)
            if win and win.winfo_exists():win.destroy()
        if self.window.winfo_exists():self.app.close()
