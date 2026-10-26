import copy,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from training_browser import TrainingBrowser,TurnNotReady,TurnExpired,UnavailableShot
from training_aim import NoAim
from autonomous_learning import AutonomousLearner
from training_evaluation import EvaluationTrial
from adaptive_training import AdaptiveTrial

class NativeReadinessTests(unittest.TestCase):
    def browser(self):
        b=TrainingBrowser.__new__(TrainingBrowser);b.guard=Mock(return_value={});b.key=Mock();b.turn_deadline=time.monotonic()+10
        return b
    def state(self):return {'hero':0,'turn':0,'turnNumber':3,'shot':1,'mode':'space','wind':2,'windAngle':90,'players':[{'id':0,'x':100,'y':100,'rawAngle':50,'look':1,'body':0},{'id':1,'x':400,'y':100}]}
    def release(self):return {'hero':0,'turn_serial':3,'shot':1,'wind':2,'windAngle':90,'x':100,'y':100,'angle':50,'pose':{'look':1,'body':0},'target_before':{'id':1,'x':400,'y':100}}
    def test_delayed_setting_is_confirmed_without_a_fixed_sleep(self):
        b=self.browser();r=Mock();old=self.state();old['shot']=0;r.read.side_effect=[old,old,self.state()];cancel=Mock();cancel.wait.return_value=False
        self.assertEqual(b.confirm_setting(r,3,'shot',1,cancel)['shot'],1);self.assertEqual(cancel.wait.call_count,2)
    def test_changed_turn_during_setting_is_not_an_unavailable_weapon(self):
        b=self.browser();r=Mock();r.read.return_value={**self.state(),'turnNumber':4}
        with self.assertRaises(TurnExpired):b.confirm_setting(r,3,'shot',1,threading.Event())
    def test_unconfirmed_setting_never_sends_space(self):
        b=self.browser();r=Mock();r.read.return_value={**self.state(),'shot':0}
        with patch('training_browser.time.monotonic',side_effect=[0,1]),self.assertRaises(UnavailableShot):b.confirm_setting(r,3,'shot',1,threading.Event())
        b.key.assert_not_called()
    def test_final_native_check_rejects_changed_pose_wind_target_and_animation(self):
        for change in ('pose','wind','target','busy','shot','mode'):
            b=self.browser();r=Mock();state=self.state()
            if change=='pose':state['players'][0]['body']=2
            elif change=='target':state['players'][1]['x']=420
            elif change=='wind':state['wind']=5
            elif change=='busy':state['busy']=True
            elif change=='shot':state['shot']=0
            else:state['mode']='drag'
            r.read.return_value=state
            with self.assertRaises(TurnNotReady,msg=change):b.verify_release(r,self.release(),threading.Event())
            b.key.assert_not_called()
    def test_final_native_check_accepts_matching_state(self):
        b=self.browser();r=Mock();r.read.return_value=self.state();b.verify_release(r,self.release(),threading.Event());b.key.assert_not_called()
    def test_dd_click_ownership_survives_confirmation_timeout(self):
        b=self.browser();b.click=Mock();b.guard.return_value={'controls':{'dual':{'x':1,'y':1}},'selectedItems':[],'dualSelected':False};r=Mock();r.read.return_value={**self.state(),'shot':0}
        with self.assertRaises(NoAim):b.select_dual(r,3,threading.Event())
        self.assertTrue(b.dual_selected_here);b.click.assert_called_once()

