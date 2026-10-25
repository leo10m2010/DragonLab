import json,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from autonomous_learning import AutonomousLearner
from continuous_training import DeadlineCancel,RollingEvaluation,transient_browser_error,ObservationArchiveError
from training_aim import NoAim
from training_controller import TrainingController
from training_session import TrainingSession

def weather_row(token='old'):
    return {'token':token,'episode':'match','profile':'dragonbound:ARMOR:0','weather_kinds':['3'],'power':180,'health_window_known':False,'enemy_health_drop':None}

class DeadlineTests(unittest.TestCase):
    def test_wait_and_input_guard_share_the_deadline_and_original_stop_event(self):
        event=Mock();event.is_set.return_value=False;event.wait.return_value=False
        cancel=DeadlineCancel(event,100)
        with patch('continuous_training.time.monotonic',return_value=99):
            self.assertFalse(cancel.is_set());self.assertFalse(cancel.wait(15))
        event.wait.assert_called_once_with(1)
        with patch('continuous_training.time.monotonic',return_value=100):
            self.assertTrue(cancel.is_set());self.assertTrue(cancel.wait(.1))
        cancel.set();event.set.assert_called_once()
    def test_continuous_bypasses_shot_count_but_never_wall_clock_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            session=TrainingSession('',None,Path(folder)/'book.json',Mock(),continuous=True,max_seconds=86400)
            controller=TrainingController(session);session.shots=10000
            with patch('training_controller.time.monotonic',return_value=86399):self.assertTrue(controller.within_limits(0))
            with patch('training_controller.time.monotonic',return_value=86400):self.assertFalse(controller.within_limits(0))
            session.continuous=False
            with patch('training_controller.time.monotonic',return_value=1):self.assertFalse(controller.within_limits(0))

class RollingTests(unittest.TestCase):
    def make(self,folder):
        learner=AutonomousLearner(Path(folder)/'learner.json');learner.episode='match'
        return RollingEvaluation(folder,learner,40)
    def test_blocks_archive_individually_and_totals_do_not_invent_directed_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            rolling=self.make(folder);first=rolling.current;first.weather_rows=[weather_row()]
            rolling.rollover();second=rolling.current;second.weather_rows=[weather_row('next')]
            report=rolling.report();self.assertEqual(report['completed_blocks'],1);self.assertEqual(report['totals']['weather_practice_shots'],2)
            self.assertEqual(report['totals']['directed_test_shots'],0);self.assertEqual(report['completed_shots'],1)
            self.assertNotEqual(first.path,second.path);self.assertTrue(first.path.exists())
            archived=json.loads(first.path.read_text());self.assertEqual(len(archived['weather_practice']),1)
            another=self.make(folder);self.assertNotEqual(rolling.directory,another.directory)
    def test_numeric_context_and_validation_ids_survive_mid_match_rollover(self):
        with tempfile.TemporaryDirectory() as folder:
            rolling=self.make(folder);previous=rolling.current;profile=previous.profile('ARMOR',0)
            previous.focus_mobile='ARMOR';previous.focus_modes={'ARMOR':1}
            profile.episode='match';profile.warmups=4;profile.frozen={'model':{'scale':2,'offset':0,'gravity':400,'wind_scale':4},'wind':0,'angle':0}
            profile.context_candidate={'model':{'scale':2},'training_ids':{'train'}};profile.prior_training_ids={'historic'}
            rolling.rollover();continued=rolling.current.profile('ARMOR',0)
            self.assertEqual(continued.frozen,profile.frozen);self.assertIsNot(continued.frozen,profile.frozen)
            self.assertEqual(continued.context_candidate,profile.context_candidate);self.assertEqual(continued.prior_training_ids,{'historic'})
            self.assertEqual((continued.episode,continued.warmups),('match',4));self.assertEqual(rolling.current.focus_modes,{'ARMOR':1})
            self.assertFalse(continued.finished);self.assertFalse(continued.tests);self.assertFalse(continued.calibration)
    def test_calibration_budget_does_not_refill_at_block_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            rolling=self.make(folder);profile=rolling.current.profile('ARMOR',0);profile.episode='match'
            # Rows assigned by older clients still reserve their episode budget.
            profile.calibration=[{'episode':'match'} for _ in range(12)]
            rolling.rollover();continued=rolling.current.profile('ARMOR',0)
            with self.assertRaises(NoAim) as raised:continued.plan({'wind':0,'windAngle':0},{},continued.probe())
            self.assertEqual(raised.exception.reason,'calibration-budget')
            rolling.learner.episode='next-match';continued.reset_episode();self.assertEqual(continued.episode_calibration_count,0)
    def test_completed_block_summaries_are_bounded_without_deleting_raw_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            rolling=self.make(folder);first=rolling.current.path
            for _ in range(27):rolling.rollover()
            self.assertEqual(rolling.report()['completed_blocks'],27);self.assertEqual(len(rolling.latest),24)
            self.assertTrue(first.exists());self.assertEqual(len(list(rolling.directory.glob('bloque-*/evaluacion-adaptativa.json'))),27)
    def test_practice_and_damage_experience_is_carried_without_counting_as_new_tests(self):
        with tempfile.TemporaryDirectory() as folder:
            rolling=self.make(folder);profile=rolling.current.profile('ARMOR',0)
            profile.experience_tests=[{'token':str(n)} for n in range(150)]
            profile.experience_calibration=[{'token':'cal'}];profile.directed_test_count=150
            rolling.current.weather_rows=[weather_row()];rolling.current.experience_recovery_rows=[{'token':'dig','episode':'match'}]
            rolling.rollover();continued=rolling.current.profile('ARMOR',0)
            self.assertEqual(len(continued.experience_tests),96);self.assertEqual(continued.directed_test_count,150)
            self.assertEqual(len(rolling.current.experience_weather_rows),1);self.assertEqual(len(rolling.current.experience_recovery_rows),1)
            self.assertEqual(rolling.current.summary()['directed_test_shots'],0)

