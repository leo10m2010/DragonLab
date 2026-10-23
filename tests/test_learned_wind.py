import json,math,statistics,tempfile,unittest,copy
from pathlib import Path
from unittest.mock import Mock
from wind_models import components,acceleration,fit_acceleration,supported,domain
from autonomous_learning import AutonomousLearner,fit,flight_error,predicted_path
from training_evaluation import EvaluationTrial,measured_prior

class LearnedWindTests(unittest.TestCase):
    def test_floor_components_preserve_negative_values_and_zero_wind(self):
        self.assertEqual(components(2,312,'floor'),(1,-2));self.assertEqual(components(3,92,'floor'),(-1,2));self.assertEqual(components(0,130,'floor'),(0,0))
        self.assertAlmostEqual(components(2,312)[0],2*math.cos(math.radians(312)))
    def test_real_future_launch_replay_improves_physics_with_separate_calibration(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/wind_component_replay.json').read_text());floor=[];smooth=[]
        for group in fixture['groups']:
            a=fit(group['training'],minimum=2,wind_mode='floor');b=fit(group['training'],minimum=2,wind_mode='smooth')
            self.assertIsNotNone(a);self.assertIsNotNone(b)
            floor.extend(flight_error(a,s) for s in group['future']);smooth.extend(flight_error(b,s) for s in group['future'])
        self.assertGreaterEqual(len(floor),90);self.assertLess(statistics.mean(floor),2);self.assertGreater(statistics.mean(smooth),5);self.assertTrue(all(e<=12 for e in floor))
    def test_model_type_is_chosen_from_measured_residual(self):
        rows=[]
        for p,w,a in ((100,3,92),(180,7,106),(260,13,217),(340,17,312)):
            ax,ay=acceleration({'gravity':390,'wind_scale':4,'wind_mode':'floor'},w,a)
            rows.append({'power':p,'speed':p*2,'wind':w,'wind_angle':a,'ax':ax,'ay':ay})
        self.assertEqual(fit(rows)['wind_mode'],'floor')
    def test_frozen_floor_weights_allow_changed_wind_inside_observed_components(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=Mock();learner.episode='game';learner.records={};learner.plan.return_value={'stage':'evaluación con modelo congelado','power':200}
            trial=EvaluationTrial(Path(folder)/'report.json',learner);trial.episode='game';trial.frozen={'model':{'scale':2,'offset':0,'gravity':390,'wind_scale':4,'wind_mode':'floor','wind_domain':[-10,10,-10,10]},'wind':10,'angle':0}
            self.assertEqual(trial.plan({'wind':8,'windAngle':90},{},{})['evaluation_phase'],'evaluation')
            with self.assertRaises(Exception):trial.plan({'wind':30,'windAngle':180},{},{})
            self.assertEqual(trial.frozen['model']['gravity'],390)
    def test_candidate_does_not_mix_or_promote_different_matches(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=AutonomousLearner(Path(folder)/'learn.json');key='dragonbound:ARMOR:0'
            for i,p in enumerate((100,180,260,340)):
                learner.add(key,{'id':'a'+str(i),'episode':'first','simple':True,'power':p,'speed':2*p,'wind':0,'wind_angle':0,'ax':0,'ay':390})
            self.assertEqual(learner.records[key]['candidate']['episode'],'first')
            learner.add(key,{'id':'new','episode':'second','simple':True,'power':200,'speed':450,'wind':0,'wind_angle':0,'ax':0,'ay':410})
            self.assertNotIn('candidate',learner.records[key]);self.assertNotIn('model',learner.records[key])
    def test_new_match_gets_own_calibration_budget_within_finite_session(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=Mock();learner.episode='new';learner.records={};learner.plan.return_value={'stage':'evaluación con modelo congelado','power':100};learner.applicable_model.return_value=(None,'missing')
            trial=EvaluationTrial(Path(folder)/'report.json',learner,max_shots=40);trial.prior={'scale':2,'offset':0,'gravity':390,'wind_scale':4}
            trial.calibration=[{'episode':'old'} for _ in range(trial.calibration_limit)]
            self.assertEqual(trial.plan({'wind':0,'windAngle':0},{},{})['evaluation_phase'],'calibration')

    def test_local_future_checks_promote_floor_model_across_wind_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=AutonomousLearner(Path(folder)/'learn.json');learner.episode='current';key='dragonbound:ARMOR:0';rows=[]
            for i,(power,wind,angle) in enumerate(((100,5,31),(180,7,106),(240,11,217),(320,13,312))):
                ax,ay=acceleration({'gravity':390,'wind_scale':4,'wind_mode':'floor'},wind,angle)
                rows.append({'id':str(i),'episode':'current','simple':True,'power':power,'speed':2*power,'ax':ax,'ay':ay,'wind':wind,'wind_angle':angle,'heading':45,'duration_s':2})
            learner.records[key]={'samples':rows};learner.wind_mode_hints[key]='floor'
            model,stage=learner.applicable_model(learner.records[key],5,90)
            self.assertIsNotNone(model);self.assertEqual(model['wind_mode'],'floor');self.assertEqual(stage,'apuntar con ajuste local comprobado')
            self.assertIsNone(learner.applicable_model(learner.records[key],30,90)[0])
