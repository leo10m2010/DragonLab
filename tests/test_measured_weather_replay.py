import json,math,unittest
from pathlib import Path
from core import Settings
from physics_extensions import segments,at
from gunbound_weather import normalize_weather

def replay(case):
    points=case['path'];dt=.05;a,b,c=points[:3]
    vx=(b['x']-a['x'])/dt;vy=(b['y']-a['y'])/dt
    ax=(c['x']-2*b['x']+a['x'])/dt**2;ay=(c['y']-2*b['y']+a['y'])/dt**2
    settings=Settings(hero_x=a['x'],hero_y=a['y'],muzzle=False,look=int(vx>0),angle=math.degrees(math.atan2(-vy,abs(vx))),power_scale=math.hypot(vx,vy)/case['power'],gravity=ay,max_time=5,environment={'weatherModel':'gunbound-world','nativeEulerStep':dt,'observedAcceleration':[ax,ay],'activeWeathers':normalize_weather(case['weather'],case['zones'])})
    parts,events=segments(settings,case['power']);errors=[];other=[]
    for q in points:
        t=q['t'];part=next((p for p in parts if p['start']-1e-7<=t<=p['end']+1e-7),None)
        if not part:continue
        phase=max((e for e in events if e['time']<=t+1e-7),key=lambda e:e['time'],default=None)
        phase_start=phase['time'] if phase else 0
        step=1/30 if phase and phase['kind'] in ('enter','bounce') else .05
        regular=abs((t-phase_start)/step-round((t-phase_start)/step))<1e-5
        predicted=at(part,t);error=math.dist(predicted,(q['x'],q['y']))
        (errors if regular else other).append(error)
    return {'weather':case['weather'],'regular_points':len(errors),'regular_max_error':max(errors),'other_points':len(other),'other_max_error':max(other,default=0),'events':events,'scope':'Measured launch/acceleration isolates column timing; terrain impact points excluded from accuracy claim'}

class MeasuredWeatherReplayTests(unittest.TestCase):
    def test_real_mirror_and_full_tornado_match_native_samples(self):
        cases=json.loads((Path(__file__).parent/'fixtures/gunbound_weather_crossings.json').read_text())
        self.assertEqual({c['weather'] for c in cases},{'mirror','tornado'})
        for case in cases:
            with self.subTest(weather=case['weather']):
                report=replay(case)
                self.assertGreater(report['regular_points'],45)
                self.assertLess(report['regular_max_error'],1e-7)
                if case['weather']=='tornado':self.assertEqual([e['kind'] for e in report['events']],['enter','bounce','bounce','exit'])
                else:self.assertEqual([e['kind'] for e in report['events']],['mirror'])
