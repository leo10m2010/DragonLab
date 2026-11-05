import json,math,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
from battle_metrics import BattleMetrics,health
from shot_attribution import identity


def state(serial=1,enemy=500,own=1000,**extra):
    return {'status':'live','heroId':0,'turnSerial':serial,'activePlayer':0 if serial==1 else 1,'over':False,'shots':[],
            'players':[{'id':0,'x':0,'y':0,'hp':own,'shield':0,'dead':False},{'id':1,'x':500,'y':0,'hp':enemy,'shield':0,'dead':False}],**extra}


class CombatFeedbackTests(unittest.TestCase):
    def make(self,folder):
        return BattleMetrics(Path(folder)/'battle.json',Mock(),Mock())
    def note(self,metrics,token='shot-a',before=None):
        before=state() if before is None else before
        metrics.observe(before)
        metrics.note({'hero':0,'turn_serial':1,'health_before':{'0':health(before['players'][0]),'1':health(before['players'][1])}}, {'target_id':1},before,token)

    def test_known_window_exposes_observed_own_cost_and_target_gain_without_claiming_a_hit(self):
        with tempfile.TemporaryDirectory() as folder:
            metrics=self.make(folder);self.note(metrics)
            metrics.observe(state(2,enemy=300,own=970));row=metrics.callback.call_args.args[0]
            self.assertTrue(row['reward_eligible']);self.assertTrue(row['known'])
            self.assertEqual(row['enemy_health_drop'],200);self.assertEqual(row['own_health_drop'],30)
            self.assertEqual((row['own_health_before'],row['own_health_after']),(1000,970))
            self.assertEqual((row['enemy_health_before'],row['enemy_health_after']),(500,300))
            self.assertFalse(row['confirmed_impact']);self.assertIsNone(row['reward_rejection'])

    def test_foreign_and_unresolved_projectiles_cannot_reward_an_action(self):
        foreign={'id':8,'native':True,'start':[500,0,45,200,0,400]}
        unknown={'id':9,'native':False,'x':1,'y':1}
        for projectile in (foreign,unknown,{'id':10,'native':True,'auxiliary':True}):
            with self.subTest(projectile=projectile),tempfile.TemporaryDirectory() as folder:
                metrics=self.make(folder);self.note(metrics)
                metrics.observe(state(2,enemy=300,shots=[projectile]));row=metrics.callback.call_args.args[0]
                self.assertFalse(row['reward_eligible'])

    def test_final_direct_completion_also_rejects_foreign_damage(self):
        with tempfile.TemporaryDirectory() as folder:
            metrics=self.make(folder);self.note(metrics)
            final=state(2,enemy=300,shots=[{'id':8,'native':True,'metadata':{'player':1}}])
            metrics.complete(metrics.pending[0],final)
            self.assertFalse(metrics.callback.call_args.args[0]['reward_eligible'])

    def test_already_flying_foreign_family_is_not_ignored_for_reward(self):
        with tempfile.TemporaryDirectory() as folder:
            metrics=self.make(folder);before=state()
            shot={'id':8,'native':True,'start':[500,0,45,200,0,400],'duration':2000,'elapsed':100}
            metrics.observe(before);metrics.note({'hero':0,'turn_serial':1,'baseline':[identity(shot)]},{'target_id':1},before,'one')
            metrics.observe(state(2,enemy=300,shots=[shot]))
            self.assertFalse(metrics.callback.call_args.args[0]['reward_eligible'])

    def test_healing_seen_inside_window_invalidates_even_a_net_health_drop(self):
        with tempfile.TemporaryDirectory() as folder:
            metrics=self.make(folder);self.note(metrics)
            metrics.observe(state(enemy=400));metrics.observe(state(enemy=450));metrics.observe(state(2,enemy=350))
            row=metrics.callback.call_args.args[0]
            self.assertTrue(row['known']);self.assertEqual(row['enemy_health_drop'],150)
            self.assertFalse(row['reward_eligible']);self.assertEqual(row['reward_rejection'],'healing-observed')

    def test_missing_own_health_does_not_mean_a_zero_cost_action(self):
        with tempfile.TemporaryDirectory() as folder:
            metrics=self.make(folder);self.note(metrics)
            final=state(2,enemy=300);del final['players'][0]['shield'];metrics.observe(final)
            row=metrics.callback.call_args.args[0]
            self.assertTrue(row['known']);self.assertFalse(row['reward_eligible']);self.assertIsNone(row['own_health_drop'])

    def test_health_rejects_booleans_nonfinite_negative_and_overflowed_sum(self):
        for hp in (True,False,float('nan'),float('inf'),-1,10**400):
            self.assertIsNone(health({'hp':hp,'shield':0}))
        self.assertIsNone(health({'hp':1e308,'shield':1e308}))
        self.assertIsNone(health({'hp':100,'shield':True}))

    def test_duplicate_tokens_and_completions_do_not_duplicate_feedback(self):
        with tempfile.TemporaryDirectory() as folder:
            metrics=self.make(folder);self.note(metrics);item=metrics.pending[0]
            self.note(metrics);self.assertEqual(len(metrics.pending),1)
            metrics.complete(item,state(2,enemy=300));metrics.complete(item,state(2,enemy=200));self.note(metrics)
            self.assertFalse(metrics.pending);self.assertEqual(metrics.callback.call_count,1)

    def test_overlapping_actions_cannot_both_claim_the_same_health_change(self):
        with tempfile.TemporaryDirectory() as folder:
            metrics=self.make(folder);self.note(metrics,'one');self.note(metrics,'two')
            metrics.observe(state(2,enemy=300));self.assertEqual(metrics.callback.call_count,2)
            self.assertTrue(all(not call.args[0]['reward_eligible'] for call in metrics.callback.call_args_list))

    def test_outcome_callback_requires_native_gameover_and_fires_once(self):
        with tempfile.TemporaryDirectory() as folder:
            metrics=self.make(folder);metrics.observe(state());metrics.end()
            unknown=metrics.outcome_callback.call_args.args[0]
            self.assertFalse(unknown['outcome_known']);self.assertEqual(unknown['outcome'],'unknown')
            metrics.observe(state());final=state(over=True);final['players'][1]['dead']=True
            metrics.observe(final);metrics.observe(final);metrics.end(final)
            self.assertEqual(metrics.outcome_callback.call_count,2)
            won=metrics.outcome_callback.call_args.args[0]
            self.assertTrue(won['outcome_known']);self.assertEqual(won['outcome'],'win')
            self.assertEqual(won['source'],'native-survival-at-gameover')
            self.assertFalse(metrics.windows)

    def test_missing_native_survival_flag_does_not_prove_a_win(self):
        with tempfile.TemporaryDirectory() as folder:
            metrics=self.make(folder);metrics.observe(state());final=state(over=True)
            del final['players'][0]['dead'];final['players'][1]['dead']=True;metrics.end(final)
            self.assertFalse(metrics.outcome_callback.call_args.args[0]['outcome_known'])

    def test_cumulative_run_totals_survive_retained_display_window_rotation(self):
        with tempfile.TemporaryDirectory() as folder:
            metrics=self.make(folder)
            for i in range(101):
                metrics.begin(state());final=state(over=True)
                final['players'][0 if i else 1]['dead']=True;metrics.end(final)
            result=metrics.summary()
            self.assertEqual((result['wins'],result['losses'],result['recent_games']),(0,100,100))
            self.assertEqual(result['run_totals']['games'],101);self.assertEqual(result['run_totals']['wins'],1)
            self.assertEqual(result['run_totals']['losses'],100);self.assertEqual(result['run_totals']['scope'],'current-controller-run')
            stored=json.loads(metrics.path.read_text());self.assertEqual(stored['run_totals'],result['run_totals'])
            fresh=BattleMetrics(metrics.path);self.assertEqual(fresh.summary()['run_totals']['games'],0)


if __name__=='__main__':unittest.main()
