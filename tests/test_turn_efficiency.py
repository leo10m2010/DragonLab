import tempfile,threading,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from autonomous_learning import AutonomousLearner,predicted_path,occupied
from training_aim import NoAim
from training_browser import TrainingBrowser
from training_movement import choose_reposition
from adaptive_training import AdaptiveTrial
from weather_practice import weather_probe
from training_session import TrainingSession
from training_controller import TrainingController

MODEL={'scale':2,'offset':0,'gravity':400,'wind_scale':4}
class TurnEfficiencyTests(unittest.TestCase):
    def test_fast_low_shot_cannot_skip_wall_next_to_muzzle(self):
        path=predicted_path(MODEL,(100,90),10,244,0,0,.55)
        wall={'heights':[70 if 110<=x<=132 else 100 for x in range(500)]}
        self.assertTrue(any(occupied(wall,*p) for p in path[1:] if 110<=p[0]<=132))
        self.assertLess(max(abs(b[0]-a[0]) for a,b in zip(path,path[1:])),3.1)
    def test_reposition_does_not_return_to_visited_position(self):
        state={'heroId':0,'players':[{'id':0,'x':100,'y':100}],'terrain':{'heights':[100]*300}}
        step=choose_reposition(state,250,'terrain-blocked',visited=[[86,100]])
        self.assertEqual(step['direction'],'right')
        self.assertIsNone(choose_reposition(state,250,'terrain-blocked',visited=[[86,100],[114,100]]))
    def test_step_budget_is_shared_by_modes_and_renews_next_turn(self):
        b=TrainingBrowser.__new__(TrainingBrowser);b.guard=Mock();b.sample=Mock(return_value={});b.seconds_left=Mock(return_value=20);b.orient=Mock()
        b.walk=Mock(return_value={'from':[100,100],'to':[114,100],'direction':'right'})
        r=Mock();r.read.return_value={'hero':0,'turn':0,'turnNumber':3,'players':[{'id':0,'x':100,'y':100}]}
        learner=Mock();learner.plan.side_effect=NoAim('blocked',reposition=True)
        with patch('training_movement.choose_reposition',return_value={'direction':'right'}):
            for shot in (0,1,2):
                with self.assertRaises(NoAim):b.plan_with_reposition(r,learner,{'shot':shot},500,3,threading.Event())
            self.assertEqual(b.walk.call_count,2)
            r.read.return_value['turnNumber']=4
            with self.assertRaises(NoAim):b.plan_with_reposition(r,learner,{'shot':0},500,4,threading.Event())
            self.assertEqual(b.walk.call_count,4)
    def test_unsupported_remaining_weapon_does_not_reserve_turn(self):
        with tempfile.TemporaryDirectory() as folder:
            s=TrainingSession('',None,Path(folder)/'book.json',Mock(),autonomous=True,objective='adaptive');s.cancel.wait=Mock(return_value=False)
            c=TrainingController(s);b=Mock();b.movement_events=[]
            b.guard.return_value={'game':True,'url':'https://dragonbound.net/#server-8/room-1','controls':{'btnShotSS':True}}
            b.sample.return_value={'status':'live','heroId':0,'activePlayer':0,'turnSerial':1,'wind':0,'windAngle':0,'players':[{'id':0,'mobile':0,'x':100,'y':100}],'shots':[]}
            c.cycle(b);c.cycle(b)
            self.assertFalse(c.ledger.used);b.shoot.assert_not_called();self.assertEqual(len(c.trial.attempts),1)

class WeatherPracticeTests(unittest.TestCase):
    def plan(self):return {'power':180,'raw_angle':50,'heading':50,'target':[350,100],'weather_crossings':[{'typeId':3,'x':200,'size':20}]}
    def test_weather_probe_is_bounded_and_stops_after_observed_flight_change(self):
        error=NoAim('climate',reason='unknown-weather',recovery={'weather_probes':[self.plan()]});record={};rows=[]
        for _ in range(3):
            plan=weather_probe(error,record,rows,'game','profile');self.assertEqual(plan['evaluation_phase'],'weather');self.assertFalse(plan['use_dual'])
            rows.append({'episode':'game','profile':'profile','weather_kinds':plan['weather_kinds']})
        self.assertIsNone(weather_probe(error,record,rows,'game','profile'))
        self.assertIsNone(weather_probe(error,{'weather_effects':{'3':{'altered':1}}},[],'game','profile'))
    def test_wall_and_missing_models_do_not_become_weather_experiments(self):
        for reason in ('terrain-blocked','missing-model','wind-out-of-domain'):
            self.assertIsNone(weather_probe(NoAim('fail',reason=reason,recovery={'weather_probes':[self.plan()]}),{},[],'game','profile'))
    def test_weather_measurements_do_not_inflate_normal_aim_evaluation(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=Mock();learner.episode='game';learner.records={};trial=AdaptiveTrial(Path(folder)/'report.json',learner);profile=trial.profile('ARMOR',0)
            plan={**self.plan(),'profile':profile.key,'action':'medir clima','weather_kinds':['3']}
            trial.record({'power':180,'learner':plan},{})
            self.assertEqual(trial.summary()['weather_practice_shots'],1);self.assertEqual(trial.summary()['directed_test_shots'],0);self.assertEqual(trial.summary()['calibration_shots'],0)
    def test_recovered_turn_is_removed_from_omitted_count(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=Mock();learner.records={};trial=AdaptiveTrial(Path(folder)/'report.json',learner)
            key=('room',0,1);trial.turn_skipped(key);trial.turn_recovered(key)
            self.assertEqual(trial.summary()['skipped_turns'],0)

class WeaponLearningTests(unittest.TestCase):
    def test_provisional_observed_damage_can_guide_weapon_choice_without_validating_dd(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=Mock();learner.episode='game';learner.records={f'dragonbound:ARMOR:{s}':{'model':MODEL} for s in (0,1)};learner.applicable_model.return_value=(MODEL,'known')
            trial=AdaptiveTrial(Path(folder)/'report.json',learner,allow_dual=True)
            state={'heroId':0,'wind':0,'windAngle':0,'players':[{'id':0,'x':0,'y':0,'hp':800,'shield':0},{'id':1,'x':300,'y':0,'hp':500,'shield':0}]}
            for shot,damage in ((0,10),(1,100)):
                profile=trial.profile('ARMOR',shot)
                profile.calibration=[{'episode':'game','target_id':1,'wind':0,'wind_angle':0,'health_window_known':True,'enemy_health_drop':damage} for _ in range(3)]
                profile.plan=Mock(return_value={'target':[300,0],'evaluation_phase':'calibration'})
            probe=trial.probe('ARMOR',state,[0,1]);self.assertEqual(probe['shot'],1)
            self.assertFalse(trial.plan(state,{},probe)['use_dual']);self.assertEqual(trial.summary()['directed_test_shots'],0)
    def test_unfinished_calibration_is_concentrated_instead_of_alternating_each_shot(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=Mock();learner.records={f'dragonbound:ARMOR:{s}':{'model':MODEL} for s in (0,1)};learner.applicable_model.return_value=(None,'unknown');learner.episode='game'
            trial=AdaptiveTrial(Path(folder)/'report.json',learner);profile=trial.profile('ARMOR',1);profile.episode='game';profile.warmups=2;profile.calibration=[{},{}]
            self.assertEqual(trial.probe('ARMOR',{'wind':0,'windAngle':0},[0,1])['shot'],1)
