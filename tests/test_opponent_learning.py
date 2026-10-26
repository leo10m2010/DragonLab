import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from opponent_learning import OpponentLearner


def state(serial=1,active=1):
    return {'status':'live','heroId':0,'activePlayer':active,'turnSerial':serial,'wind':5,'windAngle':90,'weather':[],
            'players':[{'id':0,'name':'Secret hero','mobile':0,'team':0,'x':0,'y':100,'hp':500,'shield':0},
                       {'id':1,'name':'Secret opponent','mobile':1,'team':1,'x':420,'y':100,'hp':500,'shield':0,'rawAngle':45}], 'shots':[]}


def shot(owner=1,kind=0,ident=10):
    return {'id':ident,'native':True,'start':[420,100,135,320,0,400],'elapsed':0,'duration':500,'shotType':kind,'metadata':{'player':owner,'mobile':1,'selectedShot':kind,'launchSpeed':320}}


class Fixture:
    def make(self,folder,**kwargs):return OpponentLearner(Path(folder)/'opponents.json',**kwargs)
    def attack(self,learner,episode='a',serial=1,damage=30,extra=None):
        before=state(serial);learner.observe(before,episode)
        firing=copy.deepcopy(before);firing['players'][1]['x']=410;firing['shots']=[shot(ident=serial*10)]
        if extra:extra(firing)
        learner.observe(firing,episode)
        after=copy.deepcopy(firing);after.update(activePlayer=0,turnSerial=serial+1,shots=[]);after['players'][0]['hp']-=damage
        learner.observe(after,episode)
        return after


