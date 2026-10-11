import unittest,json,os,uuid
from unittest.mock import patch
from game_startup import activate_existing_game
from desktop_shell import SingleInstance

class StartupTests(unittest.TestCase):
    def response(self,data):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self):return json.dumps(data).encode()
        return Response()
    def test_existing_managed_game_activates_without_opening_another_tab(self):
        targets=[{'type':'page','url':'https://dragonbound.net/','id':'game'}]
        with patch('game_startup.urllib.request.urlopen',side_effect=[self.response(targets),self.response({})]) as read:
            self.assertTrue(activate_existing_game());self.assertEqual(read.call_args.args[0],'http://127.0.0.1:9223/json/activate/game')
    def test_wrong_hostname_is_not_a_reusable_game(self):
        with patch('game_startup.urllib.request.urlopen',return_value=self.response([{'type':'page','url':'https://dragonbound.net.evil.example/','id':'wrong'}])) as read:
            self.assertFalse(activate_existing_game());self.assertEqual(read.call_count,1)
    def test_gunbound_selection_reuses_only_the_gunbound_tab(self):
        targets=[{'type':'page','url':'https://dragonbound.net/','id':'dragon'}, {'type':'page','url':'https://play.gunbound.world/','id':'gunbound'}]
        with patch('game_startup.urllib.request.urlopen',side_effect=[self.response(targets),self.response({})]) as read:
            self.assertTrue(activate_existing_game(host='play.gunbound.world'))
            self.assertTrue(read.call_args.args[0].endswith('/gunbound'))
    def test_unknown_game_host_is_rejected(self):
        with self.assertRaises(ValueError):activate_existing_game(host='evil.example')
    def test_unavailable_browser_falls_back_to_normal_startup(self):
        with patch('game_startup.urllib.request.urlopen',side_effect=OSError()):self.assertFalse(activate_existing_game())
    @unittest.skipUnless(os.name=='nt','Windows mutex')
    def test_duplicate_instance_is_blocked_and_releases_after_exit(self):
        name='DragonLab.Test.'+uuid.uuid4().hex
        a=SingleInstance(name);b=SingleInstance(name)
        try:self.assertTrue(a.primary);self.assertFalse(b.primary)
        finally:b.close();a.close()
        c=SingleInstance(name)
        try:self.assertTrue(c.primary)
        finally:c.close()
