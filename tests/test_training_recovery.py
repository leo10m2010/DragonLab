import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from training_input import RecoverableInputError
from training_controller import TrainingController
from training_session import TrainingSession
from continuous_training import ObservationArchiveError


def state(serial):return {'status':'live','turnSerial':serial,'heroId':0,'activePlayer':0,'wind':0,'windAngle':0,'players':[{'id':0,'mobile':0,'x':0,'y':0}]}
def view():return {'url':'https://dragonbound.net/#server-8/room-1','game':True,'options':[],'controls':{'btnShot1':{'x':1,'y':1}}}


class RecoveryTests(unittest.TestCase):
    def make(self,folder):
        session=TrainingSession('',None,Path(folder)/'book.json',Mock(),continuous=True,max_seconds=86400)
        session.cancel.wait=Mock(return_value=False);session.publish=Mock()
        browser=Mock();browser.guard.return_value=view();browser.sample.return_value=state(1)
        controller=TrainingController(session);controller.observe=Mock()
        return session,controller,browser
    def test_long_replay_never_repeats_reserved_turns_across_input_errors_and_reconnects(self):
        with tempfile.TemporaryDirectory() as folder:
            s,c,b=self.make(folder);attempted=[];connected=[b];s.started_at=0
            def shoot(probe,cancel,settings_provider,before_fire):
                before_fire();serial=probe['turn_serial'];attempted.append(serial)
                if serial%29==0:raise ConnectionError('reply lost after reserved charge')
                if serial%11==0:raise RecoverableInputError('drag ack unavailable',method='drag',code='drag-not-started')
                return {},{}
            b.shoot.side_effect=shoot
            for serial in range(1,1001):
                native=state(serial);b.sample.return_value=native
                with patch('training_controller.time.monotonic',return_value=serial*86):
                    self.assertTrue(c.within_limits(0))
                    try:c.cycle(b)
                    except ConnectionError:
                        # Reconnect the transport while retaining the controller.
                        b=Mock();b.guard.return_value=view();b.sample.return_value=native;b.shoot.side_effect=shoot;connected.append(b)
                    c.cycle(b)
            self.assertEqual(attempted,list(range(1,1001)))
            self.assertGreater(len(connected),20);self.assertGreater(s.input_recoveries,50)
            with patch('training_controller.time.monotonic',return_value=86400):self.assertFalse(c.within_limits(0))
    def test_recoverable_charge_failure_keeps_ledger_and_never_retries_same_turn(self):
        with tempfile.TemporaryDirectory() as folder:
            s,c,b=self.make(folder);ledger=c.ledger
            def shoot(probe,cancel,settings_provider,before_fire):before_fire();raise RecoverableInputError('native ack timeout',method='drag',code='start-timeout')
            b.shoot.side_effect=shoot
            with patch('training_controller.time.monotonic',return_value=100):c.cycle(b);c.cycle(b)
            b.shoot.assert_called_once();self.assertIs(c.ledger,ledger);self.assertEqual(len(c.ledger.used),1)
            self.assertEqual(c.input_recovery['drag_disabled_until'],280);self.assertIs(s.input_recovery,c.input_recovery)
            self.assertEqual(s.input_recoveries,1);self.assertEqual(s.input_recovery_counts,{'drag':1});self.assertEqual(s.last_recovery_code,'start-timeout');self.assertEqual(s.last_error,'')
            self.assertEqual(s.errors[-1]['kind'],'input-recovery');self.assertEqual(c.failures,0)
    def test_three_known_drag_failures_recover_without_creating_a_new_controller(self):
        with tempfile.TemporaryDirectory() as folder:
            s,c,b=self.make(folder);learner=Mock();learner.choose_probe.return_value={'mobile':'ARMOR','shot':0,'angle':45,'power':100};c.learner=learner;c.trial=None
            c.recovery_state={'turn':'preserved'};s.started_at=5;s.started_wall=20
            b.shoot.side_effect=RecoverableInputError('drag did not start',method='drag',code='start-timeout')
            for serial in (1,2,3):
                b.sample.return_value=state(serial)
                with patch('training_controller.time.monotonic',return_value=100+serial):c.cycle(b)
            self.assertIs(c.learner,learner);self.assertEqual(len(c.ledger.used),3);self.assertEqual(s.started_at,5);self.assertEqual(s.started_wall,20)
            self.assertEqual(s.input_recoveries,3);self.assertEqual(c.recovery_state,{'turn':'preserved'});self.assertFalse(s.last_error)
    def test_next_native_turn_can_fire_once_and_resets_recovery_streak(self):
        with tempfile.TemporaryDirectory() as folder:
            s,c,b=self.make(folder)
            def shoot(probe,cancel,settings_provider,before_fire):
                before_fire()
                if probe['turn_serial']==1:raise RecoverableInputError('drag did not start',method='drag',code='start-timeout')
                return {},{}
            b.shoot.side_effect=shoot;c.cycle(b);b.sample.return_value=state(2);c.cycle(b);c.cycle(b)
            self.assertEqual(b.shoot.call_count,2);self.assertEqual(len(c.ledger.used),2);c.observe.assert_called_once()
    def test_space_recovery_does_not_invent_drag_cooldown(self):
        with tempfile.TemporaryDirectory() as folder:
            s,c,b=self.make(folder);key=('room','0',1)
            c.recover_input(key,RecoverableInputError('space timeout',method='space',code='charge-timeout'))
            self.assertNotIn('drag_disabled_until',c.input_recovery);self.assertEqual(s.input_recovery_counts,{'space':1})
    def test_recovery_backoff_is_bounded_and_cancellable(self):
        with tempfile.TemporaryDirectory() as folder:
            s,c,b=self.make(folder)
            for serial in range(20):c.recover_input(('room','0',serial),RecoverableInputError('start timeout',method='drag',code='start-timeout'))
            waits=[call.args[0] for call in s.cancel.wait.call_args_list]
            self.assertGreater(min(waits),0);self.assertLessEqual(max(waits),2);self.assertEqual(s.input_recoveries,20)
    def test_unknown_control_failure_still_stops_after_three(self):
        with tempfile.TemporaryDirectory() as folder:
            s,c,b=self.make(folder);b.shoot.side_effect=RuntimeError('unknown unsafe control')
            for serial in (1,2):b.sample.return_value=state(serial);c.cycle(b)
            b.sample.return_value=state(3)
            with self.assertRaisesRegex(RuntimeError,'Tres fallos'):c.cycle(b)
            self.assertEqual(s.input_recoveries,0)
    def test_archive_failure_is_never_downgraded_to_input_recovery(self):
        with tempfile.TemporaryDirectory() as folder:
            s,c,b=self.make(folder);b.shoot.side_effect=ObservationArchiveError('archive unavailable')
            with self.assertRaises(ObservationArchiveError):c.cycle(b)
            self.assertEqual(s.input_recoveries,0)
    def test_reconnect_retains_the_shared_input_fallback_state(self):
        with tempfile.TemporaryDirectory() as folder:
            s,c,b=self.make(folder);next_browser=Mock();c.input_recovery['drag_disabled_until']=999999999
            calls=[]
            def cycle(browser):
                calls.append(browser)
                if len(calls)==1:raise ConnectionError('connection lost')
                return False
            c.cycle=cycle
            with patch('training_controller.TrainingBrowser',side_effect=[b,next_browser]),patch('training_power.SleepLease'):c.run()
            self.assertIs(b.input_recovery,c.input_recovery);self.assertIs(next_browser.input_recovery,c.input_recovery);self.assertEqual(s.reconnects,1)
    def test_watchdog_refreshes_connection_without_forgetting_reserved_turn(self):
        with tempfile.TemporaryDirectory() as folder:
            s,c,b=self.make(folder);key=('room','0',9);c.ledger.consume(key);ledger=c.ledger
            with patch('training_controller.time.monotonic',return_value=100):c.watch_native_progress(('game',9))
            with patch('training_controller.time.monotonic',return_value=219):c.watch_native_progress(('game',9))
            with patch('training_controller.time.monotonic',return_value=220):
                with self.assertRaisesRegex(ConnectionError,'sin salir'):c.watch_native_progress(('game',9))
            self.assertIs(c.ledger,ledger);self.assertFalse(c.ledger.available(key));self.assertEqual(s.watchdog_reconnects,1)
            b.click.assert_not_called();b.shoot.assert_not_called()
    def test_native_progress_resets_watchdog_but_polling_alone_does_not(self):
        with tempfile.TemporaryDirectory() as folder:
            s,c,b=self.make(folder)
            with patch('training_controller.time.monotonic',return_value=100):c.watch_native_progress(('game',1))
            with patch('training_controller.time.monotonic',return_value=200):c.watch_native_progress(('game',2))
            with patch('training_controller.time.monotonic',return_value=319):c.watch_native_progress(('game',2))
            self.assertEqual(c.watchdog_at,200);self.assertEqual(s.watchdog_reconnects,0)
    def test_known_modal_loading_and_retirement_do_not_trigger_watchdog(self):
        with tempfile.TemporaryDirectory() as folder:
            s,c,b=self.make(folder)
            for special in ({'blocked':True},{'loading':True},{'retirement':{'seconds':59,'point':{}}}):
                c.watchdog_token=('old',);c.watchdog_at=0;b.guard.return_value={**view(),**special}
                with patch('training_controller.time.monotonic',return_value=1000):c.cycle(b)
                self.assertIsNone(c.watchdog_at);self.assertEqual(s.watchdog_reconnects,0)
    def test_observation_marks_real_shot_progress_and_resets_recovery_streak(self):
        with tempfile.TemporaryDirectory() as folder:
            s,c,b=self.make(folder);s.input_recovery_streak=4
            with patch('training_controller.time.monotonic',return_value=100):TrainingController.observe(c,{'mobile':'ARMOR','shot':0,'power':222,'turn_serial':1},{'power':222,'angle':45},{})
            self.assertEqual(s.shots,1);self.assertEqual(s.input_recovery_streak,0);self.assertEqual(s.confirmed_shot_at,100)
    def test_completed_block_with_missing_game_is_covered_by_watchdog(self):
        with tempfile.TemporaryDirectory() as folder:
            s,c,b=self.make(folder);c.in_game=True;key=('room','0',3);c.ledger.consume(key)
            with patch('training_controller.time.monotonic',return_value=100):self.assertFalse(c.next_block(b,{'game':False,'url':'room'}))
            with patch('training_controller.time.monotonic',return_value=220):
                with self.assertRaises(ConnectionError):c.next_block(b,{'game':False,'url':'room'})
            self.assertFalse(c.ledger.available(key));b.click.assert_not_called()
    def test_completed_block_cannot_hide_a_known_notice_behind_rollover_wait(self):
        with tempfile.TemporaryDirectory() as folder:
            s,c,b=self.make(folder);c.in_game=True;c.trial=Mock();c.trial.done.return_value=True;c.rolling=Mock();c.next_block=Mock()
            b.guard.return_value={**view(),'game':False,'blocked':True,'notice':{'kind':'gift-received','point':{'x':1,'y':1}}}
            c.cycle(b);b.click.assert_called_once();c.next_block.assert_not_called()


