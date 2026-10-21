import tempfile,unittest,math
from pathlib import Path
from autonomous_learning import AutonomousLearner,flight_error
from training_policy import next_probe

class RegimeTests(unittest.TestCase):
    def test_meter_rounding_cannot_lock_curriculum_to_one_force(self):
        samples=[{'power':p-1,'wind':0} for p in [100,300,180,360,120,320,220]]
        samples.extend({'power':359,'wind':0} for _ in range(20))
        record={'dragonbound:ARMOR:0':{'samples':samples}}
        self.assertNotEqual(next_probe(record,'ARMOR',0)['power'],360)
        choices=[]
        for n in range(7):
            p=next_probe(record,'ARMOR',0,n)['power'];choices.append(p);samples.append({'power':p-1,'wind':0})
        self.assertGreaterEqual(len(set(choices)),5)
    def test_historical_model_is_not_accepted_in_a_new_match_without_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=AutonomousLearner(Path(tmp)/'learn.json');model={'scale':2,'offset':0,'gravity':400,'wind_scale':4}
            self.assertIsNone(learner.applicable_model({'model':model,'samples':[]},10,0)[0])
    def test_long_flight_exposes_error_that_a_launch_threshold_can_hide(self):
        sample={'power':200,'speed':400,'ax':0,'ay':400,'wind':0,'wind_angle':0,'duration_s':5,'heading':45}
        model={'scale':2,'offset':0,'gravity':405,'wind_scale':0}
        self.assertGreater(flight_error(model,sample),60)
    def test_local_adjustment_needs_separate_future_shots_and_is_match_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=AutonomousLearner(Path(tmp)/'learn.json')
            samples=[{'id':str(n),'episode':learner.episode,'simple':True,'power':p,'speed':2*p,'ax':40,'ay':400,'wind':10,'wind_angle':0,'heading':45,'duration_s':2} for n,p in enumerate([100,300,180,360])]
            record={'samples':samples[:3]};self.assertIsNone(learner.applicable_model(record,10,0)[0])
            record['samples']=samples;model,stage=learner.applicable_model(record,10,0)
            self.assertAlmostEqual(model['scale'],2);self.assertEqual(stage,'apuntar con ajuste local comprobado')
            self.assertIsNone(learner.applicable_model(record,20,0)[0])
            learner.episode='new-room';self.assertIsNone(learner.applicable_model(record,10,0)[0])
    def test_mismatched_local_trajectory_rejects_fit_instead_of_firing_with_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=AutonomousLearner(Path(tmp)/'learn.json')
            samples=[{'id':str(n),'episode':learner.episode,'simple':True,'power':p,'speed':2*p,'ax':0,'ay':400 if n<2 else 407,'wind':0,'wind_angle':0,'heading':45,'duration_s':4} for n,p in enumerate([100,300,180,360])]
            self.assertIsNone(learner.applicable_model({'samples':samples},0,0)[0])
    def test_lab_rejects_small_launch_error_that_becomes_large_in_a_high_shot(self):
        from learning_guard import errors,good
        sample={'power':200,'vx':400,'vy':0,'ax':0,'ay':400,'wind':0,'wind_angle':0,'duration_s':5,'simple_trajectory':True}
        fit={'power_scale':2,'speed_offset':0,'gravity':405,'wind_scale':0,'wind_observed':True}
        report=errors(fit,sample);self.assertEqual(report['acceleration'],5)
        self.assertGreater(report['trajectory'],60);self.assertFalse(good(report))
    def test_weather_pause_does_not_permanently_mark_vehicle_as_multibullet(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=AutonomousLearner(Path(tmp)/'learn.json')
            state={'status':'live','heroId':0,'activePlayer':0,'players':[{'id':0,'x':0,'y':0,'mobile':0},{'id':1,'x':300,'y':0}],'wind':0,'windAngle':0,'weather':[], 'shots':[{'id':1,'native':True,'elapsed':0,'duration':1000,'start':[0,0,45,200,0,400],'change':{'at':200,'dur':100},'shotType':0,'metadata':{'player':0,'power':100}}]}
            release={'hero':0,'x':0,'y':0,'power':100,'shot':0,'wind':0,'windAngle':0,'baseline':[],'learner':{'target':[300,0],'elevation':45}}
            learner.observe({'mobile':'ARMOR','shot':0},release,state)
            record=learner.records['dragonbound:ARMOR:0'];self.assertFalse(record['multi_projectile']);self.assertTrue(record['weather_modified_last_shot'])
            self.assertIn('path_miss_px',record['cases'][-1])
