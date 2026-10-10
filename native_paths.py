"""Pure numeric reconstruction of observed server paths; no game calls."""
import math

def position(shot,seconds):
    x,y,angle,speed,ax,ay=shot['start'][:6]
    vx=speed*math.cos(math.radians(angle));vy=-speed*math.sin(math.radians(angle));start=0
    for jump in sorted(shot.get('jumps') or [],key=lambda j:j[0]):
        if jump[0]>seconds*1000:break
        start=jump[0]/1000;x,y,vx,vy=jump[1:5]
        if len(jump)>5 and jump[5] is not None:ax=jump[5]
        if len(jump)>6 and jump[6] is not None:ay=jump[6]
    dt=seconds-start;x+=vx*dt+ax*dt*dt/2;y+=vy*dt+ay*dt*dt/2
    orbit=shot.get('orbit');wave=shot.get('wave');path=shot.get('path')
    if path and len(path)>=3:
        duration=max(.001,shot.get('duration',0)/1000);count=len(path)//3;index=seconds/duration*count
        lo=min(count-1,max(0,int(index)));hi=min(count-1,lo+1);weight=index-math.floor(index)
        return tuple(path[lo*3+k]*(1-weight)+path[hi*3+k]*weight for k in (0,1))
    if orbit and len(orbit)==4:
        initial,rate,growth,radius=orbit;r=radius*min(1,seconds/max(1e-9,growth));a=math.radians(initial+rate*seconds)
        x+=r*math.cos(a);y-=r*math.sin(a)
    elif wave in range(1,8):
        # Direction from the native five millisecond backward difference.
        a=-math.atan2(vy+ay*(dt-.0025),vx+ax*(dt-.0025))
        ms=seconds*1000
        if wave in (1,2):radius=15*math.sin(ms/60);a+=math.pi/2 if wave==1 else -math.pi/2
        elif wave in (3,4):
            radius=ms/400*25 if ms<400 else 25*math.cos((ms-400)/95) if ms<2200 else 25-(ms-2200)/400*22 if ms<2600 else 3
            a+=math.pi/2 if wave==3 else -math.pi/2
        else:radius=15*math.sin(ms/60+math.radians((wave-5)*120));a+=math.pi/2
        x+=radius*math.cos(a);y-=radius*math.sin(a)
    return x,y

def trail(shot,step=.025,max_points=1000):
    duration=shot.get('duration');elapsed=shot.get('elapsed')
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (duration,elapsed)):return []
    time=max(0,min(duration,elapsed-shot.get('delay',0)))/1000
    if time<=0:return []
    count=max(1,min(max_points,math.ceil(time/step)));times={time*i/count for i in range(count+1)}
    times.update(j[0]/1000 for j in shot.get('jumps',[]) if 0<=j[0]/1000<=time)
    return [position(shot,t) for t in sorted(times)]
