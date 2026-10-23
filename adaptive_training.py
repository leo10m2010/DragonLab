"""Choose measured profiles, never transfer a fit between vehicles or weapons."""
import json,statistics,uuid
from pathlib import Path
from training_evaluation import EvaluationTrial,measured_prior
from training_aim import NoAim
from calibration_book import mobile_name
from local_storage import atomic_write
from weapon_policy import enemy_for,comparable,damage_evidence,dual_decision

def experience_rows(*groups):
    """Retain policy evidence across report blocks without counting it twice."""
    rows=[];seen=set()
    for group in groups:
        for row in group:
            token=row.get('token')
            if token and token in seen:continue
            if token:seen.add(token)
            rows.append(row)
    return rows[-192:]

class AdaptiveTrial:
    def __init__(self,path,learner,max_shots=40,allow_dual=False):
        self.path=Path(path);self.learner=learner;self.max_shots=max_shots;self.allow_dual=allow_dual;self.dual_rows=[];self.recovery_rows=[];self.reserved_recoveries=[];self.weather_rows=[];self.experience_weather_rows=[];self.experience_recovery_rows=[];self.experience_reserved_recoveries=[];self.profiles={};self.selected=None;self.attempts=[];self.omitted_turns=[];self.omitted_count=0;self.finished=False;self.focus_mobile=None;self.focus_modes={};self.last_excavation_reason=None
        self.reserved_count=0
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
        focused=next((o for o in choices if mobile_name(o['name'])==self.focus_mobile),None)
        if focused:return focused
        priority={'ARMOR':0,'ICE':1,'MAGE':2}
        chosen=min(choices,key=lambda o:(priority.get(mobile_name(o['name']),3),attempted.get(mobile_name(o['name']),0),-sum(self.supported(mobile_name(o['name']),s) for s in (0,1)),o.get('id',999))) if choices else None
        if chosen:self.focus_mobile=mobile_name(chosen['name'])
        return chosen
    def probe(self,mobile,state,available):
        self.selected=None
        ready=[s for s in available if self.supported(mobile,s)]
        if not ready:raise NoAim('Sin mediciones aplicables en las modalidades disponibles',reason='missing-model')
        if mobile not in self.focus_modes:self.focus_modes[mobile]=next((mode for mode in (0,1,2) if mode in ready),ready[0])
        focus_mode=self.focus_modes[mobile]
        def tests(mode):
            t=self.profile(mobile,mode);return max(getattr(t,'directed_test_count',0),len(experience_rows(getattr(t,'experience_tests',[]),t.tests)))
        if tests(focus_mode)>=10:
            next_mode=next((mode for mode in ready if tests(mode)<10),focus_mode)
            self.focus_modes[mobile]=focus_mode=next_mode
        from battle_metrics import health
        target=enemy_for(state)
        remaining=health(target) if target else None
        def score(shot):
            trial=self.profile(mobile,shot);trial.reset_episode();record=self.learner.records.get(trial.key,{})
            model,_=self.learner.applicable_model(record,state['wind'],state['windAngle'])
            rows=comparable(experience_rows(getattr(trial,'experience_tests',[]),getattr(trial,'experience_calibration',[]),trial.tests,trial.calibration),self.learner.episode,state,target)
            damage=damage_evidence(rows)
            effective=min(damage,remaining) if remaining is not None else damage
            finishing=remaining is not None and damage>0 and damage>=remaining
            focus=0 if not trial.frozen and 0<trial.warmups<6 else 1
            return (0 if model else 1,0 if finishing else 1,shot==2 if finishing else False,-effective,0 if shot==focus_mode else 1,focus,len(trial.calibration)+len(trial.tests),len(trial.skips),shot)
        shot=min(ready,key=score);trial=self.profile(mobile,shot);self.selected=trial
        # A few directed alternate arcs provide a real spread of forces.
        # They still require a clear calculated path; no arbitrary charge.
        alternate=not trial.frozen and trial.warmups in (1,3,5)
        angle=(70 if trial.warmups in (1,5) else 40) if alternate else 55
        return {**trial.probe(),'angle':angle,'adaptive':True,'prefer_current_angle':not alternate}
    def plan(self,state,player,probe,actual=False,previous=None):
        trial=self.profile(probe['mobile'],probe['shot']);self.selected=trial
        try:result=trial.plan(state,player,probe,actual,previous)
        except NoAim as error:
            from weather_practice import weather_probe
            candidate=weather_probe(error,self.learner.records.get(trial.key,{}),experience_rows(self.experience_weather_rows,self.weather_rows),self.learner.episode,trial.key)
            if candidate:return candidate
            if actual and previous and previous.get('action')=='abrir paso':
                result=self.excavate(state,player,probe,error,actual=True)
                if result:return result
            raise
        enemy=enemy_for(state,result.get('target'))
        rows=comparable(experience_rows(getattr(trial,'experience_tests',[]),trial.tests),self.learner.episode,state,enemy)
        from battle_metrics import health
        remaining=health(enemy) if enemy else None
        dual,reason=dual_decision(rows,remaining,self.allow_dual,probe['shot'],result.get('evaluation_phase'))
        return {**result,'target_id':enemy['id'] if enemy else None,'profile':trial.key,'use_dual':dual,'item_reason':reason}
    def excavation_model(self,state,probe):
        """Check flight independently; digging does not require approved aim."""
        from autonomous_learning import error,flight_error
        from training_evaluation import current_checks,varied_checks
        from wind_models import supported as wind_supported
        trial=self.profile(probe['mobile'],probe['shot']);trial.reset_episode()
        record=self.learner.records.get(trial.key,{})
        self.last_excavation_reason='Faltan dos comprobaciones de vuelo independientes y fuerzas variadas en esta partida'
        if any(record.get(k) for k in ('multi_projectile','variable_projectiles','patterns','observed_phases')):
            self.last_excavation_reason='Esta bala tiene un patrón especial sin excavación comprobada';return None
        rows=[s for s in record.get('samples',[]) if s.get('episode')==self.learner.episode and s.get('simple')]
        candidates=[]
        if trial.frozen:
            model=trial.frozen['model']
            in_domain=wind_supported(model,state['wind'],state['windAngle']) if model.get('wind_mode')=='floor' else abs(state['wind']-trial.frozen['wind'])<=1 and (not state['wind'] or abs((state['windAngle']-trial.frozen['angle']+180)%360-180)<=5)
            excluded=set(trial.prior_training_ids)
            if trial.context_candidate:excluded.update(trial.context_candidate['training_ids'])
            validation=record.get('last_local_validation') or {}
            if validation.get('episode')==self.learner.episode:excluded.update(validation.get('training_ids',[]))
            if in_domain:candidates.append((model,excluded,True))
        if trial.context_candidate:candidates.append((trial.context_candidate['model'],trial.context_candidate['training_ids'],False))
        if trial.prior:candidates.append((trial.prior,trial.prior_training_ids,False))
        for model,training_ids,frozen in candidates:
            checks=current_checks([s for s in rows if s.get('id') not in training_ids],state['wind'],state['windAngle'],model)
            # Frozen aim already passed independent checks. A provisional
            # hypothesis must still pass different current-match launches.
            checks=checks[-3:]
            if not varied_checks(checks):continue
            if any(error(model,s)>5 or flight_error(model,s) is None or flight_error(model,s)>12 for s in checks):continue
            return {'model':model,'source':'frozen' if frozen else 'independently-checked-provisional','check_ids':[s['id'] for s in checks],'power_range':[min(s['power'] for s in checks),max(s['power'] for s in checks)]}
        return None
    def excavate(self,state,player,probe,error,actual=False):
        import math
        from autonomous_learning import occupied
        def reject(message):
            self.last_excavation_reason=message;error.excavation_reason=message;return None
        # Explicit terrain-clearing experiment, never scored as an aimed hit.
        if error.reason!='terrain-blocked' or not isinstance(error.recovery,dict):return None
        if probe['mobile'] not in ('ARMOR','ICE','MAGE','TRICO') or probe['shot'] not in (0,1):return reject('Esta modalidad no tiene excavación comprobada')
        trial=self.profile(probe['mobile'],probe['shot'])
        evidence=self.excavation_model(state,probe)
        if not evidence:return reject(self.last_excavation_reason)
        attempts=[r for r in experience_rows(self.experience_recovery_rows,self.recovery_rows,self.experience_reserved_recoveries,self.reserved_recoveries) if r.get('episode')==self.learner.episode and r.get('profile')==trial.key]
        if len(attempts)>=3:return reject('Se agotaron los tres intentos de excavación de esta modalidad en la partida')
        hero=next((p for p in state.get('players',[]) if str(p['id'])==str(state.get('heroId'))),None)
        if not hero:return reject('No se confirmó la posición del carro')
        # Recompute with the checked physics, including the actual angle on
        # final verification. Never reuse a stale or feedback-only wall plan.
        proposal=self.learner.plan(state,player,probe,actual=actual,model_override=evidence['model'])
        if proposal.get('unavailable_reason')!='terrain-blocked':return reject('No hay un choque calculado contra terreno antes de un clima desconocido')
        origin=(hero['x'],hero['y']);choices=[]
        for candidate in proposal.get('blocked_plans',[]):
            impact=candidate.get('impact');target=candidate.get('target');power=candidate.get('power');raw=candidate.get('raw_angle')
            if not isinstance(impact,(list,tuple)) or len(impact)!=2 or not isinstance(target,(list,tuple)) or len(target)!=2:continue
            if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in [*impact,*target,power,raw]):continue
            if not 1<=power<=400 or not evidence['power_range'][0]<=power<=evidence['power_range'][1]:continue
            if not player['minAngle']<=raw<=player['maxAngle'] or actual and abs(raw-player['rawAngle'])>.5:continue
            if not occupied(state.get('terrain'),*impact):continue
            if math.dist(origin,impact)<90 or abs(impact[0]-hero['x'])<70:continue
            if math.dist(impact,target)>math.dist(origin,target)-30:continue
            allies=[p for p in state.get('players',[]) if str(p['id'])!=str(hero['id']) and not p.get('dead') and (hero.get('team') is not None and p.get('team')==hero['team'] or (hero.get('team') is None or p.get('team') is None) and math.dist((p['x'],p['y']),target)>20)]
            if any(math.dist((p['x'],p['y']),impact)<90 for p in allies):continue
            same=[r for r in attempts if r.get('impact') and math.dist(r['impact'],impact)<35]
            last_open=max((i for i,r in enumerate(same) if r.get('terrain_opened') is True),default=-1)
            unresolved=same[last_open+1:]
            if any(r.get('terrain_opened') is None for r in unresolved) or sum(r.get('terrain_opened') is False for r in unresolved)>=2:continue
            choices.append(candidate)
        if not choices:return reject('No hay impacto seguro con fuerza medida; puede estar cerca, protegido o ya intentado')
        best=min(choices,key=lambda c:abs(c['raw_angle']-player['rawAngle']))
        self.last_excavation_reason=None
        return {**best,'stage':'abrir paso: experimento sobre terreno','action':'abrir paso','evaluation_phase':'recovery','profile':trial.key,'use_dual':False,'approximate':True,'expected_terrain_impact':best['impact'],'excavation_evidence':{k:v for k,v in evidence.items() if k!='model'}}
    def reserve_action(self,plan,key):
        """Reserve a dig before charging, including releases never confirmed."""
        if plan.get('action')!='abrir paso':return
        profile=plan.get('profile');impact=plan.get('expected_terrain_impact')
        if profile not in self.profiles or plan.get('evaluation_phase')!='recovery' or not isinstance(impact,(list,tuple)) or len(impact)!=2:
            raise RuntimeError('La excavación no tiene un plan comprobado para reservar')
        rows=experience_rows(self.experience_recovery_rows,self.recovery_rows,self.experience_reserved_recoveries,self.reserved_recoveries)
        attempts=[r for r in rows if r.get('episode')==self.learner.episode and r.get('profile')==profile]
        if len(attempts)>=3:raise RuntimeError('Se agotaron los intentos de excavación en esta partida')
        token=uuid.uuid4().hex
        self.reserved_recoveries.append({'token':token,'episode':self.learner.episode,'profile':profile,'turn':key[-1],'native_key':list(key),'impact':list(impact),'confirmed':False,'terrain_opened':None})
        self.reserved_count+=1;self.reserved_recoveries=self.reserved_recoveries[-192:]
        plan['recovery_reservation']=token
        self.save()
    def record(self,release,state):
        key=(release.get('learner') or {}).get('profile')
        if key not in self.profiles:raise ValueError('El tiro no identifica su perfil adaptativo')
        if (release.get('learner') or {}).get('action')=='medir clima':
            token=uuid.uuid4().hex;self.weather_rows.append({'token':token,'episode':self.learner.episode,'profile':key,'weather_kinds':release['learner']['weather_kinds'],'power':release.get('power'),'health_window_known':False,'enemy_health_drop':None})
        elif (release.get('learner') or {}).get('action')=='abrir paso':
            token=release['learner'].get('recovery_reservation') or uuid.uuid4().hex
            reservation=next((r for r in self.reserved_recoveries if r['token']==token),None)
            if reservation:reservation['confirmed']=True
            self.recovery_rows.append({'token':token,'episode':self.learner.episode,'turn':release.get('turn_serial'),'profile':key,'action':'abrir paso','power':release.get('power'),'impact':release['learner'].get('impact'),'evidence':release['learner'].get('excavation_evidence'),'health_window_known':False,'enemy_health_drop':None,'terrain_opened':None})
        elif release.get('item'):
            token=uuid.uuid4().hex;self.dual_rows.append({'token':token,'profile':key,'item':release['item'],'power':release.get('power'),'shot':release.get('shot'),'episode':self.learner.episode,'target_id':release['learner'].get('target_id'),'wind':release.get('wind'),'wind_angle':release.get('windAngle'),'decision':release['learner'].get('item_reason'),'health_window_known':False,'enemy_health_drop':None})
        else:token=self.profiles[key].record(release,state)
        self.save();return token
    def health_result(self,result):
        for row in self.reserved_recoveries:
            if row['token']==result['token']:row['terrain_opened']=result.get('terrain_opened')
        for row in self.weather_rows:
            if row['token']==result['token']:row.update(health_window_known=result['known'],enemy_health_drop=result['enemy_health_drop'])
        for row in self.recovery_rows:
            if row['token']==result['token']:row.update(health_window_known=result['known'],enemy_health_drop=result['enemy_health_drop'],terrain_opened=result.get('terrain_opened'))
        for row in self.dual_rows:
            if row['token']==result['token']:row.update(health_window_known=result['known'],enemy_health_drop=result['enemy_health_drop'])
        for trial in self.profiles.values():trial.health_result(result)
        self.save()
    def skip(self,reason):
        if self.selected:self.selected.skip(reason)
        self.attempts.append({'code':getattr(reason,'reason','unclassified'),'reason':str(reason),'excavation_reason':getattr(reason,'excavation_reason',None),'profile':self.selected.key if self.selected else None,'turn':getattr(reason,'turn_serial',None)});self.attempts=self.attempts[-128:];self.save()
    def turn_skipped(self,key):
        if key not in self.omitted_turns:self.omitted_turns.append(key);self.omitted_count+=1
        self.omitted_turns=self.omitted_turns[-128:];self.save()
    def turn_recovered(self,key):
        if key in self.omitted_turns:self.omitted_turns.remove(key);self.omitted_count=max(0,self.omitted_count-1)
    def done(self):return sum(len(t.calibration)+len(t.tests) for t in self.profiles.values())+len(self.dual_rows)+len(self.recovery_rows)+len(self.weather_rows)>=self.max_shots
    def summary(self):
        reports={k:t.summary() for k,t in self.profiles.items()};tests=[row for t in self.profiles.values() for row in t.tests];errors=[row['path_error_px'] for row in tests if row['path_error_px'] is not None]
        known=[row for row in tests if row['health_window_known']];damaged=[row for row in known if (row['enemy_health_drop'] or 0)>0]
        reasons={code:sum(a['code']==code for a in self.attempts) for code in sorted({a['code'] for a in self.attempts})}
        return {'status':'complete' if self.finished else 'running','approved':False,'adaptive':True,'focus_mobile':self.focus_mobile,'focus_modes':dict(self.focus_modes),'calibration_shots':sum(len(t.calibration) for t in self.profiles.values()),'directed_test_shots':len(tests),'skipped_turns':self.omitted_count,'rejected_modes':len(self.attempts),'skip_reasons':reasons,'near_target_shots':sum(e<=20 for e in errors),'near_target_rate':round(sum(e<=20 for e in errors)*100/len(errors),1) if errors else None,'median_path_error_px':round(statistics.median(errors),2) if errors else None,'known_health_windows':len(known),'health_drop_windows':len(damaged),'exploration_budget':sum(t.calibration_limit for t in self.profiles.values()),'minimum_directed_tests':10,'prediction_improvement_proven':False,'full_autonomy_proven':False,'profiles':reports,'weather_practice_shots':len(self.weather_rows),'dual_uses':len(self.dual_rows),'terrain_attempts':len(self.recovery_rows),'terrain_reserved_attempts':self.reserved_count,'terrain_openings_observed':sum(r['terrain_opened'] is True for r in self.recovery_rows)}
    def save(self):atomic_write(self.path,json.dumps({'schema':1,'summary':self.summary(),'attempts':self.attempts,'dual_observations':self.dual_rows,'terrain_recovery':self.recovery_rows,'reserved_terrain_actions':self.reserved_recoveries,'weather_practice':self.weather_rows},allow_nan=False).encode())
    def finish(self):
        self.finished=True
        for trial in self.profiles.values():trial.finish()
        self.save()
