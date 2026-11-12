import copy,json,math,os,pathlib,random,threading,time,unittest
from dataclasses import replace
from unittest.mock import Mock,patch
from core import Settings,solve as reference,PROFILES
from native_solver import NativeSolver,NativeUnsupported,library_path
from solve_control import CancellationToken,SolveCancelled
from native_overlay import NativeScene,NativeGuide,NativeTrajectory,annotations

class CancellationTests(unittest.TestCase):
    def test_unregister_serializes_with_native_callback_before_handle_can_be_freed(self):
        token=CancellationToken();entered=threading.Event();release=threading.Event();freed=threading.Event()
        def callback():entered.set();release.wait(2);self.assertFalse(freed.is_set())
        unregister=token.subscribe(callback);setter=threading.Thread(target=token.set);setter.start();self.assertTrue(entered.wait(2))
        cleanup=threading.Thread(target=lambda:(unregister(),freed.set()));cleanup.start();self.assertFalse(freed.wait(.02))
        release.set();setter.join(2);cleanup.join(2);self.assertTrue(freed.is_set())
    def test_subscribing_after_cancel_immediately_notifies_and_unregisters(self):
        token=CancellationToken();token.set();callback=Mock();unregister=token.subscribe(callback);callback.assert_called_once();unregister();token.set();callback.assert_called_once()

@unittest.skipUnless(library_path('dragonlab_core').is_file(),'build native Rust core first')
class NativeParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.native=NativeSolver()
    def equivalent(self,actual,expected,path='result'):
        if isinstance(expected,dict):
            self.assertEqual(set(actual),set(expected),path)
            for key in expected:self.equivalent(actual[key],expected[key],path+'.'+key)
        elif isinstance(expected,(list,tuple)):
            self.assertEqual(len(actual),len(expected),path)
            for i,(a,e) in enumerate(zip(actual,expected)):self.equivalent(a,e,path+f'[{i}]')
        elif isinstance(expected,(int,float)) and not isinstance(expected,bool):self.assertTrue(math.isclose(actual,expected,abs_tol=1e-7,rel_tol=1e-10),(path,actual,expected))
        else:self.assertEqual(actual,expected,path)
    def test_all_regression_fields_and_vertices_match_including_weather_and_blocked_reference(self):
        fixtures=json.loads((pathlib.Path(__file__).parent/'fixtures/ballistics.json').read_text())
        for i,case in enumerate(fixtures):
            with self.subTest(case=i):
                settings=Settings(**case['settings']);self.equivalent(self.native.solve(settings),reference(settings))
    def test_seeded_matrix_preserves_power_contact_and_geometry(self):
        rng=random.Random(190)
        for i in range(120):
            mobile=rng.choice(['ARMOR','ICE','ADUKA','LIGHTNING','JD','ASATE','FOX','ELECTRICO','RAON','DRAGON2'])
            g,w,p,*_=PROFILES[mobile]
            environment={} if i<30 else {'hitTolerance':18,'terrain':{'heights':[450]*1200,'height':900}}
            if i>=70:environment['activeWeathers']=[{'typeId':7 if i%2 else 8,'x':400,'size':160}]
            settings=Settings(mobile=mobile,angle=rng.uniform(15,85),wind=rng.uniform(0,30),wind_angle=rng.uniform(-360,360),wind_mode='floor' if i%3==0 else 'smooth',gravity=g*5,power_scale=p*2.4,wind_scale=w*5,hero_x=150 if i%2 else 950,target_x=700 if i%2 else 300,hero_y=400,target_y=rng.uniform(250,450),look=i%2,muzzle=i%3!=0,body_angle=rng.uniform(-15,15),selected_shot=i%3,environment=environment)
            with self.subTest(case=i,mobile=mobile):self.equivalent(self.native.solve(settings),reference(settings))
    def test_special_projectiles_remain_explicit_fallbacks(self):
        for mobile,shot,environment in [('NAK',1,{}),('KALSIDDON',2,{}),('TRICO',1,{}),('ARMOR',0,{'weatherModel':'gunbound-world'}),('ARMOR',0,{'projectiles':[{'speedRatio':.9}]})]:
            with self.subTest(mobile=mobile),self.assertRaises(NativeUnsupported):self.native.solve(Settings(mobile=mobile,selected_shot=shot,environment=environment))
    def test_invalid_numbers_and_cancelled_tokens_never_produce_a_force(self):
        with self.assertRaises(ValueError):self.native.solve(Settings(wind=float('nan')))
        token=CancellationToken();token.set()
        with self.assertRaises(SolveCancelled):self.native.solve(Settings(),token)
    def test_background_native_calculation_can_be_cancelled_and_joined(self):
        token=CancellationToken();started=threading.Event();finished=threading.Event();errors=[]
        settings=Settings(angle=78,max_time=60,max_power=2000,environment={'activeWeathers':[{'typeId':8,'x':400,'size':160},{'typeId':7,'x':900}]})
        def calculate():
            started.set()
            try:self.native.solve(settings,token)
            except SolveCancelled:pass
            except Exception as error:errors.append(error)
            finally:finished.set()
        thread=threading.Thread(target=calculate,daemon=True);thread.start();started.wait(2);deadline=time.monotonic()+3
        while not finished.wait(.001) and time.monotonic()<deadline:token.set()
        thread.join(.2);self.assertFalse(thread.is_alive());self.assertEqual(errors,[])

