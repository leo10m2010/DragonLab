"""Truthful status for the single product window."""
import time
from strength_guide import guide_power

def capture_status(app):
    if getattr(app,'last_error',None):return 'Revisar guía','La guía encontró un error; vuelve a conectar.'
    if not app.last_live or time.monotonic()-app.last_live>4:
        return 'Esperando partida',getattr(app,'reader_reason','') or 'Captura conectada. Esperando una partida activa.'
    if not app.has_position_data:return 'Identificando jugadores','Esperando identificar tu jugador y un enemigo vivo.'
    if app.dirty or app.computing:return 'Calculando','Actualizando la fuerza con el ángulo y el objetivo actuales.'
    if guide_power(app.result) is None:
        if app.clone_id=='gunbound-world':return 'Sin calibración','GunBound World necesita un perfil de fuerza propio. No hay potencia validada para este tiro.'
        return 'Sin potencia válida',app.result.get('reason') or 'Este tiro necesita otro ángulo u objetivo.'
    if not app.game_visible:return 'Guía preparada','Vuelve al juego para ver la guía sobre la barra.'
    if not app.guide_points:return 'Buscando barra','Los jugadores están detectados; esperando ubicar la barra de fuerza.'
    if not app.power_guide or not app.power_guide.win.winfo_viewable():return 'Guía oculta','La guía aún no está visible sobre el juego.'
    return 'Guía activa','Fuerza '+str(app.result.get('power') or app.result.get('guide_power'))+' · captura activa.'
