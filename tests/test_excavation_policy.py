import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock

from adaptive_training import AdaptiveTrial
from autonomous_learning import AutonomousLearner
from training_aim import NoAim

MODEL={'scale':2,'offset':0,'gravity':400,'wind_scale':4}

class ExcavationTests(unittest.TestCase):
    def make(self,tmp,powers=(100,300)):
        learner=AutonomousLearner(Path(tmp)/'learner.json');learner.episode='current'
        key='dragonbound:ARMOR:0'
        learner.records[key]={'samples':[{'id':str(i),'episode':'current','simple':True,'power':power,'speed':power*2,'ax':0,'ay':400,'wind':0,'wind_angle':0,'heading':40,'duration_s':.5} for i,power in enumerate(powers)]}
        adaptive=AdaptiveTrial(Path(tmp)/'report.json',learner);trial=adaptive.profile('ARMOR',0)
        trial.prior=copy.deepcopy(MODEL);trial.prior_training_ids={'historical'}
        ground=[100]*500
        for x in range(220,232):ground[x]=-500
        state={'status':'live','heroId':0,'wind':0,'windAngle':0,'players':[{'id':0,'x':100,'y':100,'mobile':0,'muzzleX':0,'muzzleY':-10,'team':0},{'id':1,'x':350,'y':100,'team':1}],'terrain':{'heights':ground},'weather':[]}
        player={'look':1,'body':0,'rawAngle':40,'minAngle':10,'maxAngle':55}
        probe={'mobile':'ARMOR','shot':0,'angle':55,'power':100,'adaptive':True}
        error=NoAim('wall',reason='terrain-blocked',recovery=learner.plan(state,player,probe,model_override=MODEL))
        return adaptive,trial,state,player,probe,error

    def test_checked_provisional_physics_can_open_wall_before_aim_is_frozen(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,s,p,probe,error=self.make(tmp)
            self.assertIsNone(t.frozen)
            result=a.excavate(s,p,probe,error)
            self.assertEqual(result['action'],'abrir paso');self.assertFalse(result['use_dual'])
            self.assertEqual(result['excavation_evidence']['check_ids'],['0','1'])
            self.assertEqual(result['evaluation_phase'],'recovery')
            self.assertGreater(result['impact'][0],219);self.assertLess(result['power'],300)
            token=a.record({'power':result['power'],'turn_serial':8,'learner':result},{})
            self.assertFalse(t.tests);self.assertFalse(t.calibration);self.assertEqual(t.warmups,0)
            self.assertEqual(a.recovery_rows[0]['episode'],'current')
            a.health_result({'token':token,'known':True,'enemy_health_drop':0,'terrain_opened':True})
            self.assertEqual(a.summary()['terrain_openings_observed'],1)

    def test_final_plan_recomputes_the_collision_at_the_actual_angle(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,s,p,probe,error=self.make(tmp);initial=a.excavate(s,p,probe,error)
            p['rawAngle']=43
            result=a.plan(s,p,probe,actual=True,previous=initial)
            self.assertEqual(result['raw_angle'],43);self.assertFalse(result['use_dual'])
            self.assertNotEqual(initial['impact'],result['impact'])

    def test_fit_samples_are_not_reused_as_independent_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,s,p,probe,error=self.make(tmp)
            t.prior_training_ids={'0','1'}
            self.assertIsNone(a.excavate(s,p,probe,error))
            t.prior=None;t.context_candidate={'model':MODEL,'training_ids':{'0','1'}}
            self.assertIsNone(a.excavate(s,p,probe,error))
            t.episode='current';t.frozen={'model':MODEL,'wind':0,'angle':0}
            self.assertIsNone(a.excavate(s,p,probe,error))

    def test_prior_episode_checks_or_unchecked_physics_do_not_authorize_digging(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,s,p,probe,error=self.make(tmp)
            for sample in a.learner.records[t.key]['samples']:sample['episode']='old'
            self.assertIsNone(a.excavate(s,p,probe,error))
            for sample in a.learner.records[t.key]['samples']:sample.update(episode='current',speed=1000)
            self.assertIsNone(a.excavate(s,p,probe,error))

    def test_provisional_dig_power_must_be_inside_checked_force_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,s,p,probe,error=self.make(tmp,powers=(100,140))
            # Every trajectory that reaches this wall needs >140 force.
            self.assertIsNone(a.excavate(s,p,probe,error))

    def test_near_muzzle_wall_and_known_or_unknown_allies_are_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,s,p,probe,error=self.make(tmp)
            for team in (0,None):
                s['players'].append({'id':2,'x':221,'y':40,'team':team})
                self.assertIsNone(a.excavate(s,p,probe,error));s['players'].pop()
            for x in range(110,132):s['terrain']['heights'][x]=-500
            self.assertIsNone(a.excavate(s,p,probe,error))

    def test_unknown_weather_before_wall_rejects_but_weather_behind_wall_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,s,p,probe,error=self.make(tmp)
            s['weather']=[{'typeId':5,'x':160,'size':20}]
            self.assertIsNone(a.excavate(s,p,probe,error))
            s['weather'][0]['x']=300
            self.assertIsNotNone(a.excavate(s,p,probe,error))

    def test_no_special_bullets_ss_or_variable_projectiles_are_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,s,p,probe,error=self.make(tmp)
            for change in ({'shot':2},{'mobile':'NAK'},{'mobile':'LIGHTNING'},{'mobile':'RANDOMIZER'}):
                self.assertIsNone(a.excavate(s,p,{**probe,**change},error))
            a.learner.records[t.key]['multi_projectile']=True
            self.assertIsNone(a.excavate(s,p,probe,error))

    def test_bullet_two_needs_its_own_checked_simple_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,s,p,probe,error=self.make(tmp);probe={**probe,'shot':1}
            self.assertIsNone(a.excavate(s,p,probe,error))
            self.assertIn('comprobaciones',error.excavation_reason)
            second=a.profile('ARMOR',1);second.prior=copy.deepcopy(MODEL);second.prior_training_ids={'historical'}
            a.learner.records[second.key]=copy.deepcopy(a.learner.records[t.key])
            self.assertIsNotNone(a.excavate(s,p,probe,error))
            for attribute in ('patterns','observed_phases'):
                a.learner.records[second.key][attribute]=[{}]
                self.assertIsNone(a.excavate(s,p,probe,error));a.learner.records[second.key].pop(attribute)

    def test_pending_failed_and_total_attempt_budgets_prevent_repeated_blind_digs(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,s,p,probe,error=self.make(tmp);impact=a.excavate(s,p,probe,error)['impact']
            p['rawAngle']=38
            dig=lambda:a.excavate(s,p,probe,error,actual=True)
            row={'episode':'current','profile':t.key,'impact':impact,'terrain_opened':None}
            a.recovery_rows=[row];self.assertIsNone(dig())
            row['terrain_opened']=False;a.recovery_rows=[copy.deepcopy(row),copy.deepcopy(row)]
            self.assertIsNone(dig())
            a.recovery_rows[-1]['terrain_opened']=True
            self.assertIsNotNone(dig())
            a.recovery_rows.append({**row,'impact':[400,100]})
            self.assertIsNone(dig())
            for row in a.recovery_rows:row['episode']='previous'
            self.assertIsNotNone(dig())

    def test_missing_solid_impact_or_malformed_candidate_is_never_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,s,p,probe,error=self.make(tmp)
            candidate={'power':150,'raw_angle':40,'target':[350,100],'impact':None}
            a.learner.plan=Mock(return_value={'unavailable_reason':'terrain-blocked','blocked_plans':[candidate]})
            for impact in (None,8,[float('nan'),100],[220,-600]):
                candidate['impact']=impact;self.assertIsNone(a.excavate(s,p,probe,error))

    def test_previous_report_block_retains_dig_quota_without_inflating_new_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,s,p,probe,error=self.make(tmp);impact=a.excavate(s,p,probe,error)['impact']
            a.experience_recovery_rows=[{'token':str(i),'episode':'current','profile':t.key,'impact':impact,'terrain_opened':False} for i in range(3)]
            self.assertIsNone(a.excavate(s,p,probe,error))
            self.assertEqual(a.summary()['terrain_attempts'],0);self.assertFalse(a.done())

    def test_previous_report_block_retains_weather_quota_without_counting_old_shots(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,s,p,probe,error=self.make(tmp)
            weather=NoAim('climate',reason='unknown-weather',recovery={'weather_probes':[{'power':180,'raw_angle':40,'weather_crossings':[{'typeId':3}]}]})
            t.plan=Mock(side_effect=weather)
            a.experience_weather_rows=[{'token':str(i),'episode':'current','profile':t.key,'weather_kinds':['3']} for i in range(3)]
            with self.assertRaises(NoAim):a.plan(s,p,probe)
            self.assertEqual(a.summary()['weather_practice_shots'],0);self.assertFalse(a.done())

    def test_previous_report_block_retains_checked_weapon_evidence_without_recount(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,s,p,probe,error=self.make(tmp);a.allow_dual=True;s['players'][1].update(hp=150,shield=0)
            t.experience_tests=[{'token':str(i),'episode':'current','target_id':1,'wind':0,'wind_angle':0,'path_error_px':5,'health_window_known':True,'enemy_health_drop':100} for i in range(5)]
            t.plan=Mock(return_value={'target':[350,100],'evaluation_phase':'evaluation'})
            self.assertTrue(a.plan(s,p,probe)['use_dual'])
            self.assertEqual(a.summary()['directed_test_shots'],0);self.assertFalse(a.done())
    def test_uncertain_dig_reserves_quota_and_does_not_count_as_a_confirmed_shot(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,s,p,probe,error=self.make(tmp);plan=a.excavate(s,p,probe,error)
            a.reserve_action(plan,('room','0',1))
            self.assertIsNone(a.excavate(s,p,probe,error,actual=True))
            self.assertFalse(a.recovery_rows);self.assertFalse(a.reserved_recoveries[0]['confirmed'])
            self.assertEqual(a.summary()['terrain_attempts'],0);self.assertEqual(a.summary()['terrain_reserved_attempts'],1)
            # Confirmation links the reservation; it must not consume quota twice.
            token=a.record({'power':plan['power'],'turn_serial':1,'learner':plan},{})
            self.assertEqual(token,a.reserved_recoveries[0]['token'])
            a.health_result({'token':token,'known':True,'enemy_health_drop':0,'terrain_opened':True})
            self.assertTrue(a.reserved_recoveries[0]['terrain_opened'])
            self.assertIsNotNone(a.excavate(s,p,probe,error))
    def test_long_block_omissions_remain_accurate_after_recent_history_rotates(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,*_=self.make(tmp)
            for serial in range(300):a.turn_skipped(('room','0',serial))
            self.assertEqual(a.summary()['skipped_turns'],300);self.assertEqual(len(a.omitted_turns),128)
            a.turn_skipped(('room','0',299));self.assertEqual(a.summary()['skipped_turns'],300)
            a.turn_recovered(('room','0',299));self.assertEqual(a.summary()['skipped_turns'],299)
