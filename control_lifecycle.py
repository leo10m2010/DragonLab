"""Coordinate manual assistance and autonomous control on the UI thread."""


def cancel_actions(app):
    app.pending_fire=None
    app.fire_cancel.set()
    session=getattr(app,'training_session',None)
    if session:session.stop()


def cancel_from_game(app):
    session=getattr(app,'training_session',None)
    if session and hasattr(session,'sessions') and session.running:
        # Each bound browser worker observes its own trusted Escape event.
        # The primary guide's fallback listener must not stop the peer.
        app.pending_fire=None;app.fire_cancel.set();return
    cancel_actions(app)


def prepare_training(app):
    if getattr(app,'fire_busy',False):
        raise RuntimeError('Espera a que termine el tiro solicitado con el atajo.')
    app.pending_fire=None
    app.fire_cancel.set()
    invalidate_guide(app)


def invalidate_guide(app):
    # An in-flight calculation can finish, but its generation is now obsolete.
    app.compute_generation=getattr(app,'compute_generation',0)+1
    app.result_context=None
    app.result={}
    app.dirty=True


def sync_control_mode(app):
    session=getattr(app,'training_session',None)
    active=bool(session and session.running)
    previous=getattr(app,'training_control_active',False)
    if active==previous:return False
    app.training_control_active=active
    app.pending_fire=None
    if previous and not active and getattr(app,'book',None):app.book.release=None
    invalidate_guide(app)
    app.hide_power_guide()
    app.hide_overlay()
    return True
