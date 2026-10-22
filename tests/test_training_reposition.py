import threading,unittest
from unittest.mock import Mock,patch
from training_browser import TrainingBrowser,TurnExpired
from training_aim import NoAim

class RepositionTests(unittest.TestCase):
    def setup_browser(self):
        b=TrainingBrowser.__new__(TrainingBrowser);b.guard=Mock();b.sample=Mock(return_value={'players':[]});b.seconds_left=Mock(return_value=20);b.orient=Mock()
        b.walk=Mock(return_value={'from':[100,100],'to':[114,100],'direction':'right'})
        reader=Mock();reader.read.return_value={'hero':0,'turn':0,'turnNumber':3,'players':[{'id':0,'x':100,'y':100}]}
        return b,reader,threading.Event()
    def test_geometry_failure_walks_and_replans_without_an_arbitrary_shot(self):
        b,r,c=self.setup_browser();learner=Mock();learner.plan.side_effect=[NoAim('angle',reposition=True),{'power':200,'raw_angle':40}]
        with patch('training_movement.choose_reposition',return_value={'direction':'right','distance':14}):result,movement=b.plan_with_reposition(r,learner,{},500,3,c)
        self.assertEqual(result['power'],200);self.assertEqual(learner.plan.call_count,2);self.assertEqual(len(movement['steps']),1);b.walk.assert_called_once();b.orient.assert_called_once()
    def test_uncalibrated_weather_or_missing_model_does_not_trigger_movement(self):
        b,r,c=self.setup_browser();learner=Mock();learner.plan.side_effect=NoAim('unknown weather')
        with self.assertRaises(NoAim):b.plan_with_reposition(r,learner,{},500,3,c)
        b.walk.assert_not_called()
    def test_no_ground_or_short_turn_does_not_walk(self):
        for seconds in (7,20):
            b,r,c=self.setup_browser();b.seconds_left.return_value=seconds;learner=Mock();learner.plan.side_effect=NoAim('blocked',reposition=True)
            with patch('training_movement.choose_reposition',return_value=None),self.assertRaises(NoAim):b.plan_with_reposition(r,learner,{},500,3,c)
            b.walk.assert_not_called()
    def test_two_failed_steps_end_without_shooting_or_looping(self):
        b,r,c=self.setup_browser();learner=Mock();learner.plan.side_effect=NoAim('blocked',reposition=True)
        with patch('training_movement.choose_reposition',return_value={'direction':'right'}),self.assertRaises(NoAim):b.plan_with_reposition(r,learner,{},500,3,c)
        self.assertEqual(b.walk.call_count,2);self.assertEqual(learner.plan.call_count,3)
    def test_changed_turn_cancels_before_movement_or_replanning(self):
        b,r,c=self.setup_browser();r.read.return_value['turnNumber']=4;learner=Mock()
        with self.assertRaises(TurnExpired):b.plan_with_reposition(r,learner,{},500,3,c)
        b.walk.assert_not_called();learner.plan.assert_not_called()
    def test_stalled_direction_is_not_repeated(self):
        b,r,c=self.setup_browser();b.walk.return_value={'from':[100,100],'to':[100,100],'direction':'right'}
        learner=Mock();learner.plan.side_effect=[NoAim('blocked',reposition=True),NoAim('blocked',reposition=True),{'power':200}]
        with patch('training_movement.choose_reposition',return_value={'direction':'right'}) as step:b.plan_with_reposition(r,learner,{},500,3,c)
        self.assertEqual(step.call_args_list[1].kwargs['avoid'],'right')
