import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from training_session import TrainingSession


class DurationTests(unittest.TestCase):
    def test_24h_allowed_but_longer_sessions_rejected_before_start(self):
        session=TrainingSession('',None,'book.json',Mock(),continuous=True,objective='adaptive',max_seconds=86400)
        self.assertEqual(session.time_remaining(),86400)
        self.assertFalse(session.running)
        with self.assertRaises(ValueError):TrainingSession('',None,'book.json',Mock(),max_seconds=86401)

    def test_remaining_time_uses_monotonic_clock_and_clamps_at_zero(self):
        session=TrainingSession('',None,'book.json',Mock(),max_seconds=60)
        session.started_at=100
        with patch('training_session.time.monotonic',return_value=145):self.assertEqual(session.time_remaining(),15)
        with patch('training_session.time.monotonic',return_value=190):self.assertEqual(session.time_remaining(),0)

    def test_live_status_reports_deadline_and_separates_block_and_total(self):
        with tempfile.TemporaryDirectory() as folder:
            session=TrainingSession('',None,Path(folder)/'book.json',Mock(),continuous=True,objective='adaptive',max_seconds=86400)
            session.started_at=100;session.started_wall=2000;session.shots=43
            session.report={'block':2,'completed_blocks':1}
            with patch('training_session.time.monotonic',return_value=3700):session.publish('Entrenando')
            status=json.loads((Path(folder)/'entrenamiento-estado.json').read_text())
            self.assertEqual(status['remaining_seconds'],82800)
            self.assertEqual(status['expires_at'],88400)
            self.assertIsNone(status['limit_shots'])
            self.assertEqual(status['report']['completed_blocks'],1)
            self.assertEqual(status['shots'],43)

    def test_finite_test_remains_available_without_continuous_rollover(self):
        from training_ui import start_training
        import threading
        app=SimpleNamespace(fire_cancel=threading.Event(),clone_id='dragonbound',training_session=None,last_live=0,endpoint=Mock(),browser_target=None,book=SimpleNamespace(path=Path('book.json'),records={}),events=Mock())
        with patch('training_session.TrainingSession') as factory:start_training(app,limit='20')
        options=factory.call_args.kwargs
        self.assertFalse(options['continuous']);self.assertEqual(options['max_shots'],20)
        self.assertEqual(options['max_seconds'],900)

    def test_single_evaluation_cannot_silently_become_a_24h_session(self):
        from training_ui import start_training
        app=SimpleNamespace(clone_id='dragonbound',training_session=None,last_live=0,endpoint=Mock(),browser_target=None)
        with patch('control_lifecycle.prepare_training') as prepare:
            with self.assertRaises(ValueError):start_training(app,objective='evaluation')
        prepare.assert_not_called()

    def test_panel_distinguishes_current_block_from_session_total(self):
        from training_ui import session_caption
        session=SimpleNamespace(continuous=True,time_remaining=lambda:3700,report={'block':3},shots=83)
        text=session_caption(session)
        self.assertIn('01:01',text);self.assertIn('Bloque 3',text);self.assertIn('83 tiros en total',text)
        session.continuous=False;self.assertEqual(session_caption(session),'')
    def test_requested_stop_is_preserved_in_saved_status(self):
        with tempfile.TemporaryDirectory() as folder:
            session=TrainingSession('',None,Path(folder)/'book.json',Mock())
            session.stop();session.publish('Detenido')
            status=json.loads((Path(folder)/'entrenamiento-estado.json').read_text())
            self.assertEqual(status['stop_reason'],'requested');self.assertTrue(session.cancel.is_set())
