"""Share attributed observations with the Lab's independently validated book."""
def share_observation(book,state,release):
    # The input is a confirmed real release, never a predicted trajectory.
    book.observe_training(state,release)
    records=[v for k,v in book.records.items() if k.startswith('dragonbound:')]
    improved=sum(len(v.get('accepted_validation',[]))>=3 and all(x.get('baseline') is not None for x in v['accepted_validation']) and sum(x['candidate']['score'] for x in v['accepted_validation'])+.05<.95*sum(x['baseline']['score'] for x in v['accepted_validation']) for v in records if v.get('fit') and not v.get('drift_pending'))
    return {'measured_lab_improvements':improved,'validated_lab_modes':sum(bool(v.get('fit')) and not v.get('drift_pending') for v in records),
            'lab_candidates':sum(bool(v.get('candidate')) for v in records),
            'lab_observations':sum(len(v.get('samples',[])) for v in records)}
