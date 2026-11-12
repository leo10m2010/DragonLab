import tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from launcher import Launcher


class TrainingColdStartTests(unittest.TestCase):
    def app(self,folder):
        value=SimpleNamespace(closed=False,authenticated=True,training_mode=True,engine=SimpleNamespace(app=SimpleNamespace(book=SimpleNamespace(path=Path(folder)/'book.json'))),training_instances=2,status=Mock(),root=Mock())
        value.start_training=lambda:Launcher.start_training(value)
        return value
    def test_second_browser_opens_once_and_only_ready_sessions_start(self):
        with tempfile.TemporaryDirectory() as folder:
            app=self.app(folder)
            with patch('training_browsers.ready_slots',side_effect=[ValueError('not yet'),ValueError('loading'),[{},{}]]),patch('training_browsers.open_second_browser') as open_browser,patch('training_ui.open_training') as panel,patch('training_ui.start_training') as train:
                app.start_training();app.start_training()
                open_browser.assert_called_once_with(Path(folder));train.assert_not_called();panel.assert_not_called()
                self.assertEqual(app.root.after.call_count,2)
                app.start_training();train.assert_called_once_with(app.engine.app,instances=2)
                self.assertEqual(app.training_browser_attempts,0)
    def test_missing_sessions_have_bounded_retry_and_no_background_match_actions(self):
        with tempfile.TemporaryDirectory() as folder:
            app=self.app(folder);app.training_browser_attempts=30
            with patch('training_browsers.ready_slots',side_effect=ValueError('missing')),patch('training_browsers.open_second_browser') as open_browser,patch('training_ui.start_training') as train:
                app.start_training();open_browser.assert_not_called();train.assert_not_called();app.root.after.assert_not_called()
                self.assertIn('No se conectaron',app.status.config.call_args.kwargs['text'])
    def test_pending_retry_cannot_reopen_browsers_after_launcher_closes(self):
        with tempfile.TemporaryDirectory() as folder:
            app=self.app(folder);app.closed=True
            with patch('training_browsers.ready_slots') as ready,patch('training_ui.start_training') as train:
                app.start_training();ready.assert_not_called();train.assert_not_called()


if __name__=='__main__':unittest.main()
