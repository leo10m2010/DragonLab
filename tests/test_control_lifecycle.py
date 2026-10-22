import threading,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from control_lifecycle import cancel_actions,prepare_training,sync_control_mode
from product_status import capture_status

class LifecycleTests(unittest.TestCase):
    def app(self):
        return SimpleNamespace(endpoint=Mock(),last_live=0,training_session=None,pending_fire=('old','context'),fire_cancel=threading.Event(),fire_busy=False,compute_generation=7,result_context=('old',),result={'power':120},dirty=False,computing=True,hide_power_guide=Mock(),hide_overlay=Mock())
    def test_manual_charge_cannot_overlap_training_start(self):
        app=self.app();app.fire_busy=True
        with self.assertRaisesRegex(RuntimeError,'tiro solicitado'):prepare_training(app)
        self.assertEqual(app.compute_generation,7);self.assertFalse(app.fire_cancel.is_set())
    def test_training_start_discards_pending_manual_action_and_old_calculation(self):
        app=self.app();prepare_training(app)
        self.assertIsNone(app.pending_fire);self.assertTrue(app.fire_cancel.is_set());self.assertEqual(app.compute_generation,8)
        self.assertTrue(app.computing);self.assertIsNone(app.result_context);self.assertTrue(app.dirty)
    def test_stop_restores_guide_calculation_without_replaying_pending_shot(self):
        app=self.app();app.training_session=SimpleNamespace(running=True)
        self.assertTrue(sync_control_mode(app));self.assertFalse(sync_control_mode(app))
        app.result={'power':320};app.result_context=('training',);app.pending_fire=('queued',)
        app.training_session.running=False
        self.assertTrue(sync_control_mode(app));self.assertEqual(app.result,{});self.assertIsNone(app.pending_fire);self.assertTrue(app.dirty)
        self.assertEqual(app.compute_generation,9);self.assertEqual(app.hide_overlay.call_count,2)
    def test_escape_cancels_manual_and_autonomous_actions_together(self):
        app=self.app();app.training_session=Mock();cancel_actions(app)
        self.assertIsNone(app.pending_fire);self.assertTrue(app.fire_cancel.is_set());app.training_session.stop.assert_called_once()
    def test_stopping_is_distinct_from_active_training(self):
        app=self.app();app.training_session=SimpleNamespace(running=True,cancel=threading.Event(),status='Viejo',shots=2)
        app.training_session.cancel.set();self.assertEqual(capture_status(app)[0],'Deteniendo')
    def test_live_guide_status_returns_after_training_finishes(self):
        app=self.app();app.training_session=SimpleNamespace(running=False,status='Finalizado');app.worker=Mock();app.worker.is_alive.return_value=True
        app.last_live=0;app.last_error=None
        self.assertEqual(capture_status(app)[0],'Esperando partida')
    def test_start_rejects_a_running_manual_shot_before_creating_session(self):
        from training_ui import start_training
        app=self.app();app.clone_id='dragonbound';app.fire_busy=True
        with patch('training_session.TrainingSession') as session:
            with self.assertRaises(RuntimeError):start_training(app)
            session.assert_not_called()

    def test_invalid_session_options_preserve_existing_manual_guide(self):
        from training_ui import start_training
        app=self.app();app.clone_id='dragonbound';app.last_live=0;app.endpoint=Mock()
        with self.assertRaises(ValueError):start_training(app,limit='bad')
        self.assertEqual(app.result,{'power':120});self.assertEqual(app.compute_generation,7)

