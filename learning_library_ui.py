"""A small read-only catalog for the manual player's learned launches."""
import tkinter as tk
from rounded_controls import RoundedTable
from ui_shell import BG,TEXT,MUTED,GREEN
from autonomous_learning import special_continuation
from mobile_catalog import MANUAL_MOBILES,display_name,mode_record
from rounded_widgets import RoundedButton

def open_library(app):
    existing=getattr(app,'learning_library_window',None)
    if existing and existing.winfo_exists():existing.lift();return existing
    win=tk.Toplevel(getattr(app,'ui_parent',app.root));app.learning_library_window=win
    win.title('DragonLab · Balas aprendidas');win.geometry('640x560');win.minsize(600,440);win.configure(bg=BG)
    from desktop_shell import style_window
    style_window(win)
    tk.Label(win,text='Tu guía aprendida',bg=BG,fg=TEXT,font=('Bahnschrift',22,'bold')).pack(anchor='w',padx=24,pady=(18,8))
    tk.Label(win,text='El Lab aprovecha los tiros de práctica y los que haces al jugar.\nCada bala conserva su propio ajuste y sus límites de fuerza y viento.',bg=BG,fg=MUTED,font=('Bahnschrift',11),justify='left').pack(anchor='w',padx=24,pady=(0,12))
    actions=tk.Frame(win,bg=BG);actions.pack(fill='x',padx=24,pady=(0,10))
    from catalog_ui import open_catalog
    from calibration_ui import open_calibration
    RoundedButton(actions,text='Consultar catálogo',command=lambda:open_catalog(app),bg=BG,fg=TEXT,font=('Bahnschrift',10)).pack(side='left')
    RoundedButton(actions,text='Revisar calibración',command=lambda:open_calibration(app),bg=BG,fg=TEXT,font=('Bahnschrift',10)).pack(side='left',padx=10)
    table=RoundedTable(win,columns=('mode','state','shots'),show='headings',height=16)
    for key,label,width in (('mode','Carro · bala',170),('state','Estado',320),('shots','Tiros',60)):
        table.heading(key,text=label);table.column(key,width=width,stretch=key=='state')
    table.pack(fill='both',expand=True,padx=24)
    footer=tk.Label(win,bg=BG,fg=GREEN,font=('Bahnschrift',10),wraplength=585,justify='left');footer.pack(fill='x',padx=24,pady=14)
    def refresh():
        if not win.winfo_exists():return
        library=getattr(app,'learned_launches',None)
        if library and app.clone_id=='dragonbound':
            for mobile in MANUAL_MOBILES:
                for shot,label in enumerate(('1','2','SS')):
                    key=f'dragonbound:{mobile}:{shot}';proofs=library.profiles.get(key,[]);data=library.coverage.get(key,{})
                    mode=mode_record(app,'dragonbound',mobile,shot)
                    text='Proyectil variable · pendiente' if mobile=='RANDOMIZER' else 'Mecanismo especial pendiente' if special_continuation(key) or data.get('special') else 'Aprendida · rango comprobado' if mode['quality']=='validated' else 'Faltan comprobaciones' if data.get('samples') else 'Sin tiros útiles todavía'
                    values=(display_name(mobile)+' · '+label,text,data.get('samples',0))
                    if table.exists(key):table.item(key,values=values)
                    else:table.insert('','end',iid=key,values=values)
            summary=library.summary();footer.config(text=summary['error'] or f"{summary['available_modes']}/{len(MANUAL_MOBILES)*3} modalidades con ajustes aprendidos. Reconocer un carro no implica calibrar todas sus balas.")
        else:footer.config(text='Esta biblioteca corresponde a DragonBound. GunBound World conserva sus calibraciones por separado.')
        win.refresh_job=win.after(2000,refresh)
    def cancel_refresh():
        if getattr(win,'refresh_job',None):
            try:win.after_cancel(win.refresh_job)
            except tk.TclError:pass
            win.refresh_job=None
    def close():cancel_refresh();win.destroy()
    win.bind('<Destroy>',lambda e:cancel_refresh() if e.widget==win else None)
    win.protocol('WM_DELETE_WINDOW',close);win.bind('<Escape>',lambda e:close());refresh();return win
