import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from browser_targets import choose_page,resolve_game_target,AmbiguousGamePages,NoGamePage
from session_lifecycle import scoped_epoch,SourceLifecycle
from cdp import CDP

PAGES=[{'id':key,'type':'page','url':'https://dragonbound.net/'} for key in ('old','new')]

class BrowserTargetTests(unittest.TestCase):
    def test_focused_game_replaces_the_other_active_tab(self):
        states={'old':{'game':True},'new':{'game':True,'focused':True}}
        self.assertEqual(choose_page(PAGES,states,'old'),'new')

    def test_only_running_game_wins_over_a_lobby(self):
        states={'old':{'game':False,'focused':True},'new':{'game':True}}
        self.assertEqual(choose_page(PAGES,states),'new')

    def test_background_tabs_keep_the_previous_connection(self):
        states={'old':{'game':True},'new':{'game':True}}
        self.assertEqual(choose_page(PAGES,states,'old'),'old')
        with self.assertRaises(AmbiguousGamePages):choose_page(PAGES,states)

    def test_visible_game_is_selected_when_the_application_has_focus(self):
        states={'old':{'game':True},'new':{'game':True,'visible':True}}
        self.assertEqual(choose_page(PAGES,states,'old'),'new')

    def test_two_lobbies_can_connect_without_enabling_a_shot(self):
        self.assertEqual(choose_page(PAGES,{'old':{'game':False},'new':{'game':False}}),'old')

    def test_closed_automatic_tab_does_not_block_rediscovery(self):
        with patch('cdp.CDP') as connect:
            self.assertEqual(resolve_game_target('http://127.0.0.1:9223',['dragonbound.net'],preferred='closed',pages=PAGES[:1]),'old')
            connect.assert_not_called()

    def test_unrelated_hosts_are_never_probed(self):
        with patch('cdp.CDP') as connect:
            with self.assertRaises(NoGamePage):resolve_game_target('http://127.0.0.1:9223',['dragonbound.net'],pages=[{'id':'other','type':'page','url':'https://dragonbound.net.evil.example/'}])
            connect.assert_not_called()

    def test_probes_pin_their_pages_and_release_their_sockets(self):
        clients=[]
        def connect(endpoint,target_id,hostname):
            client=Mock();client.call.return_value={'result':{'value':{'game':target_id=='new'}}};clients.append(client);return client
        with patch('cdp.CDP',side_effect=connect) as constructor:
            self.assertEqual(resolve_game_target('http://127.0.0.1:9223',['dragonbound.net'],pages=PAGES),'new')
            self.assertEqual([call.kwargs['target_id'] for call in constructor.call_args_list],['old','new'])
        for client in clients:client.close.assert_called_once()

    def test_identical_native_epochs_from_different_tabs_remain_distinct(self):
        native='100:0:1:2:0'
        first=scoped_epoch(native,'old');second=scoped_epoch(native,'new')
        self.assertNotEqual(first,second);self.assertEqual(scoped_epoch(first,'old'),first)

    def test_cdp_tagging_remains_stable_when_applied_twice(self):
        client=SimpleNamespace(lifecycle=SourceLifecycle('old'),source_epoch='initial')
        first=CDP.tag_sample(client,{'sourceEpoch':'100:0:1:2:0'})
        second=CDP.tag_sample(client,dict(first))
        self.assertEqual(first['sourceEpoch'],second['sourceEpoch']);self.assertEqual(client.source_epoch,first['sourceEpoch'])

if __name__=='__main__':unittest.main()
