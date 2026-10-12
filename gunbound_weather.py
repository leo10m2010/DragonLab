"""Normalize observed GunBound weather names and separate spatial zones."""
import math
KINDS={'force':3,'lightning':4,'black-force':5,'mirror':7,'tornado':8}
NAMES={'force':'Fuerza','lightning':'Rayo','black-force':'Negro','mirror':'Mirror','tornado':'Tornado','thor':'Thor','sun':'Sol','moon':'Luna','eclipse':'Eclipse','no-items':'Sin ítems','wind-change':'Cambio de viento','none':'Normal','normal':'Normal'}
def canonical(value):
    if not isinstance(value,str):return ''
    kind=value.strip().lower()
    return {'blackforce':'black-force','black_force':'black-force'}.get(kind,kind)
def weather_name(value):
    kind=canonical(value);return NAMES.get(kind,kind or 'Normal')
def normalize_weather(current,zones):
    records=[]
    for zone in zones if isinstance(zones,list) else []:
        if not isinstance(zone,dict):continue
        kind=canonical(zone.get('kind'));x=zone.get('x');size=zone.get('size')
        if not kind or not isinstance(x,(int,float)) or not math.isfinite(x):continue
        record={'kind':kind,'name':weather_name(kind),'x':x}
        if kind in KINDS:record['typeId']=KINDS[kind];record['resolvedTypeId']=KINDS[kind]
        if isinstance(size,(int,float)) and math.isfinite(size) and size>0:record['size']=size
        records.append(record)
    kind=canonical(current)
    if kind and not any(r['kind']==kind for r in records):records.append({'kind':kind,'name':weather_name(kind),'global':True})
    return records

# Observed Colyseus state sends weatherZones as JSON text, not an ArraySchema.
WEATHER_ZONES_JS=r"""((value)=>{try{
 if(typeof value==='string'){if(value.length>16384)return [];value=JSON.parse(value)}
 const list=Array.isArray(value)?value:Array.from(value?.$items?.values?.()??value?.values?.()??[]);
 return list.slice(0,32).filter(w=>w&&typeof w.kind==='string'&&Number.isFinite(w.x)).map(w=>({kind:w.kind,x:w.x,size:w.size}));
}catch{return []}})(s?.weatherZones)"""
