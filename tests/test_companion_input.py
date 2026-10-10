import copy
import math
import threading
import time
import unittest
from unittest.mock import patch

from auto_fire import execute
from app import App
from core import Settings
from trajectories import TrajectoryOverlay


class Backend:
    def __init__(self):
        self.actions=[];self.held=False;self.point=(450,400);self.window=123;self.rect=(0,0,1000,700)
    def foreground(self):return self.window,10,'Fixture'
    def window_rect(self,h):return self.rect
    def input_busy(self):return False
    def escaped(self):return False
    def cursor(self):return self.point
    def point_in_window(self,x,y,h):return self.window==h
    def key(self,down):self.actions.append(('key',down));self.held=down
    def mouse(self,down):self.actions.append(('mouse',down));self.held=down
    def move(self,x,y):self.point=(x,y);self.actions.append(('move',x,y))


class Reader:
    def __init__(self,backend,mode='drag'):
        self.backend=backend;self.mode=mode;self.count=0;self.mutate=None;self.stale=False
    def drag_start(self,window):return 16,130
    def read(self):
        self.count+=1
        state={'turn':0,'hero':0,'shot':0,'wind':1,'windAngle':30,'over':False,'chat':False,'focused':True,'moving':False,
               'mode':self.mode,'busy':self.backend.held,'dragSens':1.37 if self.backend.held else 1.65,'power':round((self.backend.point[0]-16)/1.37) if self.mode=='drag' and self.backend.held else min(400,(self.count-1)*10) if self.backend.held else 320,
               'players':[{'id':0,'x':10,'y':20,'rawAngle':60,'dead':False},{'id':1,'x':400,'y':20,'dead':False}]}
        if self.stale and self.count==2:state.update(busy=False,power=320)
        if self.mutate:self.mutate(state,self.count)
        return state


def plan(power=150):
    return {'power':power,'window':123,'hero':0,'target':1,'shot':0,'wind':1,'windAngle':30,
            'heroState':{'x':10,'y':20,'rawAngle':60},'targetState':{'x':400,'y':20},'dpr':1,'screenBox':(0,0,1000,600)}


class InputTests(unittest.TestCase):
    def run_shot(self,b,r,p=None):
        with patch('auto_fire.time.sleep'):
            return execute(p or plan(),r,threading.Event(),b)
    def test_drag_tracks_randomized_gain_and_starts_on_field(self):
        b=Backend();r=Reader(b);out=self.run_shot(b,r)
        self.assertLessEqual(abs(out['power']-150),1)
        self.assertEqual(b.actions[:2],[('move',16,130),('mouse',True)])
        self.assertEqual(b.actions[2],('move',round(16+150*1.37),130))
        self.assertEqual(sum(a==('mouse',True) for a in b.actions),1)
        self.assertFalse(b.held);self.assertEqual(b.point,(450,400))
    def test_missing_fresh_sensitivity_releases_without_probe_or_retry(self):
        b=Backend();r=Reader(b)
        r.mutate=lambda s,n:s.update(dragSens=None) if n>=2 else None
        with self.assertRaisesRegex(RuntimeError,'sensibilidad'):self.run_shot(b,r)
        self.assertEqual(b.actions,[('move',16,130),('mouse',True),('mouse',False),('move',450,400)])
    def test_charge_does_not_start_never_moves_to_estimate_force(self):
        b=Backend();r=Reader(b)
        r.mutate=lambda s,n:s.update(busy=False) if n>=2 else None
        with patch('auto_fire.time.monotonic',side_effect=[0,0,1]),patch('auto_fire.time.sleep'):
            with self.assertRaisesRegex(RuntimeError,'inició'):execute(plan(),r,threading.Event(),b)
        self.assertEqual(sum(a[0]=='move' for a in b.actions),2)
    def test_slice_waits_for_new_charge_not_previous_force(self):
        b=Backend();r=Reader(b,'space');r.stale=True
        out=self.run_shot(b,r)
        self.assertEqual(out['power'],150);self.assertEqual(b.actions,[('key',True),('key',False)])
    def test_chat_other_turn_movement_invalid_mode_send_no_input(self):
        for change in ({'chat':True},{'turn':1},{'moving':True},{'mode':None},{'focused':False}):
            b=Backend();r=Reader(b);r.mutate=lambda s,n,c=change:s.update(c)
            with self.assertRaises(RuntimeError):self.run_shot(b,r)
            self.assertEqual(b.actions,[])
    def test_lost_focus_during_read_releases_without_restoring_cursor(self):
        b=Backend();r=Reader(b)
        r.mutate=lambda s,n:setattr(b,'window',456) if n==2 else None
        with self.assertRaisesRegex(RuntimeError,'foco'):self.run_shot(b,r)
        self.assertEqual(b.actions[-1],('mouse',False));self.assertFalse(b.held)
    def test_changed_angle_mid_charge_releases_once(self):
        b=Backend();r=Reader(b)
        def changed(s,n):
            if n==2:s['players'][0]['rawAngle']=61
        r.mutate=changed
        with self.assertRaisesRegex(RuntimeError,'ángulo'):self.run_shot(b,r)
        self.assertEqual(sum(a==('mouse',False) for a in b.actions),1);self.assertFalse(b.held)
    def test_cancel_before_start_sends_no_input(self):
        b=Backend();cancel=threading.Event();cancel.set()
        with self.assertRaises(RuntimeError):execute(plan(),Reader(b),cancel,b)
        self.assertEqual(b.actions,[])


