import copy,json,tempfile,unittest
from pathlib import Path
from outcome_policy import OutcomePolicy,context,MAX_CASES,MAX_PENDING


def state(distance=500,height=0,wind=5):
    return {'heroId':0,'activePlayer':0,'wind':wind,'windAngle':90,'selectedShot':0,'currentPower':200,'players':[
        {'id':0,'name':'Private hero','mobile':0,'team':0,'x':100,'y':100,'hp':800,'shield':0,'maxHp':1000},
        {'id':1,'name':'Private enemy','mobile':1,'team':1,'x':100+distance,'y':100+height,'hp':800,'shield':0,'maxHp':1000}], 'shots':[]}


def plan(shot=0,angle=45,power=200):
    return {'profile':f'dragonbound:ARMOR:{shot}','power':power,'raw_angle':angle,'elevation':angle,'origin':[126,69],'target':[600,100],'target_id':1,'stage':'evaluación con modelo congelado','evaluation_phase':'evaluation','use_dual':False}


def release(policy,candidate,token,episode='private-game',s=None):
    s=copy.deepcopy(s or state());selected=policy.choose([candidate],s,episode)
    if selected is None:selected=candidate
    mode=int(candidate['profile'].split(':')[-1]);r={'hero':0,'x':100,'y':100,'shot':mode,'power':candidate['power'],'wind':s['wind'],'windAngle':90,'baseline':[],'learner':selected}
    s['shots']=[{'id':policy.decisions+1,'native':True,'elapsed':0,'duration':1000,'start':[126,69,45,400,0,390],'shotType':mode,'metadata':{'player':0,'mobile':0,'selectedShot':mode,'power':candidate['power']}}]
    return r,s


def train(policy,candidate,token,damage=100,own=0,episode='private-game',s=None,game='native-game'):
    r,native=release(policy,candidate,token,episode,s)
    assert policy.note(token,r,native)
    assert policy.observe({'token':token,'known':True,'reward_eligible':True,'attribution':'own-shot-window','enemy_health_drop':damage,'own_health_drop':own,'game':game})


