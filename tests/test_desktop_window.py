"""Native desktop regressions. No browser, gameplay, credentials or network."""
import ctypes
import os
import pathlib
import sys
import tempfile
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from desktop_shell import native_window_style,place_in_work_area,style_window
from launcher import Launcher,CloudError
from mascot import DragonMascot,dragon_shapes
from rounded_controls import RoundedChoice,RoundedTable
from theme import PANEL

class WindowPolicyTests(unittest.TestCase):
    def test_monitor_bounds_keep_negative_coordinates(self):
        self.assertEqual(place_in_work_area(-1800,-900,600,480,(-1920,-1080,0,0)),(-1800,-900,600,480))
        x,y,width,height=place_in_work_area(100,100,600,480,(-1920,-1080,0,0))
        self.assertLess(x,0);self.assertLess(y,0);self.assertLessEqual(x+width,-8);self.assertLessEqual(y+height,-8)
    def test_dpi_fallback_precedes_first_tk_window(self):
        import launcher
        order=[];root=Mock()
        with patch('launcher.sys.argv',['launcher.py','--check']),patch('launcher.enable_high_dpi',side_effect=lambda:order.append('dpi')),patch('launcher.tk.Tk',side_effect=lambda:(order.append('tk') or root)),patch('launcher.Launcher'):
            launcher.main()
        self.assertEqual(order,['dpi','tk'])

