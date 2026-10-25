import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from training_browsers import browser_slots,game_target,open_second_browser


class BrowserProfileTests(unittest.TestCase):
    def test_slot_paths_are_absolute_and_cannot_share_browser_or_measurements(self):
        slots=browser_slots(Path('relative data'))
        self.assertNotEqual(slots[0]['endpoint'],slots[1]['endpoint'])
        self.assertNotEqual(slots[0]['directory'],slots[1]['directory'])
        self.assertTrue(all(s['directory'].is_absolute() for s in slots))

    def test_new_browser_gets_an_absolute_profile_even_with_relative_base(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('training_browsers.get_json',side_effect=OSError('closed')),patch('training_browsers.Path.is_file',return_value=True),patch('training_browsers.subprocess.Popen') as launch:
                relative=Path(os.path.relpath(Path(folder)/'data',Path.cwd()))
                self.assertFalse(relative.is_absolute());open_second_browser(relative)
            args=launch.call_args.args[0]
            directory=Path(next(a.split('=',1)[1] for a in args if a.startswith('--user-data-dir=')))
            self.assertTrue(directory.is_absolute());self.assertTrue(directory.is_relative_to(Path(folder)))
            self.assertIn('--remote-debugging-port=9224',args)
            self.assertEqual(list(directory.iterdir()),[])

    def test_reopening_second_window_does_not_add_more_game_tabs(self):
        with tempfile.TemporaryDirectory() as folder:
            tabs=[{'type':'page','id':'one','url':'https://dragonbound.net/'},{'type':'page','id':'two','url':'https://dragonbound.net/#server-8'}]
            with patch('training_browsers.get_json',return_value=tabs),patch('training_browsers.get_bytes') as activate,patch('training_browsers.subprocess.Popen') as launch:
                open_second_browser(folder)
            launch.assert_not_called();activate.assert_called_once()

    def test_training_target_is_unambiguous_and_ignores_other_sites(self):
        tabs=[{'type':'page','id':'other','url':'https://example.com/'},{'type':'page','id':'game','url':'https://dragonbound.net/#server-8'}]
        with patch('training_browsers.get_json',return_value=tabs):self.assertEqual(game_target('endpoint')['target'],'game')
        tabs.append({'type':'page','id':'second','url':'https://dragonbound.net/'})
        with patch('training_browsers.get_json',return_value=tabs),self.assertRaises(ValueError):game_target('endpoint')

    def test_profile_write_failure_stops_before_starting_chrome(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('training_browsers.get_json',side_effect=OSError('closed')),patch('training_browsers.Path.is_file',return_value=True),patch('training_browsers.Path.write_bytes',side_effect=PermissionError('read only')),patch('training_browsers.subprocess.Popen') as launch:
                with self.assertRaises(ValueError):open_second_browser(folder)
            launch.assert_not_called()
