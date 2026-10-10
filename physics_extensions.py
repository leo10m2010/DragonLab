"""Own piecewise trajectory engine, informed by inspected shipped UI behavior.

Coordinates are pixels/world units, y downward. Weather records accept typeId
7 (Mirror), 8 (Tornado) or name/type strings. The physics profile must match
the particular server. Unsupported projectile behaviors remain flagged.
"""
import math
import statistics
from dataclasses import replace

EPS=1e-7

def roots(a,b,c):
    if abs(a)<EPS:return [] if abs(b)<EPS else [-c/b]
    d=b*b-4*a*c
    if d<0:return []
    q=math.sqrt(d)
    return [(-b-q)/(2*a),(-b+q)/(2*a)]

def at(seg,t):
    dt=max(0,min(t,seg['end'])-seg['start'])
    return (seg['x']+seg['vx']*dt+seg['ax']*dt*dt/2,
            seg['y']+seg['vy']*dt+seg['ay']*dt*dt/2)

def crossing(x,v,a,bound,direction,horizon):
    candidates=[t for t in roots(a/2,v,x-bound) if EPS<t<=horizon and (v+a*t)*direction>EPS]
    return min(candidates) if candidates else None

def weather_records(environment):
    tornado=[];mirror=[]
    for w in environment.get('activeWeathers',environment.get('weathers',[])):
        if not isinstance(w,dict):continue
        kind=w.get('resolvedTypeId') if w.get('resolvedTypeId') is not None else w.get('typeId',w.get('type',w.get('name')))
        if kind in (8,'Tornado','TORNADO','tornado'):
            if w.get('size',0)>0:tornado.append((float(w['x']),max(1,float(w['size'])*.25)))
        elif kind in (7,'Mirror','MIRROR','mirror'):mirror.append(float(w['x']))
    return sorted(set(tornado)),sorted(set(mirror))

def segments(s,power):
    from core import acceleration,launch
    x,y,side=launch(s);origin=x
    angle=math.radians(s.angle+s.angle_offset)
    speed=max(0,power*s.power_scale+s.speed_offset)
    if s.quantize_power:speed=math.trunc(speed)
    vx=side*math.cos(angle)*speed;vy=-math.sin(angle)*speed
    ax,ay=acceleration(s);base=(ax,ay)
    if s.mobile=='NAK' and s.selected_shot!=1 and s.is_backshot and s.angle<=70 and not s.environment.get('activeWeathers'):
        # Observed NAK special: inverted vertical acceleration and doubled horizontal speed.
        ay*=-8;vx*=-2;base=(ax,ay)
    tornado,mirrors=weather_records(s.environment)
    entered=set();active=None;clock=0;result=[];events=[]
    for _ in range(max(8,len(tornado)*5+4,64 if mirrors else 0)):
        remaining=s.max_time-clock
        if remaining<=EPS:break
        dt=remaining;event='end';entry=None
        if active is None:
            for i,(center,width) in enumerate(tornado):
                if i in entered:continue
                lo,hi=center-width,center+width
                if lo-EPS<=x<=hi+EPS:
                    velocity=vx if abs(vx)>EPS else ax
                    if abs(velocity)<=EPS:continue
                    hit=0;side_enter=-1 if velocity>0 else 1
                else:
                    side_enter=-1 if x<lo else 1
                    hit=crossing(x,vx,ax,lo if x<lo else hi,-side_enter,remaining)
                if hit is not None:
                    quant=max(0,math.ceil((clock+hit-EPS)/.025)*.025-clock)
                    if quant<=dt:dt,event,entry=quant,'enter',(i,side_enter,0)
        else:
            i,entry_side,phase=active;center,width=tornado[i]
            edge=center+(-entry_side if phase in (0,2) else entry_side)*width
            hit=(edge-x)/vx if abs(vx)>EPS else math.inf
            if EPS<hit<=remaining:
                quant=max(0,math.ceil((clock+hit-EPS)/.025)*.025-clock)
                if quant<=dt:dt,event=quant,'bounce'
        top=s.environment.get('originY',0)-600
        for center in mirrors:
            faces=[(center,1),(center,-1)] if abs(origin-center)<25 else [(center-25,1),(center+25,-1)]
            for edge,direction in faces:
                hit=crossing(x,vx,ax,edge,direction,remaining)
                if hit is not None and y+vy*hit+ay*hit*hit/2>=top and hit<dt:
                    dt,event=hit,'mirror'
            # A high arc can enter the vertical strip through its upper edge.
            # Solving only its horizontal faces missed these descending shots.
            if abs(origin-center)>=25 and y<top:
                hit=crossing(y,vy,ay,top,1,remaining)
                if hit is not None and abs(x+vx*hit+ax*hit*hit/2-center)<25 and hit<dt:dt,event=hit,'mirror'
        floor=s.environment.get('originY',0)+max(600,s.environment.get('mapHeight',1200))+160
        hit=crossing(y,vy,ay,floor,1,remaining)
        if hit is not None and hit<=dt:dt,event=hit,'end'
        segment={'start':clock,'end':clock+dt,'x':x,'y':y,'vx':vx,'vy':vy,'ax':ax,'ay':ay}
        if dt>EPS:
            result.append(segment)
            x,y=at(segment,clock+dt);vx+=ax*dt;vy+=ay*dt;clock+=dt
        if event=='end':break
        events.append({'kind':event,'time':clock,'x':x,'y':y})
        if event=='mirror':vx=-vx
        elif event=='enter':active=entry;ax=ay=0
        elif event=='bounce':
            i,entry_side,phase=active
            if phase<2:
                # Observed UI rewinds one 25 ms native tick before each reversal.
                x,y=at(segment,segment['start']+max(0,dt-.025))
                vx=-(segment['vx']+segment['ax']*max(0,dt-.025))
                vy=segment['vy']+segment['ay']*max(0,dt-.025)
                active=(i,entry_side,phase+1)
            else:entered.add(i);active=None;ax,ay=base
    return result,events

