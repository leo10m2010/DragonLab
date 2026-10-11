"""Optional human-readable health details; no noise in the playing view."""
import tkinter as tk,pathlib,zipfile
from tkinter import filedialog,messagebox
from rounded_widgets import RoundedPanel,RoundedButton

def describe(app):
    record=app.book.records.get(app.book.key(app.clone_id,app.s.mobile,app.s.selected_shot),{})
    candidate=record.get('candidate') or {};validation=candidate.get('validation',[])
    confirmation=getattr(app,'last_shot_confirmation',{}) or {}
    labels={'confirmed':'Confirmado','mismatch':'Diferencia detectada','observed':'Proyectil observado; comprobación parcial','unconfirmed':'No se pudo confirmar','ambiguous':'Proyectiles ambiguos'}
    return [
        ('Carro y tiro',f'{app.s.mobile} · '+('SS' if app.s.selected_shot==2 else str(app.s.selected_shot+1))),
        ('Aprendizaje',record.get('status','Esperando tiros identificables')),
        ('Mediciones guardadas',str(len(record.get('samples',[])))),
        ('Ajuste nuevo',f'{len(validation)} tiros de comprobación · requiere al menos 3 y fuerzas distintas' if candidate else 'Sin cambio pendiente'),
        ('Último Q',labels.get(confirmation.get('status'),'Todavía no comprobado')),
        ('Fuerza',f"Indicada: {confirmation.get('requestedPower','—')} · Observada: {confirmation.get('actualPower',confirmation.get('observedPower','—'))}"),
        ('Rendimiento',app.performance+' · captura reducida fuera de tu turno'),
        ('Casos de prueba','Hasta 8 casos locales; sin nombres ni conversaciones'),
    ]

def open_diagnostics(app):
    bg='#11191c';panel='#1a262b';win=tk.Toplevel(app.root);win.title('Estado de DragonLab');win.configure(bg=bg);win.geometry('600x510');win.transient(app.root)
    box=RoundedPanel(win,panel);box.pack(fill='both',expand=True,padx=18,pady=18)
    for title,value in describe(app):
        tk.Label(box.body,text=title,bg=panel,fg='#72dfba',font=('Bahnschrift',10,'bold'),anchor='w').pack(fill='x',padx=18,pady=(8,0))
        tk.Label(box.body,text=value,bg=panel,fg='#edf4f1',font=('Bahnschrift',10),wraplength=500,justify='left',anchor='w').pack(fill='x',padx=18)
    def export():
        files=sorted((pathlib.Path(app.base)/'casos-regresion').glob('case-*.json'))[:8]
        if not files:messagebox.showinfo('Casos de prueba','Todavía no hay casos registrados.',parent=win);return
        target=filedialog.asksaveasfilename(parent=win,defaultextension='.zip',initialfile='DragonLab-casos.zip',filetypes=[('Casos de prueba','*.zip')])
        if not target:return
        try:
            with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
                for path in files:archive.write(path,path.name)
        except OSError:messagebox.showerror('Casos de prueba','No se pudo guardar el archivo.',parent=win)
    RoundedButton(win,text='Guardar casos de prueba',command=export).pack(side='left',padx=18,pady=(0,14))
    RoundedButton(win,text='Cerrar',command=win.destroy).pack(side='right',padx=18,pady=(0,14))
