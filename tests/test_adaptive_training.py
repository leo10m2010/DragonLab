import tempfile,threading,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from adaptive_training import AdaptiveTrial
from training_evaluation import EvaluationTrial
from training_browser import TrainingBrowser,TurnExpired
from training_aim import NoAim
from training_session import TrainingSession
from training_controller import TrainingController

def learner():
    l=Mock();l.episode='game-a';l.records={f'dragonbound:{mobile}:{shot}':{'model':{'scale':2,'offset':0,'gravity':400,'wind_scale':4}} for mobile in ('ARMOR','ICE') for shot in range(3)}
    l.applicable_model.return_value=({'scale':2,'offset':0,'gravity':400,'wind_scale':4},'known');return l

class AdaptiveTests(unittest.TestCase):
    def test_models_and_frozen_trials_are_isolated_by_vehicle_and_weapon(self):
        with tempfile.TemporaryDirectory() as tmp:
            l=learner();a=AdaptiveTrial(Path(tmp)/'report.json',l)
            first=a.profile('ARMOR',0);second=a.profile('ICE',2);first.frozen={'model':{'scale':999}}
            self.assertIsNone(second.frozen);self.assertEqual(second.key,'dragonbound:ICE:2');self.assertNotEqual(first.path,second.path)
    def test_generalized_evaluation_reads_only_its_own_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            l=learner();l.records['dragonbound:ICE:2']['model']['scale']=7
            t=EvaluationTrial(Path(tmp)/'report.json',l,mobile='ICE',shot=2)
            self.assertEqual(t.baseline['scale'],7);self.assertEqual(t.probe()['mobile'],'ICE');self.assertEqual(t.probe()['shot'],2)
    def test_available_modes_filter_excludes_ss_when_cooling_down(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=AdaptiveTrial(Path(tmp)/'report.json',learner());state={'wind':0,'windAngle':0}
            self.assertIn(a.probe('ARMOR',state,[0,1])['shot'],[0,1])
            self.assertEqual(a.probe('ARMOR',state,[2])['shot'],2)
    def test_lethal_normal_shot_preserves_ss_and_unknown_profile_is_not_misattributed(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=AdaptiveTrial(Path(tmp)/'report.json',learner());state={'wind':0,'windAngle':0,'heroId':0,'players':[{'id':0,'x':0,'y':0,'hp':1000,'shield':0},{'id':1,'x':500,'y':0,'hp':50,'shield':0}]}
            for mode,damage in ((0,100),(2,400)):
                a.profile('ARMOR',mode).tests=[{'health_window_known':True,'enemy_health_drop':damage} for _ in range(3)]
            self.assertEqual(a.probe('ARMOR',state,[0,2])['shot'],0)
            with self.assertRaises(NoAim):a.probe('NAK',state,[2])
            self.assertIsNone(a.selected)
    def test_no_data_never_becomes_an_arbitrary_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            l=learner();l.records={};a=AdaptiveTrial(Path(tmp)/'report.json',l)
            with self.assertRaises(NoAim):a.probe('ARMOR',{'wind':0,'windAngle':0},[0,1,2])
    def test_vehicle_selection_rotates_only_among_supported_cars(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=AdaptiveTrial(Path(tmp)/'report.json',learner());options=[{'id':0,'name':'Armor'},{'id':1,'name':'Ice'},{'id':2,'name':'Trico'}]
            self.assertEqual(a.choose_mobile(options,{'ARMOR':2})['name'],'Ice')
    def test_rejected_modes_do_not_inflate_skipped_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=AdaptiveTrial(Path(tmp)/'report.json',learner());a.skip(NoAim('blocked'));a.skip(NoAim('climate'))
            self.assertEqual(a.summary()['skipped_turns'],0);self.assertEqual(a.summary()['rejected_modes'],2)
            a.turn_skipped(('room',0,1));a.turn_skipped(('room',0,1));self.assertEqual(a.summary()['skipped_turns'],1)
    def test_dual_is_kept_out_of_normal_profile_evaluation(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=AdaptiveTrial(Path(tmp)/'report.json',learner());t=a.profile('ARMOR',0)
            token=a.record({'item':'dual','power':200,'learner':{'profile':t.key}}, {})
            self.assertEqual(len(t.tests),0);self.assertEqual(len(t.calibration),0);self.assertEqual(a.summary()['dual_uses'],1)
            a.health_result({'token':token,'known':True,'enemy_health_drop':300})
            self.assertEqual(a.dual_rows[0]['enemy_health_drop'],300)
    def test_dual_requires_future_aim_and_damage_evidence_and_never_ss(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=AdaptiveTrial(Path(tmp)/'report.json',learner(),allow_dual=True)
            state={'heroId':0,'players':[{'id':0,'x':0,'y':0,'hp':1000,'shield':0},{'id':1,'x':500,'y':0,'hp':1000,'shield':0}]}
            for shot in (0,2):
                t=a.profile('ARMOR',shot);t.plan=Mock(return_value={'target':[500,0],'evaluation_phase':'evaluation'})
                t.tests=[{'path_error_px':5,'health_window_known':True,'enemy_health_drop':100} for _ in range(5)]
                self.assertEqual(a.plan(state,{}, {'mobile':'ARMOR','shot':shot})['use_dual'],shot==0)
            a.allow_dual=False;self.assertFalse(a.plan(state,{}, {'mobile':'ARMOR','shot':0})['use_dual'])
            a.allow_dual=True;a.profile('ARMOR',0).tests=[];self.assertFalse(a.plan(state,{}, {'mobile':'ARMOR','shot':0})['use_dual'])
    def test_failure_tries_another_weapon_in_same_turn_without_double_charge(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=TrainingSession('',None,Path(tmp)/'book.json',lambda e:None,autonomous=True,objective='adaptive');s.cancel.wait=Mock(return_value=False)
            c=TrainingController(s);c.learner=learner();c.trial.learner=c.learner;b=Mock();b.movement_events=[]
            b.guard.return_value={'game':True,'url':'https://dragonbound.net/#server-8/room-1','controls':{'btnShot1':True,'btnShot2':True},'options':[]}
            b.sample.return_value={'status':'live','heroId':0,'activePlayer':0,'turnSerial':1,'wind':0,'windAngle':0,'players':[{'id':0,'mobile':0,'x':0,'y':0}],'shots':[]}
            b.shoot.side_effect=NoAim('blocked');c.cycle(b);self.assertFalse(c.ledger.used);c.cycle(b)
            self.assertEqual([call.args[0]['shot'] for call in b.shoot.call_args_list],[0,1]);self.assertFalse(c.ledger.used)
            c.cycle(b);self.assertEqual(len(c.ledger.used),1);self.assertEqual(c.trial.summary()['skipped_turns'],1)

class DualControls(unittest.TestCase):
    def make(self):
        b=TrainingBrowser.__new__(TrainingBrowser);b.require_charge_time=Mock();b.click=Mock();b.guard=Mock(return_value={'controls':{'dual':{'x':1,'y':1}},'selectedItems':[],'dualSelected':False})
        r=Mock();r.read.return_value={'hero':0,'turn':0,'turnNumber':3,'shot':0};return b,r,threading.Event()
    def test_dd_requires_visual_confirmation_before_charge(self):
        b,r,c=self.make();b.guard.side_effect=[{'controls':{'dual':{}},'selectedItems':[],'dualSelected':False},{'dualSelected':True}]
        self.assertFalse(b.select_dual(r,3,c));b.click.assert_not_called()
        b,r,c=self.make();b.guard.side_effect=[{'controls':{'dual':{'x':1,'y':1}},'selectedItems':[],'dualSelected':False},{'dualSelected':True}]
        self.assertTrue(b.select_dual(r,3,c));b.click.assert_called_once()
    def test_missing_confirmation_does_not_start_a_charge(self):
        b,r,c=self.make()
        with self.assertRaises(NoAim):b.select_dual(r,3,c)
    def test_dd_rejects_ss_changed_turn_or_other_selected_item(self):
        for change in ({'shot':2},{'turnNumber':4}):
            b,r,c=self.make();r.read.return_value.update(change)
            with self.assertRaises(TurnExpired):b.select_dual(r,3,c)
            b.click.assert_not_called()
        b,r,c=self.make();b.guard.return_value['selectedItems']=[{'dual':False}]
        with self.assertRaises(NoAim):b.select_dual(r,3,c)
        b.click.assert_not_called()

class OrientationTests(unittest.TestCase):
    def test_orientation_waits_for_native_confirmation_and_releases_key(self):
        b=TrainingBrowser.__new__(TrainingBrowser);b.guard=Mock();b.key=Mock();r=Mock();c=Mock();c.wait.return_value=False
        first={'hero':0,'turn':0,'turnNumber':1,'players':[{'id':0,'look':0}]}
        later={'hero':0,'turn':0,'turnNumber':1,'players':[{'id':0,'look':1}]}
        r.read.side_effect=[first,first,later]
        with patch('training_browser.desired_look',return_value=1):result=b.orient(r,True,1,c)
        self.assertEqual(result['look'],1);self.assertEqual(b.key.call_args.args,('right',False))
    def test_turn_change_during_orientation_releases_and_never_charges(self):
        b=TrainingBrowser.__new__(TrainingBrowser);b.guard=Mock();b.key=Mock();r=Mock();c=Mock();c.wait.return_value=False
        r.read.side_effect=[{'hero':0,'turn':0,'turnNumber':1,'players':[{'id':0,'look':0}]},{'hero':0,'turn':1,'turnNumber':2}]
        with patch('training_browser.desired_look',return_value=1),self.assertRaises(TurnExpired):b.orient(r,True,1,c)
        self.assertEqual(b.key.call_args.args,('right',False));self.assertNotIn('space',[call.args[0] for call in b.key.call_args_list])
