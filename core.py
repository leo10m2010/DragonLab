"""Independent ballistic model. Screen/world axes: x right, y down.

Baseline profile measurements come from the inspected shipped UI; algorithms
and application code are original. Special projectiles need calibration.
"""
from dataclasses import dataclass, asdict, field, replace
import math

# name: gravity, wind coupling, speed per UI power, muzzle angle, muzzle radius
PROFILES = {
 'ARMOR':(73.5,.74,1,52,33), 'ICE':(62.5,.625,1,58,50),
 'ADUKA':(65.5,.695,1,130,40), 'LIGHTNING':(65,.72,1,58,44),
 'BIGFOOT':(90,.74,1,58,50), 'JD':(62.5,.625,1,68,45),
 'ASATE':(76,.765,1,40,30), 'RANDOM':(81,.827,1,51,51),
 'KNIGHT':(65.5,.695,1,130,40), 'FOX':(61,.61,1,30,44),
 'DRAGON':(90,.74,1,58,50), 'NAK':(82,.867,1,130,40),
 'TRICO':(392.6577767735536,3.575285390397936,863/400,51,51),
 'MAGE':(71.5,.78,1,51,51),
 'TURTLE':(390.5073375,3.9316385,922/400,51,51),
 'BOOMER':(244,244/50,808/400,70,30),
 'ELECTRICO':(79,.87,1,51,51), 'GRUB':(61,.65,1,54,33),
 'DRAGON2':(93.5,.78,1,58,50), 'RAON':(81,.827,1,51,51),
 'RANDOMIZER':(73.5,.74,1,52,33), 'FROG':(54.3,.67,1,52,33),
 'KALSIDDON':(70,.67,1,58,50),
}
REVERSE={'ADUKA','NAK'}
SPECIAL={'BOOMER','NAK','TRICO','TURTLE','KNIGHT','RANDOMIZER','FROG','KALSIDDON','LIGHTNING'}

@dataclass
class Settings:
    mobile:str='ARMOR'
    angle:float=46
    wind:float=0
    wind_angle:float=90   # mathematical: east 0, north 90
    hero_x:float=130
    hero_y:float=430
    target_x:float=670
    target_y:float=420
    gravity:float=73.5
    wind_scale:float=.74
    power_scale:float=1
    body_angle:float=0
    muzzle:bool=True
    look:int=1
    weather:str='Normal'
    selected_shot:int=0
    environment:dict=field(default_factory=dict)
    max_time:float=20
    max_power:float=400
    speed_offset:float=0
    angle_offset:float=0
    quantize_power:bool=False
    launch_offset:object=None
    is_backshot:bool=False

def finite_settings(s):
    if s.mobile not in PROFILES:raise ValueError('Vehículo desconocido')
    for key,value in asdict(s).items():
        if isinstance(value,(int,float)) and not math.isfinite(value):
            raise ValueError('Los valores deben ser números finitos')
    if not -180<s.angle<180:raise ValueError('El ángulo debe estar entre -179 y 179 grados')
    if not 0<=s.wind<=100:raise ValueError('Viento fuera de rango (0–100)')
    if s.gravity<=0 or s.power_scale<=0 or s.wind_scale<0:
        raise ValueError('Calibración inválida')
    if not 0<s.max_time<=60 or not 0<s.max_power<=2000 or s.selected_shot not in (0,1,2):
        raise ValueError('Límites de simulación o disparo inválidos')
    if not isinstance(s.environment,dict):raise ValueError('El entorno debe ser un objeto JSON')
    def finite_tree(value):
        if isinstance(value,float) and not math.isfinite(value):raise ValueError('El entorno contiene números no finitos')
        if isinstance(value,dict):
            for v in value.values():finite_tree(v)
        elif isinstance(value,(list,tuple)):
            for v in value:finite_tree(v)
    finite_tree(s.environment)
    terrain=s.environment.get('terrain')
    if terrain is not None and not isinstance(terrain,dict):raise ValueError('El terreno debe contener heights, polygon o una máscara')
    if not isinstance(s.environment.get('activeWeathers',[]),list):raise ValueError('activeWeathers debe ser una lista')
    return s

