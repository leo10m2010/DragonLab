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

def start_training(app,limit='Continuo'):
    if app.clone_id!='dragonbound':raise ValueError('Elige DragonBound en la pantalla principal.')
    if app.training_session and app.training_session.running:return app.training_session
    from training_session import TrainingSession
    endpoint=getattr(app,'live_endpoint',None) or app.endpoint.get()
    if getattr(app,'last_live',0)==0:endpoint='http://127.0.0.1:9223'
    continuous=limit=='Continuo'
    app.training_session=TrainingSession(endpoint,app.browser_target,app.book.path,app.events.put,max_shots=60 if continuous else int(limit),continuous=continuous,autonomous=True)
    app.training_session.start();return app.training_session

def open_training(app):
    win=getattr(app,'training_window',None)
    if win and win.winfo_exists():win.lift();return win
    win=tk.Toplevel(getattr(app,'ui_parent',app.root));app.training_window=win;win.title('DragonLab · Entrenamiento');win.geometry('600x530');win.configure(bg=BG)
    tk.Label(win,text='Aprender del juego',bg=BG,fg=TEXT,font=('Bahnschrift',23,'bold')).pack(anchor='w',padx=26,pady=(24,10))
    card=RoundedPanel(win,PANEL);card.pack(fill='both',expand=True,padx=24,pady=8)
    tk.Label(card.body,text='DragonBound · Avatar Off',bg=PANEL,fg=GREEN,font=('Bahnschrift',13,'bold')).pack(anchor='w',padx=18,pady=(10,8))
    tk.Label(card.body,text="""Mide los tiros reales; el Lab no es su referencia.
Explora fuerzas y ángulos y comprueba lo aprendido.
Los carros y climas poco medidos pueden fallar al inicio.
Continuo sigue entre partidas. Esc lo detiene.""",justify='left',bg=PANEL,fg=MUTED,font=('Bahnschrift',11)).pack(anchor='w',padx=18,pady=8)
    row=tk.Frame(card.body,bg=PANEL);row.pack(fill='x',padx=18,pady=8)
    tk.Label(row,text='Duración',bg=PANEL,fg=TEXT,font=('Bahnschrift',11)).pack(side='left')
    limit=tk.StringVar(value='Continuo');RoundedChoice(row,textvariable=limit,values=['Continuo','12','30','60','120'],state='readonly',width=11).pack(side='right')
    status=tk.Label(win,text='Esc detiene la sesión. Deja el juego en primer plano.',bg=BG,fg=MUTED,font=('Bahnschrift',10),wraplength=520);status.pack(fill='x',padx=24,pady=10)
    actions=tk.Frame(win,bg=BG);actions.pack(fill='x',padx=24,pady=(0,20))
    def stop():
        if app.training_session:app.training_session.stop()
    def start():
        try:start_training(app,limit.get())
        except ValueError as error:status.config(text=str(error))
    RoundedButton(actions,text='Detener',command=stop).pack(side='left')
    RoundedButton(actions,text='Empezar entrenamiento',command=start,bg=GREEN,fg=BG).pack(side='right')
    progress_label=tk.Label(win,text='Las mediciones confirmadas también mejoran el Lab tras validarse.',bg=BG,fg=MUTED,font=('Bahnschrift',10),wraplength=520);progress_label.pack(fill='x',padx=24,pady=6)
    def refresh():
        if not win.winfo_exists():return
        if app.training_session:status.config(text=f'{app.training_session.status} · {app.training_session.shots} tiros')
        if app.training_session and app.training_session.learner:
            data=app.training_session.learner.progress();lab=app.training_session.lab_progress
            progress_label.config(text=f"Tiros medidos: {data['measured_launches']} · Modelos básicos: {data['validated_launch_modes']}\nCon experiencia: {data['retained_aimed_shots']} · Exploración: {data['retained_exploration_shots']} · Perfiles del Lab: {lab.get('validated_lab_modes',0)} · Mejorados: {lab.get('measured_lab_improvements',0)}\nModelos de salida validados; precisión de juego aún por comprobar.")
        win.after(500,refresh)
    def close():stop();win.destroy()
    win.protocol('WM_DELETE_WINDOW',close);win.bind('<Escape>',lambda e:stop());refresh();return win
