"""Lightweight native UI for the playing companion."""
import tkinter as tk
from rounded_controls import RoundedChoice,RoundedSwitch,RoundedEntry,RoundedTabs,RoundedTable,RoundedScroll
from tkinter import ttk
from rounded_widgets import RoundedPanel,RoundedButton
BG='#11191c';PANEL='#1a262b';TEXT='#edf4f1';MUTED='#a4b6b2';GREEN='#72dfba';ORANGE='#ffb86c';LINE='#2d4147'

def build(app,prefs):
    root=app.root
    style=ttk.Style();style.configure('TCombobox',padding=6,arrowsize=14)
    header=tk.Frame(root,bg=BG);header.pack(fill='x',padx=26,pady=(22,16))
    brand=tk.Frame(header,bg=BG);brand.pack(side='left')
    tk.Label(brand,text='DragonLab',font=('Bahnschrift',26,'bold'),fg=TEXT,bg=BG).pack(anchor='w')
    app.brand_caption=tk.Label(brand,text='GUÍA DE TIRO',font=('Bahnschrift',9),fg=MUTED,bg=BG);app.brand_caption.pack(anchor='w',pady=(2,0))
    app.button(header,'Ajustes',app.open_settings).pack(side='right',padx=(10,0))
    open_button=app.button(header,'Abrir juego',app.open_game_browser);open_button.configure(bg=GREEN,fg=BG,activeforeground=BG,activebackground='#9beacd');open_button.pack(side='right')
    state=tk.Frame(root,bg=BG);state.pack(fill='x',padx=26,pady=(0,14))
    app.status=tk.Label(state,text='●  Esperando partida',font=('Bahnschrift',11),fg=MUTED,bg=BG);app.status.pack(side='left')
    app.connect=app.button(state,'Pausar captura',app.toggle_live);app.connect.configure(bg=BG,fg=MUTED,pady=3);app.connect.pack(side='right')
    control_panel=RoundedPanel(root,PANEL);control_panel.pack(fill='x',padx=26,pady=(0,12));controls=control_panel.body
    vehicle=tk.Frame(controls,bg=PANEL);vehicle.pack(side='left',padx=16,pady=12)
    tk.Label(vehicle,text='VEHÍCULO',font=('Bahnschrift',9),fg=MUTED,bg=PANEL).pack(anchor='w')
    app.vehicle_label=tk.Label(vehicle,text='Por detectar',font=('Bahnschrift',13,'bold'),fg=TEXT,bg=PANEL);app.vehicle_label.pack(anchor='w',pady=(3,0))
    target=tk.Frame(controls,bg=PANEL);target.pack(side='right',padx=16,pady=10)
    tk.Label(target,text='OBJETIVO',font=('Bahnschrift',9),fg=MUTED,bg=PANEL).pack(anchor='w',pady=(0,5))
    app.target_name=tk.StringVar(value='Automático');app.target_box=RoundedChoice(target,textvariable=app.target_name,values=['Objetivo automático'],state='readonly',width=24);app.target_box.pack();app.target_box.bind('<<ComboboxSelected>>',lambda e:app.select_target())
    app.trajectory_enabled=tk.BooleanVar(value=bool(prefs.get('trajectories',True)));app.guide_enabled=tk.BooleanVar(value=bool(prefs.get('guide',True)));app.auto_guide_enabled=app.guide_enabled.get()
    app.canvas=tk.Canvas(root,bg='#0c1518',highlightthickness=0);app.canvas.bind('<Button-1>',app.click);app.canvas.bind('<Configure>',lambda e:app.draw())
    summary_panel=RoundedPanel(root,PANEL);app.summary_panel=summary_panel;summary_panel.pack(fill='x',padx=26);summary=summary_panel.body
    top=tk.Frame(summary,bg=PANEL);top.pack(fill='x',padx=20,pady=(18,0))
    tk.Label(top,text='FUERZA',font=('Bahnschrift',10,'bold'),fg=MUTED,bg=PANEL).pack(side='left')
    app.preview_button=app.button(top,'Ver mapa',app.toggle_preview);app.preview_button.configure(bg=PANEL,fg=GREEN,pady=2);app.preview_button.pack(side='right')
    reading=tk.Frame(summary,bg=PANEL);reading.pack(fill='x',padx=18,pady=(2,0))
    app.power=tk.Label(reading,text='—',font=('Bahnschrift',76,'bold'),bg=PANEL,fg=GREEN);app.power.pack(side='left',padx=(0,20))
    info=tk.Frame(reading,bg=PANEL);info.pack(side='left',fill='x',expand=True)
    app.details=tk.Label(info,text='Abre el juego e inicia una partida.\nLa guía aparecerá automáticamente.',font=('Bahnschrift',12),bg=PANEL,fg=TEXT,justify='left',anchor='w',wraplength=360);app.details.pack(anchor='w',fill='x')
    app.confidence=tk.Label(info,text='Faltan datos',font=('Bahnschrift',10),fg=MUTED,bg=PANEL,justify='left',wraplength=340);app.confidence.pack(anchor='w',pady=(8,0))
    app.force_canvas=tk.Canvas(summary,height=67,bg=PANEL,highlightthickness=0);app.force_canvas.pack(fill='x',padx=18,pady=(0,12));app.force_canvas.bind('<Configure>',lambda e:app.draw_force())
    shortcuts=tk.Frame(root,bg=BG);app.shortcut_row=shortcuts;shortcuts.pack(fill='x',padx=26,pady=(16,0))
    def hint(label):
        frame=tk.Frame(shortcuts,bg=BG);frame.pack(side='left',padx=(0,24))
        key=RoundedButton(frame,text='',font=('Bahnschrift',11,'bold'),fg=TEXT,bg=PANEL,activebackground=PANEL,activeforeground=TEXT,padx=9,pady=5,takefocus=False);key.pack(side='left')
        tk.Label(frame,text=label,font=('Bahnschrift',10),fg=MUTED,bg=BG).pack(side='left',padx=8)
        return key
    app.target_hint=hint('Cambiar objetivo');app.fire_hint=hint('Tiro con la fuerza calculada')
    app.footer=tk.Label(root,text='La guía se muestra sobre la ventana del juego.',bg=BG,fg=MUTED,font=('Bahnschrift',10),anchor='w',justify='left',wraplength=660);app.footer.pack(fill='x',padx=26,pady=(10,16))
    refresh(app);apply_layout(app)

