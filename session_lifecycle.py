"""Acquisition identity and safe roster helpers, without account or storage data."""
import math
import secrets

def scoped_epoch(epoch,target_id):
    if not isinstance(epoch,str) or not target_id:return epoch
    prefix=str(target_id)+':'
    return epoch if epoch.startswith(prefix) else prefix+epoch


def primitive_id(value):
    """Only bounded native scalar identifiers are safe dictionary/transport keys."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            return None
        return int(value) if value == int(value) else value
    if isinstance(value, str) and value.strip() and len(value) <= 80:
        value = value.strip()
        if value.lstrip('-').isdigit():
            return int(value)
        return value
    return None


class SourceLifecycle:
    """Opaque process-local epoch; exposes no user/account identity."""
    def __init__(self, target_id='', host='', adapter=''):
        self.instance = secrets.token_hex(12)
        self.revision = 0
        self.document_epoch = 0
        self.target_id = str(target_id)
        self.host = host or ''
        self.adapter = adapter
        self.reason = 'connected'
        self.hero_id = None

    @property
    def epoch(self):
        return self.instance + ':' + str(self.revision)

    def invalidate(self, reason, document=False):
        self.revision += 1
        self.document_epoch += int(document)
        self.reason = reason
        self.hero_id = None

    def hero(self, hero_id):
        hero_id = primitive_id(hero_id)
        if self.hero_id is not None and hero_id != self.hero_id:
            self.invalidate('hero-changed')
        self.hero_id = hero_id

    def tag(self, sample):
        sample['sourceEpoch'] = self.epoch
        sample['sourceContext'] = {'targetId': self.target_id, 'host': self.host,
            'adapter': self.adapter, 'documentEpoch': self.document_epoch,
            'reason': self.reason}
        return sample


# Own data descriptors only. Map.prototype methods enforce the native Map brand
# and do not call an overridden iterator, .get(), or page-defined collection code.
ROSTER_HELPERS_JS = r'''
 const own=(o,k)=>{if(!o||(typeof o!=="object"&&typeof o!=="function"))return undefined;const d=Object.getOwnPropertyDescriptor(o,k);return d&&("value"in d)?d.value:undefined};
 const pick=(o,keys)=>{for(const k of keys){const v=own(o,k);if(v!==undefined&&v!==null)return v}return null};
 const num=v=>typeof v==="number"&&Number.isFinite(v)?v:null;
 const id=v=>typeof v==="number"&&Number.isFinite(v)?v:typeof v==="string"&&v.trim()&&v.length<=80?v.trim():null;
 const primitive=(o,keys)=>{for(const k of keys){const v=id(own(o,k));if(v!==null)return v}return null};
 const flag=v=>v===true||v===1;
 const ownPath=(o,path)=>path.split('.').reduce((v,k)=>own(v,k),o);
 const entries=o=>{
   if(!o||typeof o!=="object")return [];
   try{return Array.from(Map.prototype.entries.call(o))}catch{}
   const items=own(o,"$items");if(items){try{return Array.from(Map.prototype.entries.call(items))}catch{}}
   return Object.getOwnPropertyNames(o).filter(k=>k!=="length").map(k=>[Array.isArray(o)?null:k,own(o,k)]);
 };
 // DragonBound's n/number are roster slots, whereas userId can identify an
 // account. Never let an unrelated account ID replace an explicit native slot.
 const playerId=(p,key)=>primitive(p,["n","number","actorId","userId","id"])??id(key);
 const playerLike=p=>p&&typeof p==="object"&&["x","posX","y","posY"].some(k=>own(p,k)!==undefined);
 const roster=(o,aliases)=>{
   let best=[],score=-1;
   for(const k of aliases){const rows=entries(ownPath(o,k)),valid=rows.filter(([key,p])=>playerLike(p)&&playerId(p,key)!==null&&num(pick(p,["x","posX"]))!==null&&num(pick(p,["y","posY"]))!==null).length;
     if(valid>score||(valid===score&&rows.length>best.length)){best=rows;score=valid}}
   return best;
 };
 const heroId=o=>{const direct=primitive(o,["my_player","myPlayerNumber","my_player_number","myId"]);if(direct!==null)return direct;const p=own(o,"my_player");return p&&typeof p==="object"?playerId(p,null):null};
 const heroObject=(o,rows,hid)=>{const p=own(o,"my_player");if(p&&typeof p==="object")return p;
   const matches=rows.filter(([key,v])=>playerLike(v)&&(id(playerId(v,key))===id(hid)||flag(pick(v,["is_me","isMe","is_hero"]))));return matches.length===1?matches[0][1]:null};
'''


# Shared observer metadata lets a second, independent CDP connection validate a
# plan against the same native objects. No gameplay property is changed.
SOURCE_IDENTITY_JS = r'''function(game,heroIdValue,heroRef,invalidate=false){
 const descriptor=Object.getOwnPropertyDescriptor(window,"__dragonlabSource");
 let state=descriptor&&("value"in descriptor)?descriptor.value:null;
 if(!state||state.version!==1||!(state.objects instanceof WeakMap)){
   state={version:1,objects:new WeakMap(),serial:0,revision:0,document:performance.timeOrigin,route:location.pathname};
   Object.defineProperty(window,"__dragonlabSource",{value:state,configurable:true});
 }
 if(invalidate)state.revision++;
 // Same-document routing is observed once for every independent reader.
 // Keep only its serial in exported tokens, never URLs or query strings.
 if(state.route!==location.pathname){state.route=location.pathname;state.revision++;}
 const token=o=>{if(!o||typeof o!=="object")return 0;let v=state.objects.get(o);if(!v){v=++state.serial;state.objects.set(o,v)}return v};
 const object=token(game),heroObject=token(heroRef);
 const hero=(typeof heroIdValue==="number"&&Number.isFinite(heroIdValue))||(typeof heroIdValue==="string"&&heroIdValue.length<=80)?heroIdValue:null;
 return {sourceEpoch:[state.document,state.revision,object,heroObject,JSON.stringify(hero)].join(":"),sourceDocument:state.document,sourceObject:object,sourceHeroObject:heroObject};
}'''
