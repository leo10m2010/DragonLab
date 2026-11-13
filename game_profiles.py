"""Versioned, data-only game registry. Registration never enables a connector.

Only the two existing launcher games have observed hosts and adapters. Names
from the wider catalogue remain metadata until evidence supplies those fields.
"""
from copy import deepcopy

REGISTRY_VERSION = 1

GAME_PROFILES = {
    'dragonbound': {
        'schema_version': REGISTRY_VERSION, 'id': 'dragonbound', 'name': 'DragonBound',
        'url': 'https://dragonbound.net/', 'hosts': ['dragonbound.net'],
        'adapter_id': 'dragonbound', 'status': 'supported', 'physics_namespace': 'dragonbound',
        'native_power_range': [1, 400], 'catalog_source': 'core.PROFILES',
        'capabilities': {'passive_read': True, 'manual_guide': True, 'shortcut_shot': True, 'autonomous_training': True},
        'evidence': ['game_catalog.py: original launcher entry', 'adapters.py: dragonbound', 'app.py: change_mobile'],
        'limits': 'Cada carro y bala requiere su propia evidencia; soporte no significa precisión completa.',
    },
    'gunbound-world': {
        'schema_version': REGISTRY_VERSION, 'id': 'gunbound-world', 'name': 'GunBound World',
        'url': 'https://play.gunbound.world/', 'hosts': ['play.gunbound.world'],
        'adapter_id': 'gunbound-world', 'status': 'supported', 'physics_namespace': 'gunbound-world',
        'native_power_range': [1, 100], 'catalog_source': 'calibration_book.mobile_name / core.PROFILES',
        'capabilities': {'passive_read': True, 'manual_guide': True, 'shortcut_shot': True, 'autonomous_training': False},
        'evidence': ['game_catalog.py: original launcher entry', 'adapters.py: gunbound-world',
                     'gunbound_profiles.py: ARMOR_SHOT1 / ARMOR_SHOT2 / ARMOR_SS', 'app.py: change_mobile'],
        'limits': 'Física independiente. Solo Armor tiene parámetros medidos incluidos; otras modalidades quedan pendientes.',
    },
}

for _identifier, _name in (
    ('igunsfire', 'iGunsFire'), ('shotbound', 'ShotBound'), ('worldbound', 'WorldBound'),
):
    GAME_PROFILES[_identifier] = {
        'schema_version': REGISTRY_VERSION, 'id': _identifier, 'name': _name,
        'url': None, 'hosts': [], 'adapter_id': None, 'status': 'experimental',
        'physics_namespace': _identifier, 'native_power_range': None, 'catalog_source': None,
        'capabilities': {'passive_read': False, 'manual_guide': False, 'shortcut_shot': False, 'autonomous_training': False},
        'evidence': [], 'limits': 'Solo metadatos; dominio, adaptador, catálogo y física sin comprobar.',
    }

# An observed domain is provenance only; it is deliberately absent from hosts
# so the browser connector cannot treat this metadata as an allowed target.
GAME_PROFILES['worldbound']['observed_hosts']=['world-bound.net']
GAME_PROFILES['worldbound']['evidence']=['INFORME-REA-0.1.26.md: observed reference host']


def get_profile(game_id):
    """Return an isolated record; consumers cannot mutate the registry."""
    row = GAME_PROFILES.get(game_id)
    return deepcopy(row) if row else None


def registered_profiles(supported_only=False):
    return [deepcopy(row) for row in GAME_PROFILES.values()
            if not supported_only or row['status'] == 'supported']
