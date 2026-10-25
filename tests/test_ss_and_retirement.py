import tempfile,threading,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from training_browser import TrainingBrowser,UnavailableShot,TurnNotReady,FocusPause
from training_controller import TrainingController
from training_session import TrainingSession


class ShotReadinessTests(unittest.TestCase):
    def test_selected_but_cooling_ss_is_rejected_before_any_charge(self):
        with self.assertRaises(UnavailableShot):TrainingBrowser.require_shot_ready({'shotReady':[True,True,False]},2)
        TrainingBrowser.require_shot_ready({'shotReady':[True,True,True]},2)
        TrainingBrowser.require_shot_ready({'shotReady':[True,True,False]},0)
    def test_cached_angle_limit_from_bullet_two_does_not_clamp_bullet_one(self):
        browser=TrainingBrowser.__new__(TrainingBrowser);browser.angle_mobile='ICE';browser.angle_shot=0
        browser.angle_limits={('ICE',1,0,1):{'low':40,'high':60}}
        state={'hero':0,'turn':0,'turnNumber':1,'players':[{'id':0,'rawAngle':30,'body':0,'look':1,'minAngle':10,'maxAngle':70}]}
        reader=Mock();reader.read.return_value=state
        result=browser.adjust_angle(reader,30,threading.Event(),1)
        self.assertTrue(result['reached']);self.assertEqual(result['after'],30)
    def test_replaced_control_is_never_clicked_at_old_coordinates(self):
        browser=TrainingBrowser.__new__(TrainingBrowser);browser.client=Mock();browser.guard=Mock(return_value={'controls':{'btnShotSS':None},'options':[]})
        with self.assertRaises(TurnNotReady):browser.click({'x':12,'y':12,'control':'btnShotSS'},threading.Event())
        browser.client.call.assert_not_called()
    def test_unknown_exit_confirmation_cannot_reuse_an_old_ok_point(self):
        browser=TrainingBrowser.__new__(TrainingBrowser);browser.client=Mock();browser.guard=Mock(return_value={'blocked':True,'retirement':None,'away':None,'notice':None})
        with self.assertRaises(TurnNotReady):browser.click({'x':12,'y':12,'control':'dialog-ok'},threading.Event())
        browser.client.call.assert_not_called()
    def test_dialog_appearing_mid_shot_pauses_inputs_but_remains_readable_to_controller(self):
        browser=TrainingBrowser.__new__(TrainingBrowser);browser.background=True;browser.ui=Mock(return_value={'blocked':True,'chat':False})
        browser.reader=None;self.assertTrue(browser.guard(threading.Event())['blocked'])
        browser.reader=Mock()
        with self.assertRaises(FocusPause):browser.guard(threading.Event())


class RecoveryTests(unittest.TestCase):
    def make(self,folder):
        session=TrainingSession('',None,Path(folder)/'book.json',Mock(),continuous=True,autonomous=True,objective='adaptive')
        session.cancel.wait=Mock(return_value=False);session.publish=Mock()
        return session,TrainingController(session)
    def test_retirement_respects_static_seconds_without_waiting_forever_or_early_ok(self):
        with tempfile.TemporaryDirectory() as folder:
            session,controller=self.make(folder);browser=Mock();browser.guard.return_value={'retirement':{'seconds':59,'point':{'x':1,'y':2}}}
            with patch('training_controller.time.monotonic',return_value=100):controller.cycle(browser)
            browser.click.assert_not_called();self.assertEqual(session.retirements,1)
            with patch('training_controller.time.monotonic',return_value=120):controller.cycle(browser)
            browser.click.assert_not_called();self.assertEqual(session.retirements,1)
            with patch('training_controller.time.monotonic',return_value=160):controller.cycle(browser)
            browser.click.assert_called_once();browser.shoot.assert_not_called()
    def test_all_rejected_modes_pass_once_without_firing_arbitrary_power(self):
        with tempfile.TemporaryDirectory() as folder:
            session,controller=self.make(folder);browser=Mock();browser.movement_events=[]
            url='https://dragonbound.net/#server-8/room-1';key=(url,'0',3)
            state={'status':'live','heroId':0,'activePlayer':0,'turnSerial':3,'wind':0,'windAngle':0,'players':[{'id':0,'mobile':0,'x':0,'y':0}],'shots':[]}
            browser.guard.return_value={'game':True,'url':url,'controls':{'btnShot1':True,'btnShot2':True,'btnShotSS':None},'options':[]};browser.sample.return_value=state
            controller.in_game=True;controller.current=key;controller.geometry=(0,0,0,0);controller.blocked={0,1}
            def passed(key,cancel,before):before();return True
            browser.pass_turn.side_effect=passed
            controller.cycle(browser);controller.cycle(browser)
            browser.pass_turn.assert_called_once();browser.shoot.assert_not_called();self.assertEqual(session.passed_turns,1)