class VisualTests(unittest.TestCase):
    def app(self):
        a=App.__new__(App);a.s=Settings();a.clone_id='dragonbound'
        a.mobile=type('Value',(),{'get':lambda self:'ARMOR'})()
        a.target_hero_id=0;a.auto_target_id=1;a.terrain_revision=1;a.dirty=False;a.computing=False
        a.result={'reachable':True,'power':150,'path':[(0,0),(20,10)]};a.result_context=a.visual_context();a.last_computed=time.monotonic()
        return a
    def test_previous_curve_survives_angle_recalculation(self):
        a=self.app();a.s.angle+=1;a.dirty=True;a.computing=True
        self.assertEqual(a.planned_paths(),[[(0,0),(20,10)]])
        self.assertEqual(a.display_result()['power'],150)
    def test_curve_not_reused_for_new_target_position_or_shot(self):
        for key,value in [('target_x',900),('selected_shot',1)]:
            a=self.app();setattr(a.s,key,value)
            self.assertEqual(a.planned_paths(),[])
        a=self.app();a.auto_target_id=2;self.assertEqual(a.display_result(),{})
    def test_stalled_calculation_expires_visible_solution(self):
        a=self.app();a.computing=True;a.last_computed-=2
        self.assertEqual(a.display_result(),{})


class PendingTests(unittest.TestCase):
    def app(self):
        a=App.__new__(App);a.dirty=True;a.computing=True;a.auto_shot_enabled=True;a.auto_enabled=True
        a.angle=60;a.calls=[];a.messages=[];a.fire_context=lambda:(a.angle,1)
        a.fire_notice=a.messages.append;a.trigger_auto_fire=lambda:a.calls.append('shot')
        a.pending_fire=(time.monotonic()+.8,a.fire_context())
        return a
    def test_waits_for_current_solution_then_dispatches_once(self):
        a=self.app();a.process_pending_fire();self.assertEqual(a.calls,[])
        a.dirty=False;a.computing=False;a.process_pending_fire();a.process_pending_fire()
        self.assertEqual(a.calls,['shot'])
    def test_changed_angle_or_expired_request_never_dispatches(self):
        for changed in ('angle','timeout','disabled'):
            a=self.app()
            if changed=='angle':a.angle=61
            elif changed=='timeout':a.pending_fire=(time.monotonic()-1,a.fire_context())
            else:a.auto_shot_enabled=False
            a.dirty=False;a.computing=False;a.process_pending_fire()
            self.assertEqual(a.calls,[]);self.assertIsNone(a.pending_fire)


class OverlayTests(unittest.TestCase):
    def test_invalid_new_path_removes_previous_line(self):
        removed=[]
        a=TrajectoryOverlay.__new__(TrajectoryOverlay)
        a.lines={'aim:0':42};a.marks={};a.labels={};a.visible=True;a.key=(0,0,800,516)
        a.canvas=type('Canvas',(),{'delete':lambda self,item:removed.append(item)})()
        a.update((0,0,800,600),(800,600),lambda x,y:(x,y),
                 [[(float('nan'),0),(None,None)]],{},True)
        self.assertEqual(removed,[42]);self.assertEqual(a.lines,{})


if __name__=='__main__':unittest.main()
