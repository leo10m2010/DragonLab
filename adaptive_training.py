"""Choose measured profiles, never transfer a fit between vehicles or weapons."""
import json,statistics,uuid
from pathlib import Path
from training_evaluation import EvaluationTrial,measured_prior
from training_aim import NoAim
from calibration_book import mobile_name
from local_storage import atomic_write
from weapon_policy import enemy_for,comparable,damage_evidence,dual_decision

class AdaptiveTrial:
    def __init__(self,path,learner,max_shots=40,allow_dual=False):
        self.path=Path(path);self.learner=learner;self.max_shots=max_shots;self.allow_dual=allow_dual;self.dual_rows=[];self.recovery_rows=[];self.profiles={};self.selected=None;self.attempts=[];self.omitted_turns=[];self.finished=False
    def profile(self,mobile,shot):
        key=f'dragonbound:{mobile}:{shot}'
        if key not in self.profiles:self.profiles[key]=EvaluationTrial(self.path.parent/f'evaluacion-{mobile}-{shot}.json',self.learner,self.max_shots,mobile,shot)
        return self.profiles[key]
    def supported(self,mobile,shot):
        if mobile=='RANDOMIZER':return False
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
        target=enemy_for(state)
        remaining=health(target) if target else None
        def score(shot):
            trial=self.profile(mobile,shot);record=self.learner.records.get(trial.key,{})
            model,_=self.learner.applicable_model(record,state['wind'],state['windAngle'])
            rows=comparable(trial.tests,self.learner.episode,state,target)
            damage=damage_evidence(rows)
            effective=min(damage,remaining) if remaining is not None else damage
            finishing=remaining is not None and damage>0 and damage>=remaining
            return (0 if model else 1,0 if finishing else 1,shot==2 if finishing else False,-effective,len(trial.calibration)+len(trial.tests),len(trial.skips),shot)
        shot=min(ready,key=score);trial=self.profile(mobile,shot);self.selected=trial
        return {**trial.probe(),'adaptive':True,'prefer_current_angle':True}
    def plan(self,state,player,probe,actual=False,previous=None):
        trial=self.profile(probe['mobile'],probe['shot']);self.selected=trial
        try:result=trial.plan(state,player,probe,actual,previous)
        except NoAim as error:
            if actual and previous and previous.get('action')=='abrir paso':
                result=self.excavate(state,player,probe,error)
                if result:return result
            raise
        enemy=enemy_for(state,result.get('target'))
        rows=comparable(trial.tests,self.learner.episode,state,enemy)
        from battle_metrics import health
        remaining=health(enemy) if enemy else None
        dual,reason=dual_decision(rows,remaining,self.allow_dual,probe['shot'],result.get('evaluation_phase'))
        return {**result,'target_id':enemy['id'] if enemy else None,'profile':trial.key,'use_dual':dual,'item_reason':reason}
    def excavate(self,state,player,probe,error):
        import math
        # Explicit terrain-clearing experiment, never scored as an aimed hit.
        if probe['mobile'] not in ('ARMOR','ICE','MAGE','TRICO') or probe['shot']!=0:return None
        trial=self.profile(probe['mobile'],probe['shot'])
        if not trial.frozen or error.reason!='terrain-blocked' or not isinstance(error.recovery,dict):return None
        hero=next((p for p in state.get('players',[]) if str(p['id'])==str(state.get('heroId'))),None)
        if not hero:return None
        origin=(hero['x'],hero['y']);choices=[]
        for candidate in error.recovery.get('blocked_plans',[]):
            impact=candidate['impact'];target=candidate['target']
            if math.dist(origin,impact)<90 or abs(impact[0]-hero['x'])<70:continue
            if math.dist(impact,target)>math.dist(origin,target)-30:continue
            allies=[p for p in state.get('players',[]) if str(p['id'])!=str(hero['id']) and hero.get('team') is not None and p.get('team')==hero['team'] and not p.get('dead')]
            if any(math.dist((p['x'],p['y']),impact)<90 for p in allies):continue
            choices.append(candidate)
        if not choices:return None
        best=min(choices,key=lambda c:abs(c['raw_angle']-player['rawAngle']))
        return {**best,'stage':'abrir paso: experimento sobre terreno','action':'abrir paso','evaluation_phase':'recovery','profile':trial.key,'use_dual':False,'approximate':True,'expected_terrain_impact':best['impact']}
    def record(self,release,state):
        key=(release.get('learner') or {}).get('profile')
        if key not in self.profiles:raise ValueError('El tiro no identifica su perfil adaptativo')
        if (release.get('learner') or {}).get('action')=='abrir paso':
            token=uuid.uuid4().hex;self.recovery_rows.append({'token':token,'profile':key,'action':'abrir paso','power':release.get('power'),'impact':release['learner'].get('impact'),'health_window_known':False,'enemy_health_drop':None,'terrain_opened':None})
        elif release.get('item'):
            token=uuid.uuid4().hex;self.dual_rows.append({'token':token,'profile':key,'item':release['item'],'power':release.get('power'),'shot':release.get('shot'),'episode':self.learner.episode,'target_id':release['learner'].get('target_id'),'wind':release.get('wind'),'wind_angle':release.get('windAngle'),'decision':release['learner'].get('item_reason'),'health_window_known':False,'enemy_health_drop':None})
        else:token=self.profiles[key].record(release,state)
        self.save();return token
    def health_result(self,result):
        for row in self.recovery_rows:
            if row['token']==result['token']:row.update(health_window_known=result['known'],enemy_health_drop=result['enemy_health_drop'],terrain_opened=result.get('terrain_opened'))
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
    def done(self):return sum(len(t.calibration)+len(t.tests) for t in self.profiles.values())+len(self.dual_rows)+len(self.recovery_rows)>=self.max_shots
    def summary(self):
        reports={k:t.summary() for k,t in self.profiles.items()};tests=[row for t in self.profiles.values() for row in t.tests];errors=[row['path_error_px'] for row in tests if row['path_error_px'] is not None]
        known=[row for row in tests if row['health_window_known']];damaged=[row for row in known if (row['enemy_health_drop'] or 0)>0]
        reasons={code:sum(a['code']==code for a in self.attempts) for code in sorted({a['code'] for a in self.attempts})}
        return {'status':'complete' if self.finished else 'running','approved':False,'adaptive':True,'calibration_shots':sum(len(t.calibration) for t in self.profiles.values()),'directed_test_shots':len(tests),'skipped_turns':len(self.omitted_turns),'rejected_modes':len(self.attempts),'skip_reasons':reasons,'near_target_shots':sum(e<=20 for e in errors),'near_target_rate':round(sum(e<=20 for e in errors)*100/len(errors),1) if errors else None,'median_path_error_px':round(statistics.median(errors),2) if errors else None,'known_health_windows':len(known),'health_drop_windows':len(damaged),'exploration_budget':sum(t.calibration_limit for t in self.profiles.values()),'minimum_directed_tests':10,'prediction_improvement_proven':False,'full_autonomy_proven':False,'profiles':reports,'dual_uses':len(self.dual_rows),'terrain_attempts':len(self.recovery_rows),'terrain_openings_observed':sum(r['terrain_opened'] is True for r in self.recovery_rows)}
    def save(self):atomic_write(self.path,json.dumps({'schema':1,'summary':self.summary(),'attempts':self.attempts,'dual_observations':self.dual_rows,'terrain_recovery':self.recovery_rows},allow_nan=False).encode())
    def finish(self):
        self.finished=True
        for trial in self.profiles.values():trial.finish()
        self.save()
