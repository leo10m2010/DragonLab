"""UI-thread invalidation of all state bound to a native game session."""
import time

def reset_source(app, epoch=None):
    from control_lifecycle import invalidate_guide
    app.source_epoch=epoch
    app.pending_fire=None
    app.fire_cancel.set()
    invalidate_guide(app)
    app.computing=False
    app.visual_dirty_since=time.monotonic()
    for key in ('last_live','current_game_power','live_camera','live_look','live_launch_offset',
                'auto_target_id','target_hero_id','selected_target','last_fingerprint','last_page_gesture',
                'profile_stamp','last_terrain','unrecognized_mobile_id'):
        setattr(app,key,0 if key=='last_live' else None)
    app.live_players=[];app.target_ids={};app.observed_paths={};app.gunbound_observed={}
    app.game_visible=False;app.has_position_data=False;app.auto_visible=False
    app.guide_geometry_fresh=False;app.guide_points=None;app.auto_points=None
    app.page_shortcuts_active=False;app.live_input_issue=''
    app.s.environment={};app.s.launch_offset=None
    app.terrain_revision=getattr(app,'terrain_revision',0)+1
    app.player_tracker.reset();app.trails.reset()
    app.book.release=None
    for key in ('seen','pending'):
        value=getattr(app.book,key,None)
        if hasattr(value,'clear'):value.clear()
        value=getattr(app.shot_review,key,None)
        if hasattr(value,'clear'):value.clear()
    library=getattr(app,'learned_launches',None)
    if library:
        with library.lock:library.in_game=False;library.episode=None;library.live={}
    app.hide_overlay();app.hide_power_guide()
    app.target_name.set('Objetivo automático');app.target_box.config(values=['Objetivo automático'])
    from diagnostic_log import note
    note(app.base,'source-reset',game=app.clone_id,version=__import__('app_version').PROGRAM_VERSION)

def event_current(app,event):
    """Legacy internal fixtures may omit a token; real queued inputs always have it."""
    return ('sourceEpoch' not in event or event['sourceEpoch']==getattr(app,'source_epoch',None))
