import threading,unittest
from unittest.mock import Mock,patch
from training_browser import TrainingBrowser,TurnExpired
from training_aim import NoAim


class WalkFixture:
    def __init__(self,speed=30,seconds=20):self.now=0;self.x=100;self.speed=speed;self.seconds=seconds;self.held=False;self.serial=3;self.keys=[];self.change_turn=False
    def wait(self,delay):
        self.now+=delay
        if self.held:self.x+=self.speed*delay
        if self.change_turn:self.serial+=1
        return False
    def is_set(self):return False
    def read(self):return {'hero':0,'turn':0,'turnNumber':self.serial,'players':[{'id':0,'x':self.x,'y':100,'body':0}]}
    def browser(self):
        b=TrainingBrowser.__new__(TrainingBrowser);b.guard=Mock();b.seconds_left=lambda:self.seconds-self.now
        def key(name,down):self.keys.append((name,down));self.held=down
        b.key=key;return b


class WalkExecutionTests(unittest.TestCase):
    def test_larger_safe_request_uses_actual_position_beyond_old_fixed_duration(self):
        fixture=WalkFixture();browser=fixture.browser()
        with patch('training_browser.time.monotonic',side_effect=lambda:fixture.now):result=browser.walk(fixture,{'direction':'right','distance':40},fixture,3)
        self.assertGreater(fixture.now,.65);self.assertGreaterEqual(result['actual_distance'],38);self.assertLessEqual(result['actual_distance'],41)
        self.assertEqual(result['stop'],'distance-reached');self.assertFalse(fixture.held);self.assertEqual(fixture.keys[-1],('right',False))
    def test_short_request_does_not_continue_for_full_hold_time(self):
        fixture=WalkFixture(speed=60);browser=fixture.browser()
        with patch('training_browser.time.monotonic',side_effect=lambda:fixture.now):result=browser.walk(fixture,{'direction':'right','distance':4},fixture,3)
        self.assertLess(fixture.now,.2);self.assertLessEqual(result['actual_distance'],5);self.assertFalse(fixture.held)
    def test_short_remaining_turn_never_begins_walk(self):
        fixture=WalkFixture(seconds=6.6);browser=fixture.browser()
        with patch('training_browser.time.monotonic',side_effect=lambda:fixture.now),self.assertRaises(TurnExpired):browser.walk(fixture,{'direction':'right','distance':40},fixture,3)
        self.assertFalse(fixture.keys)
    def test_turn_change_releases_held_direction(self):
        fixture=WalkFixture();fixture.change_turn=True;browser=fixture.browser()
        with patch('training_browser.time.monotonic',side_effect=lambda:fixture.now),self.assertRaises(TurnExpired):browser.walk(fixture,{'direction':'right','distance':40},fixture,3)
        self.assertEqual(fixture.keys[-1],('right',False));self.assertFalse(fixture.held)
    def test_stalled_movement_ends_without_holding_until_deadline(self):
        fixture=WalkFixture(speed=0);browser=fixture.browser()
        with patch('training_browser.time.monotonic',side_effect=lambda:fixture.now):result=browser.walk(fixture,{'direction':'right','distance':40},fixture,3)
        self.assertEqual(result['stop'],'movement-stalled');self.assertLess(fixture.now,.5);self.assertFalse(fixture.held)
    def test_unexpected_external_motion_is_not_learned_as_walking_speed(self):
        fixture=WalkFixture(speed=500);browser=fixture.browser()
        with patch('training_browser.time.monotonic',side_effect=lambda:fixture.now):result=browser.walk(fixture,{'direction':'right','distance':40},fixture,3)
        self.assertEqual(result['stop'],'external-motion');self.assertFalse(browser.walk_speeds);self.assertFalse(fixture.held)
    def test_opposite_movement_is_not_counted_as_reaching_the_requested_position(self):
        fixture=WalkFixture(speed=-30);browser=fixture.browser()
        with patch('training_browser.time.monotonic',side_effect=lambda:fixture.now):result=browser.walk(fixture,{'direction':'right','distance':14},fixture,3)
        self.assertEqual(result['stop'],'external-motion');self.assertLess(result['actual_distance'],3)
        self.assertFalse(browser.walk_speeds);self.assertFalse(fixture.held)
    def test_reverse_displacement_midwalk_is_detected_before_crossing_origin(self):
        fixture=WalkFixture();browser=fixture.browser();original_wait=fixture.wait
        def wait(delay):
            if fixture.now>.2:fixture.speed=-30
            return original_wait(delay)
        fixture.wait=wait
        with patch('training_browser.time.monotonic',side_effect=lambda:fixture.now):result=browser.walk(fixture,{'direction':'right','distance':40},fixture,3)
        self.assertEqual(result['stop'],'external-motion');self.assertGreater(result['to'][0],100)
        self.assertFalse(browser.walk_speeds);self.assertFalse(fixture.held)
    def test_ambiguous_walk_reserves_its_distance_across_reconnect(self):
        shared={};key=('room','0',3)
        def make():
            b=TrainingBrowser.__new__(TrainingBrowser);b.guard=Mock();b.sample=Mock(return_value={'players':[]});b.seconds_left=Mock(return_value=20);b.orient=Mock();b.recovery_state=shared;b.recovery_key=key
            reader=Mock();reader.read.return_value={'hero':0,'turn':0,'turnNumber':3,'players':[{'id':0,'x':100,'y':100}]}
            return b,reader
        learner=Mock();learner.plan.side_effect=NoAim('blocked',reposition=True);first,reader=make();first.walk=Mock(side_effect=ConnectionError('lost after moving'))
        with patch('training_movement.choose_reposition',return_value={'direction':'right','distance':40}),self.assertRaises(ConnectionError):first.plan_with_reposition(reader,learner,{},500,3,threading.Event())
        self.assertEqual(shared['distance_used'],40);second,reader=make()
        with patch('training_movement.choose_reposition',return_value=None) as choice,self.assertRaises(NoAim):second.plan_with_reposition(reader,learner,{},500,3,threading.Event())
        self.assertEqual(choice.call_args.kwargs['movement_budget'],32);self.assertEqual(shared['distance_used'],40)

if __name__=='__main__':unittest.main()