class OverlayContractTests(unittest.TestCase):
    def scene(self):
        scene=NativeScene.__new__(NativeScene);scene.dll=Mock();scene.dll.dl_overlay_update_json.return_value=0;scene.dll.dl_overlay_status.return_value=3
        scene.frame={'box':[0,0,800,600],'viewport':[800,600],'planned':[],'observed':{},'players':[],'annotations':[],'style':{},'guide':{'visible':False},'visible':False}
        scene.trajectory_visible=False;scene.guide_visible=False;scene.last=None;scene.closed=False;scene.owners=set();return scene
    def test_guide_only_bounds_and_state_colors_do_not_activate_the_trajectory_field(self):
        scene=self.scene();guide=NativeGuide(None,(10,550),(410,550),scene)
        guide.draw({'reachable':True,'power':200,'guide_state':'measured'},400,True)
        payload=json.loads(scene.dll.dl_overlay_update_json.call_args.args[0]);self.assertFalse(payload['visible'])
        self.assertTrue(payload['guide']['visible']);self.assertTrue(payload['guide']['updating']);self.assertTrue(payload['guide']['measured'])
        self.assertEqual(payload['guide']['power'],200);guide.close()
    def test_identical_draw_avoids_ffi_but_dead_message_thread_fails_over(self):
        scene=self.scene();scene.submit();scene.submit();self.assertEqual(scene.dll.dl_overlay_update_json.call_count,1)
        scene.dll.dl_overlay_status.return_value=0
        with self.assertRaises(RuntimeError):scene.submit()
    def test_closing_one_component_does_not_break_the_other_or_leak_owners(self):
        scene=self.scene();guide=NativeGuide(None,(10,550),(410,550),scene);overlay=NativeTrajectory(None,scene)
        guide.draw({'reachable':True,'power':200},400);overlay.update([0,0,800,600],[800,600],lambda x,y:(x,y),[[(1,2),(3,4)]],{},False)
        guide.close();self.assertFalse(scene.closed);self.assertEqual(len(scene.owners),1)
        overlay.update([0,0,800,600],[800,600],lambda x,y:(x,y),[[(1,2),(3,4)]],{},True)
        self.assertTrue(scene.trajectory_visible);overlay.close();self.assertTrue(scene.closed);self.assertEqual(scene.owners,set())
        scene.dll.dl_overlay_close.assert_called_once()
    def test_projection_keeps_explicit_gaps_and_weather_event_labels(self):
        scene=self.scene();overlay=NativeTrajectory(None,scene)
        overlay.update([0,0,800,600],[800,600],lambda x,y:(x+5,y),[[(1,2),(3,4),None,(8,9),(10,11)]],{},True,players=[{'id':0,'x':1,'y':2,'team':0},{'id':1,'x':7,'y':8,'team':1}],hero_id=0,target_id=1,weather=[{'typeId':7,'x':400}],style={'events':[{'kind':'mirror','x':400,'y':100}]})
        self.assertEqual(scene.frame['planned'],[[[6,2],[8,4]],[[13,9],[15,11]]]);self.assertEqual(len(scene.frame['players']),2)
        labels=[a['label'] for a in scene.frame['annotations']];self.assertIn('Mirror',labels);self.assertIn('Mirror · rebote',labels);overlay.close()

if __name__=='__main__':unittest.main()