class ControllerRolloverTests(unittest.TestCase):
    def make(self,folder):
        session=TrainingSession('',None,Path(folder)/'book.json',Mock(),continuous=True,autonomous=True,objective='adaptive',max_seconds=86400,max_shots=40)
        session.cancel.wait=Mock(return_value=False);session.publish=Mock()
        return session,TrainingController(session)
    def browser(self,serial=1):
        browser=Mock();browser.sample.return_value={'status':'live','heroId':0,'activePlayer':1,'turnSerial':serial,'players':[{'id':0,'x':0,'y':0,'hp':500,'shield':0},{'id':1,'x':300,'y':0,'hp':460,'shield':0}],'shots':[]}
        return browser
    def test_pending_health_results_settle_on_old_trial_before_new_block(self):
        with tempfile.TemporaryDirectory() as folder:
            session,controller=self.make(folder);old=controller.trial;old.weather_rows=[weather_row()]
            controller.battle.pending=[{'token':'old','hero':0,'target':1,'turn':1,'before':{'1':500},'expires':time.monotonic()+20,'ambiguous':False,'baseline':[]}]
            controller.current=('room','0',1);controller.ledger.consume(controller.current);controller.recovery_state={'key':controller.current,'steps':2};context=controller.recovery_state
            browser=self.browser();browser.sample.return_value['activePlayer']=0
            self.assertFalse(controller.next_block(browser,{'game':True}));self.assertIs(controller.trial,old);browser.shoot.assert_not_called()
            browser.sample.return_value.update(turnSerial=2,activePlayer=1)
            self.assertTrue(controller.next_block(browser,{'game':True}));self.assertIsNot(controller.trial,old)
            self.assertTrue(old.weather_rows[0]['health_window_known']);self.assertEqual(old.weather_rows[0]['enemy_health_drop'],40)
            self.assertIs(controller.recovery_state,context);self.assertFalse(controller.ledger.available(controller.current))
            self.assertEqual(session.report['block'],2);self.assertEqual(controller.trial.weather_rows,[])
    def test_expired_unknown_window_does_not_block_forever_or_invent_damage(self):
        with tempfile.TemporaryDirectory() as folder:
            _,controller=self.make(folder);old=controller.trial;old.weather_rows=[weather_row()]
            controller.battle.pending=[{'token':'old','hero':0,'target':1,'turn':1,'before':{'1':500},'expires':time.monotonic()-1,'ambiguous':False,'baseline':[]}]
            browser=self.browser();browser.sample.return_value={'status':'waiting'}
            self.assertTrue(controller.next_block(browser,{'game':True}));self.assertFalse(old.weather_rows[0]['health_window_known'])
            self.assertIsNone(old.weather_rows[0]['enemy_health_drop'])
    def test_unknown_alert_pauses_continuous_without_dismissing_or_shooting(self):
        with tempfile.TemporaryDirectory() as folder:
            session,controller=self.make(folder);browser=self.browser();browser.guard.return_value={'blocked':True}
            controller.cycle(browser);browser.click.assert_not_called();browser.shoot.assert_not_called()
            self.assertIn('pausa',session.publish.call_args.args[0])
    def test_missing_selected_tab_retries_without_reloading_or_changing_target(self):
        with tempfile.TemporaryDirectory() as folder:
            session,controller=self.make(folder);browser=self.browser();controller.cycle=Mock(return_value=False)
            with patch('training_controller.TrainingBrowser',side_effect=[RuntimeError('La página seleccionada no está abierta en el navegador de depuración'),browser]) as factory,patch('training_power.SleepLease'):
                controller.run()
            self.assertEqual(factory.call_count,2);self.assertIsNotNone(session.started_at);self.assertIsNotNone(session.started_wall)
            self.assertEqual(session.last_error,'');browser.arm.assert_called_once_with(focus=True)
    def test_rollover_allows_next_authoritative_turn_but_never_repeats_used_one(self):
        with tempfile.TemporaryDirectory() as folder:
            session,controller=self.make(folder);controller.trial.weather_rows=[weather_row(str(n)) for n in range(40)]
            room='https://dragonbound.net/#server-8/room-1';key=(room,'0',1);controller.ledger.consume(key)
            controller.in_game=True;controller.current=key;session.shots=40;session.matches=6
            browser=self.browser();browser.guard.return_value={'game':True,'url':room,'controls':{'btnShot1':True},'options':[]}
            browser.sample.return_value.update(activePlayer=0,wind=0,windAngle=0)
            browser.sample.return_value['players'][0]['mobile']=0
            controller.cycle(browser);browser.shoot.assert_not_called();self.assertEqual(session.report['block'],2)
            controller.trial.probe=Mock(return_value={'mobile':'ARMOR','shot':0,'power':100})
            browser.sample.return_value['turnSerial']=2
            def shoot(probe,cancel,**options):options['before_fire']();return {},{}
            browser.shoot.side_effect=shoot;controller.observe=Mock()
            controller.cycle(browser);controller.observe.assert_called_once();self.assertIn((room,'0',2),controller.ledger.used)
            self.assertEqual((session.shots,session.matches),(40,6))
    def test_context_loss_reconnects_without_releasing_the_reserved_turn(self):
        with tempfile.TemporaryDirectory() as folder:
            session,controller=self.make(folder);first=self.browser();second=self.browser()
            key=('room','0',1);controller.ledger.consume(key)
            def cycle(browser):
                if browser is first:raise RuntimeError('Cannot find context with specified id')
                self.assertFalse(controller.ledger.available(key));return False
            controller.cycle=cycle
            with patch('training_controller.TrainingBrowser',side_effect=[first,second]),patch('training_power.SleepLease'):
                controller.run()
            first.close.assert_called_once();second.arm.assert_called_once_with(focus=False)
            self.assertEqual(session.last_error,'')
    def test_context_classifier_does_not_hide_game_or_control_errors(self):
        for message in ('Cannot find context with specified id','Could not find object with given id','Execution context was destroyed, most likely because of a navigation.'):
            self.assertTrue(transient_browser_error(RuntimeError(message)))
        for message in ('Angle stuck','Tres fallos de control','Servidor no autorizado','Otra sesión controla esta pestaña'):
            self.assertFalse(transient_browser_error(RuntimeError(message)))
    def test_dom_flash_preserves_episode_turn_and_movement_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            session,controller=self.make(folder);browser=self.browser();room='https://dragonbound.net/#server-8/room-1';key=(room,'0',1)
            controller.in_game=True;controller.current=key;controller.ledger.consume(key)
            controller.recovery_state.update(key=key,steps=2);episode=controller.learner.episode
            browser.guard.return_value={'game':False,'url':room,'controls':{},'options':[]}
            controller.cycle(browser)
            self.assertEqual(controller.recovery_state['steps'],2);self.assertTrue(controller.in_game)
            browser.guard.return_value['game']=True
            browser.sample.return_value.update(activePlayer=0,wind=0,windAngle=0)
            controller.cycle(browser)
            browser.shoot.assert_not_called();self.assertEqual(controller.learner.episode,episode)
            self.assertFalse(controller.ledger.available(key))
    def test_precharge_dig_reservation_survives_ambiguous_release(self):
        with tempfile.TemporaryDirectory() as folder:
            _,controller=self.make(folder);browser=self.browser();trial=controller.trial
            key=('room','0',3);profile=trial.profile('ARMOR',0)
            browser.prepared_plan={'action':'abrir paso','evaluation_phase':'recovery','profile':profile.key,'expected_terrain_impact':[220,100]}
            controller.reserve_turn(browser,key)
            self.assertFalse(controller.ledger.available(key));self.assertEqual(len(trial.reserved_recoveries),1)
            self.assertFalse(trial.reserved_recoveries[0]['confirmed']);self.assertEqual(trial.summary()['terrain_attempts'],0)
            controller.rolling.rollover()
            self.assertEqual(len(controller.rolling.current.experience_reserved_recoveries),1)
    def test_failed_report_write_still_releases_browser_and_sleep_lease(self):
        with tempfile.TemporaryDirectory() as folder:
            session,controller=self.make(folder);browser=self.browser();controller.cycle=Mock(return_value=False)
            controller.trial.finish=Mock(side_effect=OSError('disk'))
            with patch('training_controller.TrainingBrowser',return_value=browser),patch('training_power.SleepLease') as power:
                controller.run()
            browser.close.assert_called_once();power.return_value.close.assert_called_once()
            self.assertFalse(session.running);self.assertIn('guardar',session.last_error)

