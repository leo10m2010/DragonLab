import unittest,tempfile,threading
from pathlib import Path
from unittest.mock import Mock,patch
from training_turns import TurnLedger,turn_key
from training_controller import TrainingController
from training_session import TrainingSession
from training_browser import TurnExpired,UnconfirmedShot,TrainingBrowser
from training_aim import NoAim,choose_aim,actual_solution
from training_movement import walking_step
from core import Settings
from training_power import SleepLease

class SleepLeaseTests(unittest.TestCase):
    def test_sleep_lease_is_transient_and_releases_on_close(self):
        setter=Mock(return_value=1);lease=SleepLease(setter)
        lease.hold(True);lease.hold(True);lease.close()
        self.assertEqual([c.args[0] for c in setter.call_args_list],[0x80000001,0x80000000])
    def test_failed_lease_does_not_claim_that_sleep_is_prevented(self):
        lease=SleepLease(Mock(return_value=0));lease.hold(True)
        self.assertFalse(lease.active)

def state(serial=1,active=0):
    return {'status':'live','turnSerial':serial,'heroId':0,'activePlayer':active,'wind':5,'players':[{'id':0,'mobile':0,'x':100,'y':100,'dead':False}]}
def ui():return {'url':'https://dragonbound.net/#server-8/room-1','game':True,'options':[],'controls':{'btnShot1':{},'btnShot2':{},'btnShotSS':{}}}

class TurnTests(unittest.TestCase):
    def test_consecutive_own_turn_is_available_without_seeing_enemy(self):
        ledger=TurnLedger();key=turn_key(state(1),'room');ledger.consume(key)
        self.assertFalse(ledger.available(turn_key(state(1),'room')))
        self.assertTrue(ledger.available(turn_key(state(2),'room')))
    def test_no_authoritative_turn_or_enemy_turn_never_allows_a_shot(self):
        self.assertIsNone(turn_key(state(None),'room'));self.assertIsNone(turn_key(state(1,1),'room'))
        s=state();s['over']=True;self.assertIsNone(turn_key(s,'room'))
    def test_wind_changes_do_not_authorize_a_duplicate_and_rooms_are_distinct(self):
        ledger=TurnLedger();ledger.consume(turn_key(state(1),'room-1'))
        s=state();s['wind']=24
        self.assertFalse(ledger.available(turn_key(s,'room-1')))
        self.assertTrue(ledger.available(turn_key(s,'room-2')))
    def test_ledger_remains_bounded_for_long_sessions(self):
        ledger=TurnLedger()
        for n in range(10000):ledger.consume(('room','0',n))
        self.assertEqual(len(ledger.used),128)