def launch(s):
    side=1 if s.look else -1
    # For normal aiming, follow target side. NAK/ADUKA face opposite.
    x,y=s.hero_x,s.hero_y
    if s.launch_offset is not None:
        if len(s.launch_offset)!=2 or not all(math.isfinite(v) for v in s.launch_offset):
            raise ValueError('Desplazamiento del cañón inválido')
        return x+s.launch_offset[0],y+s.launch_offset[1],side
    if s.muzzle:
        _,_,_,offset,radius=PROFILES[s.mobile]
        if s.mobile=='ICE' and s.selected_shot:offset,radius=40,40
        face=side if s.mobile not in REVERSE else -side
        a=math.radians((offset if face>0 else 180-offset)-s.body_angle)
        x+=round(math.cos(a)*radius);y-=round(math.sin(a)*radius)
    return x,y,side

def acceleration(s):
    observed=s.environment.get('observedAcceleration')
    if isinstance(observed,(list,tuple)) and len(observed)==2 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in observed):return tuple(observed)
    a=math.radians(s.wind_angle)
    return math.cos(a)*s.wind*s.wind_scale,s.gravity-math.sin(a)*s.wind*s.wind_scale

def point(s,power,t):
    x,y,side=launch(s);a=math.radians(s.angle+s.angle_offset);ax,ay=acceleration(s)
    speed=max(0,power*s.power_scale+s.speed_offset)
    if s.quantize_power:speed=math.trunc(speed)
    return x+side*speed*math.cos(a)*t+.5*ax*t*t,y-speed*math.sin(a)*t+.5*ay*t*t

def solve(s):
    finite_settings(s)
    if s.environment or s.selected_shot or s.quantize_power or s.speed_offset or s.angle_offset or s.is_backshot or s.mobile in ('BIGFOOT','DRAGON'):
        from physics_extensions import solve_extended
        return solve_extended(s)
    x,y,side=launch(s); dx=s.target_x-x;dy=s.target_y-y
    a=math.radians(s.angle);ax,ay=acceleration(s)
    c=math.cos(a);sn=math.sin(a)
    # Eliminate speed with the launch-direction cross product.
    numerator=2*(dy*c+side*dx*sn)
    denominator=ay*c+side*ax*sn
    if abs(denominator)<1e-9 or numerator/denominator<=0:
        return {'reachable':False,'reason':'Este ángulo y viento no alcanzan el objetivo.'}
    t=math.sqrt(numerator/denominator)
    vx=dx/t-.5*ax*t;vy=dy/t-.5*ay*t
    speed=side*vx*c-vy*sn
    exact=speed/s.power_scale
    if not 0<exact<=s.max_power or t>s.max_time:
        return {'reachable':False,'reason':'Se necesita otra orientación o un ángulo distinto.','required':round(exact,2)}
    power=round(exact)
    end=point(s,power,t)
    error=math.hypot(end[0]-s.target_x,end[1]-s.target_y)
    count=max(25,min(400,int(t/.02)))
    path=[point(s,power,t*i/count) for i in range(count+1)]
    approximate=s.mobile in SPECIAL or s.weather!='Normal'
    return {'reachable':True,'power':power,'exact_power':round(exact,3),
            'time':round(t,3),'error':round(error,2),'path':path,
            'distance':round(math.hypot(dx,dy)),
            'quality':'Modelo base: validar disparo especial/clima' if approximate else 'Modelo balístico base',
            'approximate':approximate,'end':end}

def calibrated_profile(s,observed_power):
    if not 1<=observed_power<=400:raise ValueError('Potencia observada: 1–400')
    r=solve(s)
    if not r['reachable']:raise ValueError('No se puede calibrar esta geometría')
    return s.power_scale*r['exact_power']/observed_power

def optimize_angles(s,minimum=5,maximum=85,step=1):
    """Find viable angles, preserving current orientation and profile."""
    if step<=0 or not 0<minimum<=maximum<180:raise ValueError('Rango de ángulos inválido')
    solutions=[];angle=float(minimum)
    while angle<=maximum+1e-9:
        result=solve(replace(s,angle=angle))
        if result.get('reachable'):solutions.append({'angle':angle,**result})
        angle+=step
    return sorted(solutions,key=lambda r:(r['error'],r['power'],r['time']))

def fit_calibration(samples):
    from physics_extensions import fit_calibration as fit
    return fit(samples)
