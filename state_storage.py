"""Stable local numeric state, including launches from temporary archive folders.

Only the four named DragonLab data formats are migration inputs. Browser
profiles, account sessions, licenses and connection configuration are never
copied. Original files remain in place and existing destinations always win.
"""
import json
import math
import os
import pathlib
import re
import tempfile


NUMERIC_FILES = ('calibraciones.json', 'preferencias.json', 'perfiles.json', 'revision-tiros.json')
MAX_MIGRATION_BYTES = 8 * 1024 * 1024
_OMIT = object()
_GAME = re.compile(r'[a-z][a-z0-9-]{0,47}\Z')
_SCOPE = re.compile(r'(?:[a-z][a-z0-9-]{0,47}:)?[A-Z][A-Z0-9]{0,31}(?::[012])?\Z')
_IDENTITY = re.compile(r'[a-fA-F0-9:, .\[\]-]{1,1024}\Z')
_EPOCH = re.compile(r'[A-Za-z0-9:_.-]{1,256}\Z')
_NUMERIC_KEYS = frozenset('''power vx vy ax ay wind wind_angle duration_s native_euler_step
    gravity power_scale speed_offset wind_scale angle_offset sample_count speed_rmse
    gravity_spread acceleration_rmse acceleration_max_error holdout_speed_error
    holdout_acceleration_error validation_count updated created archived angle radius
    shot selected_shot bullet endpoint_error model_revision schema speed acceleration
    trajectory score'''.split())
_BOOL_KEYS = frozenset(('wind_observed', 'simple_trajectory', 'quantize_power'))
_CONTAINERS = frozenset('''samples fit rollback_fit candidate training_ids validation
    accepted_validation active_failures drift_pending previous_regimes sample error
    baseline underground_samples training_patterns launches start muzzle power_range
    wind_range wind_domain launch_offset'''.split())
_SOURCES = frozenset(('native-shot-start', 'native-shot-continuation', 'native-player-aim',
                      'gunbound-own-shot-path', 'attributed-native-group', 'native-shot-path'))


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _numeric_tree(value, key='', depth=0):
    """Keep known measurement fields, with no general text/configuration fields."""
    if depth > 12:
        return _OMIT
    if key in _BOOL_KEYS:
        return value if isinstance(value, bool) else _OMIT
    if key in _NUMERIC_KEYS:
        return value if value is None or _number(value) else _OMIT
    if key in ('launch_offset', 'power_range', 'wind_range', 'wind_domain', 'start'):
        size = 4 if key == 'wind_domain' else 6 if key == 'start' else 2
        if value is None and key == 'launch_offset':
            return None
        return value if isinstance(value, list) and len(value) == size and all(_number(v) for v in value) else _OMIT
    if key in ('id', 'sample_id'):
        return value if isinstance(value, str) and _IDENTITY.fullmatch(value) else _OMIT
    if key in ('source', 'muzzle_source'):
        return value if isinstance(value, str) and value in _SOURCES else _OMIT
    if key == 'wind_mode':
        return value if value in ('smooth', 'floor') else _OMIT
    if key == 'phase':
        return value if value in ('Tiro', 'Guía', 'Entrada en tierra', 'Salida de Nak') else _OMIT
    if key == 'mobile':
        return value if isinstance(value, str) and re.fullmatch(r'[A-Z][A-Z0-9]{0,31}', value) else _OMIT
    if key == 'game_id':
        return value if value is None or isinstance(value, str) and _GAME.fullmatch(value) else _OMIT
    if key == 'model_version':
        return value if value is None or isinstance(value, str) and re.fullmatch(r'\d+\.\d+(?:\.\d+)?', value) else _OMIT
    if key == 'source_epoch':
        return value if value is None or isinstance(value, str) and _EPOCH.fullmatch(value) else _OMIT
    if isinstance(value, dict):
        # A damaged observation or model cannot become valid by silently
        # removing one of the physical inputs its consumers require.
        if any(name in value for name in ('vx', 'vy', 'ax', 'ay')) and not all(
                _number(value.get(name)) for name in ('power', 'vx', 'vy', 'ax', 'ay', 'wind', 'wind_angle')):
            return _OMIT
        if key in ('fit', 'rollback_fit') and any(name in value and not _number(value[name])
                for name in ('gravity', 'power_scale', 'speed_offset')):
            return _OMIT
        if key in ('fit', 'rollback_fit') and value.get('wind_scale') is not None and not _number(value['wind_scale']):
            return _OMIT
        result = {}
        for name, item in value.items():
            if name not in _NUMERIC_KEYS | _BOOL_KEYS | _CONTAINERS | {
                'id', 'sample_id', 'source', 'muzzle_source', 'wind_mode', 'phase',
                'mobile', 'game_id', 'model_version', 'source_epoch',
            }:
                continue
            cleaned = _numeric_tree(item, name, depth + 1)
            if cleaned is not _OMIT:
                result[name] = cleaned
        if key == 'candidate' and 'fit' in value and 'fit' not in result:
            return _OMIT
        return result
    if isinstance(value, list):
        result = []
        for item in value[:4096]:
            cleaned = (_numeric_tree(item, 'id', depth + 1) if key == 'training_ids'
                       else _numeric_tree(item, depth=depth + 1))
            if cleaned is not _OMIT:
                result.append(cleaned)
        return result
    return value if value is None or _number(value) else _OMIT


