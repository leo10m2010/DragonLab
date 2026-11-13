"""One live, bounded performance window shared by launcher and embedded tools."""
import json,tkinter as tk
from tkinter import filedialog,messagebox
from rounded_widgets import RoundedPanel,RoundedButton
from theme import BG,PANEL,TEXT,MUTED,GREEN
from runtime_metrics import RuntimeMetrics

def open_performance(root,app_provider=lambda:None):
    existing=getattr(root,'performance_window',None)
    if existing and existing.winfo_exists():existing.lift();return existing
    win=tk.Toplevel(root);root.performance_window=win;win.title('DragonLab · Rendimiento');win.configure(bg=BG);win.geometry('620x620');win.minsize(540,480)
    from desktop_shell import style_window
    style_window(win)
    tk.Label(win,text='Rendimiento',font=('Bahnschrift',22,'bold'),bg=BG,fg=TEXT).pack(anchor='w',padx=24,pady=(20,6))
    tk.Label(win,text='Mediciones del programa · actualiza cada 2 segundos',font=('Bahnschrift',10),bg=BG,fg=MUTED).pack(anchor='w',padx=24,pady=(0,16))
    actions=tk.Frame(win,bg=BG);actions.pack(side='bottom',fill='x',padx=24,pady=16)
    holder=tk.Frame(win,bg=BG);holder.pack(fill='both',expand=True,padx=24)
    canvas=tk.Canvas(holder,bg=BG,highlightthickness=0);canvas.pack(side='left',fill='both',expand=True)
    from rounded_controls import RoundedScroll
    scroll=RoundedScroll(holder,command=canvas.yview);scroll.pack(side='right',fill='y');canvas.configure(yscrollcommand=scroll.set)
    body=tk.Frame(canvas,bg=BG);item=canvas.create_window(0,0,window=body,anchor='nw')
    canvas.bind('<Configure>',lambda event:canvas.itemconfigure(item,width=event.width));body.bind('<Configure>',lambda event:canvas.configure(scrollregion=canvas.bbox('all')))
    values={}
    for title in ('CPU del proceso','Memoria residente','Memoria privada','Lectura del juego','Cálculo de fuerza','Presentaciones de la guía','Motor y dibujo','Jugadores y objetivos','Fuente de datos'):
        row=tk.Frame(body,bg=PANEL);row.pack(fill='x',pady=(0,6));row.columnconfigure(1,weight=1)
        tk.Label(row,text=title,bg=PANEL,fg=MUTED,font=('Bahnschrift',10),anchor='w').grid(row=0,column=0,sticky='w',padx=12,pady=12)
        label=tk.Label(row,bg=PANEL,fg=TEXT,font=('Consolas',10),anchor='e',justify='right',wraplength=310);label.grid(row=0,column=1,sticky='ew',padx=12,pady=12);values[title]=label
    note=tk.Label(body,text='CPU: porcentaje equivalente a un núcleo. La frecuencia de la guía no representa los FPS del juego. No se mide la memoria de Chrome.',bg=BG,fg=MUTED,font=('Bahnschrift',10),wraplength=540,justify='left');note.pack(fill='x',pady=(10,0))
    sampler=RuntimeMetrics();snapshot={};job=None
    def fmt(value,unit):return '—' if value is None else f'{value:g} {unit}'
    def refresh():
        nonlocal snapshot,job
        app=app_provider();snapshot=sampler.sample(app)
        counts=snapshot.get('roster',{});source=getattr(app,'source_context',{}) if app else {}
        rows={'CPU del proceso':fmt(snapshot.get('cpu_one_core_percent'),'% de un núcleo'),'Memoria residente':fmt(snapshot.get('working_set_mib'),'MiB'),'Memoria privada':fmt(snapshot.get('private_mib'),'MiB'),'Lectura del juego':fmt(snapshot.get('read_ms'),'ms'),'Cálculo de fuerza':fmt(snapshot.get('solve_ms'),'ms'),'Presentaciones de la guía':fmt(snapshot.get('overlay_presentations_hz'),'Hz'),'Motor y dibujo':snapshot['solver']['engine']+' · '+snapshot['overlay']['renderer'],'Jugadores y objetivos':f"{counts.get('valid',0)} válidos · {counts.get('enemy',0)} enemigos · {counts.get('unknown',0)} sin equipo",'Fuente de datos':source.get('reason') or ('Esperando partida' if not app or not app.last_live else snapshot.get('game',''))}
        for name,value in rows.items():
            if values[name].cget('text')!=value:values[name].config(text=value)
        job=win.after(2000,refresh)
    def export():
        destination=filedialog.asksaveasfilename(parent=win,defaultextension='.json',initialfile='DragonLab-rendimiento.json',filetypes=[('Diagnóstico numérico','*.json')])
        if destination:
            try:
                from local_storage import atomic_write
                atomic_write(destination,json.dumps(snapshot,indent=2,allow_nan=False).encode())
            except (OSError,ValueError):messagebox.showerror('Rendimiento','No se pudo guardar el diagnóstico.',parent=win)
    def cancel():
        nonlocal job
        if job:
            try:win.after_cancel(job)
            except tk.TclError:pass
            job=None
    def close():cancel();win.destroy()
    win.bind('<Destroy>',lambda event:cancel() if event.widget==win else None);win.protocol('WM_DELETE_WINDOW',close);win.bind('<Escape>',lambda event:close())
    RoundedButton(actions,text='Guardar diagnóstico',command=export).pack(side='left');RoundedButton(actions,text='Cerrar',command=close,bg=GREEN,fg=BG).pack(side='right')
    refresh();return win
