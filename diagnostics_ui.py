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
    from performance_ui import open_performance
    window=open_performance(getattr(app,'ui_parent',app.root),lambda:app)
    app.diagnostics_window=window
    return window
