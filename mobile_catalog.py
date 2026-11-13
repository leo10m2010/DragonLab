"""Display catalog; preserve the game's existing 0..22 numeric mapping.

Being listed is recognition, not proof of calibrated physics. RANDOM is a
selection option; special/seasonal aliases need native evidence before mapping.
"""
import copy
import math
from core import PROFILES
from game_profiles import get_profile, registered_profiles
MANUAL_MOBILES=tuple(name for name in PROFILES if name!='RANDOM')
CATALOG_VERSION=1
SHOT_LABELS=('1','2','SS')

def display_name(name):
    return {'JD':'J.D.','ASATE':'A.Sate','RAON':'Raon Launcher','KALSIDDON':'Kalsiddon','RANDOMIZER':'Randomizer','DRAGON2':'Dragon 2 · especial'}.get(name,name.title())


def _number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def _book_record(app,key):
    record=getattr(getattr(app,'book',None),'records',{}).get(key,{})
    return copy.deepcopy(record) if isinstance(record,dict) else {}


def _independent_checks(record,game_id):
    """Read promotion evidence without treating a fit or counter as proof."""
    from learning_guard import good,errors
    fit=record.get('fit') or {}
    if not all(_number(fit.get(k)) for k in ('gravity','power_scale','speed_offset')):return []
    if not 0<fit['gravity']<10000 or not .01<fit['power_scale']<30:return []
    if fit.get('wind_scale') is not None and not (_number(fit['wind_scale']) and 0<=fit['wind_scale']<100):return []
    if fit.get('wind_mode','smooth') not in ('smooth','floor'):return []
    maximum=100 if game_id=='gunbound-world' else 400
    for key,low,high in (('power_range',1,maximum),('wind_range',0,100)):
        bounds=fit.get(key)
        if not isinstance(bounds,(list,tuple)) or len(bounds)!=2 or not all(_number(v) for v in bounds) or not low<=bounds[0]<=bounds[1]<=high:return []
    checks=record.get('accepted_validation',[])
    samples=record.get('samples',[])
    if not isinstance(checks,list) or not isinstance(samples,list):return []
    source='native-shot-start' if game_id=='dragonbound' else 'gunbound-own-shot-path'
    samples={s.get('sample_id'):s for s in samples if isinstance(s,dict) and
             isinstance(s.get('sample_id'),str) and not s['sample_id'].startswith('seed:') and
             s.get('source')==source and all(_number(s.get(k)) for k in ('power','vx','vy','ax','ay','wind','wind_angle')) and
             1<=s['power']<=maximum and 0<=s['wind']<=100}
    valid=[]
    for row in checks:
        if not isinstance(row,dict) or row.get('id') not in samples:continue
        error=row.get('candidate')
        if not isinstance(error,dict) or not all(_number(error.get(k)) for k in ('speed','acceleration')):continue
        if error.get('trajectory') is not None and not _number(error['trajectory']):continue
        if good(error) and good(errors(fit,samples[row['id']])) and row['id'] not in {r['id'] for r in valid}:valid.append(row)
    # A saved counter alone cannot establish disjoint training and future checks.
    training=set(samples)-{r['id'] for r in valid}
    powers=[samples[r['id']].get('power') for r in valid]
    if len(valid)<3 or len(training)<4 or not all(_number(p) for p in powers):return []
    if len(set(powers))<2 or max(powers)-min(powers)<40:return []
    return valid


def _learned_proof(app,key,record):
    if not key.startswith('dragonbound:') or record.get('drift_pending'):return None
    library=getattr(app,'learned_launches',None)
    if not library or getattr(library,'coverage',{}).get(key,{}).get('special'):return None
    from manual_learning import valid_profile
    from autonomous_learning import error,flight_error
    for row in reversed(getattr(library,'profiles',{}).get(key,[])):
        if not valid_profile(row) or row['key']!=key:continue
        if not _number(row.get('max_flight_error_px')) or not 0<=row['max_flight_error_px']<=12:continue
        model={**row['fit'],'scale':row['fit']['power_scale'],'offset':row['fit']['speed_offset']}
        if any(error(model,s)>5 or flight_error(model,s) is None or flight_error(model,s)>12
               for s in getattr(library,'live',{}).get(key,[])):continue
        return copy.deepcopy(row)
    return None


