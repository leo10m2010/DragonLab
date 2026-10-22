"""Choose measured profiles, never transfer a fit between vehicles or weapons."""
import json,statistics,uuid
from pathlib import Path
from training_evaluation import EvaluationTrial,measured_prior
from training_aim import NoAim
from calibration_book import mobile_name
from local_storage import atomic_write

class AdaptiveTrial:
    def __init__(self,path,learner,max_shots=40,allow_dual=False):
        self.path=Path(path);self.learner=learner;self.max_shots=max_shots;self.allow_dual=allow_dual;self.dual_rows=[];self.profiles={};self.selected=None;self.attempts=[];self.omitted_turns=[];self.finished=False
    def profile(self,mobile,shot):
        key=f'dragonbound:{mobile}:{shot}'
        if key not in self.profiles:self.profiles[key]=EvaluationTrial(self.path.parent/f'evaluacion-{mobile}-{shot}.json',self.learner,self.max_shots,mobile,shot)
        return self.profiles[key]
    def supported(self,mobile,shot):
        record=self.learner.records.get(f'dragonbound:{mobile}:{shot}',{})
        return not record.get('multi_projectile') and bool(record.get('model') or measured_prior(record.get('samples',[])))
    def choose_mobile(self,options,attempted):
        choices=[o for o in options if mobile_name(o.get('name')) and o.get('name')!='Random' and any(self.supported(mobile_name(o['name']),s) for s in range(3))]
        return min(choices,key=lambda o:(attempted.get(mobile_name(o['name']),0),-sum(self.supported(mobile_name(o['name']),s) for s in range(3)),o.get('id',999))) if choices else None
    def probe(self,mobile,state,available):
        self.selected=None
        ready=[s for s in available if self.supported(mobile,s)]
        if not ready:raise NoAim('Sin mediciones aplicables en las modalidades disponibles',reason='missing-model')
        from battle_metrics import health
        hero=next((p for p in state.get('players',[]) if str(p.get('id'))==str(state.get('heroId'))),None)
        targets=[p for p in state.get('players',[]) if hero and str(p.get('id'))!=str(hero['id']) and not p.get('dead') and (hero.get('team') is None or p.get('team')!=hero['team'])]
        target=min(targets,key=lambda p:(p['x']-hero['x'])**2+(p['y']-hero['y'])**2,default=None) if hero else None
        remaining=health(target) if target else None
        def score(shot):
            trial=self.profile(mobile,shot);record=self.learner.records.get(trial.key,{})
            model,_=self.learner.applicable_model(record,state['wind'],state['windAngle'])
            known=[r['enemy_health_drop'] for r in trial.tests if r.get('health_window_known') and r.get('enemy_health_drop') is not None]
            damage=statistics.mean(known) if len(known)>=3 else 0
            effective=min(damage,remaining) if remaining is not None else damage
            reserve_ss=1 if shot==2 and remaining is not None and damage>=remaining and damage>0 else 0
            return (0 if model else 1,-effective,reserve_ss,len(trial.calibration)+len(trial.tests),len(trial.skips),shot)
        shot=min(ready,key=score);trial=self.profile(mobile,shot);self.selected=trial
        return {**trial.probe(),'adaptive':True,'prefer_current_angle':True}
    def plan(self,state,player,probe,actual=False,previous=None):
        trial=self.profile(probe['mobile'],probe['shot']);self.selected=trial
        result=trial.plan(state,player,probe,actual,previous)
        target=result.get('target');enemy=min((p for p in state.get('players',[]) if str(p.get('id'))!=str(state.get('heroId')) and not p.get('dead')),key=lambda p:(p['x']-target[0])**2+(p['y']-target[1])**2,default=None) if target else None
        known=[r for r in trial.tests if r.get('health_window_known') and (r.get('enemy_health_drop') or 0)>0];errors=[r['path_error_px'] for r in trial.tests if r.get('path_error_px') is not None]
        from battle_metrics import health
        remaining=health(enemy) if enemy else None
        dual=bool(self.allow_dual and probe['shot'] in (0,1) and result.get('evaluation_phase')=='evaluation' and len(errors)>=5 and sum(e<=20 for e in errors)/len(errors)>=.8 and len(known)>=3 and remaining is not None and remaining>statistics.median(r['enemy_health_drop'] for r in known))
        return {**result,'profile':trial.key,'use_dual':dual}
    def record(self,release,state):
        key=(release.get('learner') or {}).get('profile')
        if key not in self.profiles:raise ValueError('El tiro no identifica su perfil adaptativo')
        if release.get('item'):
            token=uuid.uuid4().hex;self.dual_rows.append({'token':token,'profile':key,'item':release['item'],'power':release.get('power'),'health_window_known':False,'enemy_health_drop':None})
        else:token=self.profiles[key].record(release,state)
        self.save();return token
    def health_result(self,result):
        for row in self.dual_rows:
            if row['token']==result['token']:row.update(health_window_known=result['known'],enemy_health_drop=result['enemy_health_drop'])
        for trial in self.profiles.values():trial.health_result(result)
        self.save()
    def skip(self,reason):
        if self.selected:self.selected.skip(reason)
        self.attempts.append({'code':getattr(reason,'reason','unclassified'),'reason':str(reason),'profile':self.selected.key if self.selected else None});self.attempts=self.attempts[-128:];self.save()
    def turn_skipped(self,key):
        if key not in self.omitted_turns:self.omitted_turns.append(key)
        self.omitted_turns=self.omitted_turns[-128:];self.save()
    def done(self):return sum(len(t.calibration)+len(t.tests) for t in self.profiles.values())+len(self.dual_rows)>=self.max_shots
    def summary(self):
        reports={k:t.summary() for k,t in self.profiles.items()};tests=[row for t in self.profiles.values() for row in t.tests];errors=[row['path_error_px'] for row in tests if row['path_error_px'] is not None]
        known=[row for row in tests if row['health_window_known']];damaged=[row for row in known if (row['enemy_health_drop'] or 0)>0]
        reasons={code:sum(a['code']==code for a in self.attempts) for code in sorted({a['code'] for a in self.attempts})}
        return {'status':'complete' if self.finished else 'running','approved':False,'adaptive':True,'calibration_shots':sum(len(t.calibration) for t in self.profiles.values()),'directed_test_shots':len(tests),'skipped_turns':len(self.omitted_turns),'rejected_modes':len(self.attempts),'skip_reasons':reasons,'near_target_shots':sum(e<=20 for e in errors),'near_target_rate':round(sum(e<=20 for e in errors)*100/len(errors),1) if errors else None,'median_path_error_px':round(statistics.median(errors),2) if errors else None,'known_health_windows':len(known),'health_drop_windows':len(damaged),'exploration_budget':sum(t.calibration_limit for t in self.profiles.values()),'minimum_directed_tests':10,'prediction_improvement_proven':False,'full_autonomy_proven':False,'profiles':reports,'dual_uses':len(self.dual_rows)}
    def save(self):atomic_write(self.path,json.dumps({'schema':1,'summary':self.summary(),'attempts':self.attempts,'dual_observations':self.dual_rows},allow_nan=False).encode())
    def finish(self):
        self.finished=True
        for trial in self.profiles.values():trial.finish()
        self.save()
