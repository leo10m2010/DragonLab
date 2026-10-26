import tempfile,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from training_group import TrainingGroup
from training_session import TrainingSession
from training_browser import TrainingBrowser
from product_status import capture_status


class HealthTests(unittest.TestCase):
    def group(self,root):
        slots=[{'id':f'sesion-{i}','endpoint':f'http://127.0.0.1:{9222+i}','target':f'target-{i}','directory':root/f'worker-{i}'} for i in (1,2)]
        return TrainingGroup(root,slots,Mock())
    def test_partial_failure_is_visible_in_product_and_overview(self):
        with tempfile.TemporaryDirectory() as tmp:
            group=self.group(Path(tmp));group._started=True;group.sessions[0].last_error='failure';group.sessions[1].running=True
            state=group.overview();self.assertEqual(state['active_sessions'],1);self.assertEqual(state['expected_sessions'],2);self.assertEqual(state['health_status'],'partial')
            title,detail=capture_status(SimpleNamespace(training_session=group));self.assertEqual(title,'Entrenamiento parcial');self.assertIn('1 de 2',detail)
    def test_stale_worker_heartbeat_is_distinguished_from_running_peer(self):
        with tempfile.TemporaryDirectory() as tmp:
            group=self.group(Path(tmp))
            for worker in group.sessions:worker.running=True;worker.health=Mock(return_value={'heartbeat_age_seconds':0,'progress_age_seconds':20})
            group.sessions[0].health.return_value['heartbeat_age_seconds']=31
            state=group.overview();self.assertEqual(state['health_status'],'stalled');self.assertEqual(state['sessions'][0]['state'],'stalled')
            self.assertEqual(capture_status(SimpleNamespace(training_session=group))[0],'Revisar entrenamiento')
    def test_health_payload_only_contains_bounded_structural_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            group=self.group(Path(tmp));group.sessions[0].health=Mock(return_value={'phase':'private-player-name','credential':'secret','heartbeat_age_seconds':1,'progress_age_seconds':float('inf'),'input_recoveries':2})
            health=group.overview()['sessions'][0]['health'];self.assertEqual(health,{'heartbeat_age_seconds':1,'input_recoveries':2})
    def test_drag_disabled_period_uses_confirmed_space_before_any_press(self):
        b=TrainingBrowser.__new__(TrainingBrowser);b.input_recovery={'drag_disabled_until':500};b.client=Mock();b.click=Mock();b.confirm_setting=Mock();b.guard=Mock(return_value={'controls':{'slice_drag_button':{}}})
        reader=Mock();reader.read.return_value={'mode':'drag'}
        with patch('training_browser.time.monotonic',return_value=400),patch('training_browser.prepare_drag') as geometry:
            method,point=b.prepare_charge(reader,2,222,threading.Event())
        geometry.assert_not_called();self.assertEqual((method,point),('space',None));b.confirm_setting.assert_called_once()
    def test_drag_is_available_again_after_cooldown(self):
        b=TrainingBrowser.__new__(TrainingBrowser);b.input_recovery={'drag_disabled_until':500};b.client=Mock()
        reader=Mock();reader.read.return_value={'mode':'drag'}
        with patch('training_browser.time.monotonic',return_value=501),patch('training_browser.prepare_drag',return_value={'x':16}) as geometry:
            method,point=b.prepare_charge(reader,2,222,threading.Event())
        self.assertEqual(method,'drag');self.assertEqual(geometry.call_count,2)

if __name__=='__main__':unittest.main()