def solid(terrain,x,y):
    """Bitmap/RLE, height profile, or explicit polygon collision."""
    x-=terrain.get('originX',0);y-=terrain.get('originY',0)
    heights=terrain.get('heights')
    if heights is not None:
        index=int(round(x))
        return 0<=index<len(heights) and heights[index] is not None and y>=heights[index]
    polygon=terrain.get('polygon')
    if polygon:
        inside=False;previous=polygon[-1]
        for current in polygon:
            x1,y1=previous;x2,y2=current
            if (y1>y)!=(y2>y) and x<(x2-x1)*(y-y1)/(y2-y1)+x1:inside=not inside
            previous=current
        return inside
    ix,iy=int(round(x)),int(round(y));width=terrain.get('width',0);height=terrain.get('height',0)
    if not 0<=ix<width or not 0<=iy<height:return False
    bitmap=terrain.get('pixels',terrain.get('mask'))
    if bitmap is not None:return bool(bitmap[iy*width+ix])
    rows=terrain.get('rows',terrain.get('runs'))
    if rows is None:return False
    row=rows[iy]
    return any(lo<=ix<hi for lo,hi in zip(row[::2],row[1::2]))

def variants(s):
    mode=s.selected_shot;face=1 if s.look else -1
    custom=s.environment.get('projectiles')
    if custom:return custom
    def offsets(pairs,scale):return [{'angleOffset':face*a,'powerOffset':p/(scale/400)} for a,p in pairs]
    if s.mobile in ('BIGFOOT','DRAGON'):
        scale=843 if s.mobile=='BIGFOOT' else 880
        if mode==0:return offsets([(-2,0),(2,10),(-4,-10),(4,20)],scale)
        if mode==1:return offsets([(5,19),(0,3),(-5,-13)],scale)*2
        return offsets([(0,0),(4,10),(-2,-10),(6,20),(1,0),(3,10),(-1,-10),(5,20)],scale)
    if s.mobile=='GRUB' and mode==1:return offsets([(4,10),(2,5),(0,0),(-2,-5)],1012)
    if s.mobile=='MAGE' and mode==1:return [{'wave':1},{'wave':2}]
    if s.mobile=='TURTLE' and mode==1:return [{'wave':3},{'wave':4}]
    if s.mobile=='TRICO' and mode==1:return [{},{'orbit':[0 if face>0 else 90,-150*face,.5,45]},{'orbit':[180 if face>0 else 270,-150*face,.5,45]}]
    if s.mobile=='BOOMER' and mode==1:return [{}]*4
    return [{}]