def _preferences(data):
    result = {}
    for key, allowed in {
        'clone': None, 'target_key': ('Ctrl', *'QERTYUIOPZXCVBNHJKLG'),
        'fire_key': tuple('QERTYUIOPZXCVBNHJKLG'),
        'performance': ('Auto', 'Ligero', 'Normal'), 'path_color': ('Menta', 'Verde', 'Blanco', 'Azul'),
    }.items():
        value = data.get(key)
        if isinstance(value, str) and (_GAME.fullmatch(value) if key == 'clone' else value in allowed):
            result[key] = value
    for key in ('auto_shot', 'trajectories', 'guide', 'compact', 'large_text'):
        if isinstance(data.get(key), bool):
            result[key] = data[key]
    if _number(data.get('path_width')):
        result['path_width'] = max(1, min(5, int(data['path_width'])))
    viewport = data.get('viewport')
    if isinstance(viewport, list) and len(viewport) == 2 and all(_number(v) and 1 <= v <= 32768 for v in viewport):
        result['viewport'] = viewport
    # Per-game preferences use the same display/control allowlist. Adapter
    # scripts, URLs and all other connection settings are deliberately omitted.
    if isinstance(data.get('games'), dict):
        result['games'] = {game: _preferences(prefs) for game, prefs in data['games'].items()
                           if isinstance(game, str) and _GAME.fullmatch(game) and isinstance(prefs, dict)}
    return result


def sanitize_numeric_state(name, data):
    """Return a migration payload, or None for an unsupported/malformed file."""
    if not isinstance(data, dict):
        return None
    if name == 'preferencias.json':
        return _preferences(data)
    if name == 'calibraciones.json':
        records = data.get('records')
        if data.get('schema') != 1 or not isinstance(records, dict):
            return None
        cleaned = {}
        for key, row in records.items():
            if isinstance(key, str) and _SCOPE.fullmatch(key) and isinstance(row, dict):
                value = _numeric_tree(row)
                if value is not _OMIT:
                    cleaned[key] = value
        return {'schema': 1, 'records': cleaned}
    if name == 'perfiles.json':
        keys = {'gravity', 'wind_scale', 'power_scale', 'speed_offset', 'angle_offset', 'quantize_power', 'launch_offset'}
        return {key: _numeric_tree({field: value for field, value in row.items() if field in keys})
                for key, row in data.items() if isinstance(key, str) and _SCOPE.fullmatch(key) and isinstance(row, dict)}
    if name == 'revision-tiros.json' and data.get('schema') in (1, 2) and isinstance(data.get('records'), list):
        rows = [_numeric_tree(row) for row in data['records'][-48:] if isinstance(row, dict)]
        return {'schema': data['schema'], 'records': [row for row in rows if row is not _OMIT]}
    return None


def is_temporary_directory(directory, temp_roots=None):
    path = pathlib.Path(directory).resolve()
    if any(part.casefold().startswith(('rar$', '_mei')) for part in path.parts):
        return True
    roots = (temp_roots if temp_roots is not None else
             [tempfile.gettempdir(), *(os.environ[key] for key in ('TEMP', 'TMP', 'TMPDIR') if os.environ.get(key))])
    for root in roots:
        try:
            path.relative_to(pathlib.Path(root).resolve())
            return True
        except ValueError:
            pass
    return False


def migrate_numeric_state(sources, destination):
    """Copy sanitized allowlisted JSON once, atomically and without clobbering."""
    destination = pathlib.Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    migrated = []
    for directory in sources:
        directory = pathlib.Path(directory)
        if directory.resolve() == destination.resolve():
            continue
        for name in NUMERIC_FILES:
            target = destination / name
            source = directory / name
            if target.exists() or source.is_symlink():
                continue
            temporary = None
            try:
                if not source.is_file() or source.stat().st_size > MAX_MIGRATION_BYTES:
                    continue
                data = sanitize_numeric_state(name, json.loads(source.read_text(encoding='utf-8-sig')))
                if data is None:
                    continue
                raw = json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2).encode('utf-8')
                with tempfile.NamedTemporaryFile(dir=destination, prefix='.numeric-migration-', delete=False) as stream:
                    temporary = pathlib.Path(stream.name)
                    stream.write(raw)
                # Hard-link creation is atomic and fails if target already
                # exists, including a destination created by another process.
                os.link(temporary, target)
                migrated.append(name)
            except (OSError, ValueError, TypeError, RecursionError):
                # The original is retained for a later run or manual recovery.
                continue
            finally:
                if temporary is not None:
                    try:
                        temporary.unlink(missing_ok=True)
                    except OSError:
                        pass
    return migrated


def engine_directory(base, client_directory=None, *, local_appdata=None, temp_roots=None):
    """Resolve the launcher's numeric data directory without retaining temp paths."""
    base = pathlib.Path(base)
    candidates = [base / 'DragonLab', base.parent / 'DragonLab', base.parent.parent / 'DragonLab']
    sources = ([pathlib.Path(client_directory)] if client_directory is not None else []) + candidates + [base / 'datos', base]
    selected = None
    if client_directory is not None and not is_temporary_directory(client_directory, temp_roots):
        selected = pathlib.Path(client_directory)
    if selected is None:
        selected = next((path for path in candidates if not is_temporary_directory(path, temp_roots)
                         and (path / 'calibraciones.json').is_file()), None)
    if selected is None:
        data = base / 'datos'
        if not is_temporary_directory(data, temp_roots) and data.is_dir():
            selected = data
    if selected is None:
        local = local_appdata or os.environ.get('LOCALAPPDATA') or pathlib.Path.home() / 'AppData' / 'Local'
        selected = pathlib.Path(local) / 'DragonLab' / 'Manual'
    selected.mkdir(parents=True, exist_ok=True)
    migrate_numeric_state(sources, selected)
    return selected