class EvidenceDomainTests(unittest.TestCase):
    def learner(self):
        learner=Mock();learner.episode='game';learner.records={};learner.applicable_model.return_value=(None,'out of domain');learner.plan.return_value={'stage':'evaluación con modelo congelado','power':100}
        return learner
    def trial(self,path):
        learner=self.learner();trial=EvaluationTrial(path,learner);trial.episode='game';trial.warmups=3;trial.prior={'scale':2,'offset':0,'gravity':400,'wind_scale':4}
        learner.records[trial.key]={'samples':[{'id':str(i),'episode':'game','simple':True,'power':p,'speed':2*p,'ax':40,'ay':400,'wind':10,'wind_angle':0,'heading':45,'duration_s':1} for i,p in enumerate([100,180,260])]}
        return trial
    def test_future_checks_at_another_wind_cannot_freeze_current_wind(self):
        with tempfile.TemporaryDirectory() as folder:
            trial=self.trial(Path(folder)/'report.json');result=trial.plan({'wind':30,'windAngle':90},{},{})
            self.assertIsNone(trial.frozen);self.assertEqual(result['evaluation_phase'],'calibration')
    def test_matching_varied_future_checks_can_promote_the_prior(self):
        with tempfile.TemporaryDirectory() as folder:
            trial=self.trial(Path(folder)/'report.json');result=trial.plan({'wind':10,'windAngle':0},{},{})
            self.assertEqual(result['evaluation_phase'],'evaluation');self.assertEqual(trial.frozen['wind'],10)
    def test_calibration_requests_alternate_directed_arcs_without_random_power(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.learner();learner.records={'dragonbound:ARMOR:0':{'model':{'scale':2}}};trial=AdaptiveTrial(Path(folder)/'report.json',learner);profile=trial.profile('ARMOR',0);profile.episode='game'
            profile.warmups=1;probe=trial.probe('ARMOR',{'wind':0,'windAngle':0},[0])
            self.assertFalse(probe['prefer_current_angle']);self.assertEqual(probe['angle'],75)
            profile.warmups=2;next_probe=trial.probe('ARMOR',{'wind':0,'windAngle':0},[0])
            self.assertFalse(next_probe['prefer_current_angle']);self.assertNotEqual(next_probe['angle'],probe['angle'])
    def test_full_native_path_counts_weather_at_launch_impact_and_column_edge(self):
        for x,size in ((5,2),(139,2),(-2,8)):
            with tempfile.TemporaryDirectory() as folder:
                learner=AutonomousLearner(Path(folder)/'learn.json')
                for i in range(3):
                    state={'status':'live','heroId':0,'activePlayer':0,'players':[{'id':0,'x':0,'y':0,'mobile':0},{'id':1,'x':300,'y':0}],'wind':0,'windAngle':0,'weather':[{'typeId':3,'x':x,'size':size}], 'shots':[{'id':i,'native':True,'elapsed':0,'duration':1000,'start':[0,0,45,200,0,400],'shotType':0,'metadata':{'player':0}}]}
                    release={'hero':0,'x':0,'y':0,'power':100,'shot':0,'wind':0,'windAngle':0,'baseline':[],'learner':{'target':[300,0],'elevation':45}}
                    learner.observe({'mobile':'ARMOR','shot':0},release,state)
                effect=learner.records['dragonbound:ARMOR:0']['weather_effects']['3'];self.assertEqual(effect,{'checked':3,'altered':0})
class RecoveryIntegrationTests(unittest.TestCase):
    def browser(self,shared,key):
        b=TrainingBrowser.__new__(TrainingBrowser);b.guard=Mock();b.sample=Mock(return_value={});b.seconds_left=Mock(return_value=20);b.orient=Mock();b.recovery_state=shared;b.recovery_key=key
        b.walk=Mock(return_value={'from':[100,100],'to':[114,100],'direction':'right'})
        r=Mock();r.read.return_value={'hero':0,'turn':0,'turnNumber':3,'players':[{'id':0,'x':100,'y':100}]}
        return b,r
    def test_reconnect_retains_budget_including_uncertain_walk(self):
        shared={};key=('room',0,3);b,r=self.browser(shared,key);learner=Mock();learner.plan.side_effect=NoAim('blocked',reposition=True)
        b.walk.side_effect=ConnectionError('lost while moving')
        with patch('training_movement.choose_reposition',return_value={'direction':'right'}):
            with self.assertRaises(ConnectionError):b.plan_with_reposition(r,learner,{},500,3,threading.Event())
            self.assertEqual(shared['steps'],1)
            reconnected,r=self.browser(shared,key)
            with self.assertRaises(NoAim):reconnected.plan_with_reposition(r,learner,{},500,3,threading.Event())
            self.assertEqual(reconnected.walk.call_count,1);self.assertEqual(shared['steps'],2)
    def test_slow_hypothetical_planning_does_not_spend_charge_reserve_walking(self):
        b,r=self.browser({},('room',0,3));b.seconds_left.side_effect=[9,4];learner=Mock();learner.plan.side_effect=NoAim('blocked',reposition=True)
        with patch('training_movement.choose_reposition',return_value={'direction':'right'}),self.assertRaisesRegex(NoAim,'tiempo restante'):
            b.plan_with_reposition(r,learner,{},500,3,threading.Event())
        b.walk.assert_not_called()
    def test_failed_mode_is_stamped_at_its_terminal_pose(self):
        from training_session import TrainingSession
        from training_controller import TrainingController
        with tempfile.TemporaryDirectory() as folder:
            session=TrainingSession('',None,Path(folder)/'book.json',Mock(),autonomous=True,objective='adaptive');session.cancel.wait=Mock(return_value=False)
            controller=TrainingController(session);controller.trial=Mock()
            controller.trial.done.return_value=False
            controller.trial.probe.side_effect=lambda mobile,state,available:{'mobile':mobile,'shot':min(available),'power':100,'angle':55}
            state={'status':'live','heroId':0,'activePlayer':0,'turnSerial':3,'wind':0,'windAngle':0,'players':[{'id':0,'mobile':0,'x':100,'y':100}],'shots':[]}
            browser=Mock();browser.movement_events=[];browser.guard.return_value={'game':True,'url':'https://dragonbound.net/#server-8/room-1','controls':{'btnShot1':True,'btnShot2':True}}
            browser.sample.side_effect=lambda:copy.deepcopy(state)
            def failed(*args,**kwargs):
                state['players'][0]['x']+=14;browser.movement_events.append({'from':[100,100],'to':[114,100]});raise NoAim('blocked')
            browser.shoot.side_effect=failed
            controller.cycle(browser);controller.cycle(browser)
            self.assertEqual([c.args[0]['shot'] for c in browser.shoot.call_args_list],[0,1]);self.assertFalse(controller.ledger.used)

class FinalRegressionTests(unittest.TestCase):
    def test_target_motion_during_planning_is_not_hidden_by_fresh_snapshot(self):
        fixture=NativeReadinessTests();browser=fixture.browser();reader=Mock();reader.read.return_value=fixture.state();release=fixture.release();release['learner']={'target':[380,100]}
        with self.assertRaisesRegex(TurnNotReady,'durante el cálculo'):browser.verify_release(reader,release,threading.Event())
        browser.key.assert_not_called()
    def test_failed_same_force_future_checks_discard_bad_context_candidate(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture=EvidenceDomainTests();trial=fixture.trial(Path(folder)/'report.json')
            trial.learner.records[trial.key]['samples']=[{'id':str(i),'episode':'game','simple':True,'power':100,'speed':200,'ax':40,'ay':400,'wind':10,'wind_angle':0,'heading':45,'duration_s':1} for i in range(2)]
            trial.context_candidate={'model':{'scale':3,'offset':0,'gravity':400,'wind_scale':4},'training_ids':{'old'}}
            trial.plan({'wind':10,'windAngle':0},{},{})
            self.assertIsNone(trial.frozen)
            self.assertNotEqual(trial.context_candidate['model']['scale'],3)
class DualCleanupIntegrationTests(unittest.TestCase):
    def test_unconfirmed_own_dd_is_cleared_without_reserving_or_firing(self):
        browser=TrainingBrowser.__new__(TrainingBrowser);browser.client=Mock();browser.client.endpoint='http://127.0.0.1:9223';browser.client.target={'id':'test'}
        reader=Mock();native={'hero':0,'turn':0,'turnNumber':3,'shot':0,'mode':'space','power':0,'wind':0,'windAngle':0,'players':[{'id':0,'x':100,'y':100,'rawAngle':50,'body':0,'look':1,'minAngle':10,'maxAngle':80},{'id':1,'x':400,'y':100}]};reader.read.return_value=native
        browser.guard=Mock(return_value={'controls':{'dual':{'x':1,'y':1}},'selectedItems':[],'dualSelected':True})
        browser.sample=Mock(return_value={'status':'live','heroId':0,'players':native['players'],'shots':[]})
        plan={'power':200,'raw_angle':50,'target':[400,100],'use_dual':True}
        browser.plan_with_reposition=Mock(return_value=(plan,None));browser.timed_plan=Mock(return_value=plan);browser.orient=Mock();browser.adjust_angle=Mock(return_value={});browser.key=Mock();browser.click=Mock()
        def unconfirmed(*args):browser.dual_selected_here=True;raise NoAim('item not confirmed',reason='item-unconfirmed')
        browser.select_dual=unconfirmed;reserve=Mock()
        with patch('training_browser.PowerReader',return_value=reader),self.assertRaises(NoAim):browser.shoot({'mobile':'ARMOR','shot':0,'angle':50,'power':200,'turn_serial':3},threading.Event(),autonomous=Mock(),before_fire=reserve)
        reserve.assert_not_called();browser.key.assert_not_called();browser.click.assert_called_once();reader.close.assert_called_once()
