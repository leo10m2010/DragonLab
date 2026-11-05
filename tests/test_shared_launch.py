import copy,math,unittest
from shared_launch import extract_prefix,classify_prefix,add_prefix_sample,prefix_record,reference_model,validated_prefix,can_prefix


def fixture(power=100,ident=1,wind=0,angle=90,durations=(1500,1200)):
    speed=2*power+20;k=.7;ax=k*wind*math.cos(math.radians(angle));ay=300-k*wind*math.sin(math.radians(angle))
    start=[10,-10,45,speed,ax,ay]
    shots=[{'id':ident+i,'native':True,'start':list(start),'elapsed':0,'duration':duration,'shotType':1,'metadata':{'player':0,'mobile':0,'selectedShot':1,'launchSpeed':speed}} for i,duration in enumerate(durations)]
    probe={'mobile':'ARMOR','shot':1};release={'hero':0,'x':0,'y':0,'shot':1,'power':power,'wind':wind,'windAngle':angle,'baseline':[]}
    state={'heroId':0,'activePlayer':-1,'currentPower':400,'selectedShot':2,'players':[{'id':0,'mobile':0,'x':0,'y':0},{'id':1,'mobile':1,'x':500,'y':0}],'shots':shots}
    return probe,release,state


def sample(power,ident,episode='game',wind=0,angle=90,durations=(1500,1200)):
    return extract_prefix(*fixture(power,ident,wind,angle,durations),episode)


def legacy():
    record={'multi_projectile':True,'patterns':[],'samples':[],'cases':[{'ends':[[800,20],[900,20]]}]}
    for i,power in enumerate((90,170,270,350)):
        start=[10,-10,45,2*power+20,0,300]
        record['patterns'].append({'power':power,'starts':[start[:],start[:]]})
        record['samples'].append({'id':'old:'+str(i),'episode':'old','power':power,'speed':start[3],'heading':45,'ax':0,'ay':300,'wind':0,'wind_angle':90,'duration_s':1+i*.2})
    return record


