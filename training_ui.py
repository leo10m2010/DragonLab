"""One temporary rounded control panel; no automatic start on app launch."""
import tkinter as tk
import threading,time
from rounded_widgets import RoundedPanel,RoundedButton
from rounded_controls import RoundedChoice
from ui_shell import BG,PANEL,TEXT,MUTED,GREEN

def settings_provider(app):
    def request(state,cancel):
        ready=threading.Event();response={}
        app.events.put({'status':'training-settings','state':state,'ready':ready,'response':response})
        deadline=time.monotonic()+2
        while not ready.wait(.025):
            if cancel.is_set() or time.monotonic()>deadline:raise RuntimeError('El Lab no confirmó los datos del tiro')
        if 'error' in response:raise RuntimeError(response['error'])
        return response['settings']
    return request

def start_training(app,limit='40',background=True,objective='adaptive'):
    if app.clone_id!='dragonbound':raise ValueError('Elige DragonBound en la pantalla principal.')
    if app.training_session and app.training_session.running:return app.training_session
    from training_session import TrainingSession
    endpoint=getattr(app,'live_endpoint',None) or app.endpoint.get()
    if getattr(app,'last_live',0)==0:endpoint='http://127.0.0.1:9223'
    if limit not in ('20','40'):raise ValueError('La prueba admite 20 o 40 tiros como máximo')
    from control_lifecycle import prepare_training
    prepare_training(app)
    continuous=False
    app.training_session=TrainingSession(endpoint,app.browser_target,app.book.path,app.events.put,max_shots=60 if continuous else int(limit),continuous=continuous,autonomous=True,objective=objective,background=background,allow_dual=True,max_matches=6,max_seconds=900)
    from training_progress import lab_summary
    app.training_session.lab_progress=lab_summary(app.book)
    app.training_session.start();return app.training_session

