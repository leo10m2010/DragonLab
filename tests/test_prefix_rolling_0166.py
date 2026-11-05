import json,tempfile,unittest
from pathlib import Path
from autonomous_learning import AutonomousLearner
from continuous_training import RollingEvaluation


class PrefixRollingTests(unittest.TestCase):
    def test_rollover_preserves_partial_scope_without_counting_full_accuracy(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=AutonomousLearner(Path(folder)/'learner.json');learner.episode='match'
            rolling=RollingEvaluation(folder,learner,40)
            profile=rolling.current.profile('ARMOR',1);profile.prefix_only=True
            profile.tests=[{'token':'one','path_error_px':0,'health_window_known':True,'enemy_health_drop':100,'prefix_only':True}]
            rolling.rollover()
            self.assertTrue(rolling.current.profile('ARMOR',1).prefix_only)
            totals=rolling.report()['totals']
            self.assertEqual(totals['directed_test_shots'],1)
            self.assertEqual(totals['prefix_directed_test_shots'],1)
            self.assertEqual(totals['full_shot_directed_tests'],0)
            self.assertEqual(totals['near_target_shots'],0)
            self.assertEqual(totals['known_health_windows'],0)

    def test_archived_native_launch_keeps_partial_validation_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=AutonomousLearner(Path(folder)/'learner.json');learner.episode='match'
            rolling=RollingEvaluation(folder,learner,40)
            rolling.record({'mobile':'ARMOR','shot':1},{'power':120,'learner':{'prefix_only':True,'prefix_horizon_s':.5,'evaluation_phase':'calibration'}},{'shots':[]})
            row=json.loads((rolling.directory/'observaciones-nativas.jsonl').read_text())
            self.assertEqual(row['scope'],'shared-launch-prefix')
            self.assertFalse(row['full_family_validated'])
            self.assertEqual(row['prefix_horizon_s'],.5)


if __name__=='__main__':unittest.main()