class ExtractionTests(unittest.TestCase):
    def test_classification_distinguishes_absence_from_proven_owned_conflict(self):
        self.assertEqual(classify_prefix(*fixture(),episode='game')['status'],'matched')
        for kind in ('one','late','unknown','rival','missing-owner','duplicate','late-conflict'):
            probe,release,state=fixture()
            if kind=='one':state['shots'].pop()
            elif kind in ('late','late-conflict'):
                for shot in state['shots']:shot['elapsed']=700
                if kind=='late-conflict':state['shots'][1]['start'][2]+=1
            elif kind=='unknown':state['shots'].append({'id':50,'native':False})
            elif kind=='rival':state['shots'].append({**copy.deepcopy(state['shots'][1]),'id':50,'metadata':{'player':1}})
            elif kind=='missing-owner':
                state['shots'][1]['metadata'].pop('player');state['shots'][1]['start'][2]+=1
            else:state['shots'][1]['id']=state['shots'][0]['id']
            with self.subTest(kind=kind):self.assertEqual(classify_prefix(probe,release,state,'game')['status'],'inconclusive')
        for kind in ('spread','wave','orbit','change','more-own'):
            probe,release,state=fixture()
            if kind=='spread':state['shots'][1]['start'][2]+=1
            elif kind=='more-own':state['shots'].append({**copy.deepcopy(state['shots'][1]),'id':50})
            else:state['shots'][1][kind]=[1,2,3,4] if kind=='orbit' else {'at':0} if kind=='change' else 1
            with self.subTest(kind=kind):self.assertEqual(classify_prefix(probe,release,state,'game')['status'],'conflict')

    def test_fresh_owned_coincident_pair_uses_actual_charge_and_minimum_duration(self):
        probe,release,state=fixture(173);original=copy.deepcopy(state);row=extract_prefix(probe,release,state,'game')
        self.assertEqual(row['power'],173);self.assertEqual(row['speed'],366);self.assertEqual(row['duration_s'],1.2)
        self.assertEqual(row['source'],'owned-coincident-prefix');self.assertFalse(row['full_family_validated']);self.assertEqual(state,original)
    def test_cardinality_duplicate_identity_and_other_new_native_family_are_rejected(self):
        for mode in ('one','three','duplicate','unknown-new'):
            probe,release,state=fixture()
            if mode=='one':state['shots'].pop()
            elif mode=='three':state['shots'].append({**state['shots'][0],'id':100})
            elif mode=='duplicate':state['shots'][1]['id']=state['shots'][0]['id']
            else:state['shots'].append({'id':100,'native':False,'x':1,'y':1})
            with self.subTest(mode=mode):self.assertIsNone(extract_prefix(probe,release,state,'game'))
    def test_baseline_old_projectiles_do_not_count_as_new_pair_members(self):
        from shot_attribution import identity
        probe,release,state=fixture();old={**state['shots'][0],'id':100};state['shots'].append(old);release['baseline']=[identity(old)]
        self.assertIsNotNone(extract_prefix(probe,release,state,'game'))
    def test_auxiliary_delayed_and_modified_paths_never_certify_a_plain_prefix(self):
        for key,value in (('auxiliary',True),('delay',1),('wave',1),('orbit',[1,2,3,4]),('path',[0,1,2]),('change',{'at':0}),('jumps',[[1,2,3,4,5]]),('unknown_mechanism',True),('mechanism','split')):
            probe,release,state=fixture();state['shots'][1][key]=value
            with self.subTest(key=key):self.assertIsNone(extract_prefix(probe,release,state,'game'))
    def test_spread_even_one_coordinate_difference_is_not_coincident(self):
        for index in range(6):
            probe,release,state=fixture();state['shots'][1]['start'][index]+=.01
            with self.subTest(index=index):self.assertIsNone(extract_prefix(probe,release,state,'game'))
    def test_foreign_owner_or_conflicting_mode_is_rejected(self):
        for field,value in (('player',1),('selectedShot',0),('selectedShot',True),('mobile',1),('power',399)):
            probe,release,state=fixture();state['shots'][1]['metadata'][field]=value
            with self.subTest(field=field,value=value):self.assertIsNone(extract_prefix(probe,release,state,'game'))
        probe,release,state=fixture();state['shots'][1]['metadata'].update(player=1,player_n=0)
        self.assertIsNone(extract_prefix(probe,release,state,'game'))
    def test_other_vehicle_shot_mode_and_items_do_not_get_this_exception(self):
        for mobile,shot,item in (('ICE',1,None),('NAK',1,None),('ADUKA',1,None),('ARMOR',0,None),('ARMOR',2,None),('ARMOR',True,None),('ARMOR',1,'dual')):
            probe,release,state=fixture();probe.update(mobile=mobile,shot=shot);release.update(shot=shot,item=item)
            with self.subTest(mobile=mobile,shot=shot,item=item):self.assertIsNone(extract_prefix(probe,release,state,'game'))
    def test_stale_or_invalid_native_durations_are_rejected(self):
        for field,value in (('elapsed',601),('elapsed',-1),('duration',0),('duration',float('nan')),('duration',20001),('shotType',True)):
            probe,release,state=fixture();state['shots'][1][field]=value
            with self.subTest(field=field,value=value):self.assertIsNone(extract_prefix(probe,release,state,'game'))


