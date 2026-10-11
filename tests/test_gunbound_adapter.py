import unittest
from unittest.mock import Mock
from adapters import AdapterClient

class GunBoundAdapterTests(unittest.TestCase):
    def client(self, phase):
        c=object.__new__(AdapterClient)
        c.game='state';c.controller='battle'
        c.profile={'id':'gunbound-world','fields':{}}
        state={'status':'live','phase':phase,'players':[{'id':'self','angle':-1}], 'wind':16}
        c.call=Mock(side_effect=[{'result':{'value':state}}, {'result':{'value':{'heroId':'self','localAngle':45,'selectedShot':2}}}, {}])
        return c

    def test_lobby_and_placement_do_not_activate_guidance(self):
        for phase in ('LOBBY','PLACEMENT','GAME_OVER'):
            with self.subTest(phase=phase):
                c=self.client(phase);self.assertEqual(c._generic_sample()['status'],'waiting');self.assertIsNone(c.game);self.assertIsNone(c.controller)

    def test_live_turn_identifies_local_player_and_angle(self):
        c=self.client('TURN');state=c._generic_sample()
        self.assertEqual(state['status'],'live')
        self.assertEqual(state['players'][0]['angle'],45)
        self.assertTrue(state['players'][0]['isHero'])
        self.assertEqual(state['selectedShot'],2)
        self.assertTrue(all(a.args[0]=='Runtime.callFunctionOn' for a in c.call.call_args_list))

    def test_discovery_disables_debugger_on_failure(self):
        c=object.__new__(AdapterClient);c.call=Mock()
        c._discover_listener_controller=Mock(side_effect=RuntimeError('closed'))
        with self.assertRaises(RuntimeError):c._discover_controller()
        self.assertEqual(c.call.call_args.args[0],'Debugger.disable')