class OpponentTests(Fixture,unittest.TestCase):
    def test_observes_explicit_enemy_volley_and_observed_position(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);self.attack(learner)
            summary=learner.summary();self.assertEqual(summary['opponent_turns'],1);self.assertEqual(summary['opponent_shots'],1);self.assertEqual(summary['position_samples'],1)
            self.assertEqual(summary['known_health_windows'],1);self.assertEqual(summary['profiles'],1)
            self.assertEqual(learner.cases[0]['observed_displacement'],[-10,0]);self.assertEqual(learner.cases[0]['hero_health_drop'],30)
            self.assertFalse(learner.cases[0]['movement_ambiguous'])
    def test_never_uses_hero_bar_or_native_launch_speed_as_opponent_charge(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder)
            def extra(firing):firing.update(currentPower=400,selectedShot=2);firing['shots'][0]['metadata']['power']=399
            self.attack(learner,extra=extra);row=learner.cases[0]
            self.assertIsNone(row['power']);self.assertEqual(row['launch_speed'],320);self.assertEqual(row['shot'],0)
    def test_unknown_or_conflicting_owner_is_rejected_even_if_near_enemy(self):
        for metadata in ({},{'player':0,'mobile':1},{'player':1,'player_n':2,'mobile':1}):
            with self.subTest(metadata=metadata),tempfile.TemporaryDirectory() as folder:
                learner=self.make(folder);s=state()
                with patch('opponent_learning.time.monotonic',return_value=100):learner.observe(s,'a')
                s['shots']=[{**shot(),'metadata':metadata}]
                with patch('opponent_learning.time.monotonic',return_value=101):learner.observe(s,'a')
                self.assertEqual(learner.summary()['opponent_shots'],0)
    def test_ally_and_own_projectiles_cannot_become_opponent_shots(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);s=state();s['players'].append({'id':2,'mobile':1,'team':0,'x':50,'y':100,'hp':500,'shield':0})
            learner.observe(s,'a');s['shots']=[shot(owner=0),shot(owner=2,ident=11)];learner.observe(s,'a')
            self.assertEqual(learner.summary()['opponent_shots'],0)
    def test_delayed_auxiliary_non_native_and_malformed_shots_are_rejected(self):
        for change in ({'delay':20},{'auxiliary':True},{'native':False},{'start':[0,1,2]},{'elapsed':700},{'start':[400,100,135,float('nan'),0,400]}):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as folder:
                learner=self.make(folder);s=state();learner.observe(s,'a');s['shots']=[{**shot(),**change}];learner.observe(s,'a')
                self.assertEqual(learner.summary()['opponent_shots'],0)
    def test_weapon_or_mobile_metadata_conflict_is_rejected(self):
        for change in ({'metadata':{'player':1,'mobile':0}}, {'metadata':{'player':1,'mobile':1,'selectedShot':2}}):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as folder:
                learner=self.make(folder);s=state();learner.observe(s,'a');s['shots']=[{**shot(),**change}];learner.observe(s,'a')
                self.assertEqual(learner.summary()['opponent_shots'],0)
    def test_multi_bullet_volley_counts_once_not_once_per_bullet(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);s=state();learner.observe(s,'a');s['shots']=[shot(ident=i) for i in range(20)]
            for _ in range(5):learner.observe(s,'a')
            self.assertEqual(learner.summary()['opponent_shots'],1);self.assertEqual(len(learner.cases),1)
    def test_transport_reconnect_same_observer_does_not_repeat_turn_or_shot(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);self.attack(learner)
            s=state();s['shots']=[shot()]
            learner.observe({'status':'waiting'},'a');learner.observe(s,'a')
            self.assertEqual(learner.summary()['opponent_turns'],1);self.assertEqual(learner.summary()['opponent_shots'],1)
    def test_same_projectile_seen_at_consecutive_enemy_turn_is_not_counted_twice(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);self.attack(learner);s=state(3);s['shots']=[shot()];learner.observe(s,'a')
            self.assertEqual(learner.summary()['opponent_shots'],1)
    def test_same_ids_and_serials_in_next_match_are_new_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);self.attack(learner,'a');self.attack(learner,'b')
            self.assertEqual(learner.summary()['opponent_shots'],2);self.assertEqual(learner.summary()['opponent_turns'],2)
            self.assertNotEqual(learner.cases[0]['episode'],learner.cases[1]['episode'])
    def test_missing_pre_shot_snapshot_cannot_claim_known_damage(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);s=state();s['shots']=[shot()];learner.observe(s,'a');s.update(turnSerial=2,activePlayer=0,shots=[]);s['players'][0]['hp']=400;learner.observe(s,'a')
            self.assertEqual(learner.summary()['opponent_shots'],1);self.assertEqual(learner.summary()['known_health_windows'],0)
    def test_enemy_health_change_flags_displacement_as_ambiguous(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder)
            self.attack(learner,extra=lambda s:s['players'][1].update(hp=450))
            self.assertTrue(learner.cases[0]['movement_ambiguous']);self.assertTrue(learner.positions[0]['movement_ambiguous'])
            self.assertFalse(learner.cases[0]['health_known'])
    def test_camera_changes_do_not_create_world_movement(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);s=state();s['camera']={'x':0};learner.observe(s,'a');s['camera']['x']=1000;s.update(activePlayer=0,turnSerial=2);learner.observe(s,'a')
            self.assertEqual(learner.positions[0]['observed_displacement'],[0,0])
    def test_multiple_enemies_or_allies_make_health_attribution_unknown(self):
        for team in (0,1):
            with self.subTest(team=team),tempfile.TemporaryDirectory() as folder:
                learner=self.make(folder)
                self.attack(learner,extra=lambda s:s['players'].append({'id':2,'team':team,'mobile':2,'x':600,'y':100,'hp':500,'shield':0}))
                self.assertEqual(learner.summary()['opponent_shots'],1);self.assertFalse(learner.cases[0]['health_known'])
    def test_intervening_other_or_unknown_projectile_rejects_damage_window(self):
        for owner in (0,None):
            with self.subTest(owner=owner),tempfile.TemporaryDirectory() as folder:
                learner=self.make(folder);s=state();learner.observe(s,'a');s['shots']=[shot()];learner.observe(s,'a')
                s['shots'].append({**shot(ident=99),'metadata':{} if owner is None else {'player':owner}});learner.observe(s,'a')
                s.update(turnSerial=2,activePlayer=0,shots=[]);s['players'][0]['hp']=400;learner.observe(s,'a');self.assertFalse(learner.cases[0]['health_known'])
    def test_delayed_families_affect_interference_but_never_count_as_new_volleys(self):
        for owner in (0,None,1):
            with self.subTest(owner=owner),tempfile.TemporaryDirectory() as folder:
                learner=self.make(folder);s=state();learner.observe(s,'a');s['shots']=[shot()];learner.observe(s,'a')
                delayed={**shot(ident=99),'delay':100,'metadata':{} if owner is None else {'player':owner}}
                s['shots'].append(delayed);learner.observe(s,'a')
                s.update(turnSerial=2,activePlayer=0,shots=[]);s['players'][0]['hp']=450;learner.observe(s,'a')
                self.assertEqual(learner.cases[0]['health_known'],owner==1)
                self.assertEqual(learner.summary()['opponent_shots'],1)
    def test_non_native_visual_families_keep_health_attribution_unknown(self):
        for owner in (0,None,1):
            with self.subTest(owner=owner),tempfile.TemporaryDirectory() as folder:
                learner=self.make(folder);s=state();learner.observe(s,'a');s['shots']=[shot()];learner.observe(s,'a')
                visual={**shot(ident=99),'native':False,'metadata':{} if owner is None else {'player':owner}}
                s['shots'].append(visual);learner.observe(s,'a')
                s.update(turnSerial=2,activePlayer=0,shots=[]);s['players'][0]['hp']=450;learner.observe(s,'a')
                self.assertFalse(learner.cases[0]['health_known']);self.assertEqual(learner.summary()['opponent_shots'],1)
    def test_hero_movement_or_healing_rejects_risk_window(self):
        for change in ({'x':10},{'hp':600}):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as folder:
                learner=self.make(folder);s=state();learner.observe(s,'a');s['shots']=[shot()];learner.observe(s,'a');s.update(turnSerial=2,activePlayer=0,shots=[]);s['players'][0].update(change);learner.observe(s,'a')
                self.assertFalse(learner.cases[0]['health_known'])
    def test_consecutive_enemy_volley_seen_before_settling_previous_is_ambiguous(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);s=state();learner.observe(s,'a');s['shots']=[shot()];learner.observe(s,'a')
            s.update(turnSerial=2);s['players'][0]['hp']=400;s['shots']=[shot(ident=99)];learner.observe(s,'a')
            self.assertFalse(learner.cases[0]['health_known']);self.assertEqual(learner.summary()['opponent_shots'],2)
    def test_mobile_changed_during_window_cannot_train_old_mobile_risk(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);s=state();learner.observe(s,'a');s['shots']=[shot()];learner.observe(s,'a')
            s.update(turnSerial=2,activePlayer=0,shots=[]);s['players'][0].update(hp=400,mobile=2);learner.observe(s,'a')
            self.assertFalse(learner.cases[0]['health_known'])
    def test_end_or_episode_change_does_not_complete_unknown_pending_window(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);s=state();learner.observe(s,'a');s['shots']=[shot()];learner.observe(s,'a');learner.end()
            self.assertFalse(learner.cases[0]['health_known']);self.assertTrue(learner.path.exists())
    def test_native_gameover_can_complete_known_window(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);s=state();learner.observe(s,'a');s['shots']=[shot()];learner.observe(s,'a');s.update(over=True,shots=[]);s['players'][0].update(hp=0,dead=True);learner.observe(s,'a')
            self.assertTrue(learner.cases[0]['health_known']);self.assertEqual(learner.cases[0]['hero_health_drop'],500)


