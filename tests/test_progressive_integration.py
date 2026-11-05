import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
from autonomous_learning import AutonomousLearner
from training_evaluation import EvaluationTrial
from training_aim import NoAim
from adaptive_training import AdaptiveTrial
from continuous_training import RollingEvaluation
from outcome_policy import OutcomePolicy
from test_local_launch_window import record
from test_outcome_policy import plan,release,state,train


class BoundedEvaluationIntegrationTests(unittest.TestCase):
    def learner(self,folder,mobile='ARMOR',mode=0):
        learner=AutonomousLearner(Path(folder)/'learner.json');learner.episode='game'
        learner.records[f'dragonbound:{mobile}:{mode}']=record()
        return learner
    def test_short_range_can_enter_evaluation_only_inside_the_checked_window(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.learner(folder);learner.plan=Mock(return_value={'stage':'evaluación con modelo congelado','power':90})
            trial=EvaluationTrial(Path(folder)/'trial.json',learner)
            result=trial.plan({'wind':0,'windAngle':90},{},{'mobile':'ARMOR','shot':0,'angle':45,'power':100})
            self.assertEqual(result['evaluation_phase'],'evaluation')
            limits=learner.plan.call_args.kwargs['validation_limits']
            self.assertEqual(limits['power_range'],[84,104]);self.assertEqual(limits['max_flight_seconds'],.7)
            self.assertEqual(len(trial.verified_check_ids({'wind':0,'windAngle':90})),3)
            self.assertNotIn('calibration_search',learner.plan.call_args.kwargs)
    def test_adaptive_probe_admits_only_the_current_narrow_window_without_a_broad_prior(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.learner(folder);adaptive=AdaptiveTrial(Path(folder)/'trial.json',learner)
            live={'wind':0,'windAngle':90,'heroId':0,'turnSerial':1,'players':[{'id':0,'x':0,'y':0},{'id':1,'x':100,'y':0}]}
            self.assertFalse(adaptive.supported('ARMOR',0))
            probe=adaptive.probe('ARMOR',live,[0])
            self.assertEqual(probe['shot'],0);self.assertIsNotNone(adaptive.selected.window_proof(live))
            self.assertTrue(adaptive.supported('ARMOR',0,live))
            with self.assertRaises(NoAim):adaptive.probe('ARMOR',{**live,'wind':1},[0])
            learner.episode='next-game'
            with self.assertRaises(NoAim):adaptive.probe('ARMOR',live,[0])
    def test_special_mechanism_cannot_use_an_ordinary_window_even_without_flags(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.learner(folder,'ADUKA',1)
            trial=EvaluationTrial(Path(folder)/'trial.json',learner,mobile='ADUKA',shot=1);trial.reset_episode()
            self.assertIsNone(trial.window_proof({'wind':0,'windAngle':90}))
            with self.assertRaises(NoAim):trial.plan({'wind':0,'windAngle':90},{},{'mobile':'ADUKA','shot':1,'angle':45,'power':100})
    def test_limited_window_does_not_authorize_a_different_power_or_longer_flight(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.learner(folder)
            state={'heroId':0,'players':[{'id':0,'x':0,'y':0},{'id':1,'x':100,'y':0}],'wind':0,'windAngle':90,'weather':[]}
            player={'look':1,'body':0,'rawAngle':45,'minAngle':45,'maxAngle':45};probe={'mobile':'ARMOR','shot':0,'angle':45,'power':100}
            model={'scale':2.42,'offset':-.4,'gravity':390,'wind_scale':4}
            for solved in ((110,.5),(90,.8)):
                learner.solve_observed=Mock(return_value=solved)
                result=learner.plan(state,player,probe,model_override=model,validation_limits={'power_range':[84,104],'max_flight_seconds':.7})
                self.assertEqual(result['unavailable_reason'],'local-window-unchecked');self.assertFalse(result['reposition_allowed'])
    def test_new_bad_native_flight_retires_frozen_model_before_next_charge(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=self.learner(folder);trial=EvaluationTrial(Path(folder)/'trial.json',learner);trial.reset_episode()
            trial.frozen={'model':{'scale':2.42,'offset':-.4,'gravity':390,'wind_scale':4,'wind_mode':'floor'},'wind':0,'angle':90}
            learner.records[trial.key]['samples'][-1]['speed']+=40
            learner.plan=Mock()
            with self.assertRaises(NoAim):trial.plan({'wind':0,'windAngle':90},{},{})
            self.assertIsNone(trial.frozen);self.assertEqual(trial.model_rejections,1);learner.plan.assert_not_called()


class ResultLearningIntegrationTests(unittest.TestCase):
    def test_prospective_comparison_preserves_baseline_and_counts_pass_only_losses(self):
        with tempfile.TemporaryDirectory() as folder:
            policy=OutcomePolicy(Path(folder)/'policy.json',comparison_enabled=True);a=plan(0,30);b=plan(1,60)
            for i in range(3):train(policy,a,'a'+str(i),10)
            for i in range(3):train(policy,b,'b'+str(i),300)
            baseline=next('game-'+str(i) for i in range(100) if policy.is_baseline('game-'+str(i)))
            learned=next('game-'+str(i) for i in range(100) if not policy.is_baseline('game-'+str(i)))
            self.assertEqual(policy.choose([a,b],state(),baseline)['profile'],a['profile'])
            self.assertEqual(policy.choose([a,b],state(),learned)['profile'],b['profile'])
            row={'id':'all-passed','strategy_episode':baseline,'outcome':'loss','outcome_known':True,'source':'native-survival-at-gameover'}
            self.assertTrue(policy.observe_outcome(row));self.assertFalse(policy.observe_outcome(row))
            summary=policy.summary()['comparison'];self.assertEqual(summary['baseline']['losses'],1)
            self.assertEqual(summary['learned']['games'],0);self.assertFalse(summary['win_improvement_proven'])
            self.assertEqual(OutcomePolicy(Path(folder)/'policy.json',comparison_enabled=True).summary()['comparison']['baseline']['losses'],1)
    def test_actual_calibration_damage_teaches_preferences_without_approving_physics(self):
        with tempfile.TemporaryDirectory() as folder:
            policy=OutcomePolicy(Path(folder)/'policy.json');candidate={**plan(),'evaluation_phase':'calibration','stage':'calibración dirigida provisional'}
            actual,native=release(policy,plan(),'research','game')
            actual['learner']=policy.describe_observation(candidate,native,'game')
            self.assertIsNone(policy.choose([candidate],native,'game'))
            self.assertTrue(policy.note('research',actual,native))
            self.assertTrue(policy.observe({'token':'research','game':'one','known':True,'reward_eligible':True,'attribution':'own-shot-window','enemy_health_drop':180,'own_health_drop':0}))
            self.assertEqual(policy.summary()['learning_updates'],1)
            self.assertEqual(policy.summary()['calibration_reward_cases'],1)
            self.assertEqual(policy.summary()['evaluated_reward_cases'],0)
            self.assertFalse(policy.cases[0]['physics_validated'])
    def test_fast_finishing_shot_keeps_pre_shot_context_and_can_teach_a_win(self):
        with tempfile.TemporaryDirectory() as folder:
            policy=OutcomePolicy(Path(folder)/'policy.json');actual,native=release(policy,plan(),'finish','game')
            native['players'][1].update(dead=True,hp=0)
            self.assertTrue(policy.note('finish',actual,native))
            self.assertTrue(policy.observe({'token':'finish','game':'one-game','known':True,'reward_eligible':True,'attribution':'own-shot-window','enemy_health_drop':800,'own_health_drop':0}))
            self.assertTrue(policy.observe_outcome({'id':'one-game','outcome':'win','outcome_known':True,'source':'native-survival-at-gameover'}))
            self.assertEqual(policy.summary()['learning_updates'],1)
            self.assertEqual(policy.summary()['credited_wins'],1)
    def test_policy_cannot_replace_a_checked_force_with_an_unvalidated_action(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=AutonomousLearner(Path(folder)/'learner.json');learner.episode='game'
            state={'heroId':0,'players':[{'id':0,'x':0,'y':0},{'id':1,'x':500,'y':0}],'wind':0,'windAngle':0,'weather':[]}
            player={'look':1,'body':0,'rawAngle':45,'minAngle':20,'maxAngle':55};probe={'mobile':'ARMOR','shot':0,'angle':45,'power':200}
            model={'scale':2,'offset':0,'gravity':300,'wind_scale':0}
            baseline=learner.plan(state,player,probe,model_override=model)
            bad=learner.plan(state,player,probe,model_override=model,candidate_selector=lambda options:{**options[0],'power':400,'outcome_policy':{'mode':'measured'}})
            self.assertEqual(bad['power'],baseline['power']);self.assertNotIn('outcome_policy',bad)
    def test_result_preference_changes_weapon_and_explores_only_checked_modes(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=Mock();learner.episode='game';model={'scale':2,'offset':0,'gravity':300,'wind_scale':0}
            learner.records={f'dragonbound:ARMOR:{i}':{'model':dict(model),'samples':[]} for i in (0,1)}
            learner.applicable_model.return_value=(model,'checked')
            policy=Mock();policy.load_error=False;policy.summary.return_value={'confirmed_decisions':0}
            policy.estimate.side_effect=lambda state,mobile,mode,plan=None:{'known':True,'expected_reward':.3 if mode==1 else .01}
            adaptive=AdaptiveTrial(Path(folder)/'report.json',learner,outcome_policy=policy)
            state={'wind':0,'windAngle':90,'turnSerial':1,'heroId':0,'players':[{'id':0,'x':0,'y':0},{'id':1,'x':400,'y':0}]}
            self.assertEqual(adaptive.probe('ARMOR',state,[0,1])['shot'],1)
            self.assertEqual(adaptive.probe('ARMOR',state,[0])['shot'],0)
            policy.summary.return_value={'confirmed_decisions':9}
            choice=adaptive.probe('ARMOR',state,[0,1]);self.assertEqual(choice['shot'],0);self.assertTrue(choice['weapon_exploration'])
            learner.applicable_model.side_effect=lambda record,*args:(model,'checked') if record is learner.records['dragonbound:ARMOR:1'] else (None,'unverified')
            choice=adaptive.probe('ARMOR',state,[0,1]);self.assertEqual(choice['shot'],1);self.assertFalse(choice['weapon_exploration'])
    def test_unreadable_strategy_does_not_get_overwritten_or_authorize_decisions(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'policy.json';path.write_text('invalid')
            policy=OutcomePolicy(path);learner=AutonomousLearner(Path(folder)/'learner.json')
            adaptive=AdaptiveTrial(Path(folder)/'trial.json',learner,outcome_policy=policy)
            self.assertTrue(adaptive.policy_error);self.assertEqual(path.read_text(),'invalid')
    def test_adaptive_confirmation_and_health_callback_feed_persistent_policy(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=AutonomousLearner(Path(folder)/'learner.json');learner.episode='game'
            policy=OutcomePolicy(Path(folder)/'policy.json');adaptive=AdaptiveTrial(Path(folder)/'trial.json',learner,outcome_policy=policy)
            chosen=plan();actual,state=release(policy,chosen,'ignored','game')
            adaptive.profile('ARMOR',0)
            token=adaptive.record(actual,state)
            self.assertEqual(policy.summary()['confirmed_decisions'],1)
            result={'token':token,'known':True,'reward_eligible':True,'attribution':'own-shot-window','enemy_health_drop':220,'own_health_drop':0,'game':'native-game'}
            adaptive.health_result(result)
            self.assertEqual(policy.summary()['learning_updates'],1)
            adaptive.game_result({'id':'native-game','outcome':'win','outcome_known':True,'source':'native-survival-at-gameover'})
            self.assertEqual(policy.summary()['credited_wins'],1)
            loaded=OutcomePolicy(Path(folder)/'policy.json')
            self.assertEqual(loaded.summary()['learning_updates'],1)
            self.assertFalse(loaded.summary()['strategy_improvement_proven'])
    def test_rolling_blocks_share_policy_without_duplicate_reward_or_reset(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=AutonomousLearner(Path(folder)/'learner.json');learner.episode='game';policy=OutcomePolicy(Path(folder)/'policy.json')
            rolling=RollingEvaluation(folder,learner,40,outcome_policy=policy)
            first=rolling.current;first.profile('ARMOR',0).model_rejections=2
            rolling.rollover()
            self.assertIs(rolling.current.outcome_policy,policy)
            self.assertEqual(rolling.current.profile('ARMOR',0).model_rejections,2)
            self.assertEqual(policy.summary()['learning_updates'],0)


if __name__=='__main__':unittest.main()
