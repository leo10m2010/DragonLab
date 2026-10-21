"""One temporary rounded control panel; no automatic start on app launch."""
import tkinter as tk
from rounded_widgets import RoundedPanel,RoundedButton
from rounded_controls import RoundedChoice
from ui_shell import BG,PANEL,TEXT,MUTED,GREEN

def open_training(app):
    win=getattr(app,'training_window',None)
    if win and win.winfo_exists():win.lift();return win
    win=tk.Toplevel(getattr(app,'ui_parent',app.root));app.training_window=win;win.title('DragonLab · Entrenamiento');win.geometry('600x490');win.configure(bg=BG)
    tk.Label(win,text='Aprender jugando',bg=BG,fg=TEXT,font=('Bahnschrift',23,'bold')).pack(anchor='w',padx=26,pady=(24,10))
    card=RoundedPanel(win,PANEL);card.pack(fill='both',expand=True,padx=24,pady=8)
    tk.Label(card.body,text='DragonBound · Avatar Off',bg=PANEL,fg=GREEN,font=('Bahnschrift',13,'bold')).pack(anchor='w',padx=18,pady=(10,8))
    tk.Label(card.body,text="""Busca partidas 1v1, cambia de carro y prueba fuerzas distintas.
Guarda tiros 1, 2 y SS, ángulos y vientos disponibles.
Los ajustes necesitan tiros nuevos de comprobación.
Los proyectiles múltiples conservan sus mediciones por separado.""",justify='left',bg=PANEL,fg=MUTED,font=('Bahnschrift',11)).pack(anchor='w',padx=18,pady=8)
    row=tk.Frame(card.body,bg=PANEL);row.pack(fill='x',padx=18,pady=8)
    tk.Label(row,text='Tiros por sesión',bg=PANEL,fg=TEXT,font=('Bahnschrift',11)).pack(side='left')
    limit=tk.StringVar(value='30');RoundedChoice(row,textvariable=limit,values=['12','30','60','120'],state='readonly',width=7).pack(side='right')
    status=tk.Label(win,text='Esc detiene la sesión. Deja el juego en primer plano.',bg=BG,fg=MUTED,font=('Bahnschrift',10),wraplength=520);status.pack(fill='x',padx=24,pady=10)
    actions=tk.Frame(win,bg=BG);actions.pack(fill='x',padx=24,pady=(0,20))
    def stop():
        if app.training_session:app.training_session.stop()
    def start():
        if app.clone_id!='dragonbound':status.config(text='Elige DragonBound en la pantalla principal.');return
        if app.training_session and app.training_session.running:return
        from training_session import TrainingSession
        endpoint=getattr(app,'live_endpoint',None) or app.endpoint.get()
        if getattr(app,'last_live',0)==0:endpoint='http://127.0.0.1:9223'
        app.training_session=TrainingSession(endpoint,app.browser_target,app.book.path,app.events.put,max_shots=int(limit.get()))
        app.training_session.start()
    RoundedButton(actions,text='Detener',command=stop).pack(side='left')
    RoundedButton(actions,text='Empezar entrenamiento',command=start,bg=GREEN,fg=BG).pack(side='right')
    def refresh():
        if not win.winfo_exists():return
        if app.training_session:status.config(text=f'{app.training_session.status} · {app.training_session.shots} tiros')
        win.after(500,refresh)
    def close():stop();win.destroy()
    win.protocol('WM_DELETE_WINDOW',close);win.bind('<Escape>',lambda e:stop());refresh();return win
