GAMES={
    'DragonBound':{'id':'dragonbound','url':'https://dragonbound.net/','host':'dragonbound.net'},
    'GunBound World':{'id':'gunbound-world','url':'https://play.gunbound.world/','host':'play.gunbound.world'},
}
def game_by_id(clone):
    return next((g for g in GAMES.values() if g['id']==clone),None)
