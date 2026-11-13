import json
import time
import unittest
from unittest.mock import Mock

from browser_shortcuts import BrowserShotEvents
from cdp import CDP
from session_lifecycle import SourceLifecycle, primitive_id
from targeting import PlayerTracker, enemies, find_hero, next_target, normalize_players, roster_diagnostics


def client():
    c = object.__new__(CDP)
    c.lifecycle = SourceLifecycle('fixture', '127.0.0.1', 'dragonbound')
    c.source_epoch = c.lifecycle.epoch
    c.game = 'old'; c.renderer = 'renderer'; c.terrain_cache = {'surface': [1]}
    c.terrain_clock = 10; c.terrain_turn = 1; c.terrain_inflight = True
    c.controller = 'controller'; c.retired_games = []; c.contexts = {7}
    c.main_frame = 'main'; c.discovery_clock = 20; c.event_handler = None
    c._source_reset = False
    return c


class SessionLifecycleTests(unittest.TestCase):
    def test_cdp_processes_navigation_events_while_waiting_for_response(self):
        c = client(); old = c.source_epoch; c.counter = 0; c.send = Mock()
        c.message = Mock(side_effect=[{'method': 'Runtime.executionContextsCleared'}, {'id': 1, 'result': {'ok': True}}])
        self.assertEqual(c.call('Runtime.evaluate'), {'ok': True})
        self.assertNotEqual(old, c.source_epoch)
        for key in ('game', 'renderer', 'terrain_cache', 'terrain_turn', 'controller'):
            self.assertIsNone(getattr(c, key))
        self.assertFalse(c.terrain_inflight)
        self.assertFalse(c._source_reset)  # Connecting another reader cannot mutate a shared native epoch.

    def test_default_context_destroy_and_spa_navigation_invalidate(self):
        for event in ({'method': 'Runtime.executionContextDestroyed', 'params': {'executionContextId': 7}},
                      {'method': 'Page.navigatedWithinDocument', 'params': {'frameId': 'main'}},
                      {'method': 'Page.frameNavigated', 'params': {'frame': {'id': 'main', 'url': 'http://127.0.0.1/new'}}}):
            c = client(); before = c.source_epoch; c.handle_event(event)
            self.assertNotEqual(c.source_epoch, before)
            self.assertIsNone(c.game)

    def test_child_frame_navigation_keeps_current_source(self):
        c = client(); before = c.source_epoch
        c.handle_event({'method': 'Page.frameNavigated', 'params': {'frame': {'id': 'child', 'parentId': 'main'}}})
        self.assertEqual(c.source_epoch, before)
        self.assertEqual(c.game, 'old')

    def test_discovery_inspects_distinct_closures_with_identical_descriptions(self):
        c = client(); c.game = None
        def prop(name, value): return {'name': name, 'value': value}
        def obj(oid): return {'type': 'object', 'objectId': oid}
        properties = {
            'handlers': {'result': [prop(str(i), {'type': 'function', 'objectId': 'fn'+str(i), 'description': 'same closure'}) for i in range(2)]},
            'fn0': {'internalProperties': [prop('[[Scopes]]', obj('scopes0'))]},
            'fn1': {'internalProperties': [prop('[[Scopes]]', obj('scopes1'))]},
            'scopes0': {'result': [prop('0', obj('scope0'))]},
            'scopes1': {'result': [prop('0', obj('scope1'))]},
            'scope0': {'result': [prop('game', obj('first'))]},
            'scope1': {'result': [prop('game', obj('second'))]},
            'first': {'result': [prop('players', obj('list')), prop('wind', {'value': 0})]},
            'second': {'result': [prop('players', obj('list')), prop('wind', {'value': 0})]},
        }
        c.call = Mock(return_value={'result': obj('handlers')})
        c.props = lambda oid: properties[oid]
        c._adopt_game = Mock(return_value='second')
        self.assertEqual(c.discover(), 'second')
        self.assertEqual(c._adopt_game.call_args.args[0], ['first', 'second'])

    def test_fresh_active_candidate_replaces_cache_and_retired_object_stays_retired(self):
        c = client(); c._same_object = lambda a, b: a == b
        def call(method, params):
            if params.get('functionDeclaration') == 'function(){return this}':return {'result': {'objectId': params['objectId']}}
            return {'result': {'value': params['objectId'] != 'ended'}}
        c.call = call
        self.assertEqual(c._adopt_game(['old', 'ended', 'new']), 'new')
        self.assertIsNone(c.renderer); self.assertIsNone(c.terrain_cache)
        self.assertIn('old', c.retired_games)
        self.assertEqual(c._adopt_game(['old', 'new']), 'new')

    def test_identity_rejects_objects_boolean_and_nonfinite(self):
        for value in ({'id': 1}, [], True, False, float('nan'), float('inf'), '', 'x'*81):
            self.assertIsNone(primitive_id(value))
        self.assertEqual(primitive_id('0'), 0)
        self.assertEqual(primitive_id('actor-0'), 'actor-0')

    def test_full_roster_duplicate_diagnostics_roles_and_control_cycle(self):
        rows = [{'id': i, 'x': i*20, 'y': 100, 'team': 1 if i < 4 else 2} for i in range(32)]
        rows[0]['isHero'] = True; rows[5]['dead'] = True; rows[8]['team'] = None
        rows += [{'id': '9', 'x': 99, 'y': 100}, {'id': None, 'x': 0, 'y': 0}, {'id': 33, 'x': None, 'y': 100}]
        stats = roster_diagnostics(rows, 0)
        self.assertEqual(stats['raw'], 35); self.assertEqual(stats['duplicates'], 2)
        self.assertEqual(stats['missingId'], 1); self.assertEqual(stats['invalidPosition'], 1)
        self.assertEqual(stats['hero'], 1); self.assertEqual(stats['ally'], 3)
        self.assertEqual(stats['unknown'], 1); self.assertEqual(stats['dead'], 1)
        valid = normalize_players(rows); targets = enemies(valid, 0)
        self.assertEqual(len(targets), 26)
        self.assertEqual(next(p['role'] for p in targets if p['id'] == 8), 'unknown')
        visited = []; current = None
        for _ in targets:current = next_target(valid, 0, current); visited.append(current)
        self.assertEqual(set(visited), {p['id'] for p in targets})
        self.assertNotIn(9, visited)
        self.assertEqual(find_hero(valid, {'id': 0})['id'], 0)

    def test_tracker_epoch_prevents_same_id_relogin_stale_coordinates(self):
        tracker = PlayerTracker()
        self.assertEqual(len(tracker.update([{'id': 0, 'x': 50, 'y': 80}], now=0, source_epoch='A')), 1)
        self.assertTrue(tracker.update([{'id': 0, 'x': None, 'y': None}], now=.1, source_epoch='A')[0]['stale'])
        self.assertEqual(tracker.update([{'id': 0, 'x': None, 'y': None}], now=.2, source_epoch='B'), [])

    def test_duplicate_id_never_reappears_from_tracker_cache(self):
        tracker = PlayerTracker(); row = {'id': 1, 'x': 5, 'y': 10}
        tracker.update([row], now=0, source_epoch='A')
        self.assertEqual(tracker.update([row, dict(row)], now=.1, source_epoch='A'), [])
        self.assertEqual(tracker.diagnostics['duplicates'], 2)

    def test_shortcut_epoch_is_payload_latched_and_old_callback_rejected(self):
        emitted = []; watcher = BrowserShotEvents('http://127.0.0.1:1', 'fixture', 'owner', lambda: 'Q', emitted.append)
        watcher.key = 'Q'; watcher.configured_epoch = 'A'; watcher.set_source_epoch('A'); watcher.document = 10
        payload = {'owner': 'owner', 'key': 81, 'count': 1, 'at': time.time()*1000, 'document': 10, 'sourceEpoch': 'A'}
        message = lambda d: {'method': 'Runtime.bindingCalled', 'params': {'name': watcher.binding, 'payload': json.dumps(d)}}
        watcher.event(message(payload)); self.assertEqual(len(emitted), 1)
        watcher.set_source_epoch('B'); watcher.event(message(payload)); self.assertEqual(len(emitted), 1)
        watcher.configured_epoch = 'B'; watcher.document = 20
        watcher.event(message({**payload, 'sourceEpoch': 'B'})); self.assertEqual(len(emitted), 1)


if __name__ == '__main__':unittest.main()