def refresh(app):
    if hasattr(app,'book'):
        c=app.book.confidence(app.clone_id,app.s.mobile,app.s.selected_shot,app.s.wind)
        result=app.display_result()
        if not app.has_position_data:text='Aprendiendo · esperando posiciones';color=MUTED
        elif result.get('blocked'):text='Bloqueado · la roca corta el recorrido';color=ORANGE
        elif not result.get('reachable'):text='Bloqueado · cambia el ángulo';color=ORANGE
        elif c['level']=='measured' and not result.get('interactions') and not result.get('deployment') and app.s.mobile not in ('NAK','KALSIDDON','TRICO'):
            text='Listo · salida calibrada';color=GREEN
        else:text='Aprendiendo · guía estimada';color=MUTED
        app.confidence.config(text=text,fg=color)
    app.target_hint.config(text=app.target_key)
    app.fire_hint.config(text=app.fire_key if app.auto_shot_enabled else 'OFF',fg=TEXT if app.auto_shot_enabled else MUTED)


def apply_layout(app):
    if app.compact:
        app.shortcut_row.pack_forget();app.brand_caption.pack_forget()
    else:
        app.brand_caption.pack(anchor='w',pady=(2,0));app.shortcut_row.pack(fill='x',padx=26,pady=(16,0),before=app.footer)
    app.root.minsize(680,540 if app.compact else 620)
    app.root.geometry('760x820' if app.map_expanded else '760x540' if app.compact else '760x620')
    app.power.config(font=('Bahnschrift',64 if app.compact else 76,'bold'))
    app.details.config(font=('Bahnschrift',14 if app.large_text else 12))
    app.confidence.config(font=('Bahnschrift',12 if app.large_text else 10))
    app.target_box.config(font=('Bahnschrift',13 if app.large_text else 10))
    app.footer.config(font=('Bahnschrift',12 if app.large_text else 10))
