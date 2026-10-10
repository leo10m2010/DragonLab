"""Secondary settings keep the playing screen small and uncluttered."""
import tkinter as tk,json,pathlib
from tkinter import ttk,filedialog,messagebox
from core import PROFILES
BG='#101c26';PANEL='#162735';TEXT='#ecf3f7';GREEN='#72dfba';MUTED='#96acb9'

def open_settings(app):
    win=tk.Toplevel(app.root);win.title('DragonLab · Ajustes');win.geometry('780x660');win.configure(bg=BG)
    tk.Label(win,text='AJUSTES',font=('Bahnschrift',22,'bold'),bg=BG,fg=TEXT).pack(anchor='w',padx=20,pady=14)
    book=ttk.Notebook(win);book.pack(fill='both',expand=True,padx=20,pady=(0,18))
    general=tk.Frame(book,bg=PANEL);cars=tk.Frame(book,bg=PANEL);extra=tk.Frame(book,bg=PANEL)
    book.add(general,text='Uso manual');book.add(cars,text='Vehículos');book.add(extra,text='Herramientas')
    tk.Label(general,text='En automático, el juego completa estos datos. Puedes ajustarlos para una captura manual.',bg=PANEL,fg=MUTED,wraplength=690,justify='left').pack(anchor='w',padx=16,pady=14)
    mobile=ttk.Combobox(general,textvariable=app.mobile,values=list(PROFILES),state='readonly');mobile.pack(fill='x',padx=16,pady=5);mobile.bind('<<ComboboxSelected>>',lambda e:app.change_mobile())
    grid=tk.Frame(general,bg=PANEL);grid.pack(fill='x',padx=16,pady=8)
    labels={'angle':'Ángulo','wind':'Viento','wind_angle':'Dirección del viento','body_angle':'Inclinación','gravity':'Gravedad','wind_scale':'Respuesta al viento','power_scale':'Velocidad / fuerza'}
    for i,(key,label) in enumerate(labels.items()):
        tk.Label(grid,text=label,bg=PANEL,fg=TEXT).grid(row=i,column=0,sticky='w',pady=4)
        tk.Entry(grid,textvariable=app.vars[key],bg=BG,fg=TEXT,insertbackground=TEXT,width=14).grid(row=i,column=1,padx=15,pady=4)
    for label,cmd in [('Capturar área',app.capture_area),('Abrir imagen',app.open_image),('Marcar mi posición',lambda:app.set_mode('hero')),('Marcar objetivo',lambda:app.set_mode('target'))]:
        app.button(general,label,lambda cmd=cmd:(win.destroy(),cmd())).pack(side='left',padx=6,pady=10)
    tk.Label(cars,text='Los tiros medibles se guardan solos, separados por vehículo y tipo de tiro. Se comprueban fuerzas distintas antes de aplicar un ajuste. Los perfiles base siguen pendientes de validación.',bg=PANEL,fg=MUTED,wraplength=690,justify='left').pack(anchor='w',padx=16,pady=12)
    table=ttk.Treeview(cars,columns=('vehicle','status','shots'),show='headings',height=15)
    for key,label,width in [('vehicle','Vehículo',150),('status','Estado',350),('shots','Tiros',65)]:table.heading(key,text=label);table.column(key,width=width,stretch=key=='status')
    table.pack(fill='both',expand=True,padx=16,pady=6)
    note=tk.Label(cars,text='',bg=PANEL,fg=GREEN,wraplength=690);note.pack(fill='x',padx=16,pady=7)
    def refresh():
        if not win.winfo_exists():return
        rows=app.book.rows(app.clone_id)
        for name,status,count in rows:
            if table.exists(name):table.item(name,values=(name,status,count))
            else:table.insert('', 'end',iid=name,values=(name,status,count))
        note.config(text=app.book.message);win.after(1500,refresh)
    refresh()
    def import_measures():
        path=filedialog.askopenfilename(parent=win,filetypes=[('Mediciones por vehículo','*.json')])
        if not path:return
        try:
            data=json.loads(pathlib.Path(path).read_text(encoding='utf-8-sig'));count=app.book.import_samples(data.get('samples',data) if isinstance(data,dict) else data,app.clone_id)
            app.profile_stamp=None;app.mark();note.config(text=f'{count} perfiles ajustados con mediciones importadas')
        except Exception as e:messagebox.showerror('Mediciones',str(e),parent=win)
    row=tk.Frame(cars,bg=PANEL);row.pack(fill='x',padx=10,pady=10)
    app.button(row,'Importar mediciones',import_measures).pack(side='left',padx=6)
    app.button(row,'Calibrar un tiro',app.calibrate).pack(side='left',padx=6)
    app.button(row,'Guardar ajuste',app.save_profile).pack(side='left',padx=6)
    from advanced import open_advanced
    from vision_tools import open_tools
    tk.Label(extra,text='Estas herramientas siguen disponibles en segundo plano. No hace falta abrirlas para jugar con la captura automática.',bg=PANEL,fg=MUTED,wraplength=680,justify='left').pack(anchor='w',padx=16,pady=16)
    for label,cmd in [('Modelo, conexiones y climas',lambda:open_advanced(app)),('Medición de terreno y proyectiles',lambda:open_tools(app)),('Guardar sesión',app.save_session),('Cargar sesión',app.load_session),('Visor de celular',app.share),('Marcar barra manualmente',lambda:__import__('strength_guide').select_game_bar(app))]:app.button(extra,label,cmd).pack(fill='x',padx=16,pady=5)
    return win
