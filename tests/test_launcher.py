import pathlib,sys,tempfile,json,unittest,os
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from launcher import installed_version,calibration_revision,fetch_manifest,CloudError,ConsentSwitch,Launcher,LauncherButton,BG
from app_version import LAUNCHER_VERSION

def destroy_root(root):
    for job in root.tk.splitlist(root.tk.call('after','info')):root.after_cancel(job)
    root.update_idletasks();root.destroy()

class VersionTests(unittest.TestCase):
    def test_program_version_requires_installation_not_just_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);(root/'installed-release.json').write_text(json.dumps({'version':'0.12.7'}))
            self.assertIsNone(installed_version(root));(root/'DragonLab-Cloud-0.12.7.exe').write_bytes(b'fixture')
            self.assertEqual(installed_version(root),'0.12.7')
    def test_revision_is_stable_and_empty_is_not_a_published_version(self):
        with tempfile.TemporaryDirectory() as d:
            path=pathlib.Path(d)/'profiles.json';self.assertEqual(calibration_revision(path),'Sin sincronizar')
            path.write_text('[]');self.assertEqual(calibration_revision(path),'Sin sincronizar')
            path.write_text('[{"a":1,"b":2}]');a=calibration_revision(path)
            path.write_text('[{"b":2,"a":1}]');self.assertEqual(calibration_revision(path),a)
    def test_update_manifest_cannot_point_outside_authorized_release(self):
        class Response:
            def __init__(self,value):self.raw=json.dumps(value).encode()
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self):return self.raw
        release={'assets':[{'name':'dragonlab-release.json','browser_download_url':'https://github.com/leo10m2010/DragonLab/releases/download/cloud-v0.13.0/dragonlab-release.json'}]}
        manifest={'schema':1,'asset':'DragonLab-Cloud.exe','version':'0.13.0','sha256':'a'*64,'url':'https://evil.example/DragonLab.exe'}
        with patch('launcher.urllib.request.urlopen',side_effect=[Response(release),Response(manifest)]):
            with self.assertRaises(CloudError):fetch_manifest()

