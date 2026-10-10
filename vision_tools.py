"""Tk tools for calibrated local vision and explicitly armed one-shot input."""
import tkinter as tk
from tkinter import ttk,messagebox,simpledialog,filedialog
import time,threading,json,ctypes,queue
from pathlib import Path
from PIL import Image,ImageTk,ImageGrab
from vision import DigitOCR,ColorTracker,detect_terrain
from firing import FireController,FirePlan

BG='#101c26';PANEL='#162735';TEXT='#ecf3f7';MUTED='#96acb9';GREEN='#72dfba'

def open_tools(app):
    win=tk.Toplevel(app.root);win.title('DragonLab · Visión y disparo');win.geometry('1030x850');win.configure(bg=BG)
    status=tk.StringVar(value='Selecciona una región arrastrando. Clic sin arrastrar elige un color.')
    tk.Label(win,textvariable=status,bg=BG,fg=GREEN,wraplength=980).pack(pady=8)
    canvas=tk.Canvas(win,width=800,height=500,bg=PANEL,highlightthickness=0);canvas.pack()
    state={'image':None,'crop':None,'box':None,'color':None,'photo':None,'tracker':None,'stop':threading.Event(),'target':None,'start':None,'end':None,'closed':False};updates=queue.Queue()
    def poll_updates():
        if state['closed']:return
        while not updates.empty():updates.get_nowait()()
        win.after(100,poll_updates)
    poll_updates()
    ocr=getattr(app,'local_ocr',None) or DigitOCR();app.local_ocr=ocr
    def say(text):
        if win.winfo_exists():status.set(text)
    def guarded(fn):
        def run():
            try:fn()
            except Exception as e:messagebox.showerror('DragonLab',str(e),parent=win)
        return run
    def refresh():
        if app.image is None:raise ValueError('Abre una captura o captura el área del juego primero')
        state['image']=app.image.convert('RGB').resize(app.viewport);state['photo']=ImageTk.PhotoImage(state['image'].resize((800,500)))
        canvas.delete('all');canvas.create_image(0,0,anchor='nw',image=state['photo']);say('Arrastra para elegir región; clic para elegir color')
    tk.Button(win,text='Usar captura actual',command=guarded(refresh)).pack(pady=4)
    def down(e):state['anchor']=(max(0,min(799,e.x)),max(0,min(499,e.y)))
    def up(e):
        if state['image'] is None:return
        x,y=state.get('anchor',(e.x,e.y));x2=max(0,min(799,e.x));y2=max(0,min(499,e.y))
        if abs(x2-x)<3 and abs(y2-y)<3:
            vw,vh=app.viewport;state['color']=state['image'].getpixel((int(x*vw/800),int(y*vh/500)));say('Color seleccionado RGB %s'%str(state['color']));return
        vw,vh=app.viewport
        box=(int(min(x,x2)*vw/800),int(min(y,y2)*vh/500),min(vw,int(max(x,x2)*vw/800)+1),min(vh,int(max(y,y2)*vh/500)+1))
        state['box']=box;state['crop']=state['image'].crop(box);canvas.delete('region');canvas.create_rectangle(box[0]*800/vw,box[1]*500/vh,box[2]*800/vw,box[3]*500/vh,outline=GREEN,width=2,tags='region');say('Región %s'%str(box))
    canvas.bind('<ButtonPress-1>',down);canvas.bind('<ButtonRelease-1>',up)
    notebook=ttk.Notebook(win);notebook.pack(fill='both',expand=True,padx=12,pady=8)
    tabs={}
    for name in ('Terreno','Números OCR','Seguimiento','Disparo'):
        tab=tk.Frame(notebook,bg=PANEL);notebook.add(tab,text=name);tabs[name]=tab
    def label(tab,text):tk.Label(tab,text=text,bg=PANEL,fg=TEXT,wraplength=950,justify='left').pack(anchor='w',padx=12,pady=5)
    def button(tab,text,fn):tk.Button(tab,text=text,command=guarded(fn),bg=BG,fg=TEXT).pack(side='left',padx=5,pady=5)
    def world(x,y):return list(app.unprojected(x,y))
    label(tabs['Terreno'],'Selecciona un color uniforme del suelo y opcionalmente una región de terreno. Es una detección por color; revisa la línea antes de usarla para colisiones.')
    tolerance=tk.StringVar(value='35');row=tk.Frame(tabs['Terreno'],bg=PANEL);row.pack(fill='x');tk.Label(row,text='Tolerancia RGB',bg=PANEL,fg=TEXT).pack(side='left');tk.Entry(row,textvariable=tolerance,width=6).pack(side='left')
    def terrain():
        if not state['color'] or state['image'] is None:raise ValueError('Selecciona primero el color del terreno')
        vw,vh=app.viewport;im=state['crop'] or state['image'];box=state['box'] if state['crop'] else (0,0,vw,vh)
        result=detect_terrain(im,state['color'],int(tolerance.get()));points=[[x+box[0],y+box[1]] for x,y in result['points']]
        if len(points)<3:raise ValueError('Terreno insuficiente; elige otro color o región')
        canvas.delete('terrain');canvas.create_line(*[v for x,y in points for v in (x*800/vw,y*500/vh)],fill='#ffb86c',width=2,tags='terrain')
        surface=[world(x,y) for x,y in points];origin=int(surface[0][0]);width=int(surface[-1][0]-origin)+1
        if width>20000:raise ValueError('La escala de cámara produce un terreno demasiado grande')
        heights=[None]*width
        for (x1,y1),(x2,y2) in zip(surface,surface[1:]):
            if x2-x1>max(8,8/(app.live_camera or {}).get('scale',1)):continue
            for x in range(max(0,round(x1)-origin),min(width,round(x2)-origin+1)):
                heights[x]=y1+(y2-y1)*(x+origin-x1)/(x2-x1) if x2!=x1 else y1
        app.s.environment=dict(getattr(app.s,'environment',{}));app.s.environment['terrain']={'heights':heights,'originX':origin,'originY':0}
        app.mark();say('Terreno: %d columnas · cobertura %.0f%%. Revisa la línea naranja.'%(len(points),100*result['confidence']))
    button(row,'Detectar y aplicar',terrain)
    def clear_terrain():
        app.s.environment.pop('terrain',None);canvas.delete('terrain');app.mark();say('Terreno eliminado')
    button(row,'Quitar terreno',clear_terrain)
    label(tabs['Números OCR'],'OCR local por plantillas: enseña recortes conocidos de los dígitos del clon. No es una IA entrenada universal; debe recalibrarse si cambia fuente, tema o escala.')
    label_value=tk.StringVar(value='');field=tk.StringVar(value='angle');ocr_row=tk.Frame(tabs['Números OCR'],bg=PANEL);ocr_row.pack(fill='x');tk.Entry(ocr_row,textvariable=label_value,width=12).pack(side='left');ttk.Combobox(ocr_row,textvariable=field,values=['angle','wind','wind_angle'],width=12,state='readonly').pack(side='left',padx=5)
    use_color=tk.BooleanVar(value=False);tk.Checkbutton(tabs['Números OCR'],text='Usar color seleccionado para texto (si no: contraste con fondo)',variable=use_color,bg=PANEL,fg=TEXT,selectcolor=BG).pack(anchor='w')
    def fg():return state['color'] if use_color.get() else None
    def teach():
        if state['crop'] is None:raise ValueError('Arrastra un recorte que contenga solo el número conocido')
        ocr.learn(label_value.get(),state['crop'],fg());say('Aprendido: %s. Dígitos disponibles: %s'%(label_value.get(),''.join(sorted(ocr.templates))))
    def read():
        if state['crop'] is None:raise ValueError('Selecciona un recorte numérico')
        result=ocr.read(state['crop'],fg());say('Lectura: %s · confianza %.0f%%'%(result['text'],result['confidence']*100))
        if result['value'] is not None:
            v=result['value'];name=field.get()
            if name=='angle' and not 0<v<180 or name=='wind' and not 0<=v<=100 or name=='wind_angle' and not -360<=v<=360:raise ValueError('El número está fuera del rango del campo')
            app.vars[name].set(str(v));app.mark()
    button(ocr_row,'Enseñar',teach);button(ocr_row,'Leer y aplicar',read)
    def save_ocr():
        path=filedialog.asksaveasfilename(parent=win,defaultextension='.json',title='Guardar plantillas OCR')
        if path:ocr.save(path)
    def load_ocr():
        path=filedialog.askopenfilename(parent=win,filetypes=[('Plantillas JSON','*.json')])
        if path:ocr.load(path);say('Plantillas cargadas')
    button(ocr_row,'Guardar',save_ocr);button(ocr_row,'Cargar',load_ocr)
    label(tabs['Seguimiento'],'Selecciona el color de un proyectil visible. Captura su trayectoria al efectuar tú un disparo. Mantén cámara y área fijas; los cambios de cámara invalidan la aceleración medida. Esc o Detener finaliza.')
    trackrow=tk.Frame(tabs['Seguimiento'],bg=PANEL);trackrow.pack(fill='x')
    def track():
        if not app.screen_box:raise ValueError('Primero captura el área de pantalla del juego')
        if not state['color']:raise ValueError('Selecciona el color del proyectil')
        state['stop'].set();stop=threading.Event();state['stop']=stop;tracker=ColorTracker(state['color'],int(tolerance.get()));state['tracker']=tracker
        box=tuple(app.screen_box)
        def worker():
            until=time.monotonic()+12
            while not stop.is_set() and time.monotonic()<until:
                if ctypes.windll.user32.GetAsyncKeyState(0x1B)&0x8000:break
                image=ImageGrab.grab(bbox=box).resize(app.viewport);sample=tracker.sample(image,timestamp=time.monotonic())
                if sample:updates.put(lambda n=len(tracker.samples):say('Seguimiento: %d medidas'%n))
                stop.wait(.04)
            updates.put(lambda:say('Seguimiento terminado: %d medidas. Ajustar o exportar.'%len(tracker.samples)))
        threading.Thread(target=worker,daemon=True).start();say('Seguimiento activo durante 12 s; dispara tú y mantén la cámara fija')
    def fit():
        if not state['tracker']:raise ValueError('Primero registra una trayectoria')
        result=state['tracker'].fit()
        scale=(app.live_camera or {}).get('scale',1) or 1
        result['velocity']=[v/scale for v in result['velocity']];result['acceleration']=[v/scale for v in result['acceleration']]
        app.measured_trajectory=result;app.trajectory_samples=state['tracker'].samples
        say('Medido: aceleración x %.2f, y %.2f px/s² · error %.2f px. Motor avanzado permite calibrar.'%(*result['acceleration'],result['rms_pixels']))
    def export():
        if not state['tracker']:raise ValueError('No hay trayectoria')
        path=filedialog.asksaveasfilename(parent=win,defaultextension='.json',title='Guardar medidas de trayectoria')
        if path:Path(path).write_text(json.dumps({'samples':state['tracker'].samples,'coordinate_space':list(app.viewport),'camera_must_be_fixed':True},indent=2),encoding='utf-8')
    button(trackrow,'Registrar',track);button(trackrow,'Detener',lambda:state['stop'].set());button(trackrow,'Ajustar curva',fit);button(trackrow,'Exportar',export)
    label(tabs['Disparo'],'Un único disparo voluntario. Configura y verifica primero duración o barra. La cuenta regresiva permite dar foco al juego. Esc cancela. La simulación no envía entradas; el modo real requiere habilitación explícita por disparo.')
    controller=FireController();app.fire_controller=controller
    method=tk.StringVar(value='space');duration=tk.StringVar(value='1800');dry=tk.BooleanVar(value=True);armed=tk.BooleanVar(value=False)
    firingrow=tk.Frame(tabs['Disparo'],bg=PANEL);firingrow.pack(fill='x');ttk.Combobox(firingrow,textvariable=method,values=['space','bar'],width=9,state='readonly').pack(side='left');tk.Label(firingrow,text='Duración máxima ms',bg=PANEL,fg=TEXT).pack(side='left');tk.Entry(firingrow,textvariable=duration,width=7).pack(side='left');tk.Checkbutton(firingrow,text='Simulación',variable=dry,bg=PANEL,fg=TEXT,selectcolor=BG).pack(side='left');tk.Checkbutton(firingrow,text='Habilitar UN disparo',variable=armed,bg=PANEL,fg=TEXT,selectcolor=BG).pack(side='left')
    def capture(which):
        say('En 3 segundos selecciona la ventana del juego / coloca el cursor en la barra');win.withdraw();app.root.iconify()
        def finish():
            if which=='target':state['target']=controller.capture_target();message='Ventana: '+state['target'][2]
            else:
                class POINT(ctypes.Structure):_fields_=[('x',ctypes.c_long),('y',ctypes.c_long)]
                pt=POINT();ctypes.windll.user32.GetCursorPos(ctypes.byref(pt));state[which]=(pt.x,pt.y);message='Barra %s: %s'%(which,state[which])
            app.root.deiconify();win.deiconify();say(message)
        app.root.after(3000,finish)
    actions=tk.Frame(tabs['Disparo'],bg=PANEL);actions.pack(fill='x');button(actions,'Elegir ventana',lambda:capture('target'));button(actions,'Inicio barra',lambda:capture('start'));button(actions,'Fin barra',lambda:capture('end'))
    def fire():
        if not armed.get():raise ValueError('Habilita este disparo')
        if not state['target']:raise ValueError('Elige la ventana del juego')
        # Recompute current editable settings before every shot.
        app.compute();result=app.result
        if not result or not result.get('reachable') or not result.get('power'):raise ValueError('No existe una solución válida')
        timestamp=app.last_live if getattr(app,'worker',None) and app.worker.is_alive() else time.monotonic()
        plan=FirePlan(power=result['power'],max_power=app.s.max_power,method=method.get(),full_power_ms=float(duration.get()),bar_start=state['start'],bar_end=state['end'],data_time=timestamp,target_hwnd=state['target'][0],target_pid=state['target'][1])
        is_dry=dry.get();armed.set(False);controller.arm();win.withdraw();app.root.iconify()
        def worker():
            try:
                result=controller.fire(plan,dry_run=is_dry);text=('Simulación completada: ' if is_dry else 'Entrada de un disparo enviada: ')+json.dumps(result,ensure_ascii=False)
            except Exception as e:text=str(e)
            def finish():app.root.deiconify();win.deiconify();say(text)
            updates.put(finish)
        threading.Thread(target=worker,daemon=True).start()
    button(actions,'Ejecutar una vez',fire);button(actions,'Cancelar',controller.cancel)
    def close():state['closed']=True;state['stop'].set();controller.cancel();win.destroy()
    win.protocol('WM_DELETE_WINDOW',close)
    if app.image is not None:refresh()
    return win
