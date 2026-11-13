"""Passive sample and prediction review. This module never fits or fires a shot."""
import copy
import json
import tkinter as tk
from tkinter import ttk
from game_profiles import registered_profiles,get_profile
from mobile_catalog import MANUAL_MOBILES,SHOT_LABELS,mode_record
from catalog_ui import style_tables,details_text
from theme import BG,PANEL,FIELD,TEXT,MUTED,GREEN,FONT,MONO
from rounded_widgets import RoundedButton
from rounded_controls import RoundedChoice


def review_snapshot(app,game_id,mobile,shot):
    """Freeze numeric evidence and model metadata without modifying a store."""
    mode=mode_record(app,game_id,mobile,shot)
    if not mode:return None
    reviews=getattr(getattr(app,'shot_review',None),'records',[])
    # Legacy reviews without an explicit game stay unattributed. They cannot
    # corroborate one game merely because another happens to be selected.
    reviews=[copy.deepcopy(row) for row in reviews if isinstance(row,dict) and
             row.get('game_id',row.get('clone'))==game_id and row.get('mobile')==mobile and row.get('shot')==shot]
    return {'scope':{'game_id':game_id,'mobile':mobile,'shot':shot,'catalog_version':mode['schema_version']},
            'mode':mode,'accepted':copy.deepcopy(mode['record'].get('fit')),
            'candidate':copy.deepcopy(mode['record'].get('candidate')),
            'accepted_validation':copy.deepcopy(mode['record'].get('accepted_validation',[])),
            'samples':copy.deepcopy(mode['record'].get('samples',[])), 'reviews':reviews}


def comparison_text(snapshot):
    mode=snapshot['mode'];candidate=snapshot['candidate'] or {}
    text=details_text(mode)+'\n\nComparación de modelos\n'
    for label,fit in (('Aceptado local',snapshot['accepted']),('Candidato',candidate.get('fit'))):
        text+=label+':\n'
        if not fit:text+='  Sin modelo registrado.\n';continue
        for key in ('gravity','power_scale','speed_offset','wind_scale','wind_mode'):
            if key in fit:text+=f'  {key}: {fit[key]}\n'
    validation=candidate.get('validation',[])
    text+=f"\nCandidato: {len(candidate.get('training_ids',[]))} muestras de ajuste; {len(validation)} comprobaciones futuras registradas.\n"
    text+=f"Aceptado: {len(snapshot['accepted_validation'])} comprobaciones registradas; {mode['validation_count']} con evidencia utilizable.\n"
    for check in validation[-8:]:
        if isinstance(check,dict):text+='\n'+json.dumps({k:check.get(k) for k in ('id','power','candidate','baseline')},ensure_ascii=False)
    return text


