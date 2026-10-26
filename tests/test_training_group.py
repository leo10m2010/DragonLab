import copy,json,tempfile,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from training_group import TrainingGroup,canonical_endpoint


class FixtureSession:
    def __init__(self,endpoint,target,book_path,emit,**options):
        self.endpoint=endpoint;self.target=target;self.book_path=Path(book_path);self.emit=emit;self.options=options
        self.running=False;self.status='Preparado';self.shots=0;self.matches=0;self.last_error='';self.errors=[];self.report={};self.cancel=threading.Event();self.thread=None
        self.lab_progress={};self.learner=object();self.history=[];self.movements=[];self.last_timing={};self.start_count=0
    def start(self):self.start_count+=1;self.running=True;self.status='Esperando turno'
    def stop(self):self.cancel.set();self.running=False;self.status='Detenido'
    def time_remaining(self):return self.options['max_seconds']


def slots(base):
    return [{'id':f'sesion-{index}','endpoint':f'http://127.0.0.1:{9222+index}','target':f'target-{index}','directory':base/'entrenamiento-paralelo'/f'sesion-{index}'} for index in (1,2)]


class ValidationTests(unittest.TestCase):
    def invalid(self,change,**options):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)/'uncreated';configuration=slots(base);change(configuration);factory=Mock()
            with self.assertRaises(ValueError):TrainingGroup(base,configuration,Mock(),session_factory=factory,**options)
            factory.assert_not_called();self.assertFalse(base.exists())
    def test_aliases_cannot_bypass_duplicate_target_validation(self):
        def duplicate(configuration):configuration[1].update(endpoint='http://localhost:9223/',target=configuration[0]['target'])
        self.invalid(duplicate)
    def test_duplicate_measurement_directory_rejected_before_creating_anything(self):
        self.invalid(lambda configuration:configuration[1].update(directory=configuration[0]['directory']))
    def test_no_unpinned_or_remote_target_can_start(self):
        self.invalid(lambda configuration:configuration[1].update(target=None))
        self.invalid(lambda configuration:configuration[1].update(endpoint='http://example.com:9224'))
        self.invalid(lambda configuration:configuration[1].update(endpoint='http://user:secret@localhost:9224'))
    def test_unsupported_group_size_and_limits_rejected_before_seeding(self):
        self.invalid(lambda configuration:configuration.pop())
        self.invalid(lambda configuration:None,max_seconds=86401)
        self.invalid(lambda configuration:None,max_shots=0)
    def test_worker_data_cannot_overwrite_the_primary_book(self):
        self.invalid(lambda configuration:configuration[0].update(directory=configuration[0]['directory'].parents[1]))
    def test_only_loopback_http_with_explicit_port_is_accepted(self):
        self.assertEqual(canonical_endpoint('http://LOCALHOST:9224/'),'http://127.0.0.1:9224')
        for value in ('https://127.0.0.1:9224','http://127.0.0.1','http://127.0.0.1:9224/private','http://127.0.0.1:9224/?token=x',None):
            with self.assertRaises(ValueError):canonical_endpoint(value)


