"""Share attributed observations with the Lab's independently validated book."""
def share_observation(book,state,release):
    # The input is a confirmed real release, never a predicted trajectory.
    book.observe_training(state,release)
    return lab_summary(book)

def lab_summary(book):
    records=[v for k,v in getattr(book,'records',{}).items() if k.startswith('dragonbound:')]
    improved=sum(len(v.get('accepted_validation',[]))>=3 and all(x.get('baseline') is not None for x in v['accepted_validation']) and sum(x['candidate']['score'] for x in v['accepted_validation'])+.05<.95*sum(x['baseline']['score'] for x in v['accepted_validation']) for v in records if v.get('fit') and not v.get('drift_pending'))
    coverage=coverage_report({},getattr(book,'records',{}))
    return {'lab_coverage_percent':coverage['lab_coverage_percent'],'lab_modes_validated':coverage['lab_modes_validated'],'measured_lab_improvements':improved,'validated_lab_modes':sum(bool(v.get('fit')) and not v.get('drift_pending') for v in records),
            'lab_candidates':sum(bool(v.get('candidate')) for v in records),
            'lab_observations':sum(len(v.get('samples',[])) for v in records)}

TRAINING_MOBILES=('ARMOR','ICE','ADUKA','LIGHTNING','BIGFOOT','JD','ASATE','NAK','TRICO','MAGE','TURTLE','BOOMER','GRUB','RANDOMIZER','RAON','FROG','KALSIDDON')

def coverage_report(records,lab_records=None,mobiles=TRAINING_MOBILES):
    """Coverage of a finite launch-model catalog, never percent of general AI."""
    modes=[]
    for mobile in mobiles:
        for shot in (0,1,2):
            key=f'dragonbound:{mobile}:{shot}';r=records.get(key,{})
            candidate=r.get('candidate') or {};checks=len(candidate.get('validation',[]))
            validated=bool(r.get('model')) and not r.get('drift')
            status='Salida validada' if validated else 'Recalibrando' if r.get('drift') else f'Comprobando: {min(checks,3)}/3' if candidate else 'Midiendo' if r.get('samples') else 'Sin mediciones'
            modes.append({'mobile':mobile,'shot':shot,'validated':validated,'checks':min(checks,3),'check_percent':round(min(checks,3)*100/3),
                          'samples':len(r.get('samples',[])),'status':status,'special_pending':bool(r.get('multi_projectile'))})
    total=len(modes);done=sum(m['validated'] for m in modes)
    lab_records=lab_records or {};lab_done=sum(bool(lab_records.get(f'dragonbound:{m}:{s}',{}).get('fit')) and not lab_records.get(f'dragonbound:{m}:{s}',{}).get('drift_pending') for m in mobiles for s in (0,1,2))
    return {'launch_coverage_percent':round(100*done/total,1) if total else 0,'launch_modes_validated':done,'launch_modes_total':total,
            'lab_coverage_percent':round(100*lab_done/total,1) if total else 0,'lab_modes_validated':lab_done,
            'aim_accuracy_percent':None,'autonomy_percent':None,'modes':modes}
