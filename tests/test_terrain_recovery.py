import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
from autonomous_learning import AutonomousLearner
from training_movement import choose_reposition
from training_aim import NoAim
from training_evaluation import EvaluationTrial
from adaptive_training import AdaptiveTrial
from variable_projectiles import record_variant
from calibration_book import CalibrationBook,mobile_name
from training_progress import coverage_report

MODEL={'scale':2,'offset':0,'gravity':400,'wind_scale':4}
def scenario(height=70,weather=None):
    ground=[100]*500
    for x in range(110,132):ground[x]=height
    state={'status':'live','heroId':0,'wind':0,'windAngle':0,'players':[{'id':0,'x':100,'y':100,'mobile':0,'muzzleX':0,'muzzleY':-10},{'id':1,'x':350,'y':100}],'terrain':{'heights':ground},'weather':weather or []}
    player={'look':1,'body':0,'rawAngle':55,'minAngle':10,'maxAngle':55};probe={'mobile':'ARMOR','shot':0,'angle':55,'power':100}
    return state,player,probe

class TerrainTests(unittest.TestCase):
    def test_unreachable_weather_behind_wall_does_not_disable_retreat(self):
        with tempfile.TemporaryDirectory() as tmp:
            l=AutonomousLearner(Path(tmp)/'learner.json');s,p,probe=scenario(0,[{'typeId':5,'x':250,'size':20}])
            result=l.plan(s,p,probe,model_override=MODEL)
            self.assertEqual(result['unavailable_reason'],'terrain-blocked');self.assertTrue(result['reposition_allowed']);self.assertTrue(result['blocked_plans'])
    def test_retreat_can_clear_a_muzzle_blocked_by_a_ridge(self):
        with tempfile.TemporaryDirectory() as tmp:
            l=AutonomousLearner(Path(tmp)/'learner.json');s,p,probe=scenario()
            result=l.plan(s,p,probe,model_override=MODEL);self.assertEqual(result['unavailable_reason'],'terrain-blocked')
            def evaluate(hypothetical,step):return l.plan(hypothetical,{**p,'body':step['expected_body']},probe,model_override=MODEL)['stage']=='evaluación con modelo congelado'
            step=choose_reposition(s,350,'terrain-blocked',evaluate=evaluate)
            self.assertEqual(step['direction'],'left');self.assertEqual(step['selection'],'predicted-clear-path')
    def test_retreat_never_chooses_a_cliff_even_when_requested(self):
        s,p,probe=scenario();s['terrain']['heights'][:100]=[None]*100
        self.assertIsNone(choose_reposition(s,350,'terrain-blocked'))
    def test_excavation_requires_a_current_frozen_model_and_separation(self):
        with tempfile.TemporaryDirectory() as tmp:
            l=Mock();l.records={};a=AdaptiveTrial(Path(tmp)/'trial.json',l);s,p,probe=scenario()
            candidate={'power':150,'raw_angle':40,'heading':40,'elevation':40,'target':[350,100],'impact':[220,100]}
            error=NoAim('wall',reason='terrain-blocked',recovery={'blocked_plans':[candidate]})
            self.assertIsNone(a.excavate(s,p,probe,error));a.profile('ARMOR',0).frozen={'model':MODEL}
            result=a.excavate(s,p,probe,error);self.assertEqual(result['action'],'abrir paso');self.assertFalse(result['use_dual'])
            token=a.record({'power':150,'learner':result},{});self.assertEqual(len(a.profile('ARMOR',0).tests),0)
            a.health_result({'token':token,'known':True,'enemy_health_drop':0,'terrain_opened':True});self.assertEqual(a.summary()['terrain_openings_observed'],1)
            candidate['impact']=[120,100];self.assertIsNone(a.excavate(s,p,probe,error))
    def test_unknown_weather_before_obstacle_is_not_an_excavation_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            l=AutonomousLearner(Path(tmp)/'learner.json');s,p,probe=scenario(0,[{'typeId':5,'x':100,'size':20}])
            result=l.plan(s,p,probe,model_override=MODEL)
            self.assertFalse(result['blocked_plans'])

class VariableTests(unittest.TestCase):
    def test_randomizer_variants_are_not_merged_or_declared_predictable(self):
        r={};release={'power':100,'wind':0,'windAngle':0}
        for bullet,speed in ((1,200),(35,600)):
            self.assertTrue(record_variant(r,{'id':bullet,'bulletId':bullet,'start':[0,0,45,speed,0,400]},release))
        self.assertEqual(set(r['projectile_variants']),{'1','35'});self.assertNotIn('model',r)
        self.assertFalse(r['projectile_variants']['1'][0]['predictable_before_release'])
    def test_historical_fixed_fits_are_not_used_for_randomizer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);saved={'schema':1,'records':{'dragonbound:RANDOMIZER:0':{'model':MODEL,'fit':MODEL,'samples':[]}}};path=root/'book.json';path.write_text(json.dumps(saved))
            l=AutonomousLearner(path);self.assertIsNone(l.applicable_model(l.records['dragonbound:RANDOMIZER:0'],0,0)[0])
            b=CalibrationBook(path);self.assertIsNone(b.profile('dragonbound','RANDOMIZER',0,0));self.assertIsNone(b.acceleration('dragonbound','RANDOMIZER',0,0,0))
            a=AdaptiveTrial(root/'trial.json',l);self.assertFalse(a.supported('RANDOMIZER',0))
            t=EvaluationTrial(root/'fixed.json',l,mobile='RANDOMIZER')
            with self.assertRaises(NoAim):t.plan({'wind':0,'windAngle':0},{},{})
            report=coverage_report(l.records,b.records,mobiles=('RANDOMIZER',));self.assertEqual(report['launch_modes_validated'],0);self.assertEqual(report['lab_modes_validated'],0)
    def test_camaleon_alias_maps_to_variable_vehicle(self):self.assertEqual(mobile_name('Camaleon'),'RANDOMIZER')
