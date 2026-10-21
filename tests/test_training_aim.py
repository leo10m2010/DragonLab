import unittest,threading,itertools
from unittest.mock import Mock,patch
from core import Settings
from training_aim import choose_aim,actual_solution
from training_browser import TrainingBrowser
from training_ui import settings_provider

class GuidedTrainingTests(unittest.TestCase):
    def test_guided_power_comes_from_lab_instead_of_probe_force(self):
        with patch('training_aim.solve',return_value={'reachable':True,'power':207}) as solve:
            angle,result=choose_aim(Settings(),55)
        self.assertEqual(angle,55);self.assertEqual(result['power'],207)
        self.assertEqual(solve.call_args.args[0].angle,55)
    def test_actual_angle_must_be_recomputed_and_blocked_result_never_fires(self):
        with patch('training_aim.solve',return_value={'reachable':True,'blocked':True,'power':200}):
            with self.assertRaises(RuntimeError):actual_solution(Settings(angle=35))
    def test_planner_respects_native_angle_range_before_solving(self):
        with patch('training_aim.solve',return_value={'reachable':True,'power':170}) as solve:
            angle,_=choose_aim(Settings(),75,(10,50))
        self.assertEqual(angle,50);self.assertEqual(solve.call_args.args[0].angle,50)
    def test_angle_hold_is_released_after_confirmed_downward_movement(self):
        browser=TrainingBrowser.__new__(TrainingBrowser);browser.guard=Mock();browser.key=Mock()
        states=[55,54,53,52]
        reader=Mock();reader.read.side_effect=[{'hero':0,'turn':0,'players':[{'id':0,'rawAngle':v}]} for v in states]
        cancel=Mock();cancel.wait.return_value=False
        result=browser.adjust_angle(reader,52,cancel)
        self.assertLess(result['after'],result['before'])
        self.assertEqual(browser.key.call_args_list[0].args,('down',True))
        self.assertEqual(browser.key.call_args_list[-1].args,('down',False))
    def test_no_angle_movement_aborts_before_charge(self):
        browser=TrainingBrowser.__new__(TrainingBrowser);browser.guard=Mock();browser.key=Mock()
        reader=Mock();reader.read.return_value={'hero':0,'turn':0,'players':[{'id':0,'rawAngle':20}]}
        cancel=Mock();cancel.wait.return_value=False
        times=itertools.count(0,.2)
        with patch('training_browser.time.monotonic',side_effect=lambda:next(times)):
            with self.assertRaisesRegex(RuntimeError,'no cambió'):browser.adjust_angle(reader,55,cancel)
        self.assertEqual(browser.key.call_args_list[-1].args,('up',False))
        self.assertNotIn(('space',True),[c.args for c in browser.key.call_args_list])
    def test_cancel_during_angle_adjustment_releases_key(self):
        browser=TrainingBrowser.__new__(TrainingBrowser);browser.guard=Mock();browser.key=Mock()
        reader=Mock();reader.read.return_value={'hero':0,'turn':0,'players':[{'id':0,'rawAngle':20}]}
        cancel=Mock();cancel.wait.return_value=True
        with self.assertRaises(RuntimeError):browser.adjust_angle(reader,55,cancel)
        self.assertEqual(browser.key.call_args_list[-1].args,('up',False))
    def test_native_car_angle_limit_is_used_before_sending_input(self):
        browser=TrainingBrowser.__new__(TrainingBrowser);browser.key=Mock()
        reader=Mock();reader.read.return_value={'hero':0,'turn':0,'players':[{'id':0,'rawAngle':55,'minAngle':10,'maxAngle':55}]}
        result=browser.adjust_angle(reader,75,threading.Event())
        self.assertTrue(result['limited']);self.assertEqual(result['after'],55)
        browser.key.assert_not_called()
    def test_reverse_range_uses_up_to_decrease_raw_angle(self):
        browser=TrainingBrowser.__new__(TrainingBrowser);browser.guard=Mock();browser.key=Mock()
        reader=Mock();reader.read.side_effect=[{'hero':0,'turn':0,'players':[{'id':0,'rawAngle':v,'minAngle':110,'maxAngle':170}]} for v in [155,150,140,130]]
        cancel=Mock();cancel.wait.return_value=False
        result=browser.adjust_angle(reader,130,cancel)
        self.assertEqual(result['after'],130)
        self.assertEqual(browser.key.call_args_list[0].args,('up',True))
        self.assertEqual(browser.key.call_args_list[-1].args,('up',False))
    def test_unexpected_key_effect_is_detected_and_corrected_before_firing(self):
        browser=TrainingBrowser.__new__(TrainingBrowser);browser.guard=Mock();browser.key=Mock()
        reader=Mock();reader.read.side_effect=[{'hero':0,'turn':0,'players':[{'id':0,'rawAngle':v,'minAngle':10,'maxAngle':70}]} for v in [40,41,39,36]]
        cancel=Mock();cancel.wait.return_value=False
        result=browser.adjust_angle(reader,35,cancel)
        self.assertLess(result['after'],result['before'])
        self.assertIn(('down',False),[c.args for c in browser.key.call_args_list])
        self.assertIn(('up',True),[c.args for c in browser.key.call_args_list])
        self.assertEqual(browser.key.call_args_list[-1].args,('up',False))
    def test_settings_bridge_rejects_cancellation_without_touching_tk(self):
        app=Mock();cancel=threading.Event();cancel.set()
        with self.assertRaises(RuntimeError):settings_provider(app)({},cancel)
        event=app.events.put.call_args.args[0]
        self.assertEqual(event['status'],'training-settings')
