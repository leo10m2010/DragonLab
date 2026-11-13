import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from core import Settings
from shot_review import ShotReview


def live(epoch='A', shot_id=1):
    return {'status': 'live', 'sourceEpoch': epoch, 'heroId': 0, 'activePlayer': 0,
            'selectedShot': 0, 'currentPower': 150, 'wind': 0, 'windAngle': 90,
            'players': [{'id': 0, 'mobile': 0, 'x': 10, 'y': 20, 'angle': 60, 'look': 1},
                        {'id': 1, 'mobile': 0, 'x': 500, 'y': 20}],
            'shots': [{'id': shot_id, 'native': True, 'start': [10, 20, 60, 300, 0, 400],
                       'elapsed': 100, 'duration': 1000, 'shotType': 0}]}


class ShotReviewTests(unittest.TestCase):
    def observe(self, review, state, **attribution):
        with patch('shot_review.trajectory', return_value={'projectile_paths': [[(10, 20, 0), (160, -40, 1)]]}):
            review.observe(state, Settings(), **attribution)

    def test_schema_two_freezes_game_epoch_and_model_at_prediction_time(self):
        with tempfile.TemporaryDirectory() as folder:
            review = ShotReview(pathlib.Path(folder)/'review.json')
            self.observe(review, live(), game_id='dragonbound', model_version='0.20.0', model_revision=5)
            self.observe(review, live(), game_id='dragonbound', model_version='0.21.0', model_revision=6)
            saved = json.loads(review.path.read_text())
            self.assertEqual(saved['schema'], 2); self.assertEqual(len(saved['records']), 1)
            row = saved['records'][0]
            self.assertEqual(row['schema'], 2); self.assertEqual(row['game_id'], 'dragonbound')
            self.assertEqual(row['source_epoch'], 'A'); self.assertEqual(row['model_version'], '0.20.0')
            self.assertEqual(row['model_revision'], 5)

    def test_reused_shot_identity_after_epoch_change_creates_new_review(self):
        with tempfile.TemporaryDirectory() as folder:
            review = ShotReview(pathlib.Path(folder)/'review.json')
            self.observe(review, live('A'), game_id='dragonbound')
            review.seen.add('old-source-id')
            self.observe(review, live('B'), game_id='dragonbound')
            self.assertEqual([row['source_epoch'] for row in review.records], ['A', 'B'])
            self.assertNotIn('old-source-id', review.seen); self.assertEqual(len(review.pending), 1)

    def test_game_change_does_not_reuse_pending_or_show_other_games_latest(self):
        with tempfile.TemporaryDirectory() as folder:
            review = ShotReview(pathlib.Path(folder)/'review.json')
            self.observe(review, live(), game_id='dragonbound')
            review.reset('gunbound-world', 'A')
            self.assertIsNone(review.latest); self.assertEqual(review.pending, {}); self.assertEqual(len(review.records), 1)
            self.observe(review, live(), game_id='gunbound-world')
            self.assertEqual([row['game_id'] for row in review.records], ['dragonbound', 'gunbound-world'])
            review.reset('dragonbound', 'C'); self.assertEqual(review.latest['game_id'], 'dragonbound')

    def test_legacy_history_stays_unattributed_and_is_preserved_when_saving(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder)/'review.json'
            legacy = {'mobile': 'ARMOR', 'shot': 0, 'endpoint_error': 7}
            path.write_text(json.dumps({'schema': 1, 'records': [legacy]}), encoding='utf-8')
            review = ShotReview(path); review.reset('dragonbound', 'A')
            self.assertIsNone(review.latest); self.assertEqual(review.records, [legacy])
            self.observe(review, live(), game_id='dragonbound')
            self.assertEqual(json.loads(path.read_text())['records'][0], legacy)

    def test_explicit_epoch_overrides_state_without_rewriting_history(self):
        with tempfile.TemporaryDirectory() as folder:
            review = ShotReview(pathlib.Path(folder)/'review.json')
            self.observe(review, live(), game_id='dragonbound', source_epoch='explicit')
            self.assertEqual(review.records[0]['source_epoch'], 'explicit')
            review.reset(); self.assertEqual(len(review.records), 1); self.assertEqual(review.pending, {})

    def test_malformed_saved_container_is_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder)/'review.json'
            for value in ([], {'schema': 1, 'records': {}}, {'schema': 100, 'records': []}):
                path.write_text(json.dumps(value), encoding='utf-8')
                self.assertEqual(ShotReview(path).records, [])

    def test_non_live_epoch_change_clears_seen_and_preserves_saved_history(self):
        with tempfile.TemporaryDirectory() as folder:
            review = ShotReview(pathlib.Path(folder)/'review.json')
            self.observe(review, live(), game_id='dragonbound'); review.seen.add('stale')
            review.observe({'status': 'waiting', 'sourceEpoch': 'B'}, Settings(), game_id='dragonbound')
            self.assertEqual(review.pending, {}); self.assertEqual(review.seen, set()); self.assertEqual(len(review.records), 1)


if __name__ == '__main__':
    unittest.main()
