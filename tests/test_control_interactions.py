"""Mapped Tk interaction regressions; no browser or gameplay input."""
import os
import tkinter as tk
import unittest
from unittest.mock import Mock

from rounded_controls import RoundedChoice,RoundedSwitch,RoundedTabs


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'requires desktop')
class ControlInteractionTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.root.title('DragonLab control interactions')
        self.root.geometry('440x340+60+60');self.errors=[]
        self.root.report_callback_exception=lambda *error:self.errors.append(error)
        self.value=tk.StringVar(self.root,value='A')
        self.choice=RoundedChoice(self.root,textvariable=self.value,values=list('ABCDEFGHIJK'))
        self.choice.pack(padx=20,pady=16)
        self.other=tk.Entry(self.root);self.other.pack(pady=10)
        self.root.update();self.root.focus_force();self.root.update()

    def tearDown(self):
        try:
            self.root.destroy()
            self.assertEqual(self.errors,[])
        finally:self.root=None

    def pump(self):
        self.root.update();self.root.update_idletasks()

    def open_mouse(self):
        self.choice.event_generate('<ButtonPress-1>',x=25,y=18)
        self.choice.event_generate('<ButtonRelease-1>',x=25,y=18)
        self.pump()
        self.assertIsNotNone(self.choice.popup)
        self.assertTrue(self.choice.popup.winfo_viewable())
        self.assertIs(self.root.grab_current(),self.choice.popup)
        return self.choice.popup

    def test_mouse_opens_and_selects_exactly_once_then_reopens(self):
        selected=[];self.choice.bind('<<ComboboxSelected>>',lambda event:selected.append(self.value.get()))
        self.open_mouse();canvas=self.choice.menu_canvas;y=8+self.choice.row_height+15
        canvas.event_generate('<ButtonPress-1>',x=30,y=y)
        canvas.event_generate('<ButtonRelease-1>',x=30,y=y);self.pump()
        self.assertEqual(self.value.get(),'B');self.assertEqual(selected,['B'])
        self.assertIsNone(self.choice.popup);self.assertIsNone(self.root.grab_current())
        self.open_mouse();self.assertEqual(self.choice.active,1)

    def test_repeated_owner_geometry_request_keeps_open_menu(self):
        popup=self.open_mouse();self.root.geometry(self.root.geometry());self.pump()
        self.assertIs(self.choice.popup,popup)
        self.assertIs(self.root.grab_current(),popup)

    def test_real_owner_move_and_resize_close_menu_without_selection(self):
        for geometry in ('440x340+100+100','470x360+100+100'):
            with self.subTest(geometry=geometry):
                self.open_mouse();self.root.geometry(geometry);self.pump()
                self.assertIsNone(self.choice.popup);self.assertIsNone(self.root.grab_current())
                self.assertEqual(self.value.get(),'A')

    def test_keyboard_navigation_scrolls_and_selects_end(self):
        self.choice.focus_force();self.pump();self.choice.event_generate('<Down>');self.pump()
        popup=self.choice.popup;self.assertIsNotNone(popup)
        popup.event_generate('<End>');self.pump()
        self.assertEqual(self.choice.active,10);self.assertEqual(self.choice.start,4)
        popup.event_generate('<Up>');popup.event_generate('<Return>');self.pump()
        self.assertEqual(self.value.get(),'J');self.assertIsNone(self.choice.popup)

    def test_escape_and_outside_click_cancel_without_selecting(self):
        popup=self.open_mouse();popup.event_generate('<Down>');popup.event_generate('<Escape>');self.pump()
        self.assertIsNone(self.choice.popup);self.assertEqual(self.value.get(),'A')
        popup=self.open_mouse()
        popup.event_generate('<ButtonPress-1>',x=-10,y=-10,rootx=popup.winfo_rootx()-10,rooty=popup.winfo_rooty()-10)
        self.pump();self.assertIsNone(self.choice.popup);self.assertEqual(self.value.get(),'A')

    def test_focus_departure_closes_popup_and_releases_grab(self):
        self.open_mouse();self.other.focus_force();self.pump()
        self.assertIsNone(self.choice.popup);self.assertIsNone(self.root.grab_current())

    def test_tab_closes_popup_and_moves_to_next_control(self):
        popup=self.open_mouse();popup.event_generate('<Tab>');self.pump()
        self.assertIsNone(self.choice.popup);self.assertIs(self.root.focus_get(),self.other)

    def test_disabled_and_changed_values_close_open_popup(self):
        self.open_mouse();self.choice.configure(state='disabled');self.pump()
        self.assertIsNone(self.choice.popup);self.choice.event_generate('<ButtonPress-1>',x=20,y=18);self.pump()
        self.assertIsNone(self.choice.popup);self.assertEqual(self.value.get(),'A')
        self.choice.configure(state='readonly');self.open_mouse();self.choice.configure(values=['X','Y']);self.pump()
        self.assertIsNone(self.choice.popup);self.assertEqual(self.value.get(),'A')

    def test_popup_restores_the_parent_dialog_grab_after_select_and_cancel(self):
        self.root.grab_set()
        popup=self.open_mouse();popup.event_generate('<Return>');self.pump()
        self.assertIs(self.root.grab_current(),self.root)
        popup=self.open_mouse();popup.event_generate('<Escape>');self.pump()
        self.assertIs(self.root.grab_current(),self.root)

    def test_owner_withdraw_releases_popup_and_does_not_restore_hidden_grab(self):
        self.root.grab_set();self.open_mouse();self.root.withdraw();self.pump()
        self.assertIsNone(self.choice.popup);self.assertIsNone(self.root.grab_current())

    def test_destroy_open_choice_cleans_callbacks_and_grab(self):
        self.open_mouse();self.choice.destroy();self.pump()
        self.assertIsNone(self.root.grab_current())

    def test_switch_constructor_disable_and_command_honor_mouse_and_keyboard(self):
        value=tk.BooleanVar(self.root,value=False);command=Mock()
        switch=RoundedSwitch(self.root,text='Trayectorias',variable=value,state='disabled',command=command)
        switch.pack();self.pump();switch.focus_force();self.pump()
        switch.event_generate('<space>');switch.event_generate('<ButtonPress-1>',x=20,y=15)
        switch.event_generate('<ButtonRelease-1>',x=20,y=15);self.pump()
        self.assertFalse(value.get());command.assert_not_called()
        switch.configure(state='normal');switch.event_generate('<ButtonPress-1>',x=20,y=15)
        switch.event_generate('<ButtonRelease-1>',x=20,y=15);self.pump()
        self.assertTrue(value.get());self.assertEqual(command.call_count,1)
        switch.focus_force();self.pump();switch.event_generate('<space>');self.pump()
        self.assertFalse(value.get());self.assertEqual(command.call_count,2)
        switch.event_generate('<ButtonPress-1>',x=20,y=15);switch.configure(state='disabled')
        switch.configure(state='normal');switch.event_generate('<ButtonRelease-1>',x=20,y=15);self.pump()
        self.assertFalse(value.get());self.assertEqual(command.call_count,2)

    def test_consent_subclass_callback_remains_single_and_disabled_is_respected(self):
        from launcher import ConsentSwitch
        value=tk.BooleanVar(self.root,value=False);command=Mock()
        switch=ConsentSwitch(self.root,variable=value,command=command,state='disabled');switch.pack();self.pump()
        switch.toggle();self.assertFalse(value.get());command.assert_not_called()
        switch.configure(state='normal');switch.toggle()
        self.assertTrue(value.get());command.assert_called_once_with()

    def test_tab_buttons_switch_visible_page_with_mouse_and_keyboard(self):
        tabs=RoundedTabs(self.root);tabs.pack(fill='both',expand=True)
        for text in ('General','Avanzado'):
            page=tk.Frame(tabs,bg='#202020');tk.Label(page,text=text).pack();tabs.add(page,text=text)
        self.pump();button=tabs.buttons[1]
        button.event_generate('<ButtonPress-1>',x=10,y=10);button.event_generate('<ButtonRelease-1>',x=10,y=10);self.pump()
        self.assertEqual(tabs.current,1);self.assertTrue(tabs.pages[1].winfo_viewable());self.assertFalse(tabs.pages[0].winfo_viewable())
        tabs.buttons[0].focus_force();self.pump();tabs.buttons[0].event_generate('<Return>');self.pump()
        self.assertEqual(tabs.current,0);self.assertTrue(tabs.pages[0].winfo_viewable())


if __name__=='__main__':unittest.main()
