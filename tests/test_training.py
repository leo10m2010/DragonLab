import unittest,tempfile,threading
from pathlib import Path
from unittest.mock import Mock,patch
from training_policy import next_probe,next_mobile,wind_bin
from training_session import TrainingSession
from training_browser import TrainingBrowser
class TrainingTests(unittest.TestCase):
    def test_probe_only_chooses_available_modes(self):self.assertEqual(next_probe({},'armor',5,available=(1,))['shot'],1)
    def test_new_validation_has_priority_over_training(self):
        r={'dragonbound:ARMOR:2':{'candidate':{'validation':[]}}}
        self.assertEqual(next_probe(r,'ARMOR',10)['shot'],2)
    def test_chooses_a_distant_validation_power(self):
        r={'dragonbound:ARMOR:0':{'candidate':{'validation':[{'power':100}]}}}
        self.assertGreater(next_probe(r,'ARMOR',10)['power'],300)
    def test_unknown_mobile_and_invalid_wind_are_rejected(self):
        with self.assertRaises(ValueError):next_probe({},'unknown',10)
        with self.assertRaises(ValueError):wind_bin(float('nan'))
    def test_multibullet_measurements_advance_the_curriculum_without_becoming_fits(self):
        records={'dragonbound:TRICO:0':{'training_patterns':[{'power':100,'wind':10}]}}
        self.assertEqual(next_probe(records,'TRICO',10)['shot'],1)
        self.assertEqual(next_probe(records,'TRICO',10,available=(0,))['power'],360)
    def test_room_is_allowed_only_on_authorized_server(self):
        b=TrainingBrowser.__new__(TrainingBrowser);b.client=Mock()
        b.client.call.return_value={'result':{'value':{'url':'https://dragonbound.net/#server-8/room-123'}}}
        self.assertIn('room-123',b.ui()['url'])
        b.client.call.return_value={'result':{'value':{'url':'https://dragonbound.net/#server-80'}}}
        with self.assertRaises(RuntimeError):b.ui()
    def test_mobile_rotation_uses_only_available_choices(self):
        options=[{'name':'Armor','id':0},{'name':'Ice','id':1}]
        self.assertEqual(next_mobile(options,{'ARMOR':1})['name'],'Ice')
    def test_session_does_not_start_just_by_construction(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=TrainingSession('http://127.0.0.1:9223',None,Path(tmp)/'book.json',lambda e:None)
            self.assertFalse(s.running);self.assertIsNone(s.thread)
    def test_session_limit_rejected_before_any_input(self):
        with self.assertRaises(ValueError):TrainingSession('',None,'book.json',lambda e:None,max_shots=0)
    def test_cancel_sends_no_click(self):
        b=TrainingBrowser.__new__(TrainingBrowser);b.client=Mock();cancel=threading.Event();cancel.set()
        with self.assertRaises(RuntimeError):b.click({'x':10,'y':10},cancel)
        b.client.call.assert_not_called()
    def test_wrong_server_rejected(self):
        b=TrainingBrowser.__new__(TrainingBrowser);b.client=Mock();b.client.call.return_value={'result':{'value':{'url':'https://dragonbound.net/#server-7'}}}
        with self.assertRaises(RuntimeError):b.ui()
    def test_lost_focus_or_chat_stops_before_input(self):
        b=TrainingBrowser.__new__(TrainingBrowser);b.client=Mock();b.ui=lambda:{'focused':False}
        with self.assertRaises(RuntimeError):b.click({'x':10,'y':10},threading.Event())
        b.client.call.assert_not_called()
    def test_mouse_release_is_attempted_even_if_press_acknowledgment_fails(self):
        b=TrainingBrowser.__new__(TrainingBrowser);b.client=Mock();b.guard=lambda cancel:{}
        b.client.call.side_effect=[TimeoutError('no acknowledgment'),{}]
        with self.assertRaises(TimeoutError):b.click({'x':10,'y':20},threading.Event())
        self.assertEqual(b.client.call.call_args_list[-1].args[1]['type'],'mouseReleased')
    def test_patterns_are_not_silently_promoted_as_a_single_bullet(self):
        from calibration_book import CalibrationBook
        with tempfile.TemporaryDirectory() as tmp:
            b=CalibrationBook(Path(tmp)/'book.json')
            hero={'id':0,'x':0,'y':0,'mobile':12};shots=[{'id':i,'native':True,'elapsed':0,'start':[0,0,45+i,200,0,100],'metadata':{'player':0,'power':100},'shotType':0} for i in range(3)]
            state={'status':'live','heroId':0,'activePlayer':0,'players':[hero,{'id':1,'x':500,'y':0}], 'shots':shots,'selectedShot':0,'currentPower':100,'wind':0,'windAngle':90}
            release={'hero':0,'x':0,'y':0,'power':100,'shot':0,'wind':0,'windAngle':90,'baseline':[]}
            b.observe_training(state,release);r=b.records['dragonbound:TRICO:0']
            self.assertEqual(len(r['training_patterns']),1);self.assertNotIn('fit',r);self.assertEqual(r['samples'],[])
            b.observe_training(state,release);self.assertEqual(len(r['training_patterns']),1)
