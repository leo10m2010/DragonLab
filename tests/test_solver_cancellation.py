import json,math,random,threading,unittest
from dataclasses import asdict
from unittest.mock import patch
from core import Settings,solve,SolveCancelled
from physics_extensions import trajectory,closest,swept_impact
from performance import Governor

class FlipCancel:
    def __init__(self,after):self.after=after;self.calls=0
    def is_set(self):self.calls+=1;return self.calls>=self.after

class SolverCancellationTests(unittest.TestCase):
    def settings(self):
        return Settings(angle=60,hero_x=150,hero_y=400,target_x=700,target_y=400,
                        gravity=396,power_scale=2.45,muzzle=False,
                        environment={'terrain':{'heights':[450]*1200,'height':900},'hitTolerance':18})
    def test_cancelled_calculation_never_returns_a_guide(self):
        stop=threading.Event();stop.set()
        for settings in (Settings(),self.settings()):
            with self.subTest(extended=bool(settings.environment)),self.assertRaises(SolveCancelled):solve(settings,cancel=stop)
    def test_unset_token_is_backward_compatible_and_not_stored_in_settings(self):
        settings=self.settings();before=asdict(settings)
        expected=solve(settings);actual=solve(settings,cancel=threading.Event())
        self.assertEqual(actual,expected);self.assertEqual(asdict(settings),before)
        json.dumps(asdict(settings),allow_nan=False)
    def test_cancel_propagates_inside_a_weather_search(self):
        settings=self.settings();settings.environment['activeWeathers']=[{'typeId':8,'x':400,'size':160}]
        stop=FlipCancel(20)
        with self.assertRaises(SolveCancelled):solve(settings,cancel=stop)
        self.assertEqual(stop.calls,20)
    def test_cancel_propagates_into_the_free_terrain_reference(self):
        settings=self.settings();settings.environment['terrain']={'polygon':[(100,370),(200,370),(200,430),(100,430)]}
        stop=threading.Event();original=trajectory;reached=[]
        def observed(settings,power,*args,**kwargs):
            if not settings.environment.get('terrain'):reached.append(True);stop.set()
            return original(settings,power,*args,**kwargs)
        with patch('physics_extensions.trajectory',side_effect=observed),self.assertRaises(SolveCancelled):solve(settings,cancel=stop)
        self.assertTrue(reached)
    def test_long_path_sampling_collision_and_scoring_are_cancellable(self):
        settings=Settings(angle=80,max_time=60,max_power=2000,muzzle=False)
        with self.assertRaises(SolveCancelled):trajectory(settings,1000,cancel=FlipCancel(5))
        path=[(float(i),float(i%13),i/10) for i in range(1000)]
        with self.assertRaises(SolveCancelled):closest(path,500,0,cancel=FlipCancel(3))
        with self.assertRaises(SolveCancelled):swept_impact({'heights':[10000]*1000},(0,0,0),(999,0,10),cancel=FlipCancel(3))
        stopped=threading.Event();stopped.set()
        with self.assertRaises(SolveCancelled):closest([(0,0,0)],0,0,cancel=stopped)
        with self.assertRaises(SolveCancelled):swept_impact({'height':1,'width':1},(100,100,0),(101,100,1),cancel=stopped)
    def test_optimized_closest_preserves_reference_arithmetic(self):
        rng=random.Random(64)
        for _ in range(100):
            path=[(rng.uniform(-200,200),rng.uniform(-200,200),float(i)) for i in range(rng.randrange(1,60))]
            x,y=rng.uniform(-100,100),rng.uniform(-100,100)
            expected=(math.hypot(path[0][0]-x,path[0][1]-y),path[0]) if len(path)==1 else (math.inf,None)
            for a,b in zip(path,path[1:]):
                dx=b[0]-a[0];dy=b[1]-a[1];length=dx*dx+dy*dy
                weight=0 if length==0 else max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/length))
                point=tuple(a[i]+weight*(b[i]-a[i]) for i in range(3));distance=math.hypot(point[0]-x,point[1]-y)
                if distance<expected[0]:expected=(distance,point)
            self.assertEqual(closest(path,x,y),expected)
    def test_verified_fine_path_is_not_recomputed_before_display(self):
        original=trajectory
        with patch('physics_extensions.trajectory',wraps=original) as tracked:result=solve(self.settings())
        same=[c for c in tracked.call_args_list if c.args[1]==result['power'] and c.kwargs.get('step')==.02]
        self.assertEqual(len(same),1);self.assertTrue(result['reachable'])

class ManualGovernorTests(unittest.TestCase):
    def test_manual_sampling_is_responsive_without_faster_screenshots_or_terrain(self):
        governor=Governor()
        for mode in ('Auto','Normal','Ligero'):
            read,capture,terrain=governor.intervals(mode,manual=True)
            self.assertLessEqual(read,.18);self.assertGreaterEqual(capture,3);self.assertGreaterEqual(terrain,3)
        self.assertEqual(governor.intervals('Ligero',manual=True,active=False),(1,6,8))
        self.assertEqual(governor.intervals('Ligero',manual=True,own_turn=False),(.25,4,5))
    def test_existing_training_intervals_keep_their_previous_contract(self):
        governor=Governor();self.assertEqual(governor.intervals('Ligero'),(.35,3,5))
        self.assertEqual(governor.intervals('Normal'),(.25,1.5,2))

if __name__=='__main__':unittest.main()
