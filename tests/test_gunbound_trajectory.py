import unittest
from core import Settings
from physics_extensions import segments
class GunBoundTrajectoryTests(unittest.TestCase):
    def settings(self,kind):return Settings(hero_x=0,hero_y=0,target_x=600,target_y=300,angle=20,look=1,muzzle=False,power_scale=5,gravity=100,max_time=5,environment={'weatherModel':'gunbound-world','activeWeathers':[{'typeId':kind,'x':200,'size':100}]})
    def test_mirror_reverses_once_and_curve_contains_reflected_leg(self):
        parts,events=segments(self.settings(7),50)
        self.assertEqual([e['kind'] for e in events],['mirror']);self.assertGreater(parts[0]['vx'],0);self.assertLess(parts[1]['vx'],0)
    def test_tornado_has_three_legs_without_gravity_and_then_resumes(self):
        parts,events=segments(self.settings(8),50)
        self.assertEqual([e['kind'] for e in events],['enter','bounce','bounce','exit'])
        self.assertEqual([p['ay'] for p in parts[1:4]],[0,0,0]);self.assertEqual(parts[-1]['ay'],100)
        for a,b in zip(parts,parts[1:]):
            from physics_extensions import at
            self.assertAlmostEqual(at(a,a['end'])[0],b['x']);self.assertAlmostEqual(at(a,a['end'])[1],b['y'])
    def test_damage_climates_do_not_invent_a_deflection(self):
        for kind in (3,4,5):
            parts,events=segments(self.settings(kind),50)
            self.assertEqual(len(events),1);self.assertEqual(parts[0]['vx'],parts[-1]['vx']);self.assertEqual(parts[-1]['ay'],100)
    def test_dragonbound_does_not_enter_gunbound_dispatch(self):
        from unittest.mock import patch
        s=self.settings(8);s.environment.pop('weatherModel')
        with patch('gunbound_trajectory.segments',side_effect=AssertionError('wrong clone')):
            parts,events=segments(s,50)
        self.assertTrue(parts);self.assertTrue(events)
