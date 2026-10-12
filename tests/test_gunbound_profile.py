import unittest,math
from gunbound_profiles import measured_profile
from core import Settings
from physics_extensions import segments,at
class GunBoundProfileTests(unittest.TestCase):
    def test_only_measured_mode_and_wind_range_are_enabled(self):
        self.assertIsNotNone(measured_profile('ARMOR',0,18))
        self.assertIsNotNone(measured_profile('ARMOR',1,0))
        self.assertIsNotNone(measured_profile('ARMOR',1,22))
        self.assertIsNotNone(measured_profile('ARMOR',2,2))
        self.assertIsNotNone(measured_profile('ARMOR',2,24))
        for mobile,shot,wind in [('ARMOR',1,23),('ARMOR',2,0),('NAK',0,0),('ARMOR',0,25)]:
            self.assertIsNone(measured_profile(mobile,shot,wind))
    def test_native_first_step_has_not_received_full_step_acceleration(self):
        s=Settings(hero_x=0,hero_y=0,angle=45,look=1,muzzle=False,gravity=400,power_scale=9.2,environment={'nativeEulerStep':.05})
        segs,_=segments(s,50);x,y=at(segs[0],.05)
        self.assertAlmostEqual(x,460/math.sqrt(2)*.05)
        self.assertAlmostEqual(y,-460/math.sqrt(2)*.05)
    def test_copies_cannot_mutate_the_shipped_profile(self):
        a=measured_profile('ARMOR',0,0);a['power_scale']=1
        self.assertGreater(measured_profile('ARMOR',0,0)['power_scale'],9)