def swept_impact(terrain,a,b):
    """Check the intervening pixels so a fast bullet cannot skip a thin ledge."""
    ox=terrain.get('originX',0);oy=terrain.get('originY',0)
    height=terrain.get('height');width=terrain.get('width')
    if height and (max(a[1],b[1])<oy-.5 or min(a[1],b[1])>=oy+height+.5):return None
    if width and (max(a[0],b[0])<ox-.5 or min(a[0],b[0])>=ox+width+.5):return None
    distance=max(abs(b[0]-a[0]),abs(b[1]-a[1]));count=max(1,math.ceil(distance))
    for i in range(1,count+1):
        weight=i/count;p=tuple(a[k]+(b[k]-a[k])*weight for k in range(3))
        if solid(terrain,p[0],p[1]):return p
    return None

def trajectory(s,power,step=.025):
    paths=[];events=[];impacts=[]
    terrain=s.environment.get('terrain')
    for variant in variants(s):
        local=replace(s,angle_offset=s.angle_offset+variant.get('angleOffset',0),
                      speed_offset=s.speed_offset+variant.get('speedOffset',0))
        parts,interactions=segments(local,power*variant.get('speedRatio',1)+variant.get('powerOffset',0))
        events.extend(interactions);path=[];impact=None
        for seg in parts:
            duration=seg['end']-seg['start'];count=max(1,math.ceil(duration/step))
            for index in range(count+1):
                time=seg['start']+duration*index/count;x,y=at(seg,time)
                orbit=variant.get('orbit')
                if orbit:
                    initial,rate,growth,radius=orbit
                    r=radius*min(1,time/max(EPS,growth));angle=math.radians(initial+rate*time)
                    x+=r*math.cos(angle);y-=r*math.sin(angle)
                wave=variant.get('wave')
                if wave:
                    elapsed=time-seg['start'];vx=seg['vx']+seg['ax']*(elapsed-.0025);vy=seg['vy']+seg['ay']*(elapsed-.0025)
                    normal=-math.atan2(vy,vx)+(math.pi/2 if wave in (1,3) else -math.pi/2)
                    ms=time*1000
                    if wave in (1,2):radius=15*math.sin(ms/60)
                    else:radius=ms/400*25 if ms<400 else 25*math.cos((ms-400)/95) if ms<2200 else 25-(ms-2200)/400*22 if ms<2600 else 3
                    x+=radius*math.cos(normal);y-=radius*math.sin(normal)
                point=(x,y,time)
                if terrain and time>0:
                    impact=swept_impact(terrain,path[-1],point) if path else point if solid(terrain,x,y) else None
                    if impact:path.append(impact);break
                path.append(point)
            if impact:break
        paths.append(path);impacts.append(impact)
    return {'projectile_paths':paths,'interactions':events,'impacts':impacts}

def closest(path,x,y):
    best=(math.inf,None)
    for a,b in zip(path,path[1:]):
        dx=b[0]-a[0];dy=b[1]-a[1];length=dx*dx+dy*dy
        weight=0 if length==0 else max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/length))
        p=tuple(a[i]+weight*(b[i]-a[i]) for i in range(3))
        distance=math.hypot(p[0]-x,p[1]-y)
        if distance<best[0]:best=(distance,p)
    return best