def open_training(app):
    from rounded_widgets import RoundedProgress
    from training_progress import coverage_report,TRAINING_MOBILES
    win=getattr(app,'training_window',None)
    if win and win.winfo_exists():win.lift();return win
    win=tk.Toplevel(getattr(app,'ui_parent',app.root));app.training_window=win
    win.title('DragonLab · Aprendizaje');height=min(680,max(500,win.winfo_screenheight()-100))
    win.geometry(f'640x{height}');win.minsize(580,min(540,height));win.configure(bg=BG)
    win.columnconfigure(0,weight=1);win.rowconfigure(2,weight=1)
    tk.Label(win,text='Juego adaptativo',bg=BG,fg=TEXT,font=('Bahnschrift',23,'bold')).grid(row=0,column=0,sticky='w',padx=24,pady=(18,4))
    status=tk.Label(win,text='DragonBound · Avatar Off',bg=BG,fg=MUTED,font=('Bahnschrift',10),wraplength=570,justify='left')
    status.grid(row=1,column=0,sticky='ew',padx=24,pady=(0,10))
    holder=tk.Frame(win,bg=BG);holder.grid(row=2,column=0,sticky='nsew',padx=20)
    from rounded_controls import RoundedScroll
    viewport=tk.Canvas(holder,bg=BG,highlightthickness=0);viewport.pack(side='left',fill='both',expand=True)
    scroll=RoundedScroll(holder,command=viewport.yview);scroll.pack(side='right',fill='y');viewport.configure(yscrollcommand=scroll.set)
    content=tk.Frame(viewport,bg=BG);item=viewport.create_window(0,0,window=content,anchor='nw')
    viewport.bind('<Configure>',lambda e:viewport.itemconfigure(item,width=e.width))
    content.bind('<Configure>',lambda e:viewport.configure(scrollregion=viewport.bbox('all')))
    win.bind('<MouseWheel>',lambda e:viewport.yview_scroll(-int(e.delta/120),'units') if not isinstance(e.widget,RoundedChoice) else None)
    trial_card=RoundedPanel(content,PANEL);trial_card.pack(fill='x',pady=(0,10))
    tk.Label(trial_card.body,text='Prueba actual · carros y modalidades con datos',bg=PANEL,fg=TEXT,font=('Bahnschrift',13,'bold')).pack(anchor='w',padx=16,pady=(8,4))
    result_label=tk.Label(trial_card.body,bg=PANEL,fg=GREEN,font=('Bahnschrift',11),justify='left',wraplength=520);result_label.pack(anchor='w',padx=16,pady=(0,10))
    card=RoundedPanel(content,PANEL);card.pack(fill='x',pady=(0,10));body=card.body
    headline=tk.Label(body,text='Calibración de salida',bg=PANEL,fg=TEXT,font=('Bahnschrift',13,'bold'));headline.pack(anchor='w',padx=16,pady=(8,4))
    launch=tk.Label(body,bg=PANEL,fg=GREEN,font=('Bahnschrift',18,'bold'));launch.pack(anchor='w',padx=16)
    launch_bar=RoundedProgress(body);launch_bar.pack(fill='x',padx=16,pady=(8,6))
    tk.Label(body,text='Porcentaje de modelos de salida validados: 17 carros × 3 modalidades.\nNo mide precisión de impactos ni dominio de todos los climas.',justify='left',bg=PANEL,fg=MUTED,font=('Bahnschrift',10),wraplength=520).pack(anchor='w',padx=16,pady=(0,10))
    row=tk.Frame(body,bg=PANEL);row.pack(fill='x',padx=16,pady=6)
    vehicle=tk.StringVar(value=app.s.mobile if getattr(getattr(app,'s',None),'mobile',None) in TRAINING_MOBILES else 'ARMOR')
    tk.Label(row,text='Ver carro',bg=PANEL,fg=TEXT,font=('Bahnschrift',11)).pack(side='left')
    choice=RoundedChoice(row,textvariable=vehicle,values=TRAINING_MOBILES,width=16);choice.pack(side='right')
    details=tk.Label(body,bg=PANEL,fg=TEXT,font=('Bahnschrift',11),justify='left',wraplength=520);details.pack(anchor='w',padx=16,pady=(4,12))
    lab_card=RoundedPanel(content,PANEL);lab_card.pack(fill='x',pady=(0,10));lab_label=tk.Label(lab_card.body,bg=PANEL,fg=TEXT,font=('Bahnschrift',12,'bold'));lab_label.pack(anchor='w',padx=16,pady=(8,6))
    lab_bar=RoundedProgress(lab_card.body);lab_bar.pack(fill='x',padx=16,pady=(0,8))
    evidence=tk.Label(lab_card.body,bg=PANEL,fg=MUTED,font=('Bahnschrift',10),wraplength=520,justify='left');evidence.pack(anchor='w',padx=16,pady=(0,10))
    tk.Label(content,text='Puntería y autonomía completa: pendientes de evaluación.\nEstos porcentajes no estiman cuánto tiempo falta.',justify='left',bg=BG,fg=MUTED,font=('Bahnschrift',10),wraplength=540).pack(anchor='w',padx=8,pady=(0,8))
    controls=tk.Frame(win,bg=BG);controls.grid(row=3,column=0,sticky='ew',padx=24,pady=6)
    tk.Label(controls,text='Duración',bg=BG,fg=MUTED,font=('Bahnschrift',10)).pack(side='left')
    tk.Label(controls,text='Modo',bg=BG,fg=MUTED,font=('Bahnschrift',10)).pack(side='left',padx=(16,4))
    mode=tk.StringVar(value='Segundo plano');mode_choice=RoundedChoice(controls,textvariable=mode,values=['Segundo plano','Juego al frente'],width=16);mode_choice.pack(side='left')
    limit=tk.StringVar(value='40');duration=RoundedChoice(controls,textvariable=limit,values=['20','40'],width=11);duration.pack(side='right')
    actions=tk.Frame(win,bg=BG);actions.grid(row=4,column=0,sticky='ew',padx=24,pady=(4,8))
    def stop():
        if app.training_session:app.training_session.stop()
    def start():
        try:start_training(app,limit.get(),background=mode.get()=='Segundo plano')
        except (ValueError,RuntimeError) as error:status.config(text=str(error))
    stop_button=RoundedButton(actions,text='Detener',command=stop);stop_button.pack(side='left')
    start_button=RoundedButton(actions,text='Empezar',command=start,bg=GREEN,fg=BG);start_button.pack(side='right')
    tk.Label(win,text='1 · 2 · SS según datos · DD con comprobación. Detener cancela la sesión.',bg=BG,fg=MUTED,font=('Bahnschrift',10)).grid(row=5,column=0,sticky='w',padx=24,pady=(0,12))
    def refresh():
        if not win.winfo_exists():return
        session=app.training_session;learner=session.learner if session else None
        running=bool(session and session.running)
        for control,state in [(start_button,'disabled' if running else 'normal'),(stop_button,'normal' if running else 'disabled'),(duration,'disabled' if running else 'readonly'),(mode_choice,'disabled' if running else 'readonly')]:
            if control.cget('state')!=state:control.config(state=state)
        if not session:result_label.config(text='La prueba separa calibración y evaluación.\nSolo considera dirigidos los tiros con una solución comprobada.')
        if session:
            trial=session.trial.summary() if session.trial else None
            detail=f" · Calibración {trial['calibration_shots']}/{trial['exploration_budget']} · Dirigidos {trial['directed_test_shots']} · Omitidos {trial['skipped_turns']}" if trial else f' · {session.shots} tiros'
            status.config(text=session.status+detail)
            if trial:
                battle=session.battle.summary() if session.battle else {}
                labels={'complete':'Sesión terminada · resultados separados por modalidad','running':'En curso','approved':'Prueba de puntería aprobada','failed':'Prueba no aprobada','insufficient-data':'Faltan tiros dirigidos para evaluar'}
                median=f"{trial['median_path_error_px']:g} px" if trial['median_path_error_px'] is not None else 'sin mediciones'
                movements=getattr(session,'movements',[]);recovered=sum(m.get('trajectory_found') is True for m in movements)
                reasons={'angle-unavailable':'falta ángulo','terrain-blocked':'terreno bloqueado','unknown-weather':'clima sin comprobar','missing-model':'falta modelo','unmeasured-wind':'viento sin medir','wind-out-of-domain':'viento fuera del ajuste','variable-projectile':'Camaleón sin proyectil previo identificado','orientation-unconfirmed':'orientación no confirmada','unsafe-ground':'suelo inseguro','calibration-budget':'límite de calibración'}
                timing=getattr(session,'last_timing',{});plan_ms=timing.get('planning_ms')
                timing_text=f'{plan_ms:g} ms' if isinstance(plan_ms,(int,float)) else 'sin registro'
                diagnostics=', '.join(f"{reasons.get(k,k)}: {v}" for k,v in trial.get('skip_reasons',{}).items()) or 'sin omisiones'
                result_label.config(text=f"{labels[trial['status']]}\nTiros cerca del objetivo: {trial['near_target_shots']}/{trial['directed_test_shots']} · Mediana: {median}\nVentanas con bajada de vida/escudo: {trial['health_drop_windows']}/{trial['known_health_windows']}\nPartidas observadas: {battle.get('wins',0)} ganadas · {battle.get('losses',0)} perdidas · {battle.get('unknown_results',0)} sin resultado confirmado\nPasos con trayectoria recuperada: {recovered}/{len(movements)} · {diagnostics}\nModalidades probadas: {len(trial.get('profiles',{})) or 1} · DD confirmados: {trial.get('dual_uses',0)}\nAbrir paso: {trial.get('terrain_attempts',0)} intentos · {trial.get('terrain_openings_observed',0)} puntos abiertos observados · Cálculo: {timing_text}")
            else:result_label.config(text='La prueba separa calibración y evaluación.\nSolo considera dirigidos los tiros con una solución comprobada.')
        report=coverage_report(learner.records if learner else {},app.book.records)
        launch.config(text=f"{report['launch_coverage_percent']:g}% · {report['launch_modes_validated']}/{report['launch_modes_total']} salidas")
        launch_bar.set(report['launch_coverage_percent']);lab_bar.set(report['lab_coverage_percent'])
        lab_label.config(text=f"Disponibles en el Lab · {report['lab_coverage_percent']:g}% · {report['lab_modes_validated']}/{report['launch_modes_total']}")
        lines=[]
        for mode in report['modes']:
            if mode['mobile']!=vehicle.get():continue
            suffix=' · patrón especial pendiente' if mode['special_pending'] else ''
            check=f" ({mode['check_percent']}% de comprobación)" if mode['checks'] and not mode['validated'] else ''
            lines.append(f"{('Tiro 1','Tiro 2','SS')[mode['shot']]} · {mode['status']}{check}{suffix}")
        details.config(text='\n'.join(lines))
        progress=learner.progress() if learner else {};shared=session.lab_progress if session else {}
        evidence.config(text=f"Mediciones: {progress.get('measured_launches',0)} · Con experiencia: {progress.get('retained_aimed_shots',0)} · Exploración: {progress.get('retained_exploration_shots',0)}\nReemplazos del Lab con menor error comprobado: {shared.get('measured_lab_improvements',0)}")
        win.after(700,refresh)
    def close():stop();win.destroy()
    win.protocol('WM_DELETE_WINDOW',close);win.bind('<Escape>',lambda e:stop());refresh();return win
