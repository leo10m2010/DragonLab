"""Classify measured column crossings without declaring incomplete shots valid."""
import math

def crossing_evidence(case):
    points=case.get('path',[])
    if not isinstance(points,list) or len(points)<3:return []
    points=[p for p in points if isinstance(p,dict) and all(isinstance(p.get(k),(int,float)) and math.isfinite(p[k]) for k in ('x','y','t'))]
    evidence=[]
    for zone in case.get('zones',[]):
        kind=zone.get('kind');center=zone.get('x');size=zone.get('size')
        if kind not in ('mirror','tornado') or not isinstance(center,(int,float)):continue
        width=25 if kind=='mirror' else size/4 if isinstance(size,(int,float)) and size>0 else None
        if width is None:continue
        lo,hi=center-width,center+width
        crossed=any(min(a['x'],b['x'])<=hi and max(a['x'],b['x'])>=lo for a,b in zip(points,points[1:]))
        reversals=[]
        # Ignore isolated impact coordinates inserted between regular samples:
        # a valid measured reversal needs two intervals of similar duration.
        for a,b,c in zip(points,points[1:],points[2:]):
            dt1=b['t']-a['t'];dt2=c['t']-b['t']
            if dt1<=0 or dt2<=0:continue
            regular=.99<=dt1/dt2<=1.01
            index=points.index(b)
            next_dt=points[index+2]['t']-c['t'] if index+2<len(points) else 0
            clipped=min(abs(b['x']-lo),abs(b['x']-hi))<.5 and next_dt>0 and .99<=dt2/next_dt<=1.01
            if not regular and not clipped:continue
            vx1=(b['x']-a['x'])/dt1;vx2=(c['x']-b['x'])/dt2
            if vx1*vx2<0 and min(abs(vx1),abs(vx2))>10 and lo-5<=b['x']<=hi+5:
                reversals.append({'time':b['t'],'x':b['x'],'from':1 if vx1>0 else -1,'to':1 if vx2>0 else -1})
        direction=next((1 if b['x']>a['x'] else -1 for a,b in zip(points,points[1:]) if abs(b['x']-a['x'])>.1),0)
        exited=points[-1]['x']>hi if direction>0 else points[-1]['x']<lo
        complete=bool(reversals) if kind=='mirror' else len(reversals)>=2 and exited
        evidence.append({'kind':kind,'center':center,'bounds':[lo,hi],'crossed':crossed,'reversals':reversals,'status':'complete-crossing' if complete else 'partial-crossing' if crossed else 'no-crossing'})
    return evidence