class ArchiveTests(unittest.TestCase):
    def make(self,folder):
        learner=AutonomousLearner(Path(folder)/'learner.json');learner.episode='match'
        rolling=RollingEvaluation(folder,learner,40)
        probe={'mobile':'ARMOR','shot':0}
        release={'hero':0,'x':100,'y':100,'power':100,'angle':45,'shot':0,'wind':0,'windAngle':90,'baseline':[],'learner':{'evaluation_phase':'calibration'},'password':'secret'}
        state={'heroId':0,'activePlayer':0,'players':[{'id':0,'x':100,'y':100,'mobile':0,'name':'private-name'},{'id':1,'x':400,'y':100}], 'weather':[{'typeId':3,'x':200,'size':25,'account':'secret'}], 'shots':[{'id':'own','native':True,'elapsed':0,'duration':2000,'start':[100,90,45,220,0,400],'shotType':0},{'id':'enemy','native':True,'elapsed':0,'duration':2000,'start':[400,90,45,220,0,400],'metadata':{'player':1}}]}
        return rolling,probe,release,state
    def test_archive_retains_numeric_evidence_past_bounded_history_and_rollover(self):
        with tempfile.TemporaryDirectory() as folder:
            rolling,probe,release,state=self.make(folder)
            for _ in range(100):rolling.record(probe,release,state)
            rolling.rollover();rolling.record(probe,release,state)
            text=(rolling.directory/'observaciones-nativas.jsonl').read_text();rows=[json.loads(line) for line in text.splitlines()]
            self.assertEqual(len(rows),101);self.assertEqual(rows[-1]['block'],2)
            self.assertEqual(rows[0]['native'][0]['start'],[100,90,45,220,0,400]);self.assertEqual(len(rows[0]['native']),1)
            for secret in ('password','secret','private-name','enemy'):self.assertNotIn(secret,text)
    def test_nonfinite_or_malformed_values_never_pollute_raw_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            rolling,probe,release,state=self.make(folder);release['angle']=float('nan')
            state['weather'][0]['size']=float('inf');state['shots'][0]['duration']=float('nan')
            state['shots'].append({'native':True,'start':[None]})
            rolling.record(probe,release,state)
            row=json.loads((rolling.directory/'observaciones-nativas.jsonl').read_text())
            self.assertIsNone(row['angle']);self.assertIsNone(row['weather'][0]['size']);self.assertIsNone(row['native'][0]['duration'])
    def test_archive_preserves_planned_and_observed_origin_for_future_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            rolling,probe,release,state=self.make(folder)
            release['learner'].update(origin=[100,90],origin_source='native-shot-muzzle')
            rolling.record(probe,release,state)
            row=json.loads((rolling.directory/'observaciones-nativas.jsonl').read_text())
            self.assertEqual(row['planned_origin'],[100,90]);self.assertEqual(row['origin_error_px'],0)
    def test_archive_failure_is_explicit_and_never_a_transient_reconnect(self):
        with tempfile.TemporaryDirectory() as folder:
            rolling,probe,release,state=self.make(folder)
            with patch('continuous_training.os.fsync',side_effect=OSError('disk')):
                with self.assertRaises(ObservationArchiveError) as raised:rolling.record(probe,release,state)
            self.assertFalse(transient_browser_error(raised.exception))

if __name__=='__main__':unittest.main()