class ControllerTests(unittest.TestCase):
    def make_session(self,tmp):
        s=TrainingSession('',None,Path(tmp)/'book.json',lambda e:None,continuous=True)
        s.cancel.wait=Mock(return_value=False);s.publish=Mock();return s
    def browser(self):
        b=Mock();view=ui();view['controls']={k:{'x':1,'y':1} for k in view['controls']};b.guard.return_value=view
        return b
    def test_controller_fires_each_native_turn_without_missing_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=self.make_session(tmp);c=TrainingController(s);b=self.browser()
            b.sample.side_effect=[state(1),state(1),state(2),state(2),state(3)]
            def shoot(probe,cancel,settings_provider,before_fire):before_fire();return {},{}
            b.shoot.side_effect=shoot;c.observe=Mock()
            for _ in range(5):c.cycle(b)
            self.assertEqual(b.shoot.call_count,3)
            self.assertEqual([call.args[0]['turn_serial'] for call in b.shoot.call_args_list],[1,2,3])
    def test_unreachable_mode_does_not_consume_whole_turn_before_other_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=self.make_session(tmp);c=TrainingController(s);b=self.browser();b.sample.return_value=state()
            def shoot(probe,cancel,settings_provider,before_fire):
                if probe['shot']==0:raise NoAim('blocked')
                before_fire();return {},{}
            b.shoot.side_effect=shoot;c.observe=Mock();c.cycle(b);c.cycle(b)
            self.assertEqual([call.args[0]['shot'] for call in b.shoot.call_args_list],[0,1])
            self.assertEqual(c.observe.call_count,1)
    def test_reconnect_does_not_repeat_an_ambiguous_charge(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=self.make_session(tmp);c=TrainingController(s);first=self.browser();second=self.browser()
            first.sample.return_value=state(1);second.sample.side_effect=[state(1),state(2)]
            def disconnected(probe,cancel,settings_provider,before_fire):before_fire();raise ConnectionError('lost after press')
            first.shoot.side_effect=disconnected
            def confirmed(probe,cancel,settings_provider,before_fire):before_fire();return {},{}
            second.shoot.side_effect=confirmed;c.observe=lambda *args:s.cancel.set()
            with patch('training_controller.TrainingBrowser',side_effect=[first,second]),patch('training_power.SleepLease'):c.run()
            self.assertEqual(first.shoot.call_count,1);self.assertEqual(second.shoot.call_count,1)
            self.assertEqual(second.shoot.call_args.args[0]['turn_serial'],2)
            second.arm.assert_called_once_with(focus=False)

class ShortTurnTests(unittest.TestCase):
    make_session=ControllerTests.make_session
    browser=ControllerTests.browser
    def test_expired_turns_do_not_halt_training_or_repeat_same_turn(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=self.make_session(tmp);c=TrainingController(s);b=self.browser()
            b.sample.side_effect=[state(n) for n in [1,1,2,2,3,3,4]]
            def shoot(probe,cancel,settings_provider,before_fire):
                if probe['turn_serial']<4:raise TurnExpired('Turno vencido')
                before_fire();return {},{}
            b.shoot.side_effect=shoot;c.observe=Mock()
            for _ in range(7):c.cycle(b)
            self.assertEqual(b.shoot.call_count,4);self.assertEqual(c.failures,0)
            self.assertEqual([e['kind'] for e in s.errors],['turn-ended']*3)
            c.observe.assert_called_once()
    def test_unconfirmed_releases_are_not_repeated_or_counted_as_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=self.make_session(tmp);c=TrainingController(s);b=self.browser();b.sample.return_value=state()
            def shoot(probe,cancel,settings_provider,before_fire):before_fire();raise UnconfirmedShot('No observation')
            b.shoot.side_effect=shoot
            c.cycle(b);c.cycle(b)
            self.assertEqual(b.shoot.call_count,1);self.assertEqual(c.failures,0)
            self.assertEqual(s.errors[0]['kind'],'unconfirmed')
    def test_genuine_control_failures_still_stop_and_preserve_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=self.make_session(tmp);c=TrainingController(s);b=self.browser();b.shoot.side_effect=RuntimeError('Angle stuck')
            for n in [1,2]:b.sample.return_value=state(n);c.cycle(b)
            b.sample.return_value=state(3)
            with self.assertRaisesRegex(RuntimeError,'último: Angle stuck'):c.cycle(b)
            self.assertEqual(len(s.errors),3);self.assertEqual(s.errors[-1]['reason'],'Angle stuck')
    def test_runtime_error_with_confirmed_turn_change_recovers(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=self.make_session(tmp);c=TrainingController(s);b=self.browser();b.sample.side_effect=[state(1),state(2,1)]
            b.shoot.side_effect=RuntimeError('Control unavailable')
            c.cycle(b)
            self.assertEqual(c.failures,0);self.assertEqual(s.errors[-1]['kind'],'turn-ended')
    def test_short_remaining_budget_does_not_begin_charge(self):
        b=TrainingBrowser.__new__(TrainingBrowser)
        with patch('training_browser.time.monotonic',return_value=100):
            b.turn_deadline=104
            with self.assertRaises(TurnExpired):b.require_charge_time()
            b.turn_deadline=110;b.require_charge_time()
    def test_control_failures_reset_at_match_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=self.make_session(tmp);c=TrainingController(s);b=self.browser();c.in_game=True;c.failures=2
            view=ui();view['game']=False;view['controls']['buttonStart1v1']={'x':1,'y':1};b.guard.return_value=view
            c.cycle(b);self.assertEqual(c.failures,0)

class MovementTests(unittest.TestCase):
    def test_no_movement_without_terrain_and_no_walk_off_cliff(self):
        s=state();self.assertIsNone(walking_step(s,150))
        s['terrain']={'heights':[100]*110+[None]*100}
        self.assertEqual(walking_step(s,150)['direction'],'left')
    def test_supported_short_step_towards_target(self):
        s=state();s['terrain']={'heights':[100]*300}
        plan=walking_step(s,200);self.assertEqual(plan['direction'],'right');self.assertLessEqual(plan['distance'],14)
    def test_terrain_clearing_requires_lab_power_and_a_distant_progressing_impact(self):
        good={'reachable':False,'blocked':True,'power':400,'guide_power':175,'preview_paths':[[(0,0),(400,420)]]}
        with patch('training_aim.solve',return_value=good):
            _,result=choose_aim(Settings(),55,allow_blocked=True)
            self.assertEqual(result['power'],175);self.assertEqual(result['training_action'],'abrir paso')
            self.assertEqual(actual_solution(Settings(),allow_blocked=True)['power'],175)
        bad={**good,'preview_paths':[[(0,0),(135,430)]]}
        with patch('training_aim.solve',return_value=bad):
            with self.assertRaises(NoAim):choose_aim(Settings(),55,allow_blocked=True)