@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'requires desktop')
class DesktopGeometryTests(unittest.TestCase):
    def setUp(self):
        self.argv=patch('launcher.sys.argv',['launcher.py','--check']);self.argv.start()
        self.root=tk.Tk();self.root.withdraw();self.app=Launcher(self.root,demo=True);self.app.enter_demo()
    def tearDown(self):
        if not self.app.closed:self.app.close()
        self.argv.stop()
    def show(self,width=720,height=750):
        self.root.geometry(f'{width}x{height}+50+50');self.root.deiconify();self.root.update();self.root.update_idletasks()
    def test_state_and_cosmetics_preserve_user_client_geometry(self):
        self.show(680,620);before=(self.root.winfo_width(),self.root.winfo_height())
        style_window(self.root);self.app.game.set('GunBound World')
        self.app.status.config(text='Estado detallado '*30);self.app.open_details();self.root.update()
        self.assertEqual(before,(self.root.winfo_width(),self.root.winfo_height()))
        self.assertEqual(self.app.hero_panel.color,PANEL)
        with patch.object(self.root,'geometry',wraps=self.root.geometry) as geometry:
            self.app.fit_window(1000,1000);self.app.show_login();self.app.enter_demo();self.root.update()
        geometry.assert_not_called()
    def test_minimum_window_scrolls_content_and_keeps_footer_accessible(self):
        self.show(600,480);self.app.open_details();self.root.update()
        self.assertEqual(self.root.minsize(),(600,480));self.assertEqual(tuple(map(bool,self.root.resizable())),(True,True))
        self.assertTrue(self.app.scrollbar.winfo_ismapped())
        for button in (self.app.settings_button,self.app.help_button,self.app.performance_button,self.app.support_button):
            self.assertTrue(button.winfo_ismapped())
            self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())
        self.root.geometry('900x1000');self.root.update()
        self.assertFalse(self.app.scrollbar.winfo_manager())
    @unittest.skipUnless(os.name=='nt','Windows window styles')
    def test_native_frame_sizing_minimize_maximize_restore(self):
        self.show(700,660);before=(self.root.winfo_width(),self.root.winfo_height())
        expected=0x00C00000|0x00040000|0x00020000|0x00010000|0x00080000
        previous=native_window_style(self.root);style_window(self.root)
        self.assertEqual(native_window_style(self.root),previous)
        self.assertEqual(previous&expected,expected)
        self.root.state('zoomed');self.root.update();self.assertEqual(self.root.state(),'zoomed')
        self.root.state('normal');self.root.update();self.assertEqual((self.root.winfo_width(),self.root.winfo_height()),before)
        self.root.iconify();self.root.update();self.assertEqual(self.root.state(),'iconic')
        self.root.deiconify();self.root.update();self.assertEqual((self.root.winfo_width(),self.root.winfo_height()),before)
    def test_launcher_has_no_manual_motion_geometry_handler(self):
        self.show()
        def visit(widget):
            self.assertFalse(widget.bind('<B1-Motion>') if not isinstance(widget,RoundedChoice) else '')
            for child in widget.winfo_children():
                if child is not self.app.scrollbar:visit(child)
        with patch.object(self.root,'geometry',wraps=self.root.geometry) as geometry:
            header=self.root.winfo_children()[0]
            for x in (20,100,200,400,100):header.event_generate('<B1-Motion>',x=x,y=12)
            self.root.update()
        geometry.assert_not_called();visit(self.root.winfo_children()[0])
    def test_busy_controls_match_handler_availability_and_help_stays_enabled(self):
        self.app.busy=True;self.app.sync_controls()
        for control in (self.app.play_button,self.app.settings_button,self.app.catalog_button,self.app.logout_button,self.app.game_choice):self.assertEqual(control.cget('state'),'disabled')
        self.assertEqual(self.app.help_button.cget('state'),'normal');self.assertEqual(self.app.performance_button.cget('state'),'normal')
        self.assertEqual(self.app.mascot.state_name,'loading')
    def test_details_expose_version_and_update_control(self):
        self.show();self.assertFalse(self.app.versions_panel.winfo_manager());self.app.account_button.invoke();self.root.update()
        self.assertTrue(self.app.versions_panel.winfo_ismapped());self.assertTrue(self.app.update_button.winfo_ismapped())
        self.assertIn('integrado',self.app.program_label.cget('text'));self.assertEqual(self.app.update_button.cget('state'),'disabled')
    def test_release_outage_uses_integrated_engine_after_access_check(self):
        with tempfile.TemporaryDirectory() as folder:
            account={'active':True};access=Mock(return_value=account)
            self.app.demo=False;self.app.client=SimpleNamespace(directory=pathlib.Path(folder),config={},account=account,session={},require_access=access)
            with patch('launcher.fetch_manifest',side_effect=CloudError('offline')),patch.object(self.app,'start_engine') as start,patch.object(self.app,'run',side_effect=lambda work,done:done(work())):
                self.app.play()
            access.assert_called_once();start.assert_called_once();self.assertIn('integrado',self.app.update_label.cget('text'))
            access.side_effect=CloudError('access denied')
            with patch('launcher.fetch_manifest') as manifest,patch.object(self.app,'start_engine') as start,patch.object(self.app,'run',side_effect=lambda work,done:done(work())):
                with self.assertRaises(CloudError):self.app.play()
            manifest.assert_not_called();start.assert_not_called()
    def test_performance_does_not_construct_an_engine(self):
        module=SimpleNamespace(open_performance=Mock())
        with patch.dict(sys.modules,{'performance_ui':module}),patch('launcher.EngineHost') as engine:
            self.app.open_performance()
        engine.assert_not_called();module.open_performance.assert_called_once()
        self.assertIsNone(module.open_performance.call_args.kwargs['app_provider']())
    def test_popup_releases_grab_when_owner_moves(self):
        self.show();choice=self.app.game_choice;choice.open();self.root.update()
        self.assertIsNotNone(choice.popup);self.root.geometry('+80+80');self.root.update()
        self.assertIsNone(choice.popup);self.assertIsNone(self.root.grab_current())
    def test_mascot_has_cached_geometry_and_no_animation_timer(self):
        self.show();before=self.root.tk.call('after','info')
        for state in DragonMascot.STATES:
            self.app.mascot.set_state(state);self.app.mascot.draw()
            self.assertTrue(self.app.mascot.find_all())
        self.assertEqual(before,self.root.tk.call('after','info'))
        self.assertIs(dragon_shapes(92,84,'active'),dragon_shapes(92,84,'active'))
    def test_table_columns_and_keyboard_keep_all_rows(self):
        table=RoundedTable(self.root,columns=('name','status'));table.column('name',width=140,stretch=False);table.column('status',width=300,stretch=True)
        for index in range(40):table.insert('','end',iid=str(index),values=('Vehicle '+str(index),'Pending '+str(index)))
        self.assertEqual(table.column('name','width'),140);self.assertEqual(len(table.get_children()),40)
        table.choose('39');self.assertEqual(table.selection(),('39',));table.item('39',values=('Vehicle 39','Ready'));self.assertIn('Ready',table.rows['39'].cget('text'))
        table.destroy()

if __name__=='__main__':unittest.main()
