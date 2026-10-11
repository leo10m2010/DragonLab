import sys,pathlib,time,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from core import Settings,solve
from app import App
from strength_guide import guide_power

class GuidanceTests(unittest.TestCase):
    def settings(self,angle=60):
        return Settings(angle=angle,hero_x=150,hero_y=400,target_x=700,target_y=400,gravity=396,power_scale=2.45,muzzle=False,environment={'terrain':{'heights':[450]*1200,'height':900},'hitTolerance':18})
    def test_fast_solver_matches_complete_search(self):
        for angle in (45,60,75,82):
            with self.subTest(angle=angle):
                s=self.settings(angle);fast=solve(s)
                with patch('physics_extensions.variants',return_value=[{'speedRatio':1}]):slow=solve(s)
                self.assertEqual(fast['reachable'],slow['reachable'])
                self.assertEqual(fast['power'],slow['power'])
    def test_covered_player_keeps_blocked_reference(self):
        s=self.settings();s.environment['terrain']={'polygon':[(100,370),(200,370),(200,430),(100,430)]}
        result=solve(s)
        self.assertFalse(result['reachable']);self.assertTrue(result['blocked'])
        self.assertEqual(guide_power(result),205)
        self.assertTrue(result['preview_paths'])
        self.assertLess(result['preview_paths'][0][-1][0],210)
        self.assertEqual((s.hero_x,s.hero_y),(150,400))
    def test_page_and_poll_events_are_deduplicated(self):
        app=type('Fixture',(),{'last_page_gesture':None})()
        event={'owner':'fixture','key':81,'count':1,'at':time.time()*1000}
        self.assertTrue(App.consume_fire_gesture(app,event))
        self.assertFalse(App.consume_fire_gesture(app,event))
        event=dict(event,count=2)
        self.assertTrue(App.consume_fire_gesture(app,event))
        self.assertFalse(App.consume_fire_gesture(app,dict(event,count=3,at=(time.time()-2)*1000)))
    def test_new_document_restarts_counter_and_clock_rounding_is_allowed(self):
        app=type('Fixture',(),{'last_page_gesture':None})()
        event={'owner':'fixture','key':81,'count':9,'document':1,'at':time.time()*1000+1}
        self.assertTrue(App.consume_fire_gesture(app,event))
        self.assertTrue(App.consume_fire_gesture(app,dict(event,count=1,document=2)))

if __name__=='__main__':unittest.main()
