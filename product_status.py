"""Truthful status for the single product window."""
import time
from strength_guide import guide_power

def capture_status(app):
    session=getattr(app,'training_session',None)
    if session is not None:
        if session.running:
            stopping=bool(getattr(session,'cancel',None) and session.cancel.is_set())
            workers=getattr(session,'sessions',None)
            if not stopping and isinstance(workers,(list,tuple)) and len(workers)>1:
                overview=session.overview();active=overview['active_sessions'];expected=overview['expected_sessions']
                label='Entrenamiento parcial' if active<expected else 'Revisar entrenamiento' if overview.get('health_status') in ('stalled','attention') else 'Entrenando'
                return label,f'{active} de {expected} sesiones activas · '+session.status+f' · {session.shots} tiros'
            return ('Deteniendo' if stopping else 'Entrenando'),('Soltando controles y guardando mediciones…' if stopping else session.status+f' · {session.shots} tiros')
        worker=getattr(app,'worker',None)
        if session.status!='Preparado' and not (worker and worker.is_alive()):return 'Entrenamiento detenido',session.status
    if getattr(app,'fire_busy',False):return 'Aplicando tiro','Aplicando la fuerza con controles de Windows…'
    if time.monotonic()<getattr(app,'notice_until',0) and getattr(app,'last_fire_message',None):return 'Atajo',app.last_fire_message
    if getattr(app,'last_error',None):return 'Revisar guía','La guía encontró un error; vuelve a conectar.'
    if not app.last_live or time.monotonic()-app.last_live>4:
        return 'Esperando partida',getattr(app,'reader_reason','') or 'Captura conectada. Esperando una partida activa.'
    if not app.has_position_data:return 'Identificando jugadores','Esperando identificar tu jugador y un enemigo vivo.'
    if app.dirty or app.computing:return 'Calculando','Actualizando la fuerza con el ángulo y el objetivo actuales.'
    if guide_power(app.result) is None:
        if app.clone_id=='gunbound-world' and getattr(app,'profile_required',True):return pending_calibration(app)
        return 'Sin potencia válida',app.result.get('reason') or 'Este tiro necesita otro ángulo u objetivo.'
    if not app.game_visible:return 'Guía preparada','Vuelve al juego para ver la guía sobre la barra.'
    if not app.guide_points:return 'Buscando barra','Los jugadores están detectados; esperando ubicar la barra de fuerza.'
    if not app.power_guide or not app.power_guide.win.winfo_viewable():return 'Guía oculta','La guía aún no está visible sobre el juego.'
    label,state=calibration_label(app)
    return 'Guía activa',(label+' · ' if label else '')+'Fuerza '+str(app.result.get('power') or app.result.get('guide_power'))+' · captura activa.'


def calibration_label(app):
    settings=getattr(app,'s',None)
    if settings is None:return '', 'approximate'
    mobile=settings.mobile.title();shot=('1','2','SS')[settings.selected_shot]
    mode=mobile+' · Tiro '+shot
    if getattr(app,'clone_id',None)=='gunbound-world' and getattr(app,'profile_required',True):return mode+' · PENDIENTE','pending'
    if getattr(app,'active_measured_profile',False):return mode+' · SALIDA MEDIDA','measured'
    return mode+' · APROXIMADO','approximate'

def pending_calibration(app):
    from gunbound_profiles import ARMOR_SHOT1,ARMOR_SHOT2,ARMOR_SS
    book=getattr(app,'book',None);settings=getattr(app,'s',None)
    if settings is None:return 'Sin calibración','Faltan mediciones para esta modalidad.'
    record=book.records.get(book.key(app.clone_id,settings.mobile,settings.selected_shot),{}) if book else {}
    fit=record.get('fit') or ({0:ARMOR_SHOT1,1:ARMOR_SHOT2,2:ARMOR_SS}.get(settings.selected_shot) if settings.mobile=='ARMOR' else None)
    if record.get('drift_pending'):return 'Recalibrando','Las últimas mediciones cambiaron; comprobando un ajuste nuevo.'
    if fit and fit.get('wind_range') and not fit['wind_range'][0]<=settings.wind<=fit['wind_range'][1]:
        return 'Ampliando viento',f"Viento {settings.wind:g}: medido entre {fit['wind_range'][0]:g} y {fit['wind_range'][1]:g}. Tus tiros manuales amplían la calibración."
    count=len(record.get('samples',[]));candidate=record.get('candidate')
    if candidate:return 'Comprobando calibración',f"{len(candidate.get('validation',[]))}/3 tiros de comprobación. Usa fuerzas variadas; el perfil se activa al validarse."
    return 'Midiendo tiros',f"{count} tiros registrados para esta modalidad. Dispara manualmente con fuerzas variadas; se guardan automáticamente."
