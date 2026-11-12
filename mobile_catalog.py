"""Display catalog; preserve the game's existing 0..22 numeric mapping.

Being listed is recognition, not proof of calibrated physics. RANDOM is a
selection option; special/seasonal aliases need native evidence before mapping.
"""
from core import PROFILES
MANUAL_MOBILES=tuple(name for name in PROFILES if name!='RANDOM')

def display_name(name):
    return {'JD':'J.D.','ASATE':'A.Sate','RAON':'Raon Launcher','KALSIDDON':'Kalsiddon','RANDOMIZER':'Randomizer','DRAGON2':'Dragon 2 · especial'}.get(name,name.title())