def open_calibration(app,game_id=None,mobile=None,shot=None):
    existing=getattr(app,'calibration_window',None)
    if existing and existing.winfo_exists():
        existing.set_scope(game_id,mobile,shot);existing.lift();return existing
    win=tk.Toplevel(getattr(app,'ui_parent',None) or app.root);app.calibration_window=win
    win.title('DragonLab · Revisar calibración');win.geometry('1000x720');win.minsize(660,490);win.configure(bg=BG)
    style_tables(win)
    header=tk.Frame(win,bg=BG);header.pack(fill='x',padx=22,pady=(18,12))
    tk.Label(header,text='Revisar calibración',bg=BG,fg=TEXT,font=(FONT,23,'bold')).pack(anchor='w')
    tk.Label(header,text='Observación pasiva de tiros propios y comparación con datos registrados.',bg=BG,fg=MUTED,font=(FONT,10)).pack(anchor='w',pady=(4,0))
    controls=tk.Frame(win,bg=BG);controls.pack(fill='x',padx=22,pady=(0,12))
    profiles=registered_profiles(supported_only=True);names={p['name']:p['id'] for p in profiles}
    game=get_profile(game_id or getattr(app,'clone_id','dragonbound'))
    win.review_game=tk.StringVar(win,value=game['name'] if game and game['status']=='supported' else profiles[0]['name'])
    initial_mobile=mobile or getattr(getattr(app,'s',None),'mobile','ARMOR')
    win.review_mobile=tk.StringVar(win,value=initial_mobile if initial_mobile in MANUAL_MOBILES else 'ARMOR')
    initial_shot=shot if shot in (0,1,2) and not isinstance(shot,bool) else getattr(getattr(app,'s',None),'selected_shot',0)
    win.review_shot=tk.StringVar(win,value=SHOT_LABELS[initial_shot] if initial_shot in (0,1,2) else '1')
    for label,var,values,width in (('Juego',win.review_game,list(names),20),('Carro',win.review_mobile,MANUAL_MOBILES,17),('Bala',win.review_shot,SHOT_LABELS,7)):
        tk.Label(controls,text=label,bg=BG,fg=MUTED,font=(FONT,10)).pack(side='left',padx=(0,6))
        RoundedChoice(controls,textvariable=var,values=values,state='readonly',width=width,font=(FONT,-12)).pack(side='left',padx=(0,10))
    notebook=ttk.Notebook(win);notebook.pack(fill='both',expand=True,padx=22)
    model_tab=tk.Frame(notebook,bg=PANEL);samples_tab=tk.Frame(notebook,bg=PANEL);review_tab=tk.Frame(notebook,bg=PANEL)
    notebook.add(model_tab,text='Modelos y comprobaciones');notebook.add(samples_tab,text='Muestras registradas');notebook.add(review_tab,text='Errores de recorrido')
    detail=tk.Text(model_tab,bg=PANEL,fg=TEXT,relief='flat',wrap='word',font=(FONT,11),padx=16,pady=14,state='disabled')
    scroll=ttk.Scrollbar(model_tab,command=detail.yview);scroll.pack(side='right',fill='y');detail.pack(fill='both',expand=True);detail.configure(yscrollcommand=scroll.set)
    def make_table(parent,columns):
        table=ttk.Treeview(parent,columns=[c[0] for c in columns],show='headings',style='Catalog.Treeview')
        for key,label,width in columns:table.heading(key,text=label);table.column(key,width=width,minwidth=55)
        sy=ttk.Scrollbar(parent,orient='vertical',command=table.yview);sx=ttk.Scrollbar(parent,orient='horizontal',command=table.xview)
        table.configure(yscrollcommand=sy.set,xscrollcommand=sx.set);table.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns');sx.grid(row=1,column=0,sticky='ew')
        parent.grid_rowconfigure(0,weight=1);parent.grid_columnconfigure(0,weight=1);return table
    win.sample_table=make_table(samples_tab,(('id','Muestra',170),('power','Fuerza',70),('wind','Viento',70),('angle','Ángulo viento',100),('speed','vx / vy',180),('acceleration','ax / ay',180),('source','Fuente',210)))
    win.review_table=make_table(review_tab,(('phase','Fase',150),('power','Fuerza',70),('error','Error final (px)',120),('source','Fuente',210),('updated','Registro',140)))
    footer=tk.Frame(win,bg=BG);footer.pack(fill='x',padx=22,pady=14)
    state=tk.Label(footer,text='',bg=BG,fg=MUTED,font=(FONT,10),anchor='w',justify='left',wraplength=600);state.pack(side='left',fill='x',expand=True)
    win.frozen_snapshot=None
    def render(*_):
        snapshot=win.frozen_snapshot or review_snapshot(app,names[win.review_game.get()],win.review_mobile.get(),SHOT_LABELS.index(win.review_shot.get()))
        win.current_snapshot=snapshot
        stamp=json.dumps([bool(win.frozen_snapshot),snapshot],sort_keys=True,default=str)
        if getattr(win,'review_stamp',None)==stamp:return
        win.review_stamp=stamp
        detail.configure(state='normal');detail.delete('1.0','end');detail.insert('1.0',comparison_text(snapshot));detail.configure(state='disabled')
        for table in (win.sample_table,win.review_table):table.delete(*table.get_children())
        for sample in snapshot['samples']:
            if not isinstance(sample,dict):continue
            win.sample_table.insert('','end',values=(sample.get('sample_id','Sin ID'),sample.get('power','—'),sample.get('wind','—'),sample.get('wind_angle','—'),
                f"{sample.get('vx','—')} / {sample.get('vy','—')}",f"{sample.get('ax','—')} / {sample.get('ay','—')}",sample.get('source','Sin fuente')))
        for review in snapshot['reviews']:
            win.review_table.insert('','end',values=(review.get('phase','—'),review.get('power','—'),review.get('endpoint_error','—'),review.get('source','—'),review.get('updated','—')))
        scope=snapshot['scope'];state.configure(text=('Comparación fijada en memoria. ' if win.frozen_snapshot else 'Vista actual. ')+
            f"{scope['game_id']} / {scope['mobile']} / {SHOT_LABELS[scope['shot']]} · {len(snapshot['reviews'])} revisiones atribuidas.\n"
            'Las muestras de ajuste y las comprobaciones futuras se muestran por separado.')
    def freeze():
        if win.frozen_snapshot:win.frozen_snapshot=None;freeze_button.configure(text='Fijar comparación')
        else:win.frozen_snapshot=copy.deepcopy(win.current_snapshot);freeze_button.configure(text='Volver a datos actuales')
        render()
    freeze_button=RoundedButton(footer,text='Fijar comparación',command=freeze,font=(FONT,10),bg=FIELD,fg=TEXT);freeze_button.pack(side='right')
    footer.bind('<Configure>',lambda event:state.configure(wraplength=max(200,event.width-freeze_button.winfo_reqwidth()-18)))
    win.freeze_comparison=freeze
    def change(*_):
        win.frozen_snapshot=None;freeze_button.configure(text='Fijar comparación');render()
    for var in (win.review_game,win.review_mobile,win.review_shot):var.trace_add('write',change)
    def set_scope(game_id=None,mobile=None,shot=None):
        profile=get_profile(game_id)
        if profile and profile['name'] in names:win.review_game.set(profile['name'])
        if mobile in MANUAL_MOBILES:win.review_mobile.set(mobile)
        if not isinstance(shot,bool) and shot in (0,1,2):win.review_shot.set(SHOT_LABELS[shot])
    win.set_scope=set_scope;win.refresh_review=render
    def tick():
        if win.winfo_exists():render();win.refresh_job=win.after(2000,tick)
    def cancel(event):
        if event.widget==win and getattr(win,'refresh_job',None):
            try:win.after_cancel(win.refresh_job)
            except tk.TclError:pass
    win.bind('<Destroy>',cancel);win.bind('<Escape>',lambda e:win.destroy());tick();return win
