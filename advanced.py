"""Own configuration, clone selection and calibration tools for DragonLab."""
import json,threading,queue,copy,pathlib,subprocess,os
import tkinter as tk
from rounded_controls import RoundedChoice,RoundedSwitch,RoundedEntry,RoundedTabs,RoundedTable,RoundedScroll,RoundedText
from tkinter import ttk,messagebox,filedialog
from dataclasses import asdict
from core import Settings,solve,optimize_angles,fit_calibration
from adapters import built_in_profiles,list_browser_pages,load_profiles

BG='#101c26';PANEL='#162735';TEXT='#ecf3f7';GREEN='#72dfba';MUTED='#96acb9'

def open_advanced(app):
    win=tk.Toplevel(app.root);win.title('DragonLab · Motor y conexiones');win.geometry('950x740');win.configure(bg=BG)
    status=tk.StringVar(value='Los perfiles físicos se guardan por juego y vehículo.');q=queue.Queue();closed=False
    tk.Label(win,textvariable=status,bg=BG,fg=GREEN,wraplength=900).pack(fill='x',padx=18,pady=12)
    book=RoundedTabs(win);book.pack(fill='both',expand=True,padx=18,pady=8)
    tabs={}
    for name in ['Juego y navegador','Proyectiles y clima','Calibración','Ángulos']:
        p=tk.Frame(book,bg=PANEL);book.add(p,text=name);tabs[name]=p
    def note(p,text):tk.Label(p,text=text,bg=PANEL,fg=TEXT,wraplength=860,justify='left').pack(anchor='w',padx=16,pady=10)
    def guard(fn):
        def call():
            try:fn()
            except Exception as e:messagebox.showerror('DragonLab',str(e),parent=win)
        return call
    def button(p,text,fn):return app.button(p,text,guard(fn))
    def task(fn,done):
        def run():
            try:q.put((done,fn(),None))
            except Exception as e:q.put((None,None,str(e)))
        threading.Thread(target=run,daemon=True).start();status.set('Procesando…')
    def poll():
        if closed:return
        while not q.empty():
            done,result,error=q.get_nowait()
            if error:status.set(error)
            else:
                try:done(result)
                except Exception as e:status.set(str(e))
        win.after(100,poll)
    def close():
        nonlocal closed
        closed=True;win.destroy()
    win.protocol('WM_DELETE_WINDOW',close);poll()

    p=tabs['Juego y navegador'];profiles=getattr(app,'adapter_profiles',built_in_profiles());app.adapter_profiles=profiles
    names={x.get('name',x['id']):x for x in profiles}
    selected=tk.StringVar(value=next((n for n,x in names.items() if x['id']==app.clone_id),'DragonBound'))
    note(p,'DragonBound: lectura comprobada. GunBound World: conector experimental y física propia por calibrar. El modo de captura permite trabajar con una ventana sin acceso interno al juego.')
    combo=RoundedChoice(p,textvariable=selected,values=list(names),state='readonly');combo.pack(fill='x',padx=16,pady=8)
    page_var=tk.StringVar(value='Selección automática por dominio');pages={}
    page_combo=RoundedChoice(p,textvariable=page_var,state='readonly',values=[page_var.get()]);page_combo.pack(fill='x',padx=16,pady=8)
    details=tk.StringVar(value=names[selected.get()]['compatibility']);tk.Label(p,textvariable=details,bg=PANEL,fg=MUTED,wraplength=850,justify='left').pack(anchor='w',padx=16,pady=8)
    combo.bind('<<ComboboxSelected>>',lambda e:details.set(names[selected.get()].get('compatibility','Perfil propio')))
    def refreshed(values):
        pages.clear();pages.update({f'{x["title"][:50]} · {x["url"][:95]}':x['id'] for x in values})
        page_combo.config(values=['Selección automática por dominio']+list(pages));status.set(f'{len(values)} páginas disponibles')
    row=tk.Frame(p,bg=PANEL);row.pack(fill='x',padx=10,pady=10)
    button(row,'Buscar páginas',lambda:task(lambda:list_browser_pages(app.endpoint.get()),refreshed)).pack(side='left',padx=5)
    def apply_adapter():
        profile=names[selected.get()]
        if app.worker and app.worker.is_alive():raise ValueError('Desconecta la lectura actual antes de cambiar de juego')
        app.clone_id=profile['id'];app.adapter_config=copy.deepcopy(profile);app.browser_target=pages.get(page_var.get())
        app.viewport=(1280,720) if app.clone_id=='gunbound-world' else (800,600)
        app.live_camera=None;app.last_live=0;app.last_fingerprint=None;app.change_mobile();app.persist_preferences();app.mark();status.set('Aplicado: '+profile.get('name',profile['id']))
    button(row,'Aplicar juego',apply_adapter).pack(side='left',padx=5)
    def import_profiles():
        path=filedialog.askopenfilename(parent=win,filetypes=[('Adaptadores JSON','*.json')])
        if path:
            values=load_profiles(path);names.clear();names.update({x.get('name',x['id']):x for x in values});app.adapter_profiles=values;combo.config(values=list(names));status.set('Adaptadores cargados; selecciona uno y aplica')
    button(row,'Importar adaptador',import_profiles).pack(side='left',padx=5)
    def launch_browser():
        profile=names[selected.get()];hosts=profile.get('hosts',[])
        if not hosts:raise ValueError('Elige un juego con dominio configurado')
        candidates=[pathlib.Path(os.environ.get('PROGRAMFILES','C:/Program Files'))/'Google/Chrome/Application/chrome.exe',pathlib.Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Microsoft/Edge/Application/msedge.exe']
        exe=next((x for x in candidates if x.exists()),None)
        if exe is None:raise ValueError('No se encontró Chrome o Edge')
        from urllib.parse import urlparse
        endpoint=urlparse(app.endpoint.get())
        if endpoint.hostname not in ('127.0.0.1','localhost') or endpoint.scheme!='http':raise ValueError('Usa una dirección local http://127.0.0.1:puerto')
        directory=pathlib.Path(os.environ.get('LOCALAPPDATA',str(app.base)))/'DragonLab'/'BrowserData'
        directory.mkdir(parents=True,exist_ok=True)
        subprocess.Popen([str(exe),f'--remote-debugging-port={endpoint.port or 9222}',f'--user-data-dir={directory}','--no-first-run','https://'+hosts[0]+'/'],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        status.set('Navegador abierto. Inicia sesión tú y vuelve a buscar páginas.')
    button(p,'Abrir navegador del juego',launch_browser).pack(anchor='w',padx=16,pady=8)
    note(p,'Este navegador usa un perfil propio de DragonLab. El programa no importa cuentas, cookies ni licencias del original. Seleccionar un dominio no confirma compatibilidad con su estado interno.')

    p=tabs['Proyectiles y clima'];values={}
    grid=tk.Frame(p,bg=PANEL);grid.pack(fill='x',padx=16,pady=8)
    fields=[('selected_shot','Disparo: 0 = 1, 1 = 2, 2 = SS'),('max_time','Tiempo máximo (s)'),('max_power','Potencia máxima'),('speed_offset','Desplazamiento velocidad'),('angle_offset','Corrección de ángulo °')]
    for i,(key,label) in enumerate(fields):
        tk.Label(grid,text=label,bg=PANEL,fg=TEXT).grid(row=i,column=0,sticky='w',pady=5)
        v=tk.StringVar(value=str(getattr(app.s,key)));values[key]=v;RoundedEntry(grid,textvariable=v,bg=BG,fg=TEXT,insertbackground=TEXT,width=15).grid(row=i,column=1,padx=16,pady=(0,4))
    quant=tk.BooleanVar(value=app.s.quantize_power);RoundedSwitch(p,text='Cuantizar velocidad del proyectil',variable=quant,bg=PANEL,fg=TEXT,selectcolor=BG).pack(anchor='w',padx=12,pady=6)
    direction=tk.StringVar(value=app.direction);RoundedChoice(p,textvariable=direction,values=['Auto','Derecha','Izquierda'],state='readonly').pack(anchor='w',padx=16,pady=3)
    backshot=tk.BooleanVar(value=False)
    note(p,'Climas: introduce su ubicación en coordenadas del mapa. Mirror usa typeId 7; Tornado usa typeId 8 y size. El terreno admite alturas, polígonos o filas de píxeles. Los modelos especiales proceden de la interfaz observada; su precisión requiere pruebas de juego.')
    env=RoundedText(p,height=10,bg=BG,fg=TEXT,insertbackground=TEXT,font=('Consolas',10));env.pack(fill='both',expand=True,padx=16,pady=8);env.insert('1.0',json.dumps(app.s.environment,indent=2))
    row=tk.Frame(p,bg=PANEL);row.pack(fill='x',padx=10,pady=8)
    def apply_engine():
        settings=Settings(**asdict(app.read()))
        for key,var in values.items():setattr(settings,key,int(var.get()) if key=='selected_shot' else float(var.get()))
        environment=json.loads(env.get('1.0','end'))
        if not isinstance(environment,dict):raise ValueError('El entorno debe ser un objeto JSON')
        settings.environment=environment;settings.quantize_power=quant.get();settings.is_backshot=backshot.get()
        from core import finite_settings
        finite_settings(settings);app.s=settings;app.direction=direction.get();app.last_fingerprint=None;app.mark();status.set('Motor actualizado')
    button(row,'Aplicar motor',apply_engine).pack(side='left',padx=5)
    def add_weather(kind):
        from tkinter.simpledialog import askfloat
        x=askfloat('Ubicación','Coordenada X del clima en el mapa',parent=win)
        if x is None:return
        data=json.loads(env.get('1.0','end'));weather={'typeId':kind,'x':x}
        if kind==8:
            size=askfloat('Tornado','Tamaño del tornado observado',minvalue=1,maxvalue=1000,parent=win)
            if size is None:return
            weather['size']=size
        data.setdefault('activeWeathers',[]).append(weather);env.delete('1.0','end');env.insert('1.0',json.dumps(data,indent=2))
    button(row,'Añadir Mirror',lambda:add_weather(7)).pack(side='left',padx=5);button(row,'Añadir Tornado',lambda:add_weather(8)).pack(side='left',padx=5)
    button(row,'Vaciar entorno',lambda:(env.delete('1.0','end'),env.insert('1.0','{}'))).pack(side='left',padx=5)

    p=tabs['Calibración'];samples=getattr(app,'calibration_samples',[]);app.calibration_samples=samples
    note(p,'Importa una lista JSON de medidas de disparos: power, vx, vy, ax, ay, wind, wind_angle. Se requieren al menos dos potencias distintas. El ajuste estima gravedad, viento, velocidad y desplazamiento; muestra el error antes de aplicarlo.')
    summary=tk.StringVar(value=f'{len(samples)} muestras');tk.Label(p,textvariable=summary,bg=PANEL,fg=GREEN,wraplength=850,justify='left').pack(anchor='w',padx=16,pady=8)
    result_box=RoundedText(p,height=14,bg=BG,fg=TEXT,insertbackground=TEXT,font=('Consolas',11));result_box.pack(fill='both',expand=True,padx=16,pady=8)
    fitted={}
    def import_samples():
        path=filedialog.askopenfilename(parent=win,filetypes=[('Muestras JSON','*.json')])
        if not path:return
        data=json.loads(pathlib.Path(path).read_text(encoding='utf-8-sig'));data=data.get('samples') if isinstance(data,dict) else data
        if not isinstance(data,list):raise ValueError('El archivo debe contener una lista de muestras')
        samples.clear();samples.extend(data);summary.set(f'{len(samples)} muestras importadas')
    def fit():
        fitted.clear();fitted.update(fit_calibration(samples));result_box.delete('1.0','end');result_box.insert('1.0',json.dumps(fitted,indent=2));summary.set('Ajuste calculado. Revisa el error de velocidad y la dispersión de gravedad.')
    def apply_fit():
        if not fitted:raise ValueError('Calcula el ajuste primero')
        for key in ('power_scale','gravity','wind_scale'):
            if fitted.get(key) is not None:app.vars[key].set(str(round(fitted[key],6)))
        app.s.speed_offset=fitted['speed_offset'];app.mark();status.set('Ajuste aplicado. Guarda el perfil para conservarlo.')
    row=tk.Frame(p,bg=PANEL);row.pack(fill='x',padx=10,pady=8)
    button(row,'Importar muestras',import_samples).pack(side='left',padx=5);button(row,'Ajustar modelo',fit).pack(side='left',padx=5);button(row,'Aplicar ajuste',apply_fit).pack(side='left',padx=5)
    def capture_measured():
        measured=getattr(app,'measured_trajectory',None)
        if not measured:raise ValueError('Registra y ajusta una trayectoria en Visión primero')
        from tkinter.simpledialog import askfloat
        power=askfloat('Potencia observada','Potencia real usada en el disparo medido',minvalue=1,maxvalue=app.s.max_power,parent=win)
        if power is None:return
        elapsed=askfloat('Primera detección','Segundos desde la salida del proyectil hasta la primera detección (0 solo si coincide con la salida)',minvalue=0,maxvalue=60,parent=win)
        if elapsed is None:return
        vx,vy=measured['velocity'];ax,ay=measured['acceleration']
        samples.append({'power':power,'vx':vx-ax*elapsed,'vy':vy-ay*elapsed,'ax':ax,'ay':ay,'wind':app.s.wind,'wind_angle':app.s.wind_angle});summary.set(f'{len(samples)} muestras. La medida requiere cámara fija y origen temporal de lanzamiento conocido.')
    button(p,'Añadir trayectoria medida',capture_measured).pack(anchor='w',padx=16,pady=8)

    p=tabs['Ángulos'];note(p,'Busca soluciones usando el perfil y el entorno actuales. Las trayectorias con clima o terreno requieren más tiempo de cálculo. La búsqueda no modifica ni dispara en el juego.')
    bounds=tk.Frame(p,bg=PANEL);bounds.pack(fill='x',padx=16,pady=8);avs=[]
    for name,value in [('Desde',10),('Hasta',80),('Paso',5)]:
        tk.Label(bounds,text=name,bg=PANEL,fg=TEXT).pack(side='left',padx=6);v=tk.StringVar(value=str(value));avs.append(v);RoundedEntry(bounds,textvariable=v,width=7).pack(side='left')
    table=RoundedTable(p,columns=('angle','power','error','time'),show='headings',height=13)
    for key,label in [('angle','Ángulo'),('power','Potencia'),('error','Error del modelo (px)'),('time','Tiempo (s)')]:table.heading(key,text=label);table.column(key,width=170)
    table.pack(fill='both',expand=True,padx=16,pady=8);solutions=[]
    def found(results):
        solutions.clear();solutions.extend(results);table.delete(*table.get_children())
        for i,r in enumerate(results):table.insert('', 'end',iid=str(i),values=[r[k] for k in ('angle','power','error','time')])
        status.set(f'{len(results)} soluciones. Selecciona una y aplica su ángulo.')
    def search():
        settings=Settings(**asdict(app.read()));a,b,step=[float(v.get()) for v in avs]
        if step<=0:raise ValueError('El paso debe ser positivo')
        if (b-a)/step>90:raise ValueError('Usa como máximo 90 ángulos por búsqueda')
        task(lambda:optimize_angles(settings,a,b,step),found)
    def select_angle():
        selected=table.selection()
        if selected:app.vars['angle'].set(str(solutions[int(selected[0])]['angle']));app.mark();status.set('Ángulo aplicado al laboratorio')
    row=tk.Frame(p,bg=PANEL);row.pack(fill='x',padx=10,pady=8);button(row,'Buscar soluciones',search).pack(side='left',padx=5);button(row,'Usar ángulo seleccionado',select_angle).pack(side='left',padx=5)
    return win
