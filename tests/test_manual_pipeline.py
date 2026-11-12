import threading,time,queue,unittest,copy,tempfile,pathlib,tkinter as tk
from types import SimpleNamespace
from unittest.mock import Mock,patch
from core import Settings,SolveCancelled
from latest_calculation import LatestCalculation
from trajectories import projected_runs
from launcher import requested_training_mode,demo_launch_requested,Launcher
from app import App,manual_input_issue
from calibration_book import mobile_name
from test_guide_wind_model import app_fixture

class ManualPipelineTests(unittest.TestCase):
    def job(self,n):return {'settings':Settings(angle=n),'generation':n,'context':('test',n)}
    def test_only_latest_pending_angle_is_solved_and_workers_never_overlap(self):
        output=queue.Queue();started=threading.Event();release=threading.Event();visited=[];active=[]
        def solver(settings,cancel):
            visited.append(settings.angle);active.append(settings.angle)
            self.assertEqual(len(active),1)
            try:
                if settings.angle==1:
                    started.set();self.assertTrue(release.wait(2));self.assertTrue(cancel.is_set());raise SolveCancelled()
                return {'reachable':True,'power':settings.angle}
            finally:active.pop()
        worker=LatestCalculation(output.put,solver)
        try:
            worker.submit(self.job(1));self.assertTrue(started.wait(2))
            worker.submit(self.job(2));worker.submit(self.job(3));release.set()
            result=output.get(timeout=2)
            self.assertEqual(visited,[1,3]);self.assertEqual(result['generation'],3);self.assertTrue(output.empty())
        finally:release.set();worker.close()
    def test_invalidating_or_closing_a_worker_cannot_publish_a_stale_force(self):
        for close in (False,True):
            with self.subTest(close=close):
                output=queue.Queue();started=threading.Event();done=threading.Event()
                def solver(settings,cancel):started.set();done.wait(2);return {'reachable':True,'power':200}
                worker=LatestCalculation(output.put,solver);worker.submit(self.job(1));self.assertTrue(started.wait(2))
                worker.close() if close else worker.invalidate();done.set();worker.thread.join(2) if close else time.sleep(.03)
                self.assertTrue(output.empty());worker.close()
    def test_unidentified_vehicle_never_draws_a_preview_with_previous_physics(self):
        output=queue.Queue();solver=Mock();worker=LatestCalculation(output.put,solver)
        try:
            with patch('physics_extensions.trajectory') as trajectory:
                worker.submit({**self.job(1),'profile_required':True,'missing_reason':'unknown vehicle','preview_power':150})
                result=output.get(timeout=2)['result']
                solver.assert_not_called();trajectory.assert_not_called()
                self.assertFalse(result['reachable']);self.assertNotIn('preview_paths',result)
        finally:worker.close()
    def test_mark_cancels_obsolete_work_without_changing_shot_state(self):
        app=SimpleNamespace(dirty=False,compute_generation=4,calculations=Mock(),pending_fire=None,fire_busy=False)
        App.mark(app);self.assertTrue(app.dirty);self.assertEqual(app.compute_generation,5);app.calculations.invalidate.assert_called_once()
        self.assertFalse(app.fire_busy);self.assertIsNone(app.pending_fire)
    def test_synchronous_manual_recompute_clears_cancelled_async_busy_state(self):
        app=SimpleNamespace(calculations=Mock(),computing=True,dirty=False,compute_generation=4,profile_required=True,profile_missing_reason='old',result={'power':300},visual_context=lambda:('new',),show_result=Mock())
        def read():
            App.mark(app);app.profile_required=False
            return Settings(angle=77)
        app.read=read
        with patch('app.solve',return_value={'reachable':True,'power':150}) as solver:
            result=App.compute(app)
        self.assertEqual(solver.call_args.args[0].angle,77)
        self.assertEqual(result['power'],150);self.assertEqual(app.compute_generation,6)
        self.assertFalse(app.computing);self.assertFalse(app.dirty);self.assertEqual(app.result_context,('new',))
    def test_failed_synchronous_recompute_leaves_no_stale_force(self):
        app=SimpleNamespace(calculations=Mock(),computing=True,dirty=False,compute_generation=4,profile_required=False,result={'power':300},read=lambda:Settings())
        with patch('app.solve',side_effect=ValueError('bad input')):
            with self.assertRaises(ValueError):App.compute(app)
        self.assertEqual(app.result,{});self.assertFalse(app.computing);self.assertTrue(app.dirty)
    def test_incomplete_native_inputs_cannot_borrow_previous_angle_wind_or_weapon(self):
        state={'wind':10,'windAngle':90,'selectedShot':0};hero={'angle':60}
        self.assertEqual(manual_input_issue(state,hero),'')
        for field,value in [('wind',None),('wind',float('nan')),('windAngle',float('inf')),('selectedShot',None),('selectedShot',True)]:
            self.assertTrue(manual_input_issue({**state,field:value},hero))
        for value in (None,True,float('nan')):self.assertTrue(manual_input_issue(state,{'angle':value}))
        self.assertEqual(manual_input_issue({**state,'wind':0,'windAngle':None},hero),'')
    def test_missing_wind_or_angle_clears_guide_and_recovers_on_complete_frame(self):
        with tempfile.TemporaryDirectory() as folder,patch('app.BASE',pathlib.Path(folder)),patch('app.App.start_target_shortcut'),patch('app.sys.argv',['app.py','--check']):
            root=tk.Tk();root.withdraw();app=App(root,embedded=True)
            state={'status':'live','heroId':0,'selectedShot':0,'wind':10,'windAngle':90,'players':[{'id':0,'name':'test hero','x':100,'y':100,'angle':60,'body':0,'look':1,'mobile':0,'team':0},{'id':1,'name':'test target','x':400,'y':100,'team':1}]}
            try:
                app.apply_live(copy.deepcopy(state));self.assertTrue(app.dirty)
                for missing_angle in (False,True):
                    app.result={'reachable':True,'power':200};app.computing=True;app.dirty=False
                    broken=copy.deepcopy(state)
                    if missing_angle:broken['players'][0]['angle']=None
                    else:broken['wind']=None
                    app.apply_live(broken)
                    self.assertEqual(app.display_result(),{});self.assertEqual(app.result,{})
                    self.assertFalse(app.computing);self.assertFalse(app.dirty);self.assertTrue(app.live_input_issue)
                    app.apply_live(copy.deepcopy(state));self.assertEqual(app.live_input_issue,'');self.assertTrue(app.dirty)
            finally:root.update_idletasks();app.close()
    def test_line_projection_keeps_every_vertex_and_explicit_break(self):
        path=[(i,i*i*.01) for i in range(501)]
        runs=projected_runs(path,lambda x,y:(x+5,y-3),2,3)
        self.assertEqual(len(runs[0]),1002);self.assertEqual(runs[0][-2:],(1010,7491))
        separated=projected_runs([(0,0),(1,1),None,(8,8),(9,9)],lambda x,y:(x,y),1,1)
        self.assertEqual(separated,[(0,0,1,1),(8,8,9,9)])
    def test_separate_entries_never_start_training_from_manual(self):
        self.assertFalse(requested_training_mode(['--train-two'],'C:/DragonLab-Manual.exe',True))
        self.assertTrue(requested_training_mode([],'C:/DragonLab-Automatico.exe',True))
        self.assertFalse(requested_training_mode([],'C:/DragonLab-Prueba.exe',True))
        for name in ('DragonLab-Manual.exe','DragonLab-Automatico.exe'):self.assertTrue(demo_launch_requested([],name,True))
        app=SimpleNamespace(closed=False,authenticated=True,training_mode=False,engine=Mock())
        with patch('training_ui.start_training') as start:Launcher.start_training(app);start.assert_not_called()
    def test_unknown_mobile_cannot_reuse_the_previous_vehicle_force_model(self):
        app=app_fixture({'gravity':390,'wind_scale':4,'power_scale':2,'speed_offset':0,'wind_observed':True})
        app.unrecognized_mobile_id=99;App.apply_measured_profile(app)
        self.assertTrue(app.profile_required);self.assertFalse(app.active_measured_profile);self.assertIn('99',app.profile_missing_reason)
        self.assertEqual(mobile_name(22),'KALSIDDON');self.assertIsNone(mobile_name(99));self.assertIsNone(mobile_name(True))

if __name__=='__main__':unittest.main()
