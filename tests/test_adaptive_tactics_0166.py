import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch

from adaptive_training import AdaptiveTrial
from autonomous_learning import AutonomousLearner
from training_aim import NoAim
from test_shared_launch import legacy
import test_excavation_policy as excavation

MODEL={'scale':2,'offset':0,'gravity':400,'wind_scale':4}


class AdaptiveTacticsTests(unittest.TestCase):
    def make(self,tmp):
        learner=AutonomousLearner(Path(tmp)/'learner.json');learner.episode='current'
        learner.records={'dragonbound:ARMOR:0':{'model':copy.deepcopy(MODEL),'samples':[]},'dragonbound:ARMOR:1':legacy()}
        adaptive=AdaptiveTrial(Path(tmp)/'report.json',learner,allow_dual=True)
        state={'status':'live','heroId':0,'turnSerial':7,'wind':0,'windAngle':90,'players':[{'id':0,'x':100,'y':100,'hp':100,'shield':0,'maxHp':1000,'team':0},{'id':1,'x':350,'y':100,'hp':900,'shield':0,'team':1}]}
        return adaptive,state
    def plan_trial(self,adaptive,shot=0,checks=('a','b','c')):
        trial=adaptive.profile('ARMOR',shot);trial.reset_episode()
        trial.plan=Mock(return_value={'target':[350,100],'evaluation_phase':'evaluation'})
        trial.frozen={'model':copy.deepcopy(MODEL),'wind':0,'angle':90}
        trial.verified_check_ids=Mock(return_value=list(checks))
        return trial

    def test_coincident_armor_second_does_not_enable_other_multiple_families(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,s=self.make(tmp)
            self.assertTrue(a.supported('ARMOR',1));self.assertTrue(a.learner.records['dragonbound:ARMOR:1']['multi_projectile'])
            for mobile in ('NAK','ADUKA','TRICO','KALSIDDON','RANDOMIZER'):
                a.learner.records[f'dragonbound:{mobile}:1']=legacy()
                self.assertFalse(a.supported(mobile,1),mobile)

    def test_prefix_ranking_does_not_consult_generic_applicability(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,s=self.make(tmp)
            with patch.object(a.learner,'applicable_model',side_effect=AssertionError('parent family must not become simple')):
                result=a.probe('ARMOR',s,[1])
            self.assertEqual(result['shot'],1);self.assertTrue(result['calibration_objective'])
            self.assertEqual(a.last_weapon_review['modes'][0]['prefix_only'],True)

    def test_rejection_of_one_mode_keeps_other_weapon_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,s=self.make(tmp);a.probe('ARMOR',s,[0,1,2])
            first=a.selected;first.plan=Mock(side_effect=NoAim('angle blocked',reason='angle-unavailable'))
            with self.assertRaises(NoAim):a.plan(s,{}, {'mobile':'ARMOR','shot':first.shot})
            other=1 if first.shot==0 else 0;a.probe('ARMOR',s,[other])
            rows={row['shot']:row for row in a.summary()['last_weapon_review']['modes']}
            self.assertEqual(rows[first.shot]['reason'],'angle-unavailable')
            self.assertEqual(rows[other]['status'],'selected');self.assertEqual(rows[2]['status'],'unsupported')

    def test_new_native_turn_resets_old_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,s=self.make(tmp);a.probe('ARMOR',s,[0]);a.review_mode(0,status='rejected',reason='old')
            a.probe('ARMOR',{**s,'turnSerial':8},[1])
            self.assertEqual([r['shot'] for r in a.last_weapon_review['modes']],[1])

    def test_pressure_dd_uses_native_health_and_unique_future_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,s=self.make(tmp);t=self.plan_trial(a)
            result=a.plan(s,{}, {'mobile':'ARMOR','shot':0})
            self.assertTrue(result['use_dual']);self.assertIn('refuerzo',result['item_reason'])
            self.assertEqual(result['verified_native_checks'],3)
            self.assertFalse(result['tactical_intent']['authorizes_action'])
            t.verified_check_ids.return_value=['a','a','b']
            self.assertFalse(a.plan(s,{}, {'mobile':'ARMOR','shot':0})['use_dual'])

    def test_own_shield_and_missing_or_invalid_maximum_preserve_dd(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,s=self.make(tmp);self.plan_trial(a);hero=s['players'][0]
            for update in ({'shield':500},{'maxHp':None},{'maxHp':True},{'maxHp':float('nan')},{'hp':True},{'dead':True}):
                previous=copy.deepcopy(hero);hero.update(update)
                with self.subTest(update=update):self.assertFalse(a.plan(s,{}, {'mobile':'ARMOR','shot':0})['use_dual'])
                hero.clear();hero.update(previous)

    def test_pressure_does_not_spend_dd_without_frozen_evaluation(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,s=self.make(tmp);t=self.plan_trial(a)
            t.frozen=None;self.assertFalse(a.plan(s,{}, {'mobile':'ARMOR','shot':0})['use_dual'])
            t.frozen={'model':MODEL};t.plan.return_value['evaluation_phase']='calibration'
            self.assertFalse(a.plan(s,{}, {'mobile':'ARMOR','shot':0})['use_dual'])

    def test_prefix_and_ss_never_spend_pressure_dd(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,s=self.make(tmp)
            for shot in (1,2):
                t=self.plan_trial(a,shot);t.prefix_only=shot==1
                result=a.plan(s,{}, {'mobile':'ARMOR','shot':shot})
                self.assertFalse(result['use_dual'])
            self.assertIn('familia completa',a.plan(s,{}, {'mobile':'ARMOR','shot':1})['item_reason'])

    def test_prefix_trials_do_not_contaminate_full_shot_precision(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,s=self.make(tmp);t=a.profile('ARMOR',1)
            t.tests=[{'path_error_px':0,'health_window_known':True,'enemy_health_drop':999}]
            result=a.summary();self.assertEqual(result['near_target_shots'],0);self.assertIsNone(result['near_target_rate'])
            self.assertEqual(result['directed_test_shots'],1);self.assertEqual(result['prefix_directed_test_shots'],1);self.assertEqual(result['full_shot_directed_tests'],0)

    def test_nak_first_can_clear_terrain_with_its_own_checked_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,s,p,probe,error=excavation.ExcavationTests().make(tmp)
            nak=a.profile('NAK',0);nak.prior=copy.deepcopy(MODEL);nak.prior_training_ids={'old'}
            a.learner.records[nak.key]=copy.deepcopy(a.learner.records[t.key]);probe={**probe,'mobile':'NAK'}
            result=a.excavate(s,p,probe,error)
            self.assertEqual(result['action'],'abrir paso');self.assertEqual(result['tactical_intent']['intent'],'clear-line')
            self.assertFalse(result['tactical_intent']['authorizes_action']);self.assertFalse(result['use_dual'])
            token=a.record({'power':result['power'],'learner':result},{})
            self.assertEqual(a.recovery_rows[0]['tactical_intent'],result['tactical_intent']);self.assertTrue(token)
            self.assertIsNone(a.excavate(s,p,{**probe,'shot':1},error))

    def test_nak_first_still_requires_real_independent_flight_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,s,p,probe,error=excavation.ExcavationTests().make(tmp)
            self.assertIsNone(a.excavate(s,p,{**probe,'mobile':'NAK'},error))
            self.assertIn('comprobaciones',error.excavation_reason)


if __name__=='__main__':unittest.main()
