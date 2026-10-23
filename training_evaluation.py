"""Finite Armor-1 experiment. Calibration and held-out aimed shots are separate."""
import copy,json,math,statistics,time,uuid
from training_aim import NoAim
from shot_attribution import attributed_start,identity
from native_paths import position
from local_storage import atomic_write

def prediction_error(model,shot,power,wind,wind_angle):
    if not model:return None
    try:
        x,y,a,_,_,_=shot['start'];duration=shot['duration']/1000;k=model.get('wind_scale')
        if k is None and wind:return None
        k=k or 0;r=math.radians(wind_angle);angle=math.radians(a);speed=model['scale']*power+model['offset']
        ax=k*wind*math.cos(r);ay=model['gravity']-k*wind*math.sin(r);values=[]
        for i in range(1,17):
            t=duration*i/16;predicted=(x+speed*math.cos(angle)*t+.5*ax*t*t,y-speed*math.sin(angle)*t+.5*ay*t*t)
            values.append(math.dist(predicted,position(shot,t)))
        return statistics.mean(values)
    except (KeyError,TypeError,ValueError):return None

def measured_prior(samples):
    # Robust hypothesis from real launch measurements. Not a validated model.
    rows=[s for s in samples if all(isinstance(s.get(k),(int,float)) and math.isfinite(s[k]) for k in ('power','speed','ax','ay','wind','wind_angle')) and s['power']>0]
    if len(rows)<6 or len({s['power'] for s in rows})<3:return None
    slopes=[(b['speed']-a['speed'])/(b['power']-a['power']) for i,a in enumerate(rows) for b in rows[i+1:] if abs(b['power']-a['power'])>=80]
    if not slopes:return None
    scale=statistics.median(slopes);offset=statistics.median(s['speed']-scale*s['power'] for s in rows)
    couplings=[s['ax']/(s['wind']*math.cos(math.radians(s['wind_angle']))) for s in rows if abs(s['wind']*math.cos(math.radians(s['wind_angle'])))>=2]
    k=statistics.median(couplings) if couplings else None
    gravity=statistics.median(s['ay']+(k or 0)*s['wind']*math.sin(math.radians(s['wind_angle'])) for s in rows)
    if not .01<scale<30 or not 0<gravity<10000 or k is not None and not 0<=k<100:return None
    return {'scale':scale,'offset':offset,'gravity':gravity,'wind_scale':k,'source':'measured-prior-unvalidated'}

def current_checks(rows,wind,angle):
    return [s for s in rows if abs(s['wind']-wind)<=1 and (not wind or abs((s['wind_angle']-angle+180)%360-180)<=5)]

def varied_checks(rows):
    return len(rows)>=2 and len({s['power'] for s in rows})>=2 and max(s['power'] for s in rows)-min(s['power'] for s in rows)>=40

def adapted_hypothesis(prior,rows):
    if not prior or len(rows)<2:return None
    rows=rows[-2:]
    if any(abs((s['wind_angle']-rows[0]['wind_angle']+180)%360-180)>5 for s in rows):return None
    offset=prior['offset'];scale=statistics.median((s['speed']-offset)/s['power'] for s in rows)
    couplings=[s['ax']/(s['wind']*math.cos(math.radians(s['wind_angle']))) for s in rows if abs(s['wind']*math.cos(math.radians(s['wind_angle'])))>=2]
    k=statistics.median(couplings) if couplings else prior['wind_scale']
    if k is None and any(s['wind'] for s in rows):return None
    gravity=statistics.median(s['ay']+(k or 0)*s['wind']*math.sin(math.radians(s['wind_angle'])) for s in rows)
    if not .01<scale<30 or not 0<gravity<10000 or k is not None and not 0<=k<100:return None
    return {'scale':scale,'offset':offset,'gravity':gravity,'wind_scale':k,'source':'local-adaptation-needs-future-checks'}