def solve_extended(s):
    # Coarse-to-fine integer power search; weather interactions are discontinuous,
    # so refine all coarse local minima instead of assuming a single minimum.
    cache={};cluster=s.mobile=='TRICO' and s.selected_shot==1
    tolerance=s.environment.get('hitTolerance',35)
    def score(candidates):
        distances=[c[0] for c in candidates]
        # Reward several predicted contacts, then tighten the whole group.
        # The single closest orb previously dominated every Trico choice.
        if cluster:return (-sum(d<=tolerance for d in distances),sum(min(d,1000) for d in distances)/len(distances),max(distances))
        return (min(distances),)
    def evaluate(power):
        if power not in cache:
            traces=trajectory(s,power,step=.04)
            candidates=[closest(p,s.target_x,s.target_y) for p in traces['projectile_paths']]
            best=min(candidates,key=lambda c:c[0]) if candidates else (math.inf,None)
            cache[power]=(score(candidates) if candidates else (math.inf,),best)
        return cache[power][0]
    tornado,mirror=weather_records(s.environment)
    # Weather creates narrow discontinuities; evaluate every available integer.
    grid=list(range(1,int(s.max_power)+1,1 if tornado or mirror or cluster else 8));grid.append(int(s.max_power))
    for p in grid:evaluate(p)
    minima=[p for i,p in enumerate(grid) if (i==0 or evaluate(p)<=evaluate(grid[i-1])) and (i==len(grid)-1 or evaluate(p)<=evaluate(grid[i+1]))]
    for p in minima:
        for fine in range(max(1,p-8),min(int(s.max_power),p+8)+1):evaluate(fine)
    power=min(cache,key=evaluate);error,end=cache[power][1]
    if cluster:
        refined=[]
        for candidate in sorted(cache,key=evaluate)[:12]:
            fine=trajectory(s,candidate,step=.02)
            contacts=[closest(p,s.target_x,s.target_y) for p in fine['projectile_paths']]
            if contacts:refined.append((score(contacts),candidate))
        if refined:power=min(refined)[1]
    traces=trajectory(s,power,step=.02)
    candidates=[closest(p,s.target_x,s.target_y) for p in traces['projectile_paths']]
    if candidates:error,end=min(candidates,key=lambda c:c[0])
    if end is None:return {'reachable':False,'reason':'No hay trayectoria válida.'}
    from core import launch,SPECIAL
    origin=launch(s)
    approximate=s.mobile in SPECIAL or s.selected_shot>0 or bool(s.environment.get('terrain')) or bool(traces['interactions']) or s.weather!='Normal'
    reachable=error<=s.environment.get('hitTolerance',35)
    return {'reachable':reachable,'reason':'' if reachable else 'Ninguna potencia alcanza el objetivo con este ángulo.',
            'power':power,'exact_power':float(power),'required':power,'time':round(end[2],3),'error':round(error,2),
            'path':[(p[0],p[1]) for p in traces['projectile_paths'][0]],
            'projectile_paths':[[(p[0],p[1]) for p in path] for path in traces['projectile_paths']],
            'interactions':traces['interactions'],'impacts':traces['impacts'],
            'cluster_hits':sum(c[0]<=tolerance for c in candidates),'projectile_count':len(candidates),
            'distance':round(math.hypot(s.target_x-origin[0],s.target_y-origin[1])),
            'quality':'Modelo de proyectil/clima: requiere validación con el servidor' if approximate else 'Modelo por segmentos',
            'approximate':approximate,'end':end[:2]}

def fit_calibration(samples):
    """Fit speed scale/offset, gravity and wind coupling from measured starts.

    Each sample: power,vx,vy,ax,ay,wind,wind_angle. Uses least squares, median
    gravity, and reports residuals; caller decides whether to apply the fit.
    """
    valid=[]
    for sample in samples:
        if all(isinstance(sample.get(k),(int,float)) and math.isfinite(sample[k]) for k in ('power','vx','vy','ax','ay','wind','wind_angle')) and sample['power']>0:valid.append(sample)
    if len(valid)<2:raise ValueError('Se necesitan al menos dos muestras válidas')
    powers=[p['power'] for p in valid];speeds=[math.hypot(p['vx'],p['vy']) for p in valid]
    meanx=statistics.mean(powers);meany=statistics.mean(speeds)
    denominator=sum((x-meanx)**2 for x in powers)
    if denominator<EPS:raise ValueError('Las muestras necesitan potencias distintas')
    scale=sum((x-meanx)*(y-meany) for x,y in zip(powers,speeds))/denominator;offset=meany-scale*meanx
    wx=[math.cos(math.radians(p['wind_angle']))*p['wind'] for p in valid]
    denom=sum(x*x for x in wx)
    coupling=sum(x*p['ax'] for x,p in zip(wx,valid))/denom if denom>EPS else None
    gravities=[p['ay']+(math.sin(math.radians(p['wind_angle']))*p['wind']*coupling if coupling is not None else 0) for p in valid]
    gravity=statistics.median(gravities)
    if scale<=0 or gravity<=0 or (coupling is not None and coupling<0):raise ValueError('Las muestras no producen una calibración física válida')
    residual=math.sqrt(statistics.mean((y-(scale*x+offset))**2 for x,y in zip(powers,speeds)))
    return {'power_scale':scale,'speed_offset':offset,'gravity':gravity,'wind_scale':coupling,
            'sample_count':len(valid),'speed_rmse':residual,'gravity_spread':max(gravities)-min(gravities),
            'wind_observed':coupling is not None}
