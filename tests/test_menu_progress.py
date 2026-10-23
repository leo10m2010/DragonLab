import unittest,tkinter as tk
from types import SimpleNamespace
from unittest.mock import Mock
from rounded_widgets import RoundedButton
from rounded_controls import RoundedChoice,RoundedSwitch
from training_progress import coverage_report

class CoverageTests(unittest.TestCase):
    def test_percent_is_fixed_catalog_coverage_not_attempt_count(self):
        records={'dragonbound:ARMOR:0':{'model':{}},'dragonbound:ICE:0':{'model':{'scale':2}},'gunbound-world:ICE:0':{'model':{'scale':2}}}
        report=coverage_report(records)
        self.assertEqual(report['launch_modes_total'],51);self.assertEqual(report['launch_modes_validated'],1)
        self.assertAlmostEqual(report['launch_coverage_percent'],2.0)
        self.assertIsNone(report['autonomy_percent']);self.assertIsNone(report['aim_accuracy_percent'])
    def test_failed_models_and_candidates_never_count_as_validated(self):
        r={'dragonbound:ARMOR:0':{'model':{'scale':2},'drift':True},'dragonbound:ICE:0':{'candidate':{'validation':[{},{}]}}}
        report=coverage_report(r);self.assertEqual(report['launch_coverage_percent'],0)
        mode=next(m for m in report['modes'] if m['mobile']=='ICE' and m['shot']==0)
        self.assertEqual(mode['check_percent'],67);self.assertEqual(mode['checks'],2)
    def test_lab_has_its_own_coverage_and_drift_does_not_inflate_it(self):
        lab={'dragonbound:ARMOR:0':{'fit':{'power_scale':2}},'dragonbound:ARMOR:1':{'fit':{'power_scale':2},'drift_pending':[{}]}}
        report=coverage_report({},lab);self.assertEqual(report['lab_modes_validated'],1);self.assertEqual(report['launch_modes_validated'],0)
    def test_special_patterns_are_visible_even_when_initial_launch_is_validated(self):
        report=coverage_report({'dragonbound:TRICO:1':{'model':{'scale':2},'multi_projectile':True}})
        mode=next(m for m in report['modes'] if m['mobile']=='TRICO' and m['shot']==1)
        self.assertTrue(mode['special_pending']);self.assertTrue(mode['validated'])

class MenuControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=tk.Tk();cls.root.withdraw()
    @classmethod
    def tearDownClass(cls):cls.root.destroy()
    def test_release_without_press_never_activates_a_button(self):
        command=Mock();button=RoundedButton(self.root,text='Guardar',command=command)
        button.click(SimpleNamespace(x=0,y=0));command.assert_not_called();button.destroy()
    def test_click_releases_once_and_disabled_button_rejects_pending_press(self):
        command=Mock();button=RoundedButton(self.root,text='Guardar',command=command)
        event=SimpleNamespace(x=0,y=0);button.press(event);button.click(event);button.click(event)
        self.assertEqual(command.call_count,1)
        button.press(event);button.config(state='disabled');button.click(event)
        self.assertEqual(command.call_count,1);button.destroy()
    def test_key_activation_stops_event_propagation_and_honors_disabled_state(self):
        command=Mock();button=RoundedButton(self.root,command=command)
        self.assertEqual(button.key_activate(),'break');self.assertEqual(command.call_count,1)
        button.config(state='disabled');button.key_activate();self.assertEqual(command.call_count,1);button.destroy()
    def test_disabling_choice_closes_popup_without_changing_value(self):
        value=tk.StringVar(self.root,value='A');choice=RoundedChoice(self.root,textvariable=value,values=['A','B']);popup=Mock();choice.popup=popup;choice.active=1
        choice.config(state='disabled');popup.grab_release.assert_called_once();popup.destroy.assert_called_once()
        self.assertIsNone(choice.popup);self.assertEqual(choice.choose(),'break');self.assertEqual(value.get(),'A');choice.destroy()
    def test_disabled_switch_cannot_change_the_setting(self):
        value=tk.BooleanVar(self.root,value=False);switch=RoundedSwitch(self.root,variable=value)
        switch.config(state='disabled');switch.toggle();self.assertFalse(value.get());switch.destroy()
    def test_switch_release_without_press_does_not_toggle(self):
        value=tk.BooleanVar(self.root,value=False);switch=RoundedSwitch(self.root,variable=value);event=SimpleNamespace(x=0,y=0)
        switch.release(event);self.assertFalse(value.get())
        switch.press(event);switch.release(event);self.assertTrue(value.get());switch.destroy()
    def test_training_panel_renders_with_no_session_and_keeps_actions_outside_scroll_area(self):
        from training_ui import open_training
        app=SimpleNamespace(root=self.root,training_window=None,training_session=None,s=SimpleNamespace(mobile='ARMOR'),book=SimpleNamespace(records={}))
        win=open_training(app);win.withdraw();win.update_idletasks()
        buttons=[]
        def visit(widget):
            for child in widget.winfo_children():
                if isinstance(child,RoundedButton):buttons.append(child)
                visit(child)
        visit(win)
        start=next(b for b in buttons if b.cget('text')=='Empezar');stop=next(b for b in buttons if b.cget('text')=='Detener')
        self.assertEqual(start.cget('state'),'normal');self.assertEqual(stop.cget('state'),'disabled')
        self.assertIs(start.master.master,win);win.destroy()
    def test_closing_monitor_panel_does_not_cancel_the_training_session(self):
        from training_ui import open_training
        from training_session import TrainingSession
        session=TrainingSession('',None,'book.json',Mock());session.stop=Mock()
        app=SimpleNamespace(root=self.root,training_window=None,training_session=session,s=SimpleNamespace(mobile='ARMOR'),book=SimpleNamespace(records={}))
        win=open_training(app);win.withdraw();win.tk.call(win.protocol('WM_DELETE_WINDOW'))
        session.stop.assert_not_called()
