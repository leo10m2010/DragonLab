"""Finite native-weather observations, never scored as validated aimed shots."""


def weather_probe(error,record,rows,episode,profile):
    if error.reason!='unknown-weather' or record.get('multi_projectile') or not isinstance(error.recovery,dict):return None
    for plan in error.recovery.get('weather_probes',[]):
        if not 40<=plan.get('power',0)<=360:continue
        crossings=plan.get('weather_crossings') or []
        kinds=sorted({str(w.get('resolvedTypeId') if w.get('resolvedTypeId') is not None else w.get('typeId')) for w in crossings})
        if not kinds or 'None' in kinds:continue
        effects=record.get('weather_effects',{})
        # Once a native trajectory shows altered flight, a ballistic probe is
        # no substitute for modelling that climate. Keep the old guard.
        if any((effects.get(kind) or {}).get('altered',0)>0 for kind in kinds):continue
        prior=[r for r in rows if r['episode']==episode and r['profile']==profile and r['weather_kinds']==kinds]
        if len(prior)>=3:continue
        return {**plan,'profile':profile,'stage':'medición experimental de clima','action':'medir clima','evaluation_phase':'weather','weather_kinds':kinds,'use_dual':False,'approximate':True,'item_reason':'DD reservado durante la medición de clima'}
    return None