class GroupTests(unittest.TestCase):
    def make(self,base,emit=None):return TrainingGroup(base,slots(base),emit or Mock(),session_factory=FixtureSession)
    def test_only_measurement_seeds_are_copied_and_existing_worker_data_survives(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);configuration=slots(base)
            seed=json.dumps({'schema':1,'records':{}})
            for name in ('calibraciones.json','aprendizaje-autonomo.json'):(base/name).write_text(seed)
            (base/'session.bin').write_bytes(b'do-not-copy');(base/'cookies.json').write_text('do-not-copy')
            first=configuration[0]['directory'];first.mkdir(parents=True)
            custom=json.dumps({'schema':1,'records':{'local-only':{'samples':[]}}});(first/'calibraciones.json').write_text(custom)
            group=TrainingGroup(base,configuration,Mock(),session_factory=FixtureSession)
            self.assertEqual((first/'calibraciones.json').read_text(),custom)
            second=configuration[1]['directory']
            self.assertEqual((second/'calibraciones.json').read_text(),seed)
            for directory in (first,second):
                self.assertEqual({path.name for path in directory.iterdir()},{'calibraciones.json','aprendizaje-autonomo.json'})
            self.assertIsNot(group.books['sesion-1'],group.books['sesion-2']);self.assertFalse(group.running)
    def test_workers_receive_explicit_targets_independent_paths_and_background_control(self):
        with tempfile.TemporaryDirectory() as folder:
            group=self.make(Path(folder));first,second=group.sessions
            self.assertEqual((first.endpoint,second.endpoint),('http://127.0.0.1:9223','http://127.0.0.1:9224'))
            self.assertEqual((first.target,second.target),('target-1','target-2'));self.assertNotEqual(first.book_path,second.book_path)
            for worker in group.sessions:
                self.assertTrue(worker.options['background']);self.assertTrue(worker.options['autonomous'])
                self.assertEqual(worker.options['objective'],'adaptive');self.assertEqual(worker.options['max_seconds'],86400)
    def test_emitted_events_are_bound_to_their_worker_and_this_group_run(self):
        with tempfile.TemporaryDirectory() as folder:
            received=[];group=self.make(Path(folder),received.append)
            for worker in group.sessions:worker.emit({'status':'training-observation','release':{},'observation':{}})
            self.assertEqual([event['session_id'] for event in received],['sesion-1','sesion-2'])
            self.assertTrue(all(event['group_run_id']==group.group_run_id for event in received))
            self.assertEqual([event['release']['measurement_session'] for event in received],[group.group_run_id+':sesion-1',group.group_run_id+':sesion-2'])
    def test_tagging_does_not_mutate_the_workers_own_release(self):
        with tempfile.TemporaryDirectory() as folder:
            received=[];group=self.make(Path(folder),received.append);release={'power':100}
            group.sessions[0].emit({'status':'training-observation','release':release,'observation':{}})
            self.assertEqual(release,{'power':100});self.assertIsNot(received[0]['release'],release)
    def test_any_running_worker_keeps_manual_control_disabled_and_totals_include_both(self):
        from product_status import capture_status
        with tempfile.TemporaryDirectory() as folder:
            group=self.make(Path(folder));group.sessions[0].last_error='Failed first';group.sessions[1].running=True
            group.sessions[0].shots=3;group.sessions[1].shots=5;group.sessions[0].matches=2;group.sessions[1].matches=4
            self.assertTrue(group.running);self.assertEqual((group.shots,group.matches),(8,6))
            self.assertEqual(capture_status(SimpleNamespace(training_session=group))[0],'Entrenamiento parcial')
            self.assertIn('Sesión 2',group.status)
    def test_selecting_a_worker_changes_inspection_without_switching_or_stopping_control(self):
        with tempfile.TemporaryDirectory() as folder:
            group=self.make(Path(folder));group.sessions[0].history=['first'];group.sessions[1].history=['second']
            self.assertEqual(group.history,['first']);group.selected=1;self.assertEqual(group.history,['second'])
            self.assertIs(group.learner,group.sessions[1].learner)
            group.lab_progress={'local':2};self.assertEqual(group.sessions[1].lab_progress,{'local':2});self.assertNotEqual(group.sessions[0].lab_progress,{'local':2})
            with self.assertRaises(ValueError):group.selected=2
    def test_start_is_idempotent_stop_signals_both_and_final_overview_is_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);group=self.make(base)
            try:
                group.start();group.start();self.assertEqual([worker.start_count for worker in group.sessions],[1,1]);self.assertTrue(group.running)
            finally:group.stop();group.join(1)
            self.assertTrue(all(worker.cancel.is_set() for worker in group.sessions));self.assertFalse(group.running)
            saved=json.loads((base/'entrenamiento-paralelo-estado.json').read_text())
            self.assertFalse(saved['active']);self.assertEqual(len(saved['sessions']),2);self.assertTrue(saved['stopping'])
    def test_one_worker_failure_does_not_cancel_its_peer(self):
        with tempfile.TemporaryDirectory() as folder:
            group=self.make(Path(folder));group.sessions[0].start=Mock(side_effect=RuntimeError('first unavailable'))
            try:
                group.start();self.assertTrue(group.sessions[1].running);self.assertFalse(group.sessions[1].cancel.is_set())
                self.assertTrue(group.running);self.assertIn('first unavailable',group.last_error)
            finally:group.stop();group.join(1)
    def test_stop_without_join_still_publishes_when_workers_finish_later(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);group=self.make(base)
            for worker in group.sessions:worker.stop=worker.cancel.set
            try:
                group.start();group.stop()
                self.assertTrue(group.running);self.assertFalse(group._monitor_stop.is_set())
                for worker in group.sessions:worker.running=False
                self.assertTrue(group._monitor_stop.wait(5))
                group._monitor.join(1)
                self.assertFalse(json.loads((base/'entrenamiento-paralelo-estado.json').read_text())['active'])
            finally:group.join(1)
    def test_join_uses_one_total_timeout_for_all_workers(self):
        with tempfile.TemporaryDirectory() as folder:
            group=self.make(Path(folder));first,second=group.sessions
            first.thread=Mock();second.thread=Mock()
            with patch('training_group.time.monotonic',side_effect=[10,10,10.6]):group.join(1)
            first.thread.join.assert_called_once_with(1);self.assertAlmostEqual(second.thread.join.call_args.args[0],.4)
    def test_overview_never_serializes_account_or_free_form_error_details(self):
        with tempfile.TemporaryDirectory() as folder:
            group=self.make(Path(folder));group.sessions[1].status='private-player-name';group.sessions[1].last_error='account-secret'
            group.sessions[1].errors=[{'credential':'secret'}]
            text=json.dumps(group.overview());self.assertNotIn('private-player-name',text);self.assertNotIn('account-secret',text);self.assertNotIn('credential',text)
            self.assertTrue(group.overview()['sessions'][1]['error']);self.assertEqual(group.overview()['sessions'][1]['error_count'],1)
    def test_new_native_measurement_is_added_only_to_its_workers_book(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);group=self.make(base)
            state={'status':'live','heroId':0,'activePlayer':0,'players':[{'id':0,'mobile':0,'x':100,'y':100},{'id':1,'x':500,'y':100}], 'shots':[{'id':'own','native':True,'elapsed':0,'duration':1500,'start':[100,100,45,220,0,400],'shotType':0}], 'wind':0,'windAngle':90,'currentPower':100,'selectedShot':0}
            release={'hero':0,'x':100,'y':100,'power':100,'shot':0,'wind':0,'windAngle':90,'baseline':[]}
            event={'status':'training-observation','session_id':'sesion-2','group_run_id':group.group_run_id,'release':release,'observation':state}
            result=group.observe(event)
            self.assertEqual(result['lab_observations'],1);self.assertFalse(group.books['sesion-1'].records)
            self.assertEqual(len(group.books['sesion-2'].records['dragonbound:ARMOR:0']['samples']),1)
            self.assertFalse((base/'calibraciones.json').exists());self.assertEqual(group.sessions[1].lab_progress,result)
    def test_stale_or_unknown_worker_event_cannot_touch_any_book(self):
        with tempfile.TemporaryDirectory() as folder:
            group=self.make(Path(folder));event={'status':'training-observation','session_id':'sesion-2','group_run_id':group.group_run_id,'release':{},'observation':{}}
            with patch('training_group.share_observation') as share:
                for change in ({'group_run_id':'old-run'},{'session_id':'sesion-3'},{'release':None}):
                    with self.assertRaises(ValueError):group.observe({**event,**change})
                share.assert_not_called()


if __name__=='__main__':unittest.main()
