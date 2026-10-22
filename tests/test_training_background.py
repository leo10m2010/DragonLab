import json,subprocess,sys,tempfile,threading,unittest,uuid
from pathlib import Path
from unittest.mock import Mock
from training_browser import TrainingBrowser,FocusPause
from training_lease import TrainingLease
from training_session import TrainingSession
from training_aim import NoAim

class BackgroundTests(unittest.TestCase):
    def browser(self,background):
        b=TrainingBrowser.__new__(TrainingBrowser);b.background=background;b.ui=Mock(return_value={'focused':False,'chat':False});return b
    def test_background_allows_blur_but_foreground_pauses(self):
        self.browser(True).guard(threading.Event())
        with self.assertRaises(FocusPause):self.browser(False).guard(threading.Event())
    def test_background_still_blocks_chat_escape_and_cancel(self):
        b=self.browser(True);c=threading.Event();b.ui.return_value['chat']=True
        with self.assertRaises(FocusPause):b.guard(c)
        b.ui.return_value.update(chat=False,stop=True)
        with self.assertRaises(RuntimeError):b.guard(c)
        self.assertTrue(c.is_set())
    def test_background_start_does_not_request_foreground(self):
        import time
        from training_controller import TrainingController
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            s=TrainingSession('',None,Path(tmp)/'book.json',lambda e:None,background=True)
            controller=TrainingController(s);controller.cycle=Mock(return_value=False);browser=Mock()
            with patch('training_controller.TrainingBrowser',return_value=browser),patch('training_power.SleepLease'):controller.run()
            browser.arm.assert_called_once_with(focus=False);self.assertTrue(browser.background)
    def test_virtual_focus_is_enabled_without_bringing_page_forward_and_cleared(self):
        b=self.browser(True);b.client=Mock();b.arm(focus=True)
        calls=b.client.call.call_args_list
        self.assertIn(('Emulation.setFocusEmulationEnabled',{'enabled':True}),[c.args for c in calls])
        self.assertNotIn('Page.bringToFront',[c.args[0] for c in calls])
        b.control_lease=Mock();b.close()
        self.assertIn(('Emulation.setFocusEmulationEnabled',{'enabled':False}),[c.args for c in b.client.call.call_args_list]);b.control_lease.close.assert_called_once()
    def test_locked_data_does_not_overwrite_the_active_sessions_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            book=Path(tmp)/'book.json';status=Path(tmp)/'entrenamiento-estado.json';status.write_text('active owner')
            with TrainingLease('data:'+str(book.parent.resolve()).casefold()):
                s=TrainingSession('',None,book,lambda e:None);s.run()
            self.assertEqual(status.read_text(),'active owner');self.assertFalse(s.running);self.assertIn('Otra sesión',s.status)
    def test_loading_home_page_waits_without_input_or_selecting_another_server(self):
        from training_controller import TrainingController
        with tempfile.TemporaryDirectory() as tmp:
            s=TrainingSession('',None,Path(tmp)/'book.json',lambda e:None);s.cancel.wait=Mock(return_value=False)
            c=TrainingController(s);b=Mock();b.guard.return_value={'url':'https://dragonbound.net/','game':False,'serverEntry':None}
            c.cycle(b);b.click.assert_not_called();b.shoot.assert_not_called()
            self.assertIn('cargue',s.status)
    def test_turn_animation_does_not_consume_or_mark_a_failed_turn(self):
        from training_controller import TrainingController
        from training_browser import TurnNotReady
        with tempfile.TemporaryDirectory() as tmp:
            s=TrainingSession('',None,Path(tmp)/'book.json',lambda e:None);s.cancel.wait=Mock(return_value=False)
            c=TrainingController(s);b=Mock();b.movement_events=[]
            b.guard.return_value={'game':True,'url':'https://dragonbound.net/#server-8/room-1','controls':{'btnShot1':True},'options':[]}
            b.sample.return_value={'status':'live','turnSerial':3,'heroId':0,'activePlayer':0,'wind':0,'players':[{'id':0,'mobile':0,'x':0,'y':0}]}
            b.shoot.side_effect=TurnNotReady('animation');c.cycle(b)
            self.assertFalse(c.ledger.used);self.assertEqual(c.failures,0);self.assertFalse(s.errors)
    def test_same_resource_is_exclusive_across_processes_and_released(self):
        key='test:'+uuid.uuid4().hex
        code='from training_lease import TrainingLease; TrainingLease('+repr(key)+').close()'
        with TrainingLease(key):
            completed=subprocess.run([sys.executable,'-B','-X','utf8','-c',code],capture_output=True,text=True)
            self.assertNotEqual(completed.returncode,0);self.assertIn('Otra sesión',completed.stderr)
        completed=subprocess.run([sys.executable,'-B','-X','utf8','-c',code],capture_output=True,text=True)
        self.assertEqual(completed.returncode,0,completed.stderr)
    def test_separate_resources_do_not_block_each_other(self):
        with TrainingLease('first:'+uuid.uuid4().hex),TrainingLease('second:'+uuid.uuid4().hex):pass
    def test_skip_diagnostic_retains_machine_readable_reason(self):
        from training_evaluation import EvaluationTrial
        with tempfile.TemporaryDirectory() as tmp:
            learner=Mock();learner.records={};trial=EvaluationTrial(Path(tmp)/'trial.json',learner)
            trial.skip(NoAim('unknown weather',reason='unknown-weather'))
            self.assertEqual(trial.summary()['skip_reasons'],{'unknown-weather':1})
