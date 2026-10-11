"""Staged settings for the player's companion."""
import tkinter as tk
from rounded_controls import RoundedChoice,RoundedSwitch,RoundedEntry,RoundedTabs,RoundedTable,RoundedScroll
from tkinter import ttk
from rounded_widgets import RoundedPanel,RoundedButton
from shortcuts import KEYS,validate_bindings
from ui_shell import BG,PANEL,TEXT,MUTED,GREEN,refresh,apply_layout

def open_settings(app):
    existing=getattr(app,'settings_window',None)
    if existing and existing.winfo_exists():existing.lift();return existing
    win=tk.Toplevel(getattr(app,'ui_parent',app.root));app.settings_window=win;win.title('DragonLab · Ajustes');height=min(720,max(540,win.winfo_screenheight()-100));win.geometry(f'620x{height}');win.minsize(620,min(640,height));win.configure(bg=BG)
    tk.Label(win,text='Ajustes',bg=BG,fg=TEXT,font=('Bahnschrift',25,'bold')).pack(anchor='w',padx=26,pady=(18,4))
    tk.Label(win,text='Guía y controles',bg=BG,fg=MUTED,font=('Bahnschrift',11)).pack(anchor='w',padx=26,pady=(0,14))
    feedback=tk.Label(win,text='',bg=BG,fg='#ffb86c',font=('Bahnschrift',10),wraplength=440);feedback.pack(fill='x',padx=26)
    actions=tk.Frame(win,bg=BG);actions.pack(side='bottom',fill='x',padx=26,pady=12)
    holder=tk.Frame(win,bg=BG);holder.pack(fill='both',expand=True)
    viewport=tk.Canvas(holder,bg=BG,highlightthickness=0);viewport.pack(side='left',fill='both',expand=True)
    scroll=RoundedScroll(holder,orient='vertical',command=viewport.yview);scroll.pack(side='right',fill='y');viewport.configure(yscrollcommand=scroll.set)
    content=tk.Frame(viewport,bg=BG);item=viewport.create_window(0,0,window=content,anchor='nw')
    content.bind('<Configure>',lambda e:viewport.configure(scrollregion=viewport.bbox('all')))
    viewport.bind('<Configure>',lambda e:viewport.itemconfigure(item,width=e.width))
    def wheel(event):
        if not isinstance(event.widget,RoundedChoice):viewport.yview_scroll(-int(event.delta/120),'units')
    win.bind('<MouseWheel>',wheel)
    def section(title):
        panel=RoundedPanel(content,PANEL);panel.pack(fill='x',padx=26,pady=(0,10));frame=panel.body
        tk.Label(frame,text=title,font=('Bahnschrift',10,'bold'),fg=MUTED,bg=PANEL).pack(anchor='w',padx=16,pady=(4,4))
        return frame
    display=section('EN EL JUEGO')
    paths=tk.BooleanVar(value=app.trajectory_enabled.get());guide=tk.BooleanVar(value=app.guide_enabled.get());auto=tk.BooleanVar(value=app.auto_shot_enabled)
    compact=tk.BooleanVar(value=app.compact);large=tk.BooleanVar(value=app.large_text)
    options=[('Trayectorias de las balas',paths),('Marca de fuerza recomendada',guide)]
    if not getattr(app,'embedded',False):options += [('Ventana compacta',compact),('Texto grande',large)]
    for text,var in options:
        RoundedSwitch(display,text=text,variable=var,bg=PANEL,fg=TEXT,activebackground=PANEL,activeforeground=TEXT,selectcolor=BG,font=('Bahnschrift',12),padx=3,pady=2).pack(anchor='w',padx=12)
    tk.Frame(display,bg=PANEL,height=4).pack()
    colors=tk.StringVar(value=app.path_color);width=tk.StringVar(value=str(app.path_width))
    visual=tk.Frame(display,bg=PANEL);visual.pack(fill='x',padx=16,pady=(4,8))
    tk.Label(visual,text='Líneas',bg=PANEL,fg=TEXT,font=('Bahnschrift',11)).pack(side='left')
    RoundedChoice(visual,textvariable=colors,values=['Menta','Azul'],state='readonly',width=10).pack(side='left',padx=14)
    tk.Label(visual,text='Grosor',bg=PANEL,fg=TEXT,font=('Bahnschrift',11)).pack(side='left')
    RoundedChoice(visual,textvariable=width,values=['1','2','3','4','5'],state='readonly',width=4).pack(side='left',padx=14)
    keys=section('ATAJOS')
    target=tk.StringVar(value=app.target_key);fire=tk.StringVar(value=app.fire_key);performance=tk.StringVar(value=app.performance)
    grid=tk.Frame(keys,bg=PANEL);grid.pack(fill='x',padx=16);grid.columnconfigure(0,weight=1)
    for row,(label,var,values) in enumerate([('Cambiar objetivo',target,list(KEYS)),('Disparar una vez',fire,[k for k in KEYS if k!='Ctrl'])]):
        tk.Label(grid,text=label,bg=PANEL,fg=TEXT,font=('Bahnschrift',12)).grid(row=row,column=0,sticky='w',pady=4)
        RoundedChoice(grid,textvariable=var,values=values,state='readonly',width=10).grid(row=row,column=1,sticky='e')
    RoundedSwitch(keys,text='Habilitar tiro por atajo',variable=auto,bg=PANEL,fg=TEXT,activebackground=PANEL,activeforeground=TEXT,selectcolor=BG,font=('Bahnschrift',11)).pack(anchor='w',padx=12,pady=(6,0))
    tk.Label(keys,text='Pulsa y suelta el atajo una vez, sin mover ni ajustar ángulo.\nFunciona en tu turno con el juego en primer plano.\nEsc libera la entrada; una carga iniciada puede lanzar parcialmente.',justify='left',bg=PANEL,fg=MUTED,font=('Bahnschrift',10)).pack(anchor='w',padx=16,pady=(5,6))
    speed=section('RENDIMIENTO')
    from diagnostics_ui import open_diagnostics
    if not getattr(app,'embedded',False):RoundedButton(speed,text='Ver diagnóstico',command=lambda:open_diagnostics(app)).pack(anchor='w',padx=16,pady=(0,6))
    row=tk.Frame(speed,bg=PANEL);row.pack(fill='x',padx=16)
    tk.Label(row,text='Modo',bg=PANEL,fg=TEXT,font=('Bahnschrift',12)).pack(side='left')
    RoundedChoice(row,textvariable=performance,values=['Auto','Ligero','Normal'],state='readonly',width=10).pack(side='right')
    tk.Label(speed,text='Auto adapta la captura a la carga; Ligero reduce la frecuencia.',bg=PANEL,fg=MUTED,font=('Bahnschrift',10)).pack(anchor='w',padx=16,pady=(6,6))
    def save():
        try:
            validate_bindings(target.get(),fire.get())
            app.target_key=target.get();app.fire_key=fire.get();app.auto_shot_enabled=auto.get();app.performance=performance.get()
            app.trajectory_enabled.set(paths.get());app.guide_enabled.set(guide.get());app.compact=compact.get();app.large_text=large.get();app.path_color=colors.get();app.path_width=int(width.get())
            app.shortcuts.set_bindings(app.target_key,app.fire_key);app.persist_preferences();app.refresh_visibility();refresh(app);apply_layout(app)
            app.footer.config(text='Ajustes guardados');win.destroy()
        except (ValueError,OSError) as error:feedback.config(text=str(error))
    def advanced():
        from settings_panel import open_settings as tools
        win.destroy();tools(app)
    if not getattr(app,'embedded',False):app.button(actions,'Opciones avanzadas',advanced).pack(side='left')
    save_button=app.button(actions,'Guardar cambios',save);save_button.configure(bg=GREEN,fg=BG,activebackground='#9beacd',activeforeground=BG);save_button.pack(side='right')
    win.bind('<Escape>',lambda e:win.destroy());return win
