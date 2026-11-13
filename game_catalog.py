"""Legacy launcher projection of the versioned, supported game registry."""
from game_profiles import registered_profiles

GAMES = {row['name']: {'id': row['id'], 'url': row['url'], 'host': row['hosts'][0]}
         for row in registered_profiles(supported_only=True)}
def game_by_id(clone):
    return next((g for g in GAMES.values() if g['id']==clone),None)
