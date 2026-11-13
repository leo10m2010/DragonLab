import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from state_storage import engine_directory, is_temporary_directory, migrate_numeric_state, sanitize_numeric_state


class StateStorageTests(unittest.TestCase):
    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')

    def test_archive_launch_uses_stable_directory_and_retains_numeric_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder); temp = root/'Temp'; base = temp/'Rar$EXa123'/'release'
            self.write(base/'datos'/'calibraciones.json', {'schema': 1, 'records': {'dragonbound:ARMOR:0': {'samples': [], 'fit': {'gravity': 396, 'power_scale': 2, 'speed_offset': 0}}}})
            target = engine_directory(base, local_appdata=root/'Local', temp_roots=[temp])
            self.assertEqual(target, root/'Local'/'DragonLab'/'Manual')
            self.assertTrue((target/'calibraciones.json').is_file())
            self.assertTrue((base/'datos'/'calibraciones.json').is_file())
            other = temp/'Rar$EXb456'/'release'
            self.assertEqual(engine_directory(other, local_appdata=root/'Local', temp_roots=[temp]), target)

    def test_existing_non_temp_calibration_candidates_keep_original_order(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder); base = root/'app'/'release'
            for directory in (base/'DragonLab', base.parent/'DragonLab', base.parent.parent/'DragonLab'):
                self.write(directory/'calibraciones.json', {'schema': 1, 'records': {}})
            self.assertEqual(engine_directory(base, local_appdata=root/'Local', temp_roots=[]), base/'DragonLab')

    def test_existing_data_folder_and_cloud_client_remain_usable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder); base = root/'app'; (base/'datos').mkdir(parents=True)
            self.assertEqual(engine_directory(base, local_appdata=root/'Local', temp_roots=[]), base/'datos')
            self.assertEqual(engine_directory(base, root/'cloud', local_appdata=root/'Local', temp_roots=[]), root/'cloud')

    def test_temporary_client_directory_is_not_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder); temp = root/'Temp'
            target = engine_directory(temp/'release', temp/'client', local_appdata=root/'Local', temp_roots=[temp])
            self.assertEqual(target, root/'Local'/'DragonLab'/'Manual')

    def test_winrar_component_is_temporary_even_without_environment_root(self):
        self.assertTrue(is_temporary_directory(pathlib.Path('Rar$EXa23')/'data', temp_roots=[]))
        self.assertFalse(is_temporary_directory(pathlib.Path('archive')/'data', temp_roots=[]))

    def test_only_allowlisted_state_and_fields_are_migrated(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder); source = root/'source'; destination = root/'target'
            for name in ('session.bin', 'cloud-desktop.json', 'license.json', 'cookies.json'):
                self.write(source/name, {'token': 'secret'})
            self.write(source/'Browser'/'Cookies', {'password': 'secret'})
            self.write(source/'preferencias.json', {'clone': 'dragonbound', 'target_key': 'Ctrl', 'fire_key': 'K', 'guide': True, 'viewport': [800, 600], 'path_width': 999, 'adapter': {'password': 'secret'}, 'session': 'secret', 'games': {'dragonbound': {'compact': True, 'cookies': 'secret'}}})
            self.write(source/'perfiles.json', {'dragonbound:ARMOR:0': {'gravity': 396, 'power_scale': 2, 'password': 'secret', 'launch_offset': [10, -5]}, 'license': {'token': 'secret'}})
            self.write(source/'calibraciones.json', {'schema': 1, 'records': {'dragonbound:ICE:0': {'samples': [], 'fit': {'gravity': 400, 'token': 'secret'}, 'cookies': {'value': 'secret'}}}, 'session': {'password': 'secret'}})
            migrated = migrate_numeric_state([source], destination)
            self.assertEqual(set(migrated), {'preferencias.json', 'perfiles.json', 'calibraciones.json'})
            self.assertEqual(set(p.name for p in destination.iterdir()), set(migrated))
            prefs = json.loads((destination/'preferencias.json').read_text())
            self.assertEqual(prefs['fire_key'], 'K'); self.assertEqual(prefs['path_width'], 5)
            self.assertEqual(prefs['games'], {'dragonbound': {'compact': True}})
            self.assertNotIn('adapter', prefs)
            for file in destination.iterdir():
                self.assertNotIn('secret', file.read_text()); self.assertNotIn('password', file.read_text())

    def test_existing_destination_wins_and_source_files_are_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder); first = root/'first'; second = root/'second'; target = root/'target'
            self.write(first/'preferencias.json', {'guide': False})
            self.write(second/'preferencias.json', {'guide': True})
            before = (first/'preferencias.json').read_bytes()
            self.assertEqual(migrate_numeric_state([first, second], target), ['preferencias.json'])
            self.assertEqual(json.loads((target/'preferencias.json').read_text()), {'guide': False})
            self.assertEqual(migrate_numeric_state([second], target), [])
            self.assertEqual((first/'preferencias.json').read_bytes(), before)

    def test_atomic_destination_race_does_not_overwrite_another_writer(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder); source = root/'source'; target = root/'target'
            self.write(source/'preferencias.json', {'guide': True})
            def competing_writer(temporary, destination):
                self.write(destination, {'guide': False})
                raise FileExistsError('Another process migrated first')
            with patch('state_storage.os.link', side_effect=competing_writer):
                self.assertEqual(migrate_numeric_state([source], target), [])
            self.assertEqual(json.loads((target/'preferencias.json').read_text()), {'guide': False})
            self.assertEqual([p.name for p in target.iterdir()], ['preferencias.json'])

    def test_invalid_json_and_nonfinite_values_cannot_escape_sanitizer(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder); source = root/'source'; target = root/'target'
            self.write(source/'perfiles.json', {'dragonbound:ARMOR': {'gravity': float('nan'), 'power_scale': 2, 'wind_scale': float('inf')}})
            (source/'preferencias.json').write_text('{broken', encoding='utf-8')
            self.assertEqual(migrate_numeric_state([source], target), ['perfiles.json'])
            self.assertEqual(json.loads((target/'perfiles.json').read_text()), {'dragonbound:ARMOR': {'power_scale': 2}})

    def test_nonfinite_vectors_and_measurements_are_dropped_whole(self):
        data = {'dragonbound:ARMOR:0': {'launch_offset': [10, float('nan')], 'gravity': 396}}
        self.assertEqual(sanitize_numeric_state('perfiles.json', data), {'dragonbound:ARMOR:0': {'gravity': 396}})
        valid = {'power': 150, 'vx': 200, 'vy': -200, 'ax': 0, 'ay': 396, 'wind': 0, 'wind_angle': 90}
        data = {'schema': 1, 'records': {'dragonbound:ARMOR:0': {'samples': [valid, {**valid, 'vx': float('inf')}], 'fit': {'gravity': float('nan'), 'power_scale': 2}}}}
        cleaned = sanitize_numeric_state('calibraciones.json', data)
        self.assertEqual(cleaned, {'schema': 1, 'records': {'dragonbound:ARMOR:0': {'samples': [valid]}}})

    def test_review_migration_preserves_only_explicit_attribution(self):
        legacy = {'mobile': 'ARMOR', 'shot': 0, 'endpoint_error': 3}
        current = {**legacy, 'schema': 2, 'game_id': 'dragonbound', 'model_version': '0.20.0', 'model_revision': 3, 'source_epoch': 'A:1:2', 'password': 'secret'}
        cleaned = sanitize_numeric_state('revision-tiros.json', {'schema': 2, 'records': [legacy, current]})
        self.assertEqual(cleaned['records'][0], legacy)
        self.assertEqual(cleaned['records'][1]['source_epoch'], 'A:1:2')
        self.assertNotIn('password', cleaned['records'][1])


if __name__ == '__main__':
    unittest.main()