class RiskAndStorageTests(Fixture,unittest.TestCase):
    def learned(self,folder,n=8,episodes=2):
        learner=self.make(folder)
        for i in range(n):self.attack(learner,str(i%episodes),serial=i*2+1,damage=0 if i%2 else 30)
        return learner
    def test_risk_requires_eight_known_windows_and_two_independent_episodes(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.learned(folder,7);self.assertIsNone(learner.risk_for_position(state(),[0,100],1))
        with tempfile.TemporaryDirectory() as folder:
            learner=self.learned(folder,8,1);self.assertIsNone(learner.risk_for_position(state(),[0,100],1))
        with tempfile.TemporaryDirectory() as folder:
            learner=self.learned(folder);risk=learner.risk_for_position(state(),[0,100],1)
            self.assertEqual(risk['samples'],8);self.assertEqual(risk['episodes'],2);self.assertEqual(risk['estimate'],.5)
            self.assertLess(risk['low'],.5);self.assertGreater(risk['high'],.5);self.assertEqual(learner.summary()['risk_ready_contexts'],1)
    def test_risk_refuses_other_mobile_wind_angle_weather_height_or_distance_bin(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.learned(folder)
            for mutate in (lambda s:s.update(wind=6),lambda s:s.update(windAngle=100),lambda s:s.update(weather=[{'typeId':7}]),lambda s:s.pop('weather'),lambda s:s['players'][0].update(mobile=2),lambda s:s['players'][1].update(mobile=2),lambda s:s['players'][1].update(x=900)):
                s=state();mutate(s);self.assertIsNone(learner.risk_for_position(s,[0,100]))
            self.assertIsNone(learner.risk_for_position(state(),[0,200]));self.assertIsNone(learner.risk_for_position(state(),[0,100],2))
    def test_weather_unknown_or_nonempty_cannot_prepare_risk_evidence(self):
        for weather in (None,[{'typeId':8,'x':200}]):
            with self.subTest(weather=weather),tempfile.TemporaryDirectory() as folder:
                learner=self.make(folder)
                for i in range(8):self.attack(learner,str(i%2),serial=i*2+1,extra=lambda s:s.update(weather=weather))
                self.assertIsNone(learner.risk_for_position(state(),[0,100]))
    def test_saved_store_is_anonymous_numeric_bounded_and_reloads_dedup(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder,max_cases=4)
            for i in range(8):self.attack(learner,'https://private-room',serial=i*2+1)
            learner.end();raw=learner.path.read_text();saved=json.loads(raw)
            self.assertNotIn('Secret',raw);self.assertNotIn('private-room',raw);self.assertNotIn('player',raw);self.assertLessEqual(len(saved['cases']),4);self.assertLessEqual(len(saved['positions']),4)
            restored=self.make(folder,max_cases=4);s=state(15);s['shots']=[shot(ident=150)];restored.observe(s,'https://private-room')
            self.assertEqual(restored.summary()['opponent_shots'],8);self.assertFalse(restored.storage_error)
    def test_buffered_save_writes_only_after_interval_and_end_forces_flush(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('opponent_learning.time.monotonic',return_value=100):learner=self.make(folder);learner.observe(state(),'a')
            self.assertFalse(learner.path.exists())
            with patch('opponent_learning.time.monotonic',return_value=104):learner.observe(state(),'a')
            self.assertFalse(learner.path.exists())
            with patch('opponent_learning.time.monotonic',return_value=105):learner.observe(state(),'a')
            self.assertTrue(learner.path.exists())
            with patch('opponent_learning.time.monotonic',return_value=106):self.attack(learner,'a');learner.end()
            self.assertEqual(json.loads(learner.path.read_text())['totals']['opponent_shots'],1)
    def test_invalid_or_unwritable_store_is_visible_and_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'opponents.json';path.write_text('{corrupt')
            learner=self.make(folder);self.assertTrue(learner.summary()['storage_error']);self.attack(learner);learner.end();self.assertEqual(path.read_text(),'{corrupt')
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);self.attack(learner)
            with patch('opponent_learning.atomic_write',side_effect=OSError('disk')):self.assertFalse(learner.save(force=True))
            self.assertTrue(learner.summary()['storage_error']);self.assertTrue(learner.save(force=True));self.assertFalse(learner.storage_error)


class TemporalOriginTests(Fixture,unittest.TestCase):
    def inference(self,learner,episode='a',serial=1,change=None,age=.1):
        before=state(serial)
        with patch('opponent_learning.time.monotonic',return_value=100):learner.observe(before,episode)
        firing=copy.deepcopy(before);firing['activePlayer']=-1;firing['shots']=[{**shot(ident=serial*10),'metadata':{'launchSpeed':320}}]
        if change:change(firing)
        untouched=copy.deepcopy(firing)
        with patch('opponent_learning.time.monotonic',return_value=100+age):learner.observe(firing,episode)
        self.assertEqual(firing,untouched)
        after=copy.deepcopy(firing);after.update(activePlayer=0,turnSerial=serial+1,shots=[]);after['players'][0]['hp']=450
        with patch('opponent_learning.time.monotonic',return_value=101):learner.observe(after,episode)
        return firing
    def test_fresh_immediately_observed_turn_and_unique_origin_are_labeled_not_native(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);self.inference(learner)
            self.assertEqual(learner.summary()['opponent_shots'],1);self.assertEqual(learner.summary()['opponent_inferred_shots'],1)
            row=learner.cases[0];self.assertEqual(row['owner_source'],'observed-turn-origin');self.assertIsNone(row['power'])
            self.assertFalse(row['health_known']);self.assertIsNone(row['context']);self.assertEqual(learner.summary()['known_health_windows'],0)
    def test_stale_snapshot_or_late_native_bullet_cannot_infer_owner(self):
        for change,age in ((None,.351),(lambda s:s['shots'][0].update(elapsed=151),.1)):
            with self.subTest(age=age),tempfile.TemporaryDirectory() as folder:
                learner=self.make(folder);self.inference(learner,change=change,age=age);self.assertEqual(learner.summary()['opponent_shots'],0)
    def test_current_actor_or_turn_change_or_wrong_origin_rejects_inference(self):
        for change in (lambda s:s.update(activePlayer=0),lambda s:s.update(turnSerial=2),lambda s:s['shots'][0].update(start=[0,100,45,320,0,400]),lambda s:s['shots'][0].update(start=[481,100,45,320,0,400])):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as folder:
                learner=self.make(folder);self.inference(learner,change=change);self.assertEqual(learner.summary()['opponent_inferred_shots'],0)
    def test_nearby_other_player_or_missing_position_rejects_unique_origin(self):
        for position in ((470,100),(None,100)):
            with self.subTest(position=position),tempfile.TemporaryDirectory() as folder:
                learner=self.make(folder)
                self.inference(learner,change=lambda s:s['players'].append({'id':2,'mobile':2,'team':1,'x':position[0],'y':position[1]}))
                self.assertEqual(learner.summary()['opponent_inferred_shots'],0)
    def test_changed_mobile_wind_weather_or_hero_pose_rejects_stable_context(self):
        for change in (lambda s:s['players'][0].update(mobile=2),lambda s:s['players'][1].update(mobile=2),lambda s:s.update(wind=6),lambda s:s.update(windAngle=100),lambda s:s.update(weather=[{'typeId':7,'x':200,'size':25}]),lambda s:s['players'][0].update(x=2)):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as folder:
                learner=self.make(folder);self.inference(learner,change=change);self.assertEqual(learner.summary()['opponent_shots'],0)
    def test_explicit_conflict_never_falls_back_to_proximity(self):
        for metadata in ({'player':0},{'player_n':None},{'player':1,'player_n':0}):
            with self.subTest(metadata=metadata),tempfile.TemporaryDirectory() as folder:
                learner=self.make(folder);self.inference(learner,change=lambda s:s['shots'][0].update(metadata=metadata))
                self.assertEqual(learner.summary()['opponent_inferred_shots'],0)
    def test_camera_changes_do_not_break_world_origin_match(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);self.inference(learner,change=lambda s:s.update(camera={'x':10000,'y':3000,'scale':2}))
            self.assertEqual(learner.summary()['opponent_inferred_shots'],1)
    def test_many_inferred_shots_remain_ineligible_for_risk_even_after_reload(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder)
            for i in range(8):self.inference(learner,episode=str(i%2),serial=i*2+1)
            learner.end();restored=self.make(folder)
            self.assertEqual(restored.summary()['opponent_inferred_shots'],8);self.assertEqual(restored.summary()['known_health_windows'],0)
            self.assertEqual(restored.summary()['risk_ready_contexts'],0);self.assertIsNone(restored.risk_for_position(state(),[0,100]))
            self.assertTrue(all(row['owner_source']=='observed-turn-origin' for row in restored.cases))


class BehaviorProfileTests(Fixture,unittest.TestCase):
    def test_profiles_summarize_observed_approach_and_weapon_without_player_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);self.attack(learner)
            profile=learner.summary()['behavior_profiles']['ICE']
            self.assertEqual(profile['toward'],1);self.assertEqual(profile['away'],0);self.assertEqual(profile['median_displacement'],10)
            self.assertEqual(profile['weapon_counts'],{'0':1,'1':0,'2':0})
            self.assertNotIn('Secret',json.dumps(learner.summary()))
    def test_ambiguous_displacement_does_not_train_position_preference(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);self.attack(learner,extra=lambda s:s['players'][1].update(hp=450))
            profile=learner.summary()['behavior_profiles']['ICE']
            self.assertEqual(profile['position_samples'],1);self.assertEqual(profile['usable_position_samples'],0)
            self.assertEqual(profile['toward'],0);self.assertIsNone(profile['median_displacement'])
    def test_position_reference_and_patterns_survive_save_and_reload(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.make(folder);self.attack(learner);learner.end();before=learner.summary()['behavior_profiles']
            restored=self.make(folder);self.assertEqual(restored.summary()['behavior_profiles'],before)

if __name__=='__main__':unittest.main()
