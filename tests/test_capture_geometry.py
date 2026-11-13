import unittest
from unittest.mock import Mock,patch
from automatic import AutoCapture,screen_geometry

class GeometryTests(unittest.TestCase):
    def test_live_fractional_css_offset_does_not_remove_the_force_marker(self):
        meta={'active':True,'dpr':1,'inner':[958,944],
              'game':[0,-0.56500244140625,958,944.8275146484375],
              'bar':[288.5975036621094,902.3499755859375,478.9999694824219,22.75250244140625]}
        area,points=screen_geometry(meta,(948,87))
        self.assertEqual(area,(948,86,1906,1031))
        self.assertEqual(points,((1237,1000),(1716,1000)))
    def test_partially_clipped_game_keeps_a_visible_power_bar_and_original_origin(self):
        meta={'active':True,'dpr':1,'inner':[958,744],'game':[-21,0,1000,800],'bar':[180,690,600,18]}
        area,points=screen_geometry(meta,(10,90))
        self.assertEqual(area,(-11,90,989,890))
        self.assertEqual(points,((190,789),(790,789)))
        # Preserve the full 400-power scale; do not resize it to the clipped map.
        self.assertEqual(points[1][0]-points[0][0],600)
        meta['game']=[1000,0,1000,800]
        self.assertEqual(screen_geometry(meta,(10,90)),(None,None))
    def test_gunbound_bar_uses_entire_gauge_and_dpi(self):
        meta={'active':True,'clone':'gunbound-world','dpr':1.5,'game':[120,0,1680,945],'bar':[626,871,840,40]}
        client=Mock();client.call.side_effect=[{'result':{'value':meta}},{'result':{'value':{'count':0}}}]
        with patch('automatic.content_origin',return_value=(10,20)):
            read=AutoCapture(client).read(capture=False)
        self.assertEqual(read['guide_points'],((949,1356),(2209,1356)))
        self.assertEqual(client.call.call_count,2)
        self.assertEqual(read['fire_gesture']['count'],0)
    def test_inactive_game_has_no_screen_overlay(self):
        self.assertEqual(screen_geometry({'active':False},(10,20)),(None,None))