class StorageAndValidationTests(unittest.TestCase):
    def test_deduplicates_pair_across_frames_without_changing_parent_family(self):
        record=legacy();parent={k:copy.deepcopy(v) for k,v in record.items()};row=sample(170,100)
        self.assertTrue(add_prefix_sample(record,row));self.assertFalse(add_prefix_sample(record,row))
        changed=dict(row,power=171);self.assertFalse(add_prefix_sample(record,changed))
        for key,value in parent.items():self.assertEqual(record[key],value)
        self.assertEqual(len(record['launch_prefix']['samples']),1)
    def test_episode_is_required_before_storing_and_same_native_ids_new_episode_are_distinct(self):
        record={};row=extract_prefix(*fixture())
        self.assertFalse(add_prefix_sample(record,row));self.assertTrue(add_prefix_sample(record,row,'a'));self.assertTrue(add_prefix_sample(record,row,'b'))
        self.assertEqual(len(record['launch_prefix']['samples']),2)
    def test_historical_coincident_data_is_prior_only_and_cannot_self_validate(self):
        record=legacy();view=prefix_record(record);prior=reference_model(record)
        self.assertTrue(can_prefix('ARMOR',1,record));self.assertFalse(can_prefix('NAK',1,record));self.assertFalse(can_prefix('ARMOR',True,record))
        self.assertTrue(all(s['id'].startswith('seed:') and s['simple'] is False for s in view['samples']))
        self.assertFalse(prior['eligible_for_aiming']);self.assertFalse(prior['full_family_validated']);self.assertIsNone(view['model']);self.assertFalse(view['cases']);self.assertFalse(view['weather_effects'])
        self.assertIsNone(validated_prefix(record,'old',0,90));self.assertTrue(record['multi_projectile'])
        self.assertEqual(view['prefix_horizon_source'],'historical-primary-hypothesis-only')
    def test_noncoincident_legacy_patterns_do_not_seed_a_reference(self):
        record=legacy()
        for p in record['patterns']:p['starts'][1][2]+=1
        self.assertIsNone(reference_model(record));self.assertFalse(can_prefix('ARMOR',1,record))
    def test_current_two_training_and_two_future_varied_launches_validate_prefix_only(self):
        record=legacy()
        for i,p in enumerate((90,270,130,250)):self.assertTrue(add_prefix_sample(record,sample(p,100+i*10)))
        evidence=validated_prefix(record,'game',0,90)
        self.assertIsNotNone(evidence);self.assertAlmostEqual(evidence['model']['scale'],2);self.assertEqual(len(evidence['training_ids']),2);self.assertEqual(len(evidence['validation_ids']),2)
        self.assertTrue(set(evidence['training_ids']).isdisjoint(evidence['validation_ids']));self.assertEqual(evidence['prefix_horizon_s'],1.2);self.assertEqual(evidence['power_range'],[130,250])
        self.assertFalse(evidence['full_family_validated']);self.assertTrue(record['multi_projectile'])
    def test_three_samples_or_narrow_future_force_span_do_not_validate(self):
        for powers in ((90,270,130),(90,270,130,150)):
            record={}
            for i,p in enumerate(powers):add_prefix_sample(record,sample(p,100+i*10))
            with self.subTest(powers=powers):self.assertIsNone(validated_prefix(record,'game',0,90))
    def test_future_launch_error_and_prefix_flight_error_are_independent_gates(self):
        for error_field,error_value in (('speed',6),('ay',6)):
            record={}
            for i,p in enumerate((90,270,130,250)):
                row=sample(p,100+i*10,durations=(5000,5000))
                if i>=2:row[error_field]+=error_value
                add_prefix_sample(record,row)
            with self.subTest(field=error_field):self.assertIsNone(validated_prefix(record,'game',0,90))
    def test_future_data_other_episode_or_wind_domain_cannot_validate_current_context(self):
        record={}
        for i,p in enumerate((90,270,130,250)):add_prefix_sample(record,sample(p,100+i*10,episode='other'))
        self.assertIsNone(validated_prefix(record,'game',0,90));self.assertIsNone(validated_prefix(record,'other',20,90))
    def test_prefix_horizon_is_each_pair_earliest_end_not_later_warhead(self):
        record={}
        for i,p in enumerate((90,270,130,250)):add_prefix_sample(record,sample(p,100+i*10,durations=(5000,500)))
        evidence=validated_prefix(record,'game',0,90);self.assertEqual(evidence['prefix_horizon_s'],.5)
        self.assertEqual(prefix_record(record)['prefix_horizon_s'],.5)
    def test_storage_is_bounded_and_cannot_accept_forged_legacy_validation_rows(self):
        record={}
        for i in range(110):add_prefix_sample(record,sample(100+(i%4)*50,100+i*10))
        self.assertEqual(len(record['launch_prefix']['samples']),96)
        fake={**sample(170,99999),'source':'legacy-coincident-prefix-reference'};self.assertFalse(add_prefix_sample(record,fake))
    def test_current_episode_contradiction_blocks_previous_prefix_evidence(self):
        record={}
        for i,p in enumerate((90,270,130,250)):add_prefix_sample(record,sample(p,100+i*10))
        self.assertIsNotNone(validated_prefix(record,'game',0,90));record['launch_prefix']['blocked_episode']='game'
        self.assertIsNone(validated_prefix(record,'game',0,90));self.assertEqual(prefix_record(record)['blocked_episode'],'game')
    def test_reference_maximum_is_hypothesis_only_and_never_the_frozen_prefix_horizon(self):
        record=legacy();reference=reference_model(record)
        self.assertAlmostEqual(reference['reference_max_primary_seconds'],1.6);self.assertFalse(reference['reference_horizon_validated'])
        self.assertIsNone(validated_prefix(record,'old',0,90))
        for i,p in enumerate((90,270,130,250)):add_prefix_sample(record,sample(p,100+i*10,durations=(2000,500)))
        self.assertAlmostEqual(prefix_record(record)['reference_max_primary_seconds'],1.6)
        self.assertEqual(validated_prefix(record,'game',0,90)['prefix_horizon_s'],.5)

if __name__=='__main__':unittest.main()