class SessionHealthTests(unittest.TestCase):
    def test_heartbeat_polling_does_not_masquerade_as_game_progress(self):
        s=TrainingSession('',None,'book.json',Mock());s.started_at=100
        with patch('training_session.time.monotonic',return_value=105):s.heartbeat('waiting-turn')
        with patch('training_session.time.monotonic',return_value=125):health=s.health()
        self.assertEqual(health['heartbeat_age_seconds'],20);self.assertEqual(health['progress_age_seconds'],25)
        self.assertEqual(health['shot_age_seconds'],25);self.assertEqual(health['last_progress_kind'],'')
    def test_native_turn_progress_does_not_reset_last_confirmed_shot_age(self):
        s=TrainingSession('',None,'book.json',Mock());s.started_at=100
        with patch('training_session.time.monotonic',return_value=110):s.heartbeat('playing',progress='shot-confirmed')
        with patch('training_session.time.monotonic',return_value=130):s.heartbeat('playing',progress='native-turn')
        with patch('training_session.time.monotonic',return_value=140):health=s.health()
        self.assertEqual(health['progress_age_seconds'],10);self.assertEqual(health['shot_age_seconds'],30)
    def test_recovery_cooldown_and_health_are_saved_without_monotonic_timestamps(self):
        with tempfile.TemporaryDirectory() as folder:
            s=TrainingSession('',None,Path(folder)/'book.json',Mock());s.started_at=100;s.started_wall=1000
            s.input_recovery['drag_disabled_until']=300;s.input_recoveries=2;s.input_recovery_counts={'drag':2};s.last_recovery_code='start-timeout'
            with patch('training_session.time.monotonic',return_value=150):s.heartbeat('input-recovery');s.publish('Entrada recuperada')
            data=json.loads((Path(folder)/'entrenamiento-estado.json').read_text())
            self.assertEqual(data['health']['drag_retry_after_seconds'],150);self.assertEqual(data['health']['input_recoveries'],2)
            self.assertNotIn('drag_disabled_until',json.dumps(data));self.assertNotIn('heartbeat_at',json.dumps(data))
    def test_state_write_failure_is_visible_in_memory_and_clearable(self):
        with tempfile.TemporaryDirectory() as folder:
            s=TrainingSession('',None,Path(folder)/'book.json',Mock())
            with patch('training_session.atomic_write',side_effect=OSError('disk unavailable')):s.publish('First')
            self.assertTrue(s.health()['status_write_error']);s.publish('Recovered');self.assertFalse(s.health()['status_write_error'])

if __name__=='__main__':unittest.main()
