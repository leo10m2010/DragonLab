"""GunBound-only column traversal. Kept separate from DragonBound's native model.

Static columns: Mirror reverses once, Tornado traverses three legs. Real
server paths are needed to validate boundary timing and moving columns.
"""
import math

def segments(settings,power):
    from core import acceleration,launch
    from physics_extensions import crossing,at,EPS
    x,y,side=launch(settings);a=math.radians(settings.angle+settings.angle_offset)
    speed=max(0,power*settings.power_scale+settings.speed_offset)
    if settings.quantize_power:speed=math.trunc(speed)
    ax,ay=acceleration(settings);base=(ax,ay);dt=settings.environment.get('nativeEulerStep',0)
    vx=side*math.cos(a)*speed-ax*dt/2;vy=-math.sin(a)*speed-ay*dt/2
    zones=[]
    for w in settings.environment.get('activeWeathers',[]):
        kind=w.get('resolvedTypeId',w.get('typeId'));center=w.get('x')
        if kind not in (3,4,5,7,8) or not isinstance(center,(int,float)) or not math.isfinite(center):continue
        width=25 if kind==7 else w.get('size',100)/4 if kind==8 else w.get('size',100)/2
        if not isinstance(width,(int,float)) or not math.isfinite(width) or width<=0:continue
        zones.append((kind,center-width,center+width))
    done=set();active=None;clock=0;parts=[];events=[]
    terrain=settings.environment.get('terrain') or {};floor=max(terrain.get('originY',0)+(terrain.get('height') or settings.environment.get('mapHeight',1200)),settings.hero_y,settings.target_y)+160
    for _ in range(8+len(zones)*5):
        remaining=settings.max_time-clock
        if remaining<=EPS:break
        duration=remaining;event='end';chosen=None
        floor_hit=crossing(y,vy,ay,floor,1,remaining)
        if floor_hit is not None:duration=floor_hit
        if active is not None:
            i,direction,leg=active;_,lo,hi=zones[i];edge=hi if direction>0 else lo
            hit=(edge-x)/vx if abs(vx)>EPS else None
            if hit is not None and EPS<hit<duration:duration=hit;event='turn';chosen=i
        else:
            for i,(kind,lo,hi) in enumerate(zones):
                if i in done:continue
                if lo+EPS<x<hi-EPS:
                    hit=0;direction=1 if vx>=0 else -1
                else:
                    direction=1 if x<=lo+EPS else -1
                    hit=crossing(x,vx,ax,lo if direction>0 else hi,direction,remaining)
                if hit is not None and hit<duration:duration=hit;event='column';chosen=(i,direction)
        part=dict(start=clock,end=clock+duration,x=x,y=y,vx=vx,vy=vy,ax=ax,ay=ay)
        if duration>EPS:
            parts.append(part);x,y=at(part,clock+duration);vx+=ax*duration;vy+=ay*duration;clock+=duration
        if event=='end':break
        if event=='column':
            i,direction=chosen;kind=zones[i][0]
            if kind==7:
                vx=-vx;done.add(i);events.append(dict(kind='mirror',time=clock,x=x,y=y))
            elif kind==8:
                active=(i,direction,1);ax=ay=0;events.append(dict(kind='enter',time=clock,x=x,y=y))
            else:
                done.add(i);events.append(dict(kind={3:'force',4:'lightning',5:'black-force'}[kind],time=clock,x=x,y=y))
        elif event=='turn':
            i,direction,leg=active
            if leg<3:
                vx=-vx;active=(i,-direction,leg+1);events.append(dict(kind='bounce',time=clock,x=x,y=y))
            else:
                done.add(i);active=None;ax,ay=base;events.append(dict(kind='exit',time=clock,x=x,y=y))
    return parts,events