class EvaluationTrial:
    def __init__(self,path,learner,max_shots=20,mobile='ARMOR',shot=0):
        self.mobile=mobile;self.shot=shot;self.key=f'dragonbound:{mobile}:{shot}'
        self.path=path;self.learner=learner;self.max_shots=max_shots;self.calibration_limit=min(12,max_shots//2);self.calibration=[];self.tests=[];self.skips=[];self.frozen=None;self.episode=None;self.context_candidate=None;self.warmups=0;self.phase='calibration';self.finished=False
        self.baseline=copy.deepcopy(learner.records.get(self.key,{}).get('model'));self.prior=measured_prior(learner.records.get(self.key,{}).get('samples',[]));self.prior_training_ids={s['id'] for s in learner.records.get(self.key,{}).get('samples',[]) if 'id' in s}
    def reset_episode(self):
        if self.episode!=self.learner.episode:self.episode=self.learner.episode;self.warmups=0;self.frozen=None;self.context_candidate=None;self.phase='calibration'
    def probe(self):
        return {'mobile':self.mobile,'shot':self.shot,'power':(100,360,220,300,120,180)[len(self.calibration)%6],'angle':55,'purpose':f'prueba controlada {self.mobile} tiro {self.shot}','wind_band':0}
    def plan(self,state,player,probe,actual=False,previous=None):
        if self.mobile=='RANDOMIZER':raise NoAim('Camaleón: proyectil no identificado antes del tiro',reason='variable-projectile')
        self.reset_episode()
        if not self.frozen and self.warmups>=1:
            model,source=self.learner.applicable_model(self.learner.records.get(self.key,{}),state['wind'],state['windAngle'])
            if not model and self.prior:
                from autonomous_learning import error,flight_error
                checks=[s for s in self.learner.records.get(self.key,{}).get('samples',[]) if s.get('episode')==self.episode and s['id'] not in self.prior_training_ids and s.get('simple')]
                checks=current_checks(checks,state['wind'],state['windAngle'])
                if len(checks)>=3 and varied_checks(checks[-3:]) and all(error(self.prior,s)<=5 and flight_error(self.prior,s) is not None and flight_error(self.prior,s)<=12 for s in checks[-3:]):model=self.prior
                if not model and self.context_candidate:
                    future=[s for s in checks if s['id'] not in self.context_candidate['training_ids']]
                    candidate=self.context_candidate['model']
                    if len(future)>=2:
                        valid=all(error(candidate,s)<=5 and flight_error(candidate,s) is not None and flight_error(candidate,s)<=12 for s in future)
                        if not valid:self.context_candidate=None
                        elif varied_checks(future):model=candidate
                if not model and not self.context_candidate and len(checks)>=2:
                    candidate=adapted_hypothesis(self.prior,checks[-2:])
                    if candidate:self.context_candidate={'model':candidate,'training_ids':{s['id'] for s in checks}}
            if model:self.frozen={'model':copy.deepcopy(model),'wind':state['wind'],'angle':state['windAngle']};self.phase='evaluation'
        if self.frozen:
            if abs(state['wind']-self.frozen['wind'])>1 or state['wind'] and abs((state['windAngle']-self.frozen['angle']+180)%360-180)>5:raise NoAim('El viento queda fuera del ajuste congelado; no se envía una carga de prueba',reason='wind-out-of-domain')
            plan=self.learner.plan(state,player,probe,actual,previous,model_override=self.frozen['model'])
            if plan.get('stage')!='evaluación con modelo congelado':raise NoAim('Sin trayectoria comprobada para esta geometría o clima; no se dispara',reposition=plan.get('reposition_allowed',False),reason=plan.get('unavailable_reason','trajectory-unavailable'),recovery=plan)
            return {**plan,'evaluation_phase':'evaluation'}
        if len(self.calibration)>=self.calibration_limit:raise NoAim('Calibración agotada sin modelo aplicable; hace falta controlar las condiciones',reason='calibration-budget')
        if self.prior:
            hypothesis=self.context_candidate['model'] if self.context_candidate else self.prior
            feedback=None
            if probe.get('adaptive'):
                from shot_feedback import corrected_hypothesis
                feedback=corrected_hypothesis(hypothesis,self.learner.records.get(self.key,{}),self.learner.episode,state,player)
            proposal=self.learner.plan(state,player,probe,actual,previous,model_override=feedback or hypothesis)
            if feedback:proposal={**proposal,'feedback_case':feedback.get('feedback_id')}
            if proposal.get('stage')=='evaluación con modelo congelado':return {**proposal,'stage':'calibración dirigida provisional','evaluation_phase':'calibration'}
            raise NoAim('Sin ángulo o recorrido libre para la hipótesis actual',reposition=proposal.get('reposition_allowed',False),reason=proposal.get('unavailable_reason','trajectory-unavailable'),recovery=proposal)
        raise NoAim('Sin hipótesis de trayectoria aplicable; no se envía una fuerza arbitraria',reason='missing-model')
    def record(self,release,state):
        phase=(release.get('learner') or {}).get('evaluation_phase')
        token=uuid.uuid4().hex;row={'token':token,'phase':phase,'decision':(release.get('learner') or {}).get('stage'),'power':release.get('power'),'turn':release.get('turn_serial'),'wind':release.get('wind'),'wind_angle':release.get('windAngle'),'path_error_px':None,'health_window_known':False,'enemy_health_drop':None,'candidate_prediction_error_px':None,'baseline_prediction_error_px':None}
        from weapon_policy import enemy_for
        target=enemy_for(state,(release.get('learner') or {}).get('target'))
        row.update(episode=self.learner.episode,target_id=target['id'] if target else None)
        if phase in ('calibration','evaluation'):
            target=(release.get('learner') or {}).get('target');distances=[];owned=[]
            for shot in state.get('shots',[]):
                if identity(shot) in release.get('baseline',[]) or not (attributed_start(state,shot,release) or {}).get('learnable'):continue
                owned.append(shot)
                try:distances.extend(math.dist(position(shot,shot['duration']/1000*i/100),target) for i in range(101))
                except (TypeError,ValueError,KeyError):continue
            row['path_error_px']=min(distances,default=None)
            if phase=='evaluation' and len(owned)==1:
                row['candidate_prediction_error_px']=prediction_error(self.frozen['model'] if self.frozen else None,owned[0],release['power'],release['wind'],release['windAngle'])
                row['baseline_prediction_error_px']=prediction_error(self.baseline,owned[0],release['power'],release['wind'],release['windAngle'])
            if phase=='evaluation':self.tests.append(row)
            else:self.calibration.append(row);self.warmups+=1
        else:raise ValueError('El tiro no indica si es calibración o evaluación')
        self.save();return token
    def health_result(self,result):
        row=next((r for r in self.tests+self.calibration if r['token']==result['token']),None)
        if row:row['health_window_known']=result['known'];row['enemy_health_drop']=result['enemy_health_drop'];self.save()
    def skip(self,reason):self.skips.append({'reason':str(reason),'code':getattr(reason,'reason','unclassified'),'at':time.time()});self.skips=self.skips[-12:];self.save()
    def done(self):return len(self.tests)>=12 or len(self.calibration)+len(self.tests)>=self.max_shots or len(self.skips)>=6
    def summary(self):
        errors=[r['path_error_px'] for r in self.tests if r['path_error_px'] is not None];known=[r for r in self.tests if r['health_window_known']];damaged=[r for r in known if (r['enemy_health_drop'] or 0)>0]
        near=sum(e<=20 for e in errors);enough=len(errors)>=10
        approved=self.finished and enough and near/len(errors)>=.8 and statistics.median(errors)<=15 and len(known)>=5 and len(damaged)/len(known)>=.6
        paired=[r for r in self.tests if r.get('candidate_prediction_error_px') is not None and r.get('baseline_prediction_error_px') is not None]
        previous=statistics.mean(r['baseline_prediction_error_px'] for r in paired) if paired else None
        current=statistics.mean(r['candidate_prediction_error_px'] for r in paired) if paired else None
        improvement=round((previous-current)*100/previous,1) if previous is not None and previous>1e-6 else None
        status='approved' if approved else 'insufficient-data' if self.finished and not enough else 'failed' if self.finished else 'running'
        return {'status':status,'approved':approved,'calibration_shots':len(self.calibration),'directed_test_shots':len(self.tests),'skipped_turns':len(self.skips),'skip_reasons':{code:sum(s.get('code')==code for s in self.skips) for code in sorted({s.get('code','unclassified') for s in self.skips})},'near_target_shots':near,'near_target_rate':round(near*100/len(errors),1) if errors else None,'median_path_error_px':round(statistics.median(errors),2) if errors else None,'known_health_windows':len(known),'health_drop_windows':len(damaged),'exploration_budget':self.calibration_limit,'minimum_directed_tests':10,'paired_prediction_tests':len(paired),'prediction_error_improvement_percent':improvement,'prediction_improvement_proven':len(paired)>=10 and improvement is not None and improvement>=10,'full_autonomy_proven':False}
    def save(self):atomic_write(self.path,json.dumps({'schema':1,'summary':self.summary(),'calibration':self.calibration,'tests':self.tests,'skips':self.skips},allow_nan=False).encode())
    def finish(self):self.finished=True;self.save()