@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'requires desktop')
class LauncherUITests(unittest.TestCase):
    def test_production_build_does_not_allow_demo_flag_to_skip_login(self):
        import tkinter as tk
        root=tk.Tk();root.withdraw()
        try:
            with patch('launcher.DEMO_ALLOWED',False),patch('launcher.CloudClient',side_effect=CloudError('No configuration')),patch('launcher.EngineHost') as engine:
                app=Launcher(root,demo=True);app.enter_demo();app.play()
                self.assertFalse(app.demo);self.assertFalse(app.authenticated);engine.assert_not_called()
        finally:destroy_root(root)
    def test_older_cloud_release_cannot_reopen_legacy_companion_or_downgrade(self):
        import tkinter as tk
        from types import SimpleNamespace
        root=tk.Tk();root.withdraw()
        with tempfile.TemporaryDirectory() as d:
            account={'active':True};client=SimpleNamespace(session=None,account=account,directory=pathlib.Path(d),config={'githubRepo':'leo10m2010/DragonLab'},require_access=lambda:account)
            try:
                with patch('launcher.CloudClient',return_value=client),patch('launcher.EngineHost') as engine,patch('launcher.fetch_manifest',return_value={'version':'0.12.11'}),patch('launcher.subprocess.Popen') as process:
                    app=Launcher(root);app.show_account(account)
                    with patch.object(app,'run',side_effect=lambda work,done:app.finish(work(),None,done)):app.play()
                    engine.assert_called_once();engine.return_value.start.assert_called_once_with('dragonbound');process.assert_not_called()
            finally:destroy_root(root)
    def test_demo_automatic_access_runs_one_embedded_engine_and_logout_stops_it(self):
        import tkinter as tk
        root=tk.Tk();root.withdraw()
        try:
            with patch('launcher.CloudClient') as cloud,patch('launcher.fetch_manifest') as manifest,patch('launcher.EngineHost') as engine:
                engine.return_value.start.return_value=True
                app=Launcher(root,demo=True);app.enter_demo()
                self.assertTrue(app.authenticated);self.assertIsNone(app.client)
                with patch('launcher.subprocess.Popen') as process:
                    app.play();app.play();engine.assert_called_once();engine.return_value.start.assert_called_once_with('dragonbound');process.assert_not_called()
                    self.assertNotEqual(root.state(),'normal') # Test root stays withdrawn; play never creates/shows another panel.
                    app.logout();engine.return_value.stop.assert_called_once();app.play();engine.assert_called_once()
                app.check_update();app.change_consent();cloud.assert_not_called();manifest.assert_not_called()
        finally:destroy_root(root)
    def test_failed_engine_can_retry_and_game_switch_stops_previous_capture(self):
        import tkinter as tk
        root=tk.Tk();root.withdraw()
        try:
            with patch('launcher.EngineHost') as host:
                app=Launcher(root,demo=True);app.enter_demo()
                host.side_effect=OSError('fixture');app.play();self.assertIsNone(app.engine)
                self.assertIn('No se pudo',app.status.cget('text'))
                host.side_effect=None;host.return_value.start.return_value=True;host.return_value.app.clone_id='dragonbound'
                app.play();self.assertIsNotNone(app.engine)
                app.game.set('GunBound World');host.return_value.stop.assert_called_once();self.assertIsNone(app.engine)
                app.play();host.return_value.start.assert_called_with('gunbound-world')
                self.assertIn('Q desactivado',app.game_note.cget('text'))
        finally:destroy_root(root)
    def test_help_opens_only_one_dialog_and_keeps_instructions_in_same_design(self):
        import tkinter as tk
        root=tk.Tk();root.withdraw()
        try:
            app=Launcher(root,demo=True);root.deiconify();root.update_idletasks();app.help();first=app.dialog
            app.help();self.assertIs(app.dialog,first)
            self.assertTrue(first.winfo_exists());self.assertEqual(first.cget('bg'),BG)
            first.update();first.update_idletasks();confirm=first.winfo_children()[-1]
            self.assertLessEqual(confirm.winfo_y()+confirm.winfo_height(),first.winfo_height())
            card=first.winfo_children()[1];self.assertGreaterEqual(card.winfo_height(),card.body.winfo_reqheight())
            app.close();self.assertTrue(app.closed)
        finally:
            if not app.closed:destroy_root(root)
    @unittest.skipUnless(os.name=='nt','Windows chrome')
    def test_custom_chrome_removes_native_white_caption(self):
        import tkinter as tk,ctypes
        from ctypes import wintypes as w
        from desktop_shell import style_window
        root=tk.Tk();root.withdraw()
        try:
            root.update_idletasks();style_window(root)
            u=ctypes.WinDLL('user32');u.GetAncestor.argtypes=[w.HWND,w.UINT];u.GetAncestor.restype=w.HWND
            u.GetWindowLongPtrW.argtypes=[w.HWND,ctypes.c_int];u.GetWindowLongPtrW.restype=ctypes.c_ssize_t
            self.assertEqual(u.GetWindowLongPtrW(u.GetAncestor(root.winfo_id(),2),-16)&0x00C00000,0)
        finally:destroy_root(root)
    def test_disabled_button_has_legible_separate_colors_and_no_hover_action(self):
        import tkinter as tk
        root=tk.Tk();root.withdraw();calls=[]
        try:
            button=LauncherButton(root,text='Entrar',bg='#54d7ee',fg=BG,state='disabled',command=lambda:calls.append(1))
            button.set_hover(True);button.invoke();self.assertEqual(calls,[])
            polygon=button.find_all()[0];label=button.find_all()[-1]
            self.assertEqual(button.itemcget(polygon,'fill'),'#26384c')
            self.assertEqual(button.itemcget(label,'fill'),'#a8b9cf')
        finally:destroy_root(root)
    def test_missing_server_disables_login_and_sharing_but_shows_version(self):
        import tkinter as tk
        root=tk.Tk();root.withdraw()
        try:
            with patch('launcher.CloudClient',side_effect=CloudError('Not configured')):app=Launcher(root)
            root.update_idletasks();self.assertEqual(app.login_button.cget('state'),'disabled');self.assertFalse(app.consent.enabled)
            app.consent.toggle();self.assertFalse(app.share.get());self.assertIn(LAUNCHER_VERSION,root.title())
        finally:destroy_root(root)
    def test_login_dashboard_and_logout_are_separate_pages(self):
        import tkinter as tk
        from types import SimpleNamespace
        root=tk.Tk();root.withdraw()
        with tempfile.TemporaryDirectory() as d:
            client=SimpleNamespace(directory=pathlib.Path(d),session=None,account=None)
            try:
                with patch('launcher.CloudClient',return_value=client):app=Launcher(root)
                self.assertEqual(app.login_page.winfo_manager(),'pack');self.assertEqual(app.dashboard_page.winfo_manager(),'')
                app.finish(None,'Credenciales inválidas',app.show_account)
                self.assertFalse(app.authenticated);self.assertEqual(app.dashboard_page.winfo_manager(),'')
                account={'active':True,'remaining_seconds':86400,'share_measurements':False}
                client.session={'user':{'email':'example@example.com'}};client.account=account
                app.finish(account,None,app.show_account)
                self.assertEqual(app.login_page.winfo_manager(),'');self.assertEqual(app.dashboard_page.winfo_manager(),'pack')
                self.assertEqual(app.play_button.cget('state'),'normal')
                account['active']=False;app.finish(account,None,app.show_account)
                self.assertEqual(app.play_button.cget('state'),'disabled')
                def logout():client.session=None
                client.logout=logout
                with patch.object(app,'run',side_effect=lambda work,done:app.finish(work(),None,done)):app.logout()
                self.assertFalse(app.authenticated);self.assertIsNone(client.account)
                self.assertEqual(app.login_page.winfo_manager(),'pack');self.assertEqual(app.dashboard_page.winfo_manager(),'')
                self.assertEqual(app.update_button.cget('state'),'disabled')
            finally:destroy_root(root)
    def test_saved_session_waits_for_verification_and_failed_logout_hides_panel(self):
        import tkinter as tk
        from types import SimpleNamespace
        root=tk.Tk();root.withdraw()
        with tempfile.TemporaryDirectory() as d:
            client=SimpleNamespace(directory=pathlib.Path(d),session={'user':{}},account={'active':True},require_access=lambda:None)
            try:
                with patch('launcher.CloudClient',return_value=client),patch.object(Launcher,'run') as work,patch('launcher.sys.argv',['launcher.py']):app=Launcher(root)
                work.assert_called_once();self.assertFalse(app.authenticated);self.assertEqual(app.dashboard_page.winfo_manager(),'')
                app.show_account(client.account);client.session=None
                app.finish(None,'Servidor no disponible',lambda value:None)
                self.assertFalse(app.authenticated);self.assertEqual(app.dashboard_page.winfo_manager(),'')
                self.assertEqual(app.play_button.cget('state'),'disabled')
            finally:destroy_root(root)
    def test_consent_switch_calls_handler_once_and_respects_busy_state(self):
        import tkinter as tk
        root=tk.Tk();root.withdraw();calls=[]
        try:
            value=tk.BooleanVar(root);switch=ConsentSwitch(root,variable=value,command=lambda:calls.append(value.get()),state='disabled')
            switch.toggle();self.assertEqual(calls,[])
            switch.config(state='normal');switch.toggle();self.assertEqual(calls,[True])
            switch.config(state='disabled');switch.toggle();self.assertEqual(calls,[True])
        finally:destroy_root(root)
