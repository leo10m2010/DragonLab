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
    vx=side*math.cos(a)*speed;vy=-math.sin(a)*speed
    zones=[]
    for w in settings.environment.get('activeWeathers',[]):
        kind=w.get('resolvedTypeId',w.get('typeId'));center=w.get('x')
        if w.get('unresolved'):kind=0
        if kind not in (0,3,4,5,7,8) or not isinstance(center,(int,float)) or not math.isfinite(center):continue
        width=25 if kind==7 else w.get('size',100)/4 if kind==8 else w.get('size',100)/2
        if not isinstance(width,(int,float)) or not math.isfinite(width) or width<=0:continue
        zones.append((kind,center-width,center+width))
    done=set();active=None;clock=0;parts=[];events=[]
    terrain=settings.environment.get('terrain') or {};floor=max(terrain.get('originY',0)+(terrain.get('height') or settings.environment.get('mapHeight',1200)),settings.hero_y,settings.target_y)+160
    # Measured battle paths use 50 ms ballistic samples, 1/60 s contact
    # detection, and 1/30 s Tornado traversal. A contact discards the rest
    # of that native tick; its velocity is retained for the next segment.
    ballistic_step=dt or .05;contact_step=1/60;tornado_step=1/30
    def append(duration,px,py,pvx,pvy,pax,pay):
        if duration>EPS:parts.append(dict(start=clock,end=clock+duration,x=px,y=py,vx=pvx,vy=pvy,ax=pax,ay=pay))
    for _ in range(12+len(zones)*6):
        remaining=settings.max_time-clock
        if remaining<=EPS:break
        if active is not None:
            i,direction,leg=active;_,lo,hi=zones[i];edge=hi if direction>0 else lo
            travel=(edge-x)/vx if abs(vx)>EPS else math.inf
            if not EPS<travel<=remaining:
                append(remaining,x,y,vx,vy,0,0);break
            ticks=math.ceil((travel-EPS)/tornado_step)
            regular=max(0,ticks-1)*tornado_step
            append(regular,x,y,vx,vy,0,0);x+=vx*regular;y+=vy*regular;clock+=regular
            used=travel-regular;duration=min(tornado_step,settings.max_time-clock)
            append(duration,x,y,(edge-x)/duration,vy*used/duration,0,0)
            x=edge;y+=vy*used;clock+=duration
            if leg<3:
                vx=-vx;active=(i,-direction,leg+1);events.append(dict(kind='bounce',time=clock,x=x,y=y))
            else:
                done.add(i);active=None;ax,ay=base;events.append(dict(kind='exit',time=clock,x=x,y=y))
            continue
        adjusted_x=vx-ax*ballistic_step/2;adjusted_y=vy-ay*ballistic_step/2
        duration=remaining;chosen=None
        floor_hit=crossing(y,adjusted_y,ay,floor,1,remaining)
        if floor_hit is not None:duration=floor_hit
        for i,(kind,lo,hi) in enumerate(zones):
            if i in done or kind not in (7,8):continue
            if lo-EPS<=x<=hi+EPS:
                hit=0;direction=1 if vx>=0 else -1;edge=x
            else:
                direction=1 if x<lo else -1;edge=lo if direction>0 else hi
                hit=crossing(x,adjusted_x,ax,edge,direction,remaining)
            if hit is not None and hit<duration:duration=hit;chosen=(i,direction,edge)
        # Damage climates only annotate crossings; they do not restart motion.
        for i,(kind,lo,hi) in enumerate(zones):
            if i in done or kind in (7,8):continue
            direction=1 if x<lo else -1;edge=lo if direction>0 else hi
            hit=0 if lo<=x<=hi else crossing(x,adjusted_x,ax,edge,direction,duration)
            if hit is not None and hit<=duration:
                ex=x+adjusted_x*hit+ax*hit**2/2;ey=y+adjusted_y*hit+ay*hit**2/2
                done.add(i);events.append(dict(kind={0:'unresolved-weather',3:'force',4:'lightning',5:'black-force'}[kind],time=clock+hit,x=ex,y=ey))
        if chosen is None:
            append(duration,x,y,adjusted_x,adjusted_y,ax,ay);break
        i,direction,edge=chosen
        regular=max(0,math.floor((duration+EPS)/ballistic_step))*ballistic_step
        px=x+adjusted_x*regular+ax*regular**2/2;py=y+adjusted_y*regular+ay*regular**2/2
        pvx=vx+ax*regular;pvy=vy+ay*regular
        used=(edge-px)/pvx if abs(pvx)>EPS else 0
        # The analytic root locates the contact tick; interpolate using that
        # tick's explicit-Euler velocity, matching measured column clipping.
        used=max(0,min(ballistic_step,used))
        append(regular,x,y,adjusted_x,adjusted_y,ax,ay);clock+=regular;x=px;y=py;vx=pvx;vy=pvy
        contact=math.ceil((used-EPS)/contact_step)*contact_step if used>EPS else 0
        if contact>EPS:
            append(contact,x,y,(edge-x)/contact,vy*used/contact,0,0);clock+=contact
        x=edge;y+=vy*used
        if zones[i][0]==7:
            vx=-vx;done.add(i);events.append(dict(kind='mirror',time=clock,x=x,y=y))
        else:
            active=(i,direction,1);ax=ay=0;events.append(dict(kind='enter',time=clock,x=x,y=y))
    return parts,events
