import unittest
from unittest.mock import Mock,patch
from automatic import AutoCapture,screen_geometry

class GeometryTests(unittest.TestCase):
    def test_gunbound_bar_uses_entire_gauge_and_dpi(self):
        meta={'active':True,'clone':'gunbound-world','dpr':1.5,'game':[120,0,1680,945],'bar':[626,871,840,40]}
        client=Mock();client.call.return_value={'result':{'value':meta}}
        with patch('automatic.content_origin',return_value=(10,20)):
            read=AutoCapture(client).read(capture=False)
        self.assertEqual(read['guide_points'],((949,1356),(2209,1356)))
        self.assertEqual(client.call.call_count,1)
        self.assertNotIn('fire_gesture',read)
    def test_inactive_game_has_no_screen_overlay(self):
        self.assertEqual(screen_geometry({'active':False},(10,20)),(None,None))
