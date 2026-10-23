import copy,tempfile,unittest,threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from training_evaluation import EvaluationTrial
from training_session import TrainingSession
from training_aim import NoAim
from battle_metrics import BattleMetrics,health

class EvaluationTests(unittest.TestCase):
    def learner(self):
        learner=Mock();learner.episode='match-a';learner.records={};learner.applicable_model.return_value=(None,'unknown')
        learner.plan.return_value={'stage':'calibración controlada','power':100,'target':[500,0]}
        return learner
    def test_default_product_starts_24h_with_finite_adaptive_blocks(self):
        from training_ui import start_training
        app=SimpleNamespace(fire_cancel=__import__('threading').Event(),clone_id='dragonbound',training_session=None,last_live=0,endpoint=Mock(),browser_target=None,book=SimpleNamespace(path=Path('book.json'),records={}),events=Mock())
        with patch('training_session.TrainingSession') as factory:start_training(app)
        options=factory.call_args.kwargs
        self.assertEqual(options['objective'],'adaptive');self.assertTrue(options['continuous']);self.assertEqual(options['max_shots'],40);self.assertEqual(options['max_seconds'],86400)
    def test_continuous_evaluation_is_rejected(self):
        with self.assertRaises(ValueError):TrainingSession('',None,'book.json',lambda e:None,continuous=True,objective='evaluation')
    def test_calibration_never_counts_as_a_directed_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            trial=EvaluationTrial(Path(tmp)/'trial.json',self.learner())
            for _ in range(4):trial.record({'learner':{'evaluation_phase':'calibration'},'power':100}, {'shots':[]})
            self.assertEqual(trial.summary()['calibration_shots'],4);self.assertEqual(trial.summary()['directed_test_shots'],0)
            trial.finish();self.assertFalse(trial.summary()['approved']);self.assertEqual(trial.summary()['status'],'insufficient-data')
    def test_frozen_model_is_independent_of_further_learning(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=self.learner();model={'scale':2,'gravity':400};learner.applicable_model.return_value=(model,'verified')
            learner.plan.return_value={'stage':'evaluación con modelo congelado','power':200}
            trial=EvaluationTrial(Path(tmp)/'trial.json',learner);trial.episode=learner.episode;trial.warmups=1
            plan=trial.plan({'wind':10,'windAngle':30},{},{})
            model['scale']=99
            self.assertEqual(trial.frozen['model']['scale'],2);self.assertEqual(plan['evaluation_phase'],'evaluation')
    def test_evaluation_never_falls_back_to_exploratory_power(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=self.learner();learner.plan.return_value={'stage':'explorar fuerzas y ángulos','power':360}
            trial=EvaluationTrial(Path(tmp)/'trial.json',learner);trial.episode=learner.episode;trial.frozen={'model':{},'wind':0,'angle':0}
            with self.assertRaises(NoAim):trial.plan({'wind':0,'windAngle':0},{},{})
            self.assertEqual(trial.summary()['directed_test_shots'],0)
    def test_out_of_domain_wind_is_skipped_without_readjusting_frozen_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=self.learner();trial=EvaluationTrial(Path(tmp)/'trial.json',learner);trial.episode=learner.episode;trial.frozen={'model':{'scale':2},'wind':10,'angle':0}
            with self.assertRaises(NoAim):trial.plan({'wind':20,'windAngle':0},{},{})
            learner.plan.assert_not_called()
    def test_repeated_unavailable_solutions_end_trial_and_preserve_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            trial=EvaluationTrial(Path(tmp)/'trial.json',self.learner())
            for _ in range(6):trial.skip('No validated trajectory')
            self.assertTrue(trial.done());trial.finish();self.assertEqual(trial.summary()['status'],'insufficient-data')
    def test_proximity_alone_does_not_approve_combat_accuracy(self):
        with tempfile.TemporaryDirectory() as tmp:
            trial=EvaluationTrial(Path(tmp)/'trial.json',self.learner())
            trial.tests=[{'path_error_px':5,'health_window_known':False,'enemy_health_drop':None} for _ in range(12)]
            trial.finish();self.assertFalse(trial.summary()['approved'])
            for row in trial.tests:row.update(health_window_known=True,enemy_health_drop=20)
            self.assertTrue(trial.summary()['approved']);self.assertFalse(trial.summary()['full_autonomy_proven'])

class ProvisionalTests(unittest.TestCase):
    learner=EvaluationTests.learner
    def test_adapted_candidate_is_used_provisionally_without_counting_as_evaluation(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=self.learner();learner.plan.return_value={'stage':'evaluación con modelo congelado','power':200}
            trial=EvaluationTrial(Path(tmp)/'trial.json',learner);trial.episode=learner.episode
            trial.prior={'scale':1};trial.context_candidate={'model':{'scale':2},'training_ids':set()}
            result=trial.plan({'wind':0,'windAngle':0},{},{})
            self.assertEqual(learner.plan.call_args.kwargs['model_override'],{'scale':2})
            self.assertEqual(result['evaluation_phase'],'calibration');self.assertIsNone(trial.frozen)
    def test_comparative_error_requires_enough_independent_tests(self):
        with tempfile.TemporaryDirectory() as tmp:
            trial=EvaluationTrial(Path(tmp)/'trial.json',self.learner())
            row={'path_error_px':5,'health_window_known':True,'enemy_health_drop':20,'candidate_prediction_error_px':5,'baseline_prediction_error_px':10}
            trial.tests=[dict(row) for _ in range(9)]
            self.assertFalse(trial.summary()['prediction_improvement_proven'])
            trial.tests.append(dict(row));self.assertEqual(trial.summary()['prediction_error_improvement_percent'],50)
            self.assertTrue(trial.summary()['prediction_improvement_proven'])

class BattleTests(unittest.TestCase):
    def state(self,serial=1,active=0,enemy=120,over=False,hero_dead=False,enemy_dead=False):
        return {'status':'live','heroId':0,'turnSerial':serial,'activePlayer':active,'over':over,'shots':[], 'players':[{'id':0,'x':0,'y':0,'hp':1000,'shield':0,'dead':hero_dead},{'id':1,'x':500,'y':0,'hp':enemy,'shield':0,'dead':enemy_dead}]}
    def test_health_window_separates_observed_loss_from_confirmed_hit(self):
        with tempfile.TemporaryDirectory() as tmp:
            callback=Mock();metrics=BattleMetrics(Path(tmp)/'battle.json',callback)
            metrics.observe(self.state());metrics.note({'hero':0,'turn_serial':1,'health_before':{'0':1000,'1':120}}, {'target_id':1},self.state(),'shot-a')
            metrics.observe(self.state(2,1,80));row=callback.call_args.args[0]
            self.assertTrue(row['known']);self.assertEqual(row['enemy_health_drop'],40);self.assertFalse(row['confirmed_impact'])
    def test_intervening_enemy_projectile_makes_health_attribution_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            callback=Mock();metrics=BattleMetrics(Path(tmp)/'battle.json',callback);metrics.observe(self.state())
            metrics.note({'hero':0,'turn_serial':1,'health_before':{'1':120}}, {'target_id':1},self.state(),'shot-a')
            state=self.state(2,1,80);state['shots']=[{'id':8,'native':True,'start':[500,0,45,200,0,400]}];metrics.observe(state)
            self.assertFalse(callback.call_args.args[0]['known']);self.assertIsNone(callback.call_args.args[0]['enemy_health_drop'])
    def test_result_missing_is_unknown_and_gameover_is_not_counted_repeatedly(self):
        with tempfile.TemporaryDirectory() as tmp:
            metrics=BattleMetrics(Path(tmp)/'battle.json');metrics.observe(self.state());metrics.end()
            self.assertEqual(metrics.summary()['unknown_results'],1);self.assertIsNone(metrics.summary()['win_rate'])
            metrics.observe(self.state(over=True));self.assertEqual(len(metrics.games),1)
    def test_confirmed_survival_outcomes_are_recorded_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            metrics=BattleMetrics(Path(tmp)/'battle.json');metrics.observe(self.state());metrics.observe(self.state(over=True,enemy_dead=True));metrics.observe(self.state(over=True,enemy_dead=True))
            self.assertEqual(metrics.summary()['wins'],1);self.assertEqual(metrics.summary()['win_rate'],100)
            metrics.observe(self.state());metrics.observe(self.state(over=True,hero_dead=True))
            self.assertEqual(metrics.summary()['losses'],1);self.assertEqual(metrics.summary()['win_rate'],50)
    def test_absent_health_does_not_mean_zero_damage_or_zero_hp(self):
        self.assertIsNone(health({'hp':100}));self.assertEqual(health({'hp':100,'shield':20}),120)

class EvaluationControllerTests(unittest.TestCase):
    def test_failed_evaluation_never_changes_to_another_weapon_or_retries_same_turn(self):
        from training_controller import TrainingController
        with tempfile.TemporaryDirectory() as tmp:
            session=TrainingSession('',None,Path(tmp)/'book.json',lambda e:None,max_shots=20,autonomous=True,objective='evaluation')
            session.cancel.wait=Mock(return_value=False);controller=TrainingController(session);browser=Mock()
            browser.guard.return_value={'game':True,'url':'https://dragonbound.net/#server-8/room-1','controls':{'btnShot1':{'x':1,'y':1},'btnShot2':{'x':1,'y':1}},'options':[]}
            browser.shoot.side_effect=NoAim('No validated trajectory')
            for turn in range(1,7):
                browser.sample.return_value={'status':'live','heroId':0,'activePlayer':0,'turnSerial':turn,'wind':0,'windAngle':0,'players':[{'id':0,'x':0,'y':0,'mobile':0}],'shots':[]}
                controller.cycle(browser);controller.cycle(browser)
            self.assertEqual(browser.shoot.call_count,6)
            self.assertTrue(all(call.args[0]['shot']==0 for call in browser.shoot.call_args_list))
            self.assertEqual(session.shots,0);self.assertTrue(controller.trial.done())

class MeasurementHypothesisTests(unittest.TestCase):
    def sample(self,n,p,scale=2):return {'id':str(n),'power':p,'speed':scale*p+20,'ax':40,'ay':400,'wind':10,'wind_angle':0,'heading':45,'duration_s':1,'simple':True,'episode':'match-a'}
    def test_prior_is_measured_but_not_mislabeled_as_validated(self):
        from training_evaluation import measured_prior
        rows=[self.sample(n,p) for n,p in enumerate([100,300,180,360,120,320])]
        prior=measured_prior(rows);self.assertAlmostEqual(prior['scale'],2);self.assertAlmostEqual(prior['offset'],20)
        self.assertEqual(prior['source'],'measured-prior-unvalidated');self.assertIsNone(measured_prior(rows[:2]))
    def test_adaptation_uses_new_measured_speed_without_mutating_the_reference(self):
        from training_evaluation import adapted_hypothesis
        prior={'scale':2,'offset':20,'gravity':400,'wind_scale':4}
        candidate=adapted_hypothesis(prior,[self.sample(1,150,2.5),self.sample(2,180,2.5)])
        self.assertAlmostEqual(candidate['scale'],2.5);self.assertEqual(prior['scale'],2)
        self.assertIn('needs-future-checks',candidate['source'])
    def test_known_release_can_be_attributed_after_crater_drop_but_not_reused(self):
        from shot_attribution import attributed_start,identity
        shot={'id':8,'native':True,'elapsed':900,'start':[10,20,45,300,0,400],'shotType':0,'metadata':{}}
        state={'heroId':0,'activePlayer':-1,'players':[{'id':0,'x':10,'y':45,'mobile':0},{'id':1,'x':500,'y':20}]}
        release={'hero':0,'x':10,'y':20,'power':150,'shot':0,'wind':0,'windAngle':0,'baseline':[]}
        self.assertTrue(attributed_start(state,shot,release)['learnable'])
        self.assertIsNone(attributed_start(state,shot))
        release['baseline']=[identity(shot)];self.assertIsNone(attributed_start(state,shot,release))
    def test_release_for_another_weapon_does_not_poison_the_calibration(self):
        from shot_attribution import attributed_start
        shot={'id':8,'native':True,'elapsed':100,'start':[10,20,45,300,0,400],'shotType':1,'metadata':{}}
        state={'heroId':0,'activePlayer':-1,'players':[{'id':0,'x':10,'y':20,'mobile':0},{'id':1,'x':500,'y':20}]}
        release={'hero':0,'x':10,'y':20,'power':150,'shot':0,'wind':0,'windAngle':0,'baseline':[]}
        self.assertIsNone(attributed_start(state,shot,release))
