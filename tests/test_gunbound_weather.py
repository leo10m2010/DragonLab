import unittest
from gunbound_weather import normalize_weather,weather_name
class GunBoundWeatherTests(unittest.TestCase):
    def test_mirror_has_spatial_position_and_solver_id(self):
        r=normalize_weather('mirror',[{'kind':'mirror','x':758,'size':92}])
        self.assertEqual(len(r),1);self.assertEqual(r[0]['resolvedTypeId'],7);self.assertEqual(r[0]['x'],758)
    def test_multiple_zones_and_black_force_alias(self):
        r=normalize_weather('tornado',[{'kind':'tornado','x':200,'size':140},{'kind':'blackForce','x':700,'size':90}])
        self.assertEqual([w['typeId'] for w in r],[8,5]);self.assertEqual(r[0]['size'],140)
    def test_global_weather_does_not_invent_a_position(self):
        r=normalize_weather('no-items',[]);self.assertEqual(r[0]['name'],'Sin ítems');self.assertNotIn('x',r[0])
    def test_invalid_zone_is_not_added_to_the_solver(self):self.assertEqual(normalize_weather('',[{'kind':'mirror','x':float('nan')}]),[])

    def test_normalized_columns_reach_trajectory_solver(self):
        from physics_extensions import weather_records
        zones=normalize_weather('mirror',[{'kind':'mirror','x':758,'size':92},{'kind':'tornado','x':300,'size':140}])
        tornado,mirror=weather_records({'activeWeathers':zones})
        self.assertEqual(mirror,[758]);self.assertEqual(tornado,[(300,35)])
    def test_alias_is_case_and_whitespace_independent(self):
        self.assertEqual(weather_name(' BlackForce '),'Negro')

    def test_random_only_uses_a_revealed_variant(self):
        r=normalize_weather('random',[{'kind':'random','x':500,'size':128,'variant':'mirror','revealed':True}])
        self.assertEqual(r[0]['resolvedTypeId'],7)
        r=normalize_weather('random',[{'kind':'random','x':500,'size':128,'variant':'mirror','revealed':False}])
        self.assertTrue(r[0]['unresolved']);self.assertNotIn('resolvedTypeId',r[0])
