import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock

from autonomous_learning import AutonomousLearner
from native_paths import position
from shared_launch import add_prefix_sample,validated_prefix
from test_shared_launch import fixture,legacy,sample
from training_aim import NoAim
from training_evaluation import EvaluationTrial


class PrefixEvaluationTests(unittest.TestCase):
    def learner(self,tmp,parent=None):
        learner=AutonomousLearner(Path(tmp)/'learner.json');learner.episode='game'
        learner.records['dragonbound:ARMOR:1']=legacy() if parent is None else parent
        return learner

    def test_historical_reference_proposes_calibration_but_cannot_freeze(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=self.learner(tmp);learner.plan=Mock(return_value={'stage':'evaluación con modelo congelado','power':180})
            trial=EvaluationTrial(Path(tmp)/'trial.json',learner,mobile='ARMOR',shot=1)
            result=trial.plan({'wind':0,'windAngle':90},{},{'mobile':'ARMOR','shot':1})
            view=learner.plan.call_args.kwargs['record_override']
            self.assertEqual(result['evaluation_phase'],'calibration');self.assertIsNone(trial.frozen)
            self.assertAlmostEqual(view['prefix_horizon_s'],1.6);self.assertFalse(view['reference_horizon_validated'])
            self.assertTrue(learner.records[trial.key]['multi_projectile']);self.assertFalse(view['cases'])

    def test_only_future_pair_checks_freeze_with_the_minimum_checked_horizon(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=self.learner(tmp);learner.plan=Mock(return_value={'stage':'evaluación con modelo congelado','power':180})
            trial=EvaluationTrial(Path(tmp)/'trial.json',learner,mobile='ARMOR',shot=1)
            parent=learner.records[trial.key]
            for i,power in enumerate((90,270,130,250)):
                add_prefix_sample(parent,sample(power,100+i*10,durations=(5000,500)))
            result=trial.plan({'wind':0,'windAngle':90},{},{'mobile':'ARMOR','shot':1})
            self.assertEqual(result['evaluation_phase'],'evaluation')
            self.assertEqual(learner.plan.call_args.kwargs['record_override']['prefix_horizon_s'],.5)
            self.assertEqual(learner.plan.call_args.kwargs['record_override']['prefix_power_range'],[130,250])
            self.assertEqual(len(trial.verified_check_ids({'wind':0,'windAngle':90})),2)
            self.assertTrue(parent['multi_projectile']);self.assertFalse(trial.summary()['full_family_validated'])

    def test_current_family_contradiction_revokes_a_frozen_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=self.learner(tmp);learner.plan=Mock(return_value={'stage':'evaluación con modelo congelado'})
            trial=EvaluationTrial(Path(tmp)/'trial.json',learner,mobile='ARMOR',shot=1)
            for i,power in enumerate((90,270,130,250)):add_prefix_sample(learner.records[trial.key],sample(power,100+i*10))
            trial.plan({'wind':0,'windAngle':90},{},{'mobile':'ARMOR','shot':1})
            learner.records[trial.key]['launch_prefix']['blocked_episode']='game'
            with self.assertRaises(NoAim) as caught:trial.plan({'wind':0,'windAngle':90},{},{'mobile':'ARMOR','shot':1})
            self.assertEqual(caught.exception.reason,'unsupported-pattern');self.assertIsNone(trial.frozen)

    def test_later_warhead_flight_cannot_improve_prefix_target_distance(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=self.learner(tmp);trial=EvaluationTrial(Path(tmp)/'trial.json',learner,mobile='ARMOR',shot=1)
            _,release,state=fixture(100,durations=(500,2000));target=position(state['shots'][1],1.2)
            release['learner']={'evaluation_phase':'evaluation','target':target}
            trial.frozen={'model':{'scale':2,'offset':20,'gravity':300,'wind_scale':.7},'wind':0,'angle':90}
            trial.record(release,state);row=trial.tests[-1]
            self.assertGreater(row['path_error_px'],80);self.assertEqual(row['prefix_horizon_s'],.5)
            self.assertTrue(row['prefix_observed']);self.assertFalse(row['full_family_validated'])
            self.assertAlmostEqual(row['candidate_prediction_error_px'],0)

    def test_invalid_family_has_no_prefix_accuracy_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=self.learner(tmp);trial=EvaluationTrial(Path(tmp)/'trial.json',learner,mobile='ARMOR',shot=1)
            _,release,state=fixture();state['shots'][1]['wave']=1
            release['learner']={'evaluation_phase':'evaluation','target':[500,0]}
            trial.record(release,state);row=trial.tests[-1]
            self.assertFalse(row['prefix_observed']);self.assertIsNone(row['path_error_px']);self.assertIsNone(row['candidate_prediction_error_px'])

    def test_prefix_proximity_and_health_never_approve_the_full_weapon(self):
        with tempfile.TemporaryDirectory() as tmp:
            trial=EvaluationTrial(Path(tmp)/'trial.json',self.learner(tmp),mobile='ARMOR',shot=1)
            trial.tests=[{'path_error_px':0,'health_window_known':True,'enemy_health_drop':100} for _ in range(12)]
            trial.finish();self.assertFalse(trial.summary()['approved']);self.assertEqual(trial.summary()['scope'],'shared-launch-prefix')

    def test_longer_target_flight_is_rejected_by_the_frozen_prefix_horizon(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=self.learner(tmp);learner.solve_observed=Mock(return_value=(180,.8))
            _,_,state=fixture();state.update(wind=0,windAngle=90,weather=[])
            view={'prefix_only':True,'prefix_horizon_s':.5,'samples':[],'weather_effects':{}}
            player={'look':1,'body':0,'rawAngle':45,'minAngle':45,'maxAngle':45}
            result=learner.plan(state,player,{'mobile':'ARMOR','shot':1,'angle':45,'power':180},model_override={'scale':2,'offset':20,'gravity':300,'wind_scale':.7},record_override=view)
            self.assertEqual(result['unavailable_reason'],'prefix-range-unchecked');self.assertFalse(result['reposition_allowed'])

    def test_family_rejection_is_saved_even_when_primary_sample_is_already_known(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=self.learner(tmp);probe,release,state=fixture();release['learner']={}
            self.assertTrue(learner.observe(probe,release,state))
            state['shots'][1]['start'][2]+=1;self.assertTrue(learner.observe(probe,release,state))
            saved=json.loads(learner.path.read_text())['records']['dragonbound:ARMOR:1']
            self.assertEqual(saved['launch_prefix']['blocked_episode'],'game');self.assertTrue(saved['multi_projectile'])

    def test_incomplete_and_late_observations_neither_add_checks_nor_promote_a_model(self):
        for incomplete in (True,False):
            with self.subTest(incomplete=incomplete),tempfile.TemporaryDirectory() as tmp:
                learner=self.learner(tmp,parent={'samples':[],'multi_projectile':True})
                for i,power in enumerate((90,270,130,250,180,300)):
                    probe,release,state=fixture(power,100+i*10)
                    if incomplete:state['shots'].pop()
                    else:
                        for shot in state['shots']:shot['elapsed']=700
                    self.assertFalse(learner.observe(probe,release,state))
                parent=learner.records['dragonbound:ARMOR:1']
                self.assertFalse(parent['samples']);self.assertNotIn('launch_prefix',parent)
                self.assertNotIn('model',parent);self.assertNotIn('candidate',parent)
                self.assertIsNone(validated_prefix(parent,'game',0,90))

    def test_inconclusive_frame_preserves_previously_checked_prefix_without_new_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=self.learner(tmp);parent=learner.records['dragonbound:ARMOR:1']
            for i,power in enumerate((90,270,130,250)):add_prefix_sample(parent,sample(power,100+i*10))
            proof=validated_prefix(parent,'game',0,90);before=copy.deepcopy(parent)
            probe,release,state=fixture(170,900);state['shots'].pop()
            self.assertFalse(learner.observe(probe,release,state))
            self.assertEqual(parent,before);self.assertEqual(validated_prefix(parent,'game',0,90),proof)

    def test_frozen_prefix_does_not_extrapolate_beyond_future_checked_forces(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=self.learner(tmp);learner.solve_observed=Mock(return_value=(320,.4))
            _,_,state=fixture();state.update(wind=0,windAngle=90,weather=[])
            view={'prefix_only':True,'prefix_horizon_s':.5,'prefix_power_range':[130,250],'samples':[],'weather_effects':{}}
            player={'look':1,'body':0,'rawAngle':45,'minAngle':45,'maxAngle':45}
            result=learner.plan(state,player,{'mobile':'ARMOR','shot':1,'angle':45,'power':180},model_override={'scale':2,'offset':20,'gravity':300,'wind_scale':.7},record_override=view)
            self.assertEqual(result['unavailable_reason'],'prefix-range-unchecked');self.assertFalse(result['reposition_allowed'])


class VerifiedCheckMembershipTests(unittest.TestCase):
    def row(self,ident,power):
        return {'id':ident,'episode':'game','simple':True,'power':power,'speed':2*power+20,'ax':0,'ay':300,'wind':0,'wind_angle':90,'heading':45,'duration_s':1}

    def test_unknown_model_membership_waits_for_future_checks_after_freeze(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=Mock();learner.episode='game';record={'samples':[self.row(str(i),power) for i,power in enumerate((90,270,130,250))]};learner.records={'dragonbound:ARMOR:0':record}
            learner.applicable_model.return_value=({'scale':2,'offset':20,'gravity':300,'wind_scale':.7},'stored')
            learner.plan.return_value={'stage':'evaluación con modelo congelado'}
            trial=EvaluationTrial(Path(tmp)/'trial.json',learner);trial.reset_episode();trial.warmups=1
            trial.plan({'wind':0,'windAngle':90},{},{})
            self.assertFalse(trial.verified_check_ids({'wind':0,'windAngle':90}))
            record['samples'] += [self.row('future:'+str(i),power) for i,power in enumerate((110,280,190))]
            self.assertEqual(len(trial.verified_check_ids({'wind':0,'windAngle':90})),3)

    def test_training_ids_duplicate_ids_and_seed_rows_do_not_become_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=Mock();learner.episode='game';learner.records={'dragonbound:ARMOR:0':{'samples':[]}}
            trial=EvaluationTrial(Path(tmp)/'trial.json',learner);trial.reset_episode();trial.frozen={'model':{'scale':2,'offset':20,'gravity':300,'wind_scale':.7},'wind':0,'angle':90,'training_ids':['train']}
            record=learner.records[trial.key];record['samples']=[self.row('train',100),self.row('seed:old',200),self.row('a',120),self.row('a',120),self.row('b',260)]
            self.assertEqual(trial.verified_check_ids({'wind':0,'windAngle':90}),['a','b'])
            record['samples'][2]['speed']+=20
            # The last duplicate still cannot create a third distinct check.
            self.assertEqual(len(trial.verified_check_ids({'wind':0,'windAngle':90})),2)

    def test_stale_local_fit_does_not_certify_stored_fallback_training_samples(self):
        for source in ('apuntar con modelo propio','apuntar con ajuste local comprobado'):
            with self.subTest(source=source),tempfile.TemporaryDirectory() as tmp:
                learner=Mock();learner.episode='game';record={'samples':[]};learner.records={'dragonbound:ARMOR:0':record}
                trial=EvaluationTrial(Path(tmp)/'trial.json',learner);trial.reset_episode();trial.warmups=1
                # These arrived after construction, but belong to an unknown
                # stored fit, not to the obsolete local fit's future checks.
                record['samples']=[self.row('stored:'+str(i),power) for i,power in enumerate((100,280,180))]
                record['last_local_validation']={'episode':'game','training_ids':['old-a','old-b'],'validation_ids':['old-c','old-d'],'model':{'scale':3,'offset':20,'gravity':300,'wind_scale':.7}}
                learner.applicable_model.return_value=({'scale':2,'offset':20,'gravity':300,'wind_scale':.7},source)
                learner.plan.return_value={'stage':'evaluación con modelo congelado'}
                trial.plan({'wind':0,'windAngle':90},{},{})
                self.assertFalse(trial.verified_check_ids({'wind':0,'windAngle':90}))
                self.assertEqual(set(trial.frozen['validation_baseline_ids']),{'stored:0','stored:1','stored:2'})
                record['samples'] += [self.row('future:'+str(i),power) for i,power in enumerate((110,290,190))]
                self.assertEqual(len(trial.verified_check_ids({'wind':0,'windAngle':90})),3)


if __name__=='__main__':unittest.main()
