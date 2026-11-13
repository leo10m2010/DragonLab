"""Functional launcher/control checks. No browser, game, login or network."""
import os,pathlib,tempfile,tkinter as tk,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch,call
from icons import ICON_NAMES,IconButton,draw_icon
from launcher import Launcher
from theme import BG,GREEN,PANEL

class IconContractTests(unittest.TestCase):
    def test_official_palette_and_every_icon_are_bundled_tabler_assets(self):
        import json
        from icons import ICON_DIRECTORY,icon_pixels
        self.assertEqual(BG,'#181916');self.assertEqual(GREEN,'#BAFF00')
        provenance=json.loads((ICON_DIRECTORY/'SOURCE.json').read_text())
        self.assertEqual(provenance['library'],'@tabler/icons-png')
        self.assertEqual(set(provenance['icons']),set(ICON_NAMES))
        for name in ICON_NAMES:
            pixels=icon_pixels(name,16,GREEN)
            self.assertEqual(pixels.size,(16,16));self.assertEqual(pixels.mode,'RGBA')
            self.assertIsNotNone(pixels.getchannel('A').getbbox())
        with self.assertRaises(ValueError):icon_pixels('missing',16,GREEN)

@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'requires desktop')
class CompactLauncherTests(unittest.TestCase):
    def setUp(self):
        self.argv=patch('launcher.sys.argv',['launcher.py','--check']);self.argv.start()
        self.root=tk.Tk();self.root.withdraw();self.app=Launcher(self.root,demo=True);self.app.enter_demo()
    def tearDown(self):
        if not self.app.closed:self.app.close()
        self.argv.stop()
    def show(self,width=680,height=600):
        self.root.geometry(f'{width}x{height}+30+30');self.root.deiconify();self.root.update();self.root.update_idletasks()
    def test_compact_geometry_retains_primary_control_footer_and_identity(self):
        self.show()
        self.assertEqual(self.app.hero_panel.color,PANEL);self.assertEqual(self.app.hero_panel.radius,12)
        self.assertEqual(self.app.headline.cget('text'),'Guía de tiro')
        self.assertEqual(self.app.play_button.cget('icon'),'play')
        self.assertLessEqual(self.app.play_button.winfo_height(),48)
        for button in (self.app.settings_button,self.app.help_button,self.app.performance_button,self.app.support_button,self.app.catalog_button):
            self.assertTrue(button.winfo_ismapped());self.assertIn(button.cget('icon'),ICON_NAMES)
        self.assertFalse(self.app.license_title.winfo_manager());self.assertFalse(self.app.license_detail.winfo_manager())
        self.assertEqual(self.app.mascot.cget('width'),'64')
    def test_custom_window_controls_invoke_real_window_actions(self):
        self.show()
        with patch.object(self.root,'iconify') as minimize:self.app.minimize_button.invoke();minimize.assert_called_once()
        with patch.object(self.root,'state',return_value='normal') as state:
            self.app.toggle_maximize();self.assertIn(call('zoomed'),state.call_args_list)
        with patch.object(self.root,'state',return_value='zoomed') as state:
            self.app.toggle_maximize();self.assertIn(call('normal'),state.call_args_list)
        for button,name in ((self.app.minimize_button,'minimize'),(self.app.maximize_button,'restore'),(self.app.close_button,'close')):
            self.assertEqual(button.cget('icon'),name)
    def test_footer_and_catalog_open_real_handlers(self):
        self.show();engine=SimpleNamespace(app=SimpleNamespace(),settings=Mock())
        with patch.object(self.app,'get_engine',return_value=engine),patch.object(self.app,'refresh_recommendations'),patch('catalog_ui.open_catalog') as catalog:
            self.app.settings_button.invoke();engine.settings.assert_called_once()
            self.app.catalog_button.invoke();catalog.assert_called_once_with(engine.app,game_id='dragonbound')
        with patch.object(self.app,'guide') as guide:self.app.help_button.invoke();guide.assert_called_once()
        with patch('performance_ui.open_performance') as performance:self.app.performance_button.invoke();performance.assert_called_once()
        with patch.object(self.app,'guide') as guide:self.app.support_button.invoke();guide.assert_called_once()
    def test_authentication_and_busy_state_disable_real_actions(self):
        self.show();self.app.busy=True;self.app.sync_controls()
        for button in (self.app.play_button,self.app.catalog_button,self.app.settings_button,self.app.game_choice):self.assertEqual(button.cget('state'),'disabled')
        self.assertEqual(self.app.help_button.cget('state'),'normal')
        self.app.busy=False;self.app.show_login();self.root.update()
        self.assertEqual(self.app.game_choice.cget('state'),'disabled');self.assertFalse(self.app.dashboard_page.winfo_manager())
    def test_icon_button_click_keyboard_and_disabled_states_share_the_same_handler(self):
        calls=[];button=IconButton(self.root,text='Ver',icon='catalog',command=lambda:calls.append(1));button.pack();self.show()
        button.press(SimpleNamespace(x=4,y=4));button.click(SimpleNamespace(x=4,y=4));button.key_activate()
        self.assertEqual(calls,[1,1]);button.configure(state='disabled');button.invoke();button.key_activate();self.assertEqual(calls,[1,1])
        button.configure(state='normal');button.press(SimpleNamespace(x=4,y=4));button.click(SimpleNamespace(x=-1,y=-1));self.assertEqual(calls,[1,1])
    def test_close_control_closes_the_application(self):
        self.show();self.app.close_button.invoke();self.assertTrue(self.app.closed)

if __name__=='__main__':unittest.main()
