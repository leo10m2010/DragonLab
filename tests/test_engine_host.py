import unittest,os,tempfile,pathlib,tkinter as tk
from unittest.mock import patch,MagicMock
from engine_host import EngineHost,EngineWindow
from game_catalog import GAMES

@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'requires desktop')
class EmbeddedTests(unittest.TestCase):
    def cleanup(self,root):
        root.update_idletasks()
        for job in root.tk.splitlist(root.tk.call('after','info')):root.after_cancel(job)
        root.destroy()
    def test_actual_engine_builds_invisible_and_never_starts_capture_before_play(self):
        root=tk.Tk();root.withdraw()
        try:
            with tempfile.TemporaryDirectory() as d,patch('app.BASE',pathlib.Path(d)),patch('app.App.start_target_shortcut'),patch('app.App.toggle_live') as live:
                host=EngineHost(root,pathlib.Path(d));root.update_idletasks()
                self.assertEqual(host.window.state(),'withdrawn');self.assertFalse(host.window.winfo_ismapped())
                live.assert_not_called();host.stop();self.assertFalse(host.window.winfo_exists())
        finally:self.cleanup(root)
    def test_engine_has_no_visible_main_panel_and_owns_only_its_callbacks(self):
        root=tk.Tk();root.withdraw();calls=[]
        parent_job=root.after(60000,lambda:calls.append('parent'))
        try:
            with tempfile.TemporaryDirectory() as d,patch('app.App') as app:
                app.return_value.open_game_browser.return_value=True
                host=EngineHost(root,pathlib.Path(d))
                self.assertEqual(host.window.state(),'withdrawn')
                app.assert_called_once_with(host.window,embedded=True)
                self.assertIs(host.app.ui_parent,root)
                self.assertTrue(host.start('gunbound-world'));self.assertEqual(host.app.clone_id,'gunbound-world')
                host.window.after(60000,lambda:calls.append('engine'))
                # The mocked app.close does not destroy its test window; destroy it here to verify timer isolation.
                host.window.destroy()
                pending=root.tk.splitlist(root.tk.call('after','info'));self.assertIn(parent_job,pending)
                self.assertFalse(host.window.jobs)
        finally:self.cleanup(root)
    def test_browser_uses_the_selected_game_url(self):
        from app import App
        root=tk.Tk();root.withdraw()
        try:
            fake=MagicMock();fake.root=root;fake.ui_parent=root;fake.clone_id='gunbound-world'
            with patch('pathlib.Path.is_file',return_value=True),patch('game_startup.activate_existing_game',return_value=False),patch('subprocess.Popen') as launch:
                self.assertTrue(App.open_game_browser(fake))
                self.assertEqual(launch.call_args.args[0][-1],GAMES['GunBound World']['url'])
        finally:self.cleanup(root)
