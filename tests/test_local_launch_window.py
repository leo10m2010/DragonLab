import copy,math,unittest
from local_launch_window import validated_window,supports_window
from wind_models import acceleration


def row(power,index,episode='game',wind=0,angle=90,duration=.7):
    model={'scale':2.42,'offset':-.4,'gravity':390,'wind_scale':4,'wind_mode':'floor'}
    ax,ay=acceleration(model,wind,angle);speed=math.floor(model['scale']*power+model['offset'])
    start=[100,200,45,speed,ax,ay]
    return {'id':str(index)+':'+str(start),'episode':episode,'simple':True,'power':power,'speed':speed,
            'ax':ax,'ay':ay,'wind':wind,'wind_angle':angle,'heading':45,'duration_s':duration}


def record():
    return {'samples':[row(p,i) for i,p in enumerate((82,95,107,84,104,92))]}


class LocalLaunchWindowTests(unittest.TestCase):
    def test_narrow_native_window_needs_disjoint_future_checks_and_has_no_extrapolation(self):
        parent=record();before=copy.deepcopy(parent);proof=validated_window(parent,'game',0,90)
        self.assertIsNotNone(proof);self.assertEqual(parent,before)
        self.assertEqual(proof['power_range'],[84,104]);self.assertEqual(proof['training_power_range'],[82,107])
        self.assertEqual(proof['max_flight_seconds'],.7)
        self.assertTrue(set(proof['training_ids']).isdisjoint(proof['validation_ids']))
        self.assertEqual(len(proof['training_ids']),3);self.assertEqual(len(proof['validation_ids']),3)
        self.assertLessEqual(proof['speed_uncertainty_bound'],2);self.assertLessEqual(proof['flight_uncertainty_bound_px'],5)
        self.assertTrue(supports_window(proof,90,.7,0,180,'game'))
        for power,time in ((83,.7),(105,.7),(90,.701),(400,.1)):
            self.assertFalse(supports_window(proof,power,time,0,90,'game'))
        self.assertFalse(supports_window(proof,90,.5,0,90,'other-game'))
        self.assertFalse(supports_window(proof,90,.5,1,90,'game'))
    def test_training_rows_alone_and_reused_duplicates_never_validate(self):
        parent=record();parent['samples']=parent['samples'][:3]
        self.assertIsNone(validated_window(parent,'game',0,90))
        parent['samples']+=copy.deepcopy(parent['samples'])
        self.assertIsNone(validated_window(parent,'game',0,90))
        parent=record();parent['samples'][-1]=copy.deepcopy(parent['samples'][-2])
        self.assertIsNone(validated_window(parent,'game',0,90))
    def test_conflicting_duplicate_identity_invalidates_instead_of_cherry_picking(self):
        parent=record();bad=copy.deepcopy(parent['samples'][-1]);bad['speed']+=1;bad['source']='confirmed-release'
        parent['samples'].append(bad)
        self.assertIsNone(validated_window(parent,'game',0,90))
    def test_bad_future_native_launch_or_new_gravity_regime_invalidates(self):
        for field,delta in (('speed',5),('ay',15),('ax',5)):
            parent=record();bad=parent['samples'][-1];bad[field]+=delta
            start=[100,200,bad['heading'],bad['speed'],bad['ax'],bad['ay']];bad['id']='changed:'+str(start)
            with self.subTest(field=field):self.assertIsNone(validated_window(parent,'game',0,90))
    def test_other_matches_unknown_duration_and_untrusted_sources_cannot_supply_checks(self):
        for change in ('episode','duration','source','seed','simple'):
            parent=record();last=parent['samples'][-1]
            if change=='episode':last['episode']='old'
            elif change=='duration':last['duration_s']=None
            elif change=='source':last['source']='mock'
            elif change=='seed':last['id']='seed:'+last['id']
            else:last['simple']=False
            with self.subTest(change=change):self.assertIsNone(validated_window(parent,'game',0,90))
    def test_special_families_cannot_borrow_a_local_ordinary_model(self):
        for flag in ('multi_projectile','variable_projectiles','special_continuation_pending','intrinsic_pattern','patterns','observed_phases','prefix_only'):
            parent=record();parent[flag]=True
            with self.subTest(flag=flag):self.assertIsNone(validated_window(parent,'game',0,90))
    def test_tiny_training_span_and_single_future_power_cannot_validate(self):
        for powers in ((90,94,98,91,96,93),(82,95,107,92,92,92)):
            parent={'samples':[row(p,i) for i,p in enumerate(powers)]}
            self.assertIsNone(validated_window(parent,'game',0,90))
    def test_minimum_future_horizon_is_kept_and_long_uncertain_flight_is_rejected(self):
        parent=record();parent['samples'][-1]['duration_s']=.4
        self.assertEqual(validated_window(parent,'game',0,90)['max_flight_seconds'],.4)
        for sample in parent['samples']:sample['duration_s']=5
        self.assertIsNone(validated_window(parent,'game',0,90))
    def test_floor_wind_is_selected_from_training_and_only_checked_domain_is_supported(self):
        values=[(82,4,312),(95,8,106),(107,12,217),(84,6,312),(104,9,106),(92,10,217)]
        parent={'model':{'wind_mode':'smooth'},'samples':[row(p,i,wind=w,angle=a,duration=.35) for i,(p,w,a) in enumerate(values)]}
        proof=validated_window(parent,'game',6,312)
        self.assertIsNotNone(proof);self.assertEqual(proof['model']['wind_mode'],'floor')
        self.assertFalse(supports_window(proof,90,.3,9,106,'game'))
        self.assertIsNotNone(validated_window(parent,'game',9,106))
        self.assertFalse(supports_window(proof,90,.3,40,312,'game'))
        self.assertIsNone(validated_window(parent,'game',40,312))
    def test_explicit_owned_source_is_supported_but_not_synthetic_seed_identity(self):
        parent=record()
        for i,sample in enumerate(parent['samples']):sample.update(id='owned-'+str(i),source='confirmed-release')
        self.assertIsNotNone(validated_window(parent,'game',0,90))
        parent['samples'][-1]['id']='seed:owned-5'
        self.assertIsNone(validated_window(parent,'game',0,90))


if __name__=='__main__':unittest.main()