def mode_record(app,game_id,mobile,shot):
    """Return one game/vehicle/shot view, with baseline and evidence separated.

    This is a read-only projection of existing stores. It never fits, imports,
    saves, changes the active vehicle, or promotes an existing baseline.
    """
    game=get_profile(game_id)
    if not game or game['status']!='supported' or mobile not in MANUAL_MOBILES or isinstance(shot,bool) or shot not in (0,1,2):return None
    from autonomous_learning import special_continuation
    key=f'{game_id}:{mobile}:{shot}'
    record=_book_record(app,key)
    special=mobile=='RANDOMIZER' or (game_id=='dragonbound' and special_continuation(key))
    baseline={};sources=[];builtin=None
    if game_id=='dragonbound':
        gravity,wind_scale,power_scale,muzzle_angle,muzzle_radius=PROFILES[mobile]
        baseline={'gravity':gravity,'wind_scale':wind_scale,'power_scale':power_scale,
                  'muzzle_angle':muzzle_angle,'muzzle_radius':muzzle_radius}
        sources.append({'source':'core.py:PROFILES','scope':'vehicle-base','validated':False})
    elif mobile=='ARMOR':
        from gunbound_profiles import ARMOR_SHOT1,ARMOR_SHOT2,ARMOR_SS
        builtin=copy.deepcopy((ARMOR_SHOT1,ARMOR_SHOT2,ARMOR_SS)[shot])
        sources.append({'source':'gunbound_profiles.py:'+('ARMOR_SHOT1','ARMOR_SHOT2','ARMOR_SS')[shot],
                        'scope':'measured-launch','validated':False})
    fit=record.get('fit') if isinstance(record.get('fit'),dict) else None
    checks=_independent_checks(record,game_id) if fit else []
    proof=_learned_proof(app,key,record)
    drift=bool(record.get('drift_pending') or record.get('drift') or record.get('active_failures'))
    # Model success concerns an initial launch. Known secondary mechanisms stay
    # pending even when their initial parameters have passed checks.
    eligible=not special and not any(record.get(k) for k in
        ('multi_projectile','special_continuation_pending','training_patterns','patterns','intrinsic_pattern'))
    validated=not drift and eligible and bool(checks or proof)
    parameters=copy.deepcopy(proof['fit'] if proof else fit or builtin or baseline)
    power_range=copy.deepcopy(proof.get('power_range') if proof else (fit or builtin or {}).get('power_range'))
    wind_range=copy.deepcopy((fit or builtin or {}).get('wind_range'))
    if proof:sources.append({'source':'manual_learning.py:LearnedLaunchLibrary','scope':proof['scope'],'validated':True})
    if record:sources.append({'source':'calibration_book.py:CalibrationBook','key':key,'scope':'local-measurements','validated':bool(checks)})
    quality='validated' if validated else 'drift' if drift else 'measured' if fit or builtin else 'base' if baseline else 'pending'
    status=('Recalibrando · cambio observado' if drift else 'Mecanismo especial pendiente' if special else
            'Validada · rango comprobado' if validated else 'Comprobando candidato' if record.get('candidate') else
            'Salida medida · comprobación pendiente' if fit or builtin else 'Perfil base · sin validar' if baseline else 'Sin parámetros medidos')
    sample_count=len(record.get('samples',[]))
    coverage=getattr(getattr(app,'learned_launches',None),'coverage',{}).get(key,{}) if game_id=='dragonbound' else {}
    sample_count=max(sample_count,coverage.get('samples',0) if isinstance(coverage,dict) else 0,proof.get('sample_count',0) if proof else 0)
    return {'schema_version':CATALOG_VERSION,'key':key,'game_id':game_id,'game_name':game['name'],
            'native_id':list(PROFILES).index(mobile),'mobile':mobile,'name':display_name(mobile),'shot':shot,'shot_label':SHOT_LABELS[shot],
            'baseline':baseline,'baseline_source':'core.py:PROFILES' if baseline else None,
            'parameters':parameters,'quality':quality,'status':status,'model': 'special-pending' if special else 'launch',
            'special_pending':special,'mechanism_eligible':eligible,'full_path_validated':False,
            'sample_count':sample_count,'builtin_sample_count':(builtin or {}).get('sample_count',0),
            'validation_count':len(proof['validation_ids']) if proof else len(checks),
            'power_range':power_range,'wind_range':wind_range,'wind_domain':copy.deepcopy(proof.get('fit',{}).get('wind_domain')) if proof else None,
            'native_power_range':game['native_power_range'],'evidence':sources,'record':record,'learned_proof':proof,
            'drift_pending':drift,'calibration_status':status}


def catalog_records(app=None,game_id=None):
    games=[get_profile(game_id)] if game_id else registered_profiles(supported_only=True)
    return [mode_record(app,game['id'],mobile,shot) for game in games if game and game['status']=='supported'
            for mobile in MANUAL_MOBILES for shot in (0,1,2)]


def filter_records(records,query='',game_id=None,mobile=None,shot=None):
    """Pure filtering shared by the real UI and regression tests."""
    tokens=str(query).casefold().split()
    return [r for r in records if (not game_id or r['game_id']==game_id)
            and (not mobile or r['mobile']==mobile) and (shot is None or r['shot']==shot)
            and all(token in ' '.join(str(r[k]) for k in ('game_name','mobile','name','shot_label','status','native_id')).casefold() for token in tokens)]


def is_recommended(row):
    return row['quality']=='validated' and row['mechanism_eligible'] and not row['drift_pending'] and row['validation_count']>=3


def recommendations(app,game_id):
    """Only independently validated, non-drifting and eligible launch models."""
    rows=[r for r in catalog_records(app,game_id) if is_recommended(r)]
    return sorted(rows,key=lambda r:(-r['validation_count'],-r['sample_count'],r['native_id'],r['shot']))
