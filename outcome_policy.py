"""Empirical combat preferences among already checked trajectories only.

This module never supplies a force, validates physics, or sends game input.
Unknown health windows and displaced launch origins cannot train it.
"""
import hashlib,json,math,statistics
from pathlib import Path
from calibration_book import mobile_name
from local_storage import atomic_write

MAX_CASES=512
MAX_PENDING=64
MIN_EXACT=3


def number(value):return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)
def digest(value):return hashlib.sha256(str(value).encode()).hexdigest()
def identifier(value):return isinstance(value,str) and 0<len(value)<=200
def hashed(value):return digest(value) if identifier(value) else None
def hexkey(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
def bounded(value,low,high):return max(low,min(high,value))


def players_for(state,plan):
    rows=state.get('players',[]) if isinstance(state,dict) else []
    valid=[p for p in rows if isinstance(p,dict) and all(number(p.get(k)) for k in ('x','y'))]
    hero=next((p for p in valid if str(p.get('id'))==str(state.get('heroId'))),None)
    if not hero:return None,None
    enemies=[p for p in valid if str(p.get('id'))!=str(hero.get('id')) and not p.get('dead') and (hero.get('team') is None or p.get('team')!=hero['team'])]
    if plan.get('target_id') is not None:
        return hero,next((p for p in enemies if str(p.get('id'))==str(plan['target_id'])),None)
    point=plan.get('target')
    if not isinstance(point,(list,tuple)) or len(point)!=2 or not all(number(v) for v in point):point=(hero['x'],hero['y'])
    return hero,min(enemies,key=lambda p:math.dist((p['x'],p['y']),point),default=None)


def context(state,plan,mobile,shot):
    """Transient IDs resolve players, but only anonymous buckets are returned."""
    if not isinstance(state,dict) or not isinstance(plan,dict):return None
    name=mobile_name(mobile) if not isinstance(mobile,bool) else None
    if not name or not isinstance(shot,int) or isinstance(shot,bool) or shot not in (0,1,2):return None
    if state.get('clone_id','dragonbound')!='dragonbound':return None
    hero,target=players_for(state,plan)
    wind=state.get('wind')
    if not hero or not target or not number(wind) or not 0<=wind<=100:return None
    from mobile_tactics import terrain_vulnerability
    terrain=terrain_vulnerability(state,target)
    weak=terrain.get('weak_support') if terrain.get('support_known') is True else None
    if weak is not True and weak is not False:weak=None
    native_health=all(number(hero.get(k)) and hero[k]>=0 for k in ('hp','shield','maxHp')) and hero['maxHp']>0
    life='critical' if native_health and hero['hp']+hero['shield']<=.3*hero['maxHp'] else 'normal' if native_health else 'unknown'
    return {'mobile':name,'target_mobile':mobile_name(target.get('mobile')) or 'UNKNOWN',
            'distance_band':int(bounded(math.hypot(target['x']-hero['x'],target['y']-hero['y'])//200,0,20)),
            'height_band':int(bounded((target['y']-hero['y'])//100,-10,10)),
            'wind_band':0 if wind==0 else int(math.ceil(wind/10)),
            'weak_support':weak,'own_life':life}


def valid_context(value):
    return isinstance(value,dict) and set(value)=={'mobile','target_mobile','distance_band','height_band','wind_band','weak_support','own_life'} and mobile_name(value['mobile'])==value['mobile'] and (value['target_mobile']=='UNKNOWN' or mobile_name(value['target_mobile'])==value['target_mobile']) and all(isinstance(value[k],int) and not isinstance(value[k],bool) and low<=value[k]<=high for k,low,high in (('distance_band',0,20),('height_band',-10,10),('wind_band',0,10))) and (value['weak_support'] is None or isinstance(value['weak_support'],bool)) and value['own_life'] in ('critical','normal','unknown')


def arm(plan,shot,item=None):
    angle=plan.get('elevation',plan.get('raw_angle'))
    if not number(angle) or not -360<=angle<=360:return None
    angle=(angle+180)%360-180
    return {'shot':shot,'angle_band':int(math.floor(angle/15))*15,'item':'dual' if item=='dual' else 'normal'}


def valid_arm(value):
    return isinstance(value,dict) and set(value)=={'shot','angle_band','item'} and isinstance(value['shot'],int) and not isinstance(value['shot'],bool) and value['shot'] in (0,1,2) and isinstance(value['angle_band'],int) and not isinstance(value['angle_band'],bool) and -180<=value['angle_band']<=165 and value['angle_band']%15==0 and value['item'] in ('normal','dual')


def mode_for(plan,state):
    profile=plan.get('profile');parts=profile.split(':') if isinstance(profile,str) else []
    if len(parts)==3 and parts[0]!='dragonbound':return None,None
    name=plan.get('mobile') or (parts[1] if len(parts)==3 else None)
    shot=plan.get('shot')
    if shot is None and len(parts)==3:
        try:shot=int(parts[2])
        except ValueError:pass
    hero,_=players_for(state,plan)
    if name is None and hero:name=hero.get('mobile')
    return name,shot


def checked_candidate(plan):
    return isinstance(plan,dict) and plan.get('evaluation_phase')=='evaluation' and plan.get('stage')=='evaluación con modelo congelado' and plan.get('prefix_only') is not True and plan.get('scope')!='shared-launch-prefix' and plan.get('full_family_validated') is not False and plan.get('action') in (None,'attack') and number(plan.get('power')) and 1<=plan['power']<=400 and number(plan.get('raw_angle')) and isinstance(plan.get('origin'),(list,tuple)) and len(plan['origin'])==2 and all(number(v) for v in plan['origin'])


def observed_candidate(plan):
    if checked_candidate(plan):return True
    if not isinstance(plan,dict) or plan.get('evaluation_phase')!='calibration' or plan.get('stage')!='calibración dirigida provisional':return False
    # A real attributed health result can teach an action preference even
    # before its physics is approved. It never authorizes the next action or
    # turns that calibration shot into a held-out accuracy test.
    return checked_candidate({**plan,'evaluation_phase':'evaluation','stage':'evaluación con modelo congelado'})


class OutcomePolicy:
    context=staticmethod(context)
    def __init__(self,path,comparison_enabled=False):
        self.path=Path(path);self.cases=[];self.pending={};self.seen=[];self.games=[]
        self.decisions=0;self.updates=0;self.explorations=0;self.measured_selections=0;self.changed_selections=0;self.rejected=0;self.game_updates=0;self.wins=0;self.losses=0;self.load_error=False
        self.comparison_enabled=bool(comparison_enabled);self.comparison={'baseline_wins':0,'baseline_losses':0,'learned_wins':0,'learned_losses':0}
        try:
            if self.path.stat().st_size>2000000:raise ValueError('Oversized policy')
            saved=json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(saved,dict) or saved.get('schema')!=1:raise ValueError('Unknown policy schema')
            self.cases=[r for r in saved.get('cases',[])[-MAX_CASES:] if self.valid_case(r)]
            self.pending={r['token']:r for r in saved.get('pending',[])[-MAX_PENDING:] if self.valid_pending(r)}
            self.seen=[x for x in saved.get('seen',[])[-2048:] if hexkey(x)]
            self.games=[x for x in saved.get('games',[])[-512:] if hexkey(x)]
            counters=saved.get('counters') or {}
            comparison=saved.get('comparison') or {}
            for key in self.comparison:
                value=comparison.get(key,0)
                if isinstance(value,int) and not isinstance(value,bool) and value>=0:self.comparison[key]=value
            for key in ('decisions','updates','explorations','measured_selections','changed_selections','rejected','game_updates','wins','losses'):
                value=counters.get(key,0)
                if isinstance(value,int) and not isinstance(value,bool) and value>=0:setattr(self,key,value)
        except FileNotFoundError:pass
        except (OSError,ValueError,TypeError,KeyError,AttributeError):self.load_error=True
    @staticmethod
    def valid_pending(row):
        return isinstance(row,dict) and hexkey(row.get('token')) and hexkey(row.get('episode')) and valid_context(row.get('context')) and valid_arm(row.get('arm')) and number(row.get('origin_error_px')) and 0<=row['origin_error_px']<=3
    @classmethod
    def valid_case(cls,row):
        return cls.valid_pending(row) and number(row.get('reward')) and -1<=row['reward']<=1 and number(row.get('terminal_credit',0)) and abs(row.get('terminal_credit',0))<=.15 and (row.get('game') is None or hexkey(row['game']))
    def save(self):
        atomic_write(self.path,json.dumps({'schema':1,'comparison':self.comparison,'cases':self.cases[-MAX_CASES:],'pending':list(self.pending.values())[-MAX_PENDING:],'seen':self.seen[-2048:],'games':self.games[-512:],'counters':{k:getattr(self,k) for k in ('decisions','updates','explorations','measured_selections','changed_selections','rejected','game_updates','wins','losses')}},allow_nan=False,separators=(',',':')).encode())
    def is_baseline(self,episode):
        key=hashed(episode)
        return bool(self.comparison_enabled and key and int(key[:8],16)%5==0)
    def comparison_summary(self):
        report={'enabled':self.comparison_enabled,'assignment':'episode-hash-20-percent-baseline','win_improvement_proven':False}
        for group in ('baseline','learned'):
            wins=self.comparison[group+'_wins'];losses=self.comparison[group+'_losses'];count=wins+losses
            report[group]={'wins':wins,'losses':losses,'games':count,'win_rate':round(wins*100/count,1) if count else None}
        report['status']='collecting' if min(report['baseline']['games'],report['learned']['games'])<20 else 'descriptive-comparison'
        return report
    def estimate_context(self,ctx,action):
        empty={'support':0,'effective_support':0,'expected_reward':None,'known':False,'uncertainty':None,'backoff':'none','episodes':0}
        if not valid_context(ctx) or not valid_arm(action):return empty
        matches=[r for r in self.cases if r['arm']==action]
        exact=[(r,1.0) for r in matches if r['context']==ctx]
        scope='exact';values=exact
        if len(exact)<MIN_EXACT:
            compatible=[]
            for row in matches:
                other=row['context']
                if any(other[k]!=ctx[k] for k in ('mobile','target_mobile','weak_support','own_life')):continue
                delta=[abs(other[k]-ctx[k]) for k in ('distance_band','height_band','wind_band')]
                if any(d>1 for d in delta):continue
                compatible.append((row,(1-.35*delta[0])*(1-.35*delta[1])*(1-.25*delta[2])))
            values=compatible;scope='nearby-context'
        values=values[-24:]
        if not values:return empty
        weighted=[(row,weight*(.9**(len(values)-i-1))) for i,(row,weight) in enumerate(values)]
        total=sum(w for _,w in weighted);squared=sum(w*w for _,w in weighted)
        effective=total*total/squared if squared else 0
        mean=sum(bounded(row['reward']+row.get('terminal_credit',0),-1,1)*weight for row,weight in weighted)/total
        variance=sum(weight*(bounded(row['reward']+row.get('terminal_credit',0),-1,1)-mean)**2 for row,weight in weighted)/total
        episodes=len({row['episode'] for row,_ in values})
        known=len(values)>=MIN_EXACT and effective>=2.5 if scope=='exact' else len(values)>=5 and effective>=3 and episodes>=2
        # Shrink sparse nearby experience toward neutral instead of promoting
        # a single lucky hit. The interval is descriptive, not proof of gain.
        strength=effective/(effective+(1 if scope=='exact' else 3))
        return {'support':len(values),'effective_support':round(effective,3),'expected_reward':mean*strength if known else None,'observed_mean':mean,'known':bool(known),'uncertainty':min(1,1.96*math.sqrt(max(.01,variance)/max(1,effective))+1/max(1,effective)),'backoff':scope,'episodes':episodes}
    def estimate(self,state,mobile,shot,plan=None):
        plan=plan if isinstance(plan,dict) else {}
        ctx=context(state,plan,mobile,shot)
        item='dual' if plan.get('use_dual') is True else 'normal'
        actions=[]
        if number(plan.get('raw_angle')):actions=[arm(plan,shot,item)]
        else:
            for row in self.cases:
                a=row['arm']
                if a['shot']==shot and a['item']==item and a not in actions:actions.append(a)
        estimates=[self.estimate_context(ctx,a) for a in actions if a]
        known=[v for v in estimates if v['known']]
        return max(known,key=lambda v:v['expected_reward']) if known else max(estimates,key=lambda v:v['support'],default={'support':0,'effective_support':0,'expected_reward':None,'known':False,'uncertainty':None,'backoff':'none','episodes':0})
    def choose(self,candidates,state,episode):
        options=[];contexts={};estimates={}
        for index,plan in enumerate(candidates if isinstance(candidates,(list,tuple)) else []):
            if not checked_candidate(plan):continue
            mobile,shot=mode_for(plan,state)
            point=plan.get('target');point=tuple(point) if isinstance(point,(list,tuple)) and len(point)==2 and all(number(v) for v in point) else None
            key=(mobile,shot,str(plan.get('target_id')),point)
            if key not in contexts:contexts[key]=context(state,plan,mobile,shot)
            ctx=contexts[key]
            action=arm(plan,shot,'dual' if plan.get('use_dual') is True else None)
            if ctx is None or not valid_arm(action):continue
            estimate_key=json.dumps([ctx,action],sort_keys=True)
            if estimate_key not in estimates:estimates[estimate_key]=self.estimate_context(ctx,action)
            options.append((index,plan,ctx,action,estimates[estimate_key]))
        if not options:return None
        baseline=self.is_baseline(episode)
        known=[] if baseline else [option for option in options if option[4]['known']]
        best=max(known,key=lambda o:o[4]['expected_reward']-.15*o[4]['uncertainty']) if known else options[0]
        mode='baseline-evaluation' if baseline else 'measured' if known else 'baseline'
        # Proposals do not consume the quota; only confirmed own releases do.
        # Ten re-plans in the same turn cannot create ten exploration credits.
        if not baseline and (self.decisions+1)%10==0 and len({json.dumps(o[3],sort_keys=True) for o in options})>1:
            alternatives=[o for o in options if o[3]!=best[3]]
            if alternatives:
                best=min(alternatives,key=lambda o:(o[4]['support'],o[0]));mode='explore'
        index,plan,ctx,action,estimate=best
        metadata={'candidate_index':index,'decision_number':self.decisions+1,'mode':mode,'candidate_count':len(options),'context':ctx,'arm':action,'episode_key':hashed(episode),'support':estimate['support'],'expected_reward':estimate['expected_reward'],'backoff':estimate['backoff'],'uncertainty':estimate['uncertainty'],'authorizes_action':False}
        return {**plan,'outcome_policy':metadata}
    def describe_observation(self,plan,state,episode):
        if not observed_candidate(plan):return plan
        mobile,shot=mode_for(plan,state);ctx=context(state,plan,mobile,shot)
        if ctx is None:return plan
        return {**plan,'outcome_policy':{'mode':'research-observation','decision_number':self.decisions+1,'context':ctx,'episode_key':hashed(episode),'physics_validated':False,'authorizes_action':False}}
    def note(self,token,release,state):
        """Queue a confirmed, geometrically checked own decision for reward."""
        from shot_attribution import attributed_start,identity
        key=hashed(token)
        if key is None or key in self.seen or key in self.pending or not isinstance(release,dict):return False
        plan=release.get('learner')
        if not observed_candidate(plan) or release.get('hero')!=state.get('heroId'):return False
        if not number(release.get('power')) or not 1<=release['power']<=400:return False
        item=release.get('item')
        if item not in (None,'dual') or plan.get('use_dual') is True and item!='dual' or item=='dual' and plan.get('use_dual') is not True:return False
        mobile,mode=mode_for(plan,state)
        if mode!=release.get('shot'):return False
        metadata=plan.get('outcome_policy') or {}
        if isinstance(metadata,dict) and metadata and metadata.get('decision_number')!=self.decisions+1:return False
        # A fast finishing shot can already have killed the target in the
        # first confirmed frame. Preserve the checked pre-shot context so
        # successful finishes are not systematically missing from learning.
        saved_context=metadata.get('context') if isinstance(metadata,dict) else None
        ctx=saved_context if valid_context(saved_context) and saved_context['mobile']==mobile_name(mobile) else context(state,plan,mobile,mode)
        action=arm(plan,mode,item)
        episode=metadata.get('episode_key') if isinstance(metadata,dict) else None
        if not hexkey(episode):episode=hashed(release.get('episode') or plan.get('episode'))
        if ctx is None or not valid_arm(action) or episode is None:return False
        shots=state.get('shots')
        if not isinstance(shots,list) or len(shots)>64 or any(not isinstance(s,dict) for s in shots):return False
        fresh=[s for s in shots if identity(s) not in release.get('baseline',[])]
        own=[]
        for shot in fresh:
            attribution=attributed_start(state,shot,release)
            if not attribution or not attribution.get('learnable') or attribution.get('shot')!=mode:return False
            own.append(shot)
        if not own:return False
        errors=[math.dist(s['start'][:2],plan['origin']) for s in own]
        if max(errors)>3:return False
        self.pending[key]={'token':key,'episode':episode,'context':ctx,'arm':action,'origin_error_px':max(errors),'phase':plan['evaluation_phase'],'physics_validated':plan['evaluation_phase']=='evaluation'}
        self.pending=dict(list(self.pending.items())[-MAX_PENDING:]);self.decisions+=1
        if isinstance(metadata,dict) and metadata.get('mode')=='explore':self.explorations+=1
        if isinstance(metadata,dict) and metadata.get('mode')=='measured':self.measured_selections+=1
        if isinstance(metadata,dict) and metadata.get('mode') in ('measured','explore') and isinstance(metadata.get('candidate_index'),int) and metadata['candidate_index']>0:self.changed_selections+=1
        self.save();return True
    def observe(self,result):
        if not isinstance(result,dict):return False
        key=hashed(result.get('token'));pending=self.pending.pop(key,None)
        if pending is None or key in self.seen:return False
        self.seen=(self.seen+[key])[-2048:]
        enemy=result.get('enemy_health_drop');own=result.get('own_health_drop')
        eligible=result.get('known') is True and result.get('reward_eligible') is True and result.get('attribution')=='own-shot-window' and all(number(v) and 0<=v<=10000 for v in (enemy,own))
        if not eligible:self.rejected+=1;self.save();return False
        reward=bounded((enemy-own)/1000,-1,1)
        self.cases=(self.cases+[{**pending,'reward':reward,'terminal_credit':0,'game':hashed(result.get('game'))}])[-MAX_CASES:]
        self.updates+=1;self.save();return True
    def observe_outcome(self,row):
        if not isinstance(row,dict) or row.get('outcome_known') is not True or row.get('source')!='native-survival-at-gameover' or row.get('outcome') not in ('win','loss'):return False
        key=hashed(row.get('id'))
        if key is None or key in self.games:return False
        eligible=[r for r in self.cases if r.get('game')==key]
        episode_key=hashed(row.get('strategy_episode'))
        if not eligible and not (self.comparison_enabled and episode_key):return False
        if eligible:
            credit=(.15 if row['outcome']=='win' else -.15)/len(eligible)
            for case in eligible:case['terminal_credit']=credit
        episode_keys={case['episode'] for case in eligible}
        if episode_key:episode_keys.add(episode_key)
        cohorts={('baseline' if int(key[:8],16)%5==0 else 'learned') for key in episode_keys}
        if self.comparison_enabled and len(cohorts)==1:
            cohort=next(iter(cohorts));self.comparison[cohort+('_wins' if row['outcome']=='win' else '_losses')]+=1
        self.games=(self.games+[key])[-512:]
        if eligible:
            self.game_updates+=1
            if row['outcome']=='win':self.wins+=1
            else:self.losses+=1
        self.save();return True
    def summary(self):
        arms={json.dumps([r['context'],r['arm']],sort_keys=True) for r in self.cases}
        return {'comparison':self.comparison_summary(),'measured_selections':self.measured_selections,'changed_selections':self.changed_selections,'confirmed_decisions':self.decisions,'learning_updates':self.updates,'retained_reward_cases':len(self.cases),'calibration_reward_cases':sum(r.get('phase')=='calibration' for r in self.cases),'evaluated_reward_cases':sum(r.get('phase')=='evaluation' for r in self.cases),'pending_windows':len(self.pending),'observed_arms':len(arms),'exploration_decisions':self.explorations,'unknown_or_rejected_rewards':self.rejected,'known_game_outcomes':self.game_updates,'credited_wins':self.wins,'credited_losses':self.losses,'source':'empirical-own-health-windows','strategy_improvement_proven':False,'win_improvement_proven':False,'load_error':self.load_error}
