import json,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from training_session import TrainingSession
from training_controller import TrainingController


def view():return {'url':'https://dragonbound.net/#server-8/room-1','game':True,'controls':{'btnShot1':True},'options':[]}
def scene():return {'status':'live','heroId':0,'activePlayer':1,'turnSerial':3,'wind':0,'windAngle':0,'weather':[],'players':[{'id':0,'x':100,'y':100,'mobile':0,'team':0,'hp':800,'shield':0},{'id':1,'x':300,'y':100,'mobile':0,'team':1,'hp':800,'shield':0}],'shots':[]}


class OpponentIntegrationTests(unittest.TestCase):
    def make(self,folder):
        session=TrainingSession('',None,Path(folder)/'book.json',Mock(),continuous=True,autonomous=True)
        session.cancel.wait=Mock(return_value=False);controller=TrainingController(session);browser=Mock();browser.guard.return_value=view();browser.sample.return_value=scene()
        return session,controller,browser
    def test_enemy_turn_is_sampled_before_own_turn_early_return(self):
        with tempfile.TemporaryDirectory() as folder:
            session,controller,browser=self.make(folder);observer=Mock();observer.summary.return_value={'opponent_turns':1};controller.opponents=observer
            controller.cycle(browser)
            observer.observe.assert_called_once_with(browser.sample.return_value,controller.learner.episode);browser.shoot.assert_not_called()
    def test_enemy_shots_never_seed_own_physical_models(self):
        with tempfile.TemporaryDirectory() as folder:
            session,controller,browser=self.make(folder);controller.cycle(browser)
            state=scene();state['shots']=[{'id':1,'native':True,'elapsed':0,'duration':1000,'start':[300,100,135,250,0,400],'shotType':0,'metadata':{'player':1,'mobile':0,'launchSpeed':250}}];browser.sample.return_value=state
            controller.cycle(browser)
            self.assertEqual(controller.opponents.summary()['opponent_shots'],1);self.assertFalse(controller.learner.records);browser.shoot.assert_not_called()
    def test_optional_observer_failure_does_not_interrupt_control(self):
        with tempfile.TemporaryDirectory() as folder:
            session,controller,browser=self.make(folder);controller.opponents=Mock();controller.opponents.observe.side_effect=ValueError('bad optional case')
            controller.cycle(browser);controller.cycle(browser)
            self.assertTrue(controller.opponents_disabled);self.assertTrue(session.opponent_error);self.assertIsNone(browser.opponent_observer);self.assertFalse(session.last_error)
            self.assertEqual(controller.opponents.observe.call_count,1)
    def test_reconnect_preserves_same_passive_observer_and_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            session,controller,first=self.make(folder);second=Mock();observer=controller.opponents;calls=[]
            def cycle(browser):
                calls.append(browser)
                if len(calls)==1:raise ConnectionError('transport')
                return False
            controller.cycle=cycle
            with patch('training_controller.TrainingBrowser',side_effect=[first,second]),patch('training_power.SleepLease'):controller.run()
            self.assertIs(first.opponent_observer,observer);self.assertIs(second.opponent_observer,observer)
    def test_lobby_finalizes_passive_window_without_inventing_a_result(self):
        with tempfile.TemporaryDirectory() as folder:
            session,controller,browser=self.make(folder);controller.in_game=True;controller.opponents=Mock();controller.opponents.summary.return_value={'opponent_shots':2}
            browser.guard.return_value={**view(),'game':False,'controls':{'buttonStart1v1':True}}
            controller.cycle(browser);controller.opponents.end.assert_called_once();self.assertEqual(session.opponent_progress,{'opponent_shots':2})
    def test_status_publishes_separate_opponent_progress(self):
        with tempfile.TemporaryDirectory() as folder:
            session=TrainingSession('',None,Path(folder)/'book.json',Mock());session.opponent_progress={'opponent_turns':3,'opponent_shots':2};session.publish('Observando')
            data=json.loads((Path(folder)/'entrenamiento-estado.json').read_text());self.assertEqual(data['opponents']['opponent_shots'],2);self.assertFalse(data['opponents']['observer_error']);self.assertEqual(data['shots'],0)

if __name__=='__main__':unittest.main()
