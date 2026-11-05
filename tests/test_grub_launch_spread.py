"""Calibration changes the base speed, not Grub's relative launch spread."""
import math,unittest
from dataclasses import replace
from core import Settings
from physics_extensions import variants,segments


class GrubLaunchSpreadTests(unittest.TestCase):
    def test_speed_differences_survive_calibration_in_both_directions(self):
        for scale in (1,1012/400,3.1):
            for look in (0,1):
                with self.subTest(scale=scale,look=look):
                    settings=Settings(mobile='GRUB',selected_shot=1,look=look,power_scale=scale,muzzle=False,max_time=.1,wind=0,angle=45)
                    observed=[]
                    for variant in variants(settings):
                        local=replace(settings,angle_offset=variant['angleOffset'],speed_offset=variant['speedOffset'])
                        first=segments(local,200)[0][0]
                        observed.append(math.hypot(first['vx'],first['vy'])-200*scale)
                    for actual,expected in zip(observed,(10,5,0,-5)):
                        self.assertAlmostEqual(actual,expected,places=8)
    def test_angles_mirror_while_speed_spread_stays_asymmetric(self):
        right=variants(Settings(mobile='GRUB',selected_shot=1,look=1))
        left=variants(Settings(mobile='GRUB',selected_shot=1,look=0))
        self.assertEqual([v['angleOffset'] for v in right],[4,2,0,-2])
        self.assertEqual([v['angleOffset'] for v in left],[-4,-2,0,2])
        self.assertEqual([v['speedOffset'] for v in left],[10,5,0,-5])
        self.assertTrue(all('powerOffset' not in v for v in right+left))
    def test_other_grub_modes_have_no_four_ball_spread(self):
        for mode in (0,2):self.assertEqual(variants(Settings(mobile='GRUB',selected_shot=mode)),[{}])
    def test_observed_custom_projectiles_keep_precedence(self):
        native=[{'angleOffset':1,'speedOffset':7}]
        self.assertIs(variants(Settings(mobile='GRUB',selected_shot=1,environment={'projectiles':native})),native)


if __name__=='__main__':unittest.main()