class OutcomePreferenceTests(unittest.TestCase):
    def test_known_actual_damage_teaches_preference_among_valid_options(self):
        with tempfile.TemporaryDirectory() as folder:
            p=OutcomePolicy(Path(folder)/'policy.json');a=plan(0,30);b=plan(1,60)
            for i in range(3):train(p,a,'a'+str(i),10)
            for i in range(3):train(p,b,'b'+str(i),300)
            options=[a,b];original=copy.deepcopy(options);choice=p.choose(options,state(),'next-game')
            self.assertEqual(choice['profile'],b['profile']);self.assertEqual(options,original)
            self.assertEqual(choice['outcome_policy']['candidate_index'],1)
            self.assertEqual(choice['outcome_policy']['mode'],'measured')
            self.assertFalse(choice['outcome_policy']['authorizes_action'])
            self.assertGreater(p.estimate(state(),'ARMOR',1)['expected_reward'],p.estimate(state(),'ARMOR',0)['expected_reward'])
    def test_recent_bad_results_can_replace_a_previously_better_action(self):
        with tempfile.TemporaryDirectory() as folder:
            p=OutcomePolicy(Path(folder)/'policy.json');a=plan(0,30);b=plan(1,60)
            for i in range(8):train(p,a,'good'+str(i),300)
            for i in range(8):train(p,b,'steady'+str(i),150)
            self.assertEqual(p.choose([a,b],state(),'before')['profile'],a['profile'])
            for i in range(12):train(p,a,'bad'+str(i),0,500)
            self.assertEqual(p.choose([a,b],state(),'after')['profile'],b['profile'])
    def test_exploration_is_bounded_and_never_synthesizes_an_action(self):
        with tempfile.TemporaryDirectory() as folder:
            p=OutcomePolicy(Path(folder)/'policy.json');options=[plan(0,30,180),plan(1,60,240)]
            for i in range(30):
                selected=p.choose(options,state(),'match')
                self.assertIn({k:v for k,v in selected.items() if k!='outcome_policy'},options)
                # note() receives exactly the current choice rather than a new
                # proposal whose candidate_index would refer to another list.
                native=state();mode=int(selected['profile'].split(':')[-1]);r={'hero':0,'x':100,'y':100,'shot':mode,'power':selected['power'],'wind':5,'windAngle':90,'baseline':[],'learner':selected}
                native['shots']=[{'id':i,'native':True,'elapsed':0,'duration':1000,'start':[126,69,45,400,0,390],'shotType':mode,'metadata':{'player':0,'mobile':0,'power':selected['power']}}]
                self.assertTrue(p.note(str(i),r,native))
                p.observe({'token':str(i),'known':True,'reward_eligible':True,'attribution':'own-shot-window','enemy_health_drop':100,'own_health_drop':0})
            self.assertEqual(p.summary()['confirmed_decisions'],30)
            self.assertEqual(p.summary()['exploration_decisions'],3)
            self.assertLessEqual(p.explorations,p.decisions//10)
    def test_nearby_context_backoff_requires_multiple_episodes_and_keeps_mobile_item_boundaries(self):
        with tempfile.TemporaryDirectory() as folder:
            p=OutcomePolicy(Path(folder)/'policy.json');candidate=plan(1,60)
            for i in range(6):train(p,candidate,str(i),200,episode='game-'+str(i%2),s=state(distance=700,wind=15))
            estimate=p.estimate(state(distance=500,wind=5),'ARMOR',1,candidate)
            self.assertTrue(estimate['known']);self.assertEqual(estimate['backoff'],'nearby-context')
            self.assertGreater(estimate['expected_reward'],0);self.assertGreater(estimate['uncertainty'],0)
            self.assertFalse(p.estimate(state(distance=500,wind=5),'NAK',1,candidate)['known'])
            self.assertFalse(p.estimate(state(distance=500,wind=5),'ARMOR',1,{**candidate,'use_dual':True})['known'])
            foreign=state();foreign['players'][1]['mobile']=2
            self.assertFalse(p.estimate(foreign,'ARMOR',1,candidate)['known'])
    def test_only_candidates_still_available_can_be_selected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=OutcomePolicy(Path(folder)/'policy.json');a=plan(0,30);b=plan(1,60)
            for i in range(3):train(p,b,str(i),400)
            self.assertEqual(p.choose([a],state(),'new')['profile'],a['profile'])
            self.assertIsNone(p.choose([{**b,'prefix_only':True}],state(),'new'))


class OutcomeEvidenceTests(unittest.TestCase):
    def test_unknown_windows_and_duplicate_callbacks_never_teach(self):
        with tempfile.TemporaryDirectory() as folder:
            p=OutcomePolicy(Path(folder)/'policy.json');r,s=release(p,plan(),'token')
            self.assertTrue(p.note('token',r,s));self.assertFalse(p.note('token',r,s))
            self.assertFalse(p.observe({'token':'token','known':False,'reward_eligible':False,'enemy_health_drop':900,'own_health_drop':0}))
            self.assertFalse(p.observe({'token':'token','known':True,'reward_eligible':True,'attribution':'own-shot-window','enemy_health_drop':900,'own_health_drop':0}))
            self.assertEqual(p.updates,0);self.assertEqual(p.rejected,1)
    def test_bad_origin_foreign_projectile_and_incomplete_attribution_are_rejected(self):
        for change in ('origin','foreign','late','unknown'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as folder:
                p=OutcomePolicy(Path(folder)/'policy.json');r,s=release(p,plan(),'token')
                if change=='origin':s['shots'][0]['start'][0]+=3.1
                elif change=='foreign':s['shots'][0]['metadata']['player']=1
                elif change=='late':s['shots'][0]['elapsed']=1300
                else:s['shots'].append({'id':9,'native':False})
                self.assertFalse(p.note('token',r,s));self.assertEqual(p.decisions,0)
    def test_calibration_partial_weather_and_unconfirmed_dual_do_not_train(self):
        changes=({'evaluation_phase':'calibration'},{'prefix_only':True},{'scope':'shared-launch-prefix'},{'full_family_validated':False},{'action':'abrir paso'},{'action':'medir clima'},{'use_dual':True})
        for changeset in changes:
            with self.subTest(changeset=changeset),tempfile.TemporaryDirectory() as folder:
                p=OutcomePolicy(Path(folder)/'policy.json');r,s=release(p,{**plan(),**changeset},'token')
                self.assertFalse(p.note('token',r,s))
    def test_missing_own_health_healing_foreign_source_or_nonfinite_reward_does_not_train(self):
        for field,value in [('own_health_drop',None),('own_health_drop',-1),('enemy_health_drop',float('nan')),('attribution','unknown'),('reward_eligible',False)]:
            with self.subTest(field=field,value=value),tempfile.TemporaryDirectory() as folder:
                p=OutcomePolicy(Path(folder)/'policy.json');r,s=release(p,plan(),'token');self.assertTrue(p.note('token',r,s))
                result={'token':'token','known':True,'reward_eligible':True,'attribution':'own-shot-window','enemy_health_drop':100,'own_health_drop':0};result[field]=value
                self.assertFalse(p.observe(result));self.assertFalse(p.cases)
    def test_same_known_damage_accounts_for_own_health_loss(self):
        with tempfile.TemporaryDirectory() as folder:
            p=OutcomePolicy(Path(folder)/'policy.json');train(p,plan(),'token',100,250)
            self.assertAlmostEqual(p.cases[0]['reward'],-.15)
    def test_persistence_is_private_bounded_and_deduplicated_per_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'one.json';p=OutcomePolicy(path);train(p,plan(),'token',100)
            raw=path.read_text(encoding='utf-8')
            self.assertNotIn('Private hero',raw);self.assertNotIn('Private enemy',raw);self.assertNotIn('private-game',raw);self.assertNotIn('native-game',raw)
            restored=OutcomePolicy(path);self.assertEqual(restored.updates,1)
            r,s=release(restored,plan(),'token');self.assertFalse(restored.note('token',r,s))
            other=OutcomePolicy(Path(folder)/'two.json');self.assertFalse(other.cases)
            # A large imported/reloaded history is bounded and malformed rows
            # cannot become policy rewards.
            saved=json.loads(raw);saved['cases']=saved['cases']*(MAX_CASES+5)+[{'reward':1}]
            saved['pending']=[{**p.cases[0],'token':format(i,'064x')} for i in range(MAX_PENDING+5)]
            path.write_text(json.dumps(saved),encoding='utf-8');bounded=OutcomePolicy(path)
            self.assertLessEqual(len(bounded.cases),MAX_CASES);self.assertLessEqual(len(bounded.pending),MAX_PENDING)
    def test_replans_do_not_consume_exploration_quota_or_allow_stale_choice_notes(self):
        with tempfile.TemporaryDirectory() as folder:
            p=OutcomePolicy(Path(folder)/'policy.json');options=[plan(0,30),plan(1,60)]
            for _ in range(50):p.choose(options,state(),'game')
            self.assertEqual(p.decisions,0);self.assertEqual(p.explorations,0)
            r,s=release(p,plan(),'one');self.assertTrue(p.note('one',r,s))
            self.assertFalse(p.note('different-token',r,s))


class TerminalCreditTests(unittest.TestCase):
    def test_one_native_game_contributes_one_bounded_credit_once(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'policy.json';p=OutcomePolicy(path)
            for i in range(3):train(p,plan(),str(i),100,game='one-game')
            row={'id':'one-game','outcome':'win','outcome_known':True,'source':'native-survival-at-gameover'}
            self.assertTrue(p.observe_outcome(row));self.assertAlmostEqual(sum(r['terminal_credit'] for r in p.cases),.15)
            self.assertEqual(p.summary()['known_game_outcomes'],1);self.assertEqual(p.summary()['credited_wins'],1)
            self.assertFalse(p.observe_outcome(row));self.assertFalse(OutcomePolicy(path).observe_outcome(row))
            self.assertFalse(p.summary()['win_improvement_proven'])
    def test_unknown_or_unrelated_games_cannot_assign_credit(self):
        with tempfile.TemporaryDirectory() as folder:
            p=OutcomePolicy(Path(folder)/'policy.json');train(p,plan(),'a',100,game='one')
            for row in ({'id':'one','outcome':'unknown','outcome_known':False,'source':'native-survival-at-gameover'}, {'id':'one','outcome':'win','outcome_known':True,'source':'inferred'}, {'id':'another','outcome':'loss','outcome_known':True,'source':'native-survival-at-gameover'}):
                self.assertFalse(p.observe_outcome(row))
            self.assertEqual(p.cases[0]['terminal_credit'],0)


if __name__=='__main__':unittest.main()
