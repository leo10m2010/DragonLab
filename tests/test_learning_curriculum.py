import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
from adaptive_training import AdaptiveTrial
from continuous_training import RollingEvaluation
from training_aim import NoAim


def learner():
    value=Mock();value.episode='current-match';value.records={f'dragonbound:{name}:{mode}':{'model':{'scale':2,'offset':0,'gravity':400,'wind_scale':4}} for name in ('ARMOR','ICE','MAGE') for mode in range(3)}
    value.applicable_model.return_value=(None,'not checked in this match')
    return value


class LearningCurriculumTests(unittest.TestCase):
    def make(self,folder):return AdaptiveTrial(Path(folder)/'report.json',learner())
    def state(self):return {'heroId':0,'wind':0,'windAngle':0,'players':[{'id':0,'x':0,'y':0,'hp':800,'shield':0},{'id':1,'x':500,'y':0,'hp':700,'shield':0}]}
    def current_profile(self,trial,shot,warmups):
        profile=trial.profile('ARMOR',shot);profile.episode=trial.learner.episode;profile.warmups=warmups
        return profile
    def test_unfrozen_calibration_keeps_varying_solved_arcs_after_six_warmups(self):
        with tempfile.TemporaryDirectory() as folder:
            trial=self.make(folder);profile=self.current_profile(trial,0,6)
            first=trial.probe('ARMOR',self.state(),[0]);profile.warmups=7;second=trial.probe('ARMOR',self.state(),[0]);profile.warmups=8;third=trial.probe('ARMOR',self.state(),[0])
            self.assertEqual([p['angle'] for p in (first,second,third)],[40,55,75])
            self.assertTrue(all(not p['prefer_current_angle'] for p in (first,second,third)))
            self.assertTrue(all(p['calibration_objective']=='varied-native-checks' for p in (first,second,third)))
            self.assertFalse(profile.frozen);self.assertFalse(profile.tests)
    def test_verified_model_retains_current_angle_preference(self):
        with tempfile.TemporaryDirectory() as folder:
            trial=self.make(folder);trial.learner.applicable_model.return_value=({'scale':2},'checked')
            profile=self.current_profile(trial,0,6)
            probe=trial.probe('ARMOR',self.state(),[0])
            self.assertTrue(probe['prefer_current_angle']);self.assertIsNone(probe['calibration_objective'])
    def test_ordinary_profile_with_current_progress_precedes_unvalidated_ss_focus(self):
        with tempfile.TemporaryDirectory() as folder:
            trial=self.make(folder);trial.focus_modes['ARMOR']=2;self.current_profile(trial,0,2);self.current_profile(trial,2,1)
            self.assertEqual(trial.probe('ARMOR',self.state(),[0,2])['shot'],0)
            # A rejected normal mode remains excluded by the controller's list.
            self.assertEqual(trial.probe('ARMOR',self.state(),[2])['shot'],2)
    def test_known_finishing_ss_still_precedes_nonlethal_calibration(self):
        with tempfile.TemporaryDirectory() as folder:
            trial=self.make(folder);self.current_profile(trial,0,2);ss=self.current_profile(trial,2,1)
            ss.calibration=[{'episode':'current-match','target_id':1,'wind':0,'wind_angle':0,'health_window_known':True,'enemy_health_drop':800} for _ in range(3)]
            self.assertEqual(trial.probe('ARMOR',self.state(),[0,2])['shot'],2)
    def test_vehicle_rotation_uses_least_attempted_supported_alternative(self):
        with tempfile.TemporaryDirectory() as folder:
            trial=self.make(folder);options=[{'id':0,'name':'Armor'},{'id':1,'name':'Ice'},{'id':2,'name':'Mage'},{'id':3,'name':'Nak'}]
            self.assertEqual(trial.choose_mobile(options,{'ARMOR':10,'ICE':7,'MAGE':0})['name'],'Armor')
            self.assertEqual(trial.choose_mobile(options,{'ARMOR':12,'ICE':7,'MAGE':0})['name'],'Armor')
            self.assertEqual(trial.choose_mobile(options,{'ARMOR':13,'ICE':7,'MAGE':0})['name'],'Mage')
            self.assertEqual(trial.focus_stint_start,0);self.assertEqual(trial.focus_selections,1)
    def test_unsupported_pattern_or_missing_model_never_enters_rotation_or_probe(self):
        with tempfile.TemporaryDirectory() as folder:
            trial=self.make(folder);trial.learner.records['dragonbound:ICE:0']['multi_projectile']=True
            for mode in (1,2):trial.learner.records.pop(f'dragonbound:ICE:{mode}')
            options=[{'id':0,'name':'Armor'},{'id':1,'name':'Ice'},{'id':2,'name':'Nak'}]
            trial.choose_mobile(options,{});self.assertEqual(trial.choose_mobile(options,{'ARMOR':20})['name'],'Armor')
            with self.assertRaises(NoAim):trial.probe('ICE',self.state(),[0,1,2])
    def test_stint_does_not_reset_at_reporting_block_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            rolling=RollingEvaluation(folder,learner(),40);options=[{'id':0,'name':'Armor'},{'id':1,'name':'Ice'}]
            rolling.current.choose_mobile(options,{'ARMOR':8});rolling.current.choose_mobile(options,{'ARMOR':10})
            rolling.rollover()
            self.assertEqual(rolling.current.focus_stint_start,8);self.assertEqual(rolling.current.focus_selections,3)
            self.assertEqual(rolling.current.choose_mobile(options,{'ARMOR':11})['name'],'Ice')
            self.assertEqual(rolling.current.summary()['directed_test_shots'],0)
    def test_curriculum_reports_actual_native_evidence_without_inventing_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            trial=self.make(folder);profile=self.current_profile(trial,0,2)
            trial.learner.records[profile.key]['samples']=[{'episode':'old','simple':True,'power':400},{'episode':'current-match','simple':True,'power':120},{'episode':'current-match','simple':True,'power':240},{'episode':'current-match','simple':False,'power':350}]
            summary=trial.summary();current=summary['curriculum']['profiles'][profile.key]
            self.assertEqual(current['current_match_native_samples'],2);self.assertEqual(current['current_match_power_span'],120)
            self.assertFalse(current['checked_for_current_match']);self.assertEqual(current['aimed_checks_total'],0)
            self.assertFalse(summary['prediction_improvement_proven']);self.assertFalse(summary['approved'])


if __name__=='__main__':unittest.main()
