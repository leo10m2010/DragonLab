import json,tempfile,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from calibration_book import CalibrationBook
from training_ui import start_training


class DualIntegrationTests(unittest.TestCase):
    def app(self,path):
        return SimpleNamespace(fire_cancel=threading.Event(),clone_id='dragonbound',training_session=None,last_live=0,endpoint=Mock(),browser_target=None,book=SimpleNamespace(path=path,records={}),events=Mock())

    def test_two_workers_use_explicit_endpoints_and_background_control(self):
        with tempfile.TemporaryDirectory() as folder:
            app=self.app(Path(folder)/'book.json');slots=[{'id':'sesion-1'},{'id':'sesion-2'}]
            with patch('training_browsers.ready_slots',return_value=slots),patch('training_group.TrainingGroup') as factory:
                result=start_training(app,instances=2)
            self.assertIs(result,factory.return_value);self.assertIs(app.training_session,result)
            self.assertEqual(factory.call_args.args[1],slots);result.start.assert_called_once()
            self.assertEqual(factory.call_args.kwargs['max_seconds'],86400)

    def test_two_workers_cannot_silently_start_foreground_or_invalid_count(self):
        app=self.app(Path('book.json'))
        for options in ({'instances':2,'background':False},{'instances':8}):
            with patch('control_lifecycle.prepare_training') as prepare,self.assertRaises(ValueError):start_training(app,**options)
            prepare.assert_not_called()

    def test_identical_native_ids_from_two_sessions_keep_distinct_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            book=CalibrationBook(Path(folder)/'book.json')
            state={'status':'live','heroId':0,'activePlayer':0,'selectedShot':0,'currentPower':100,'wind':0,'windAngle':0,'players':[{'id':0,'mobile':0,'x':0,'y':0},{'id':1,'x':500,'y':0}], 'shots':[{'id':7,'native':True,'elapsed':0,'duration':1000,'start':[0,0,45,200,0,400],'shotType':0,'metadata':{'player':0,'power':100}}]}
            release={'hero':0,'x':0,'y':0,'shot':0,'power':100,'wind':0,'windAngle':0,'baseline':[]}
            for scope in ('run:sesion-1','run:sesion-2'):book.observe_training(state,{**release,'measurement_session':scope})
            samples=book.records['dragonbound:ARMOR:0']['samples']
            self.assertEqual(len(samples),2);self.assertNotEqual(samples[0]['sample_id'],samples[1]['sample_id'])
            self.assertNotEqual(samples[0]['measurement_session'],samples[1]['measurement_session'])
            book.observe_training(state,{**release,'measurement_session':'run:sesion-2'})
            self.assertEqual(len(book.records['dragonbound:ARMOR:0']['samples']),2)

    def test_primary_game_escape_does_not_cancel_the_other_worker(self):
        from control_lifecycle import cancel_from_game,cancel_actions
        app=self.app(Path('book.json'));app.pending_fire=('stale',)
        app.training_session=SimpleNamespace(sessions=[Mock(),Mock()],running=True,stop=Mock())
        cancel_from_game(app)
        self.assertIsNone(app.pending_fire);self.assertTrue(app.fire_cancel.is_set())
        app.training_session.stop.assert_not_called()
        cancel_actions(app);app.training_session.stop.assert_called_once()
