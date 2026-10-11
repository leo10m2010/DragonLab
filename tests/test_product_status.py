import time,unittest
from types import SimpleNamespace
from unittest.mock import Mock
from product_status import capture_status
class ProductStatusTests(unittest.TestCase):
    def app(self,**changes):
        values=dict(last_live=time.monotonic(),has_position_data=True,dirty=False,computing=False,clone_id='gunbound-world',result={'reachable':True,'power':55},game_visible=True,guide_points=((0,0),(100,0)),power_guide=SimpleNamespace(win=SimpleNamespace(winfo_viewable=lambda:True)))
        values.update(changes);return SimpleNamespace(**values)
    def test_valid_visible_guide_is_active(self):self.assertEqual(capture_status(self.app())[0],'Guía activa')
    def test_unreachable_candidate_power_is_not_active(self):self.assertEqual(capture_status(self.app(result={'reachable':False,'power':100}))[0],'Sin calibración')
    def test_unfocused_window_does_not_claim_visible_guide(self):self.assertEqual(capture_status(self.app(game_visible=False))[0],'Guía preparada')
    def test_hidden_native_window_is_reported(self):self.assertEqual(capture_status(self.app(power_guide=None))[0],'Guía oculta')
    def test_stale_sample_is_not_active(self):self.assertEqual(capture_status(self.app(last_live=time.monotonic()-10))[0],'Esperando partida')
