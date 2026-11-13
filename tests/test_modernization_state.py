import json,pathlib,tempfile,threading,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from app_lifecycle import reset_source,event_current
from runtime_metrics import RuntimeMetrics
from diagnostic_log import note
from automatic import screen_geometry
from app import App
from core import Settings

class ModernizationStateTests(unittest.TestCase):
    def test_account_reset_cancels_old_input_without_releasing_worker_ownership(self):
        with tempfile.TemporaryDirectory() as folder:
            book=SimpleNamespace(release={'power':100},seen={1},pending={1:2})
            review=SimpleNamespace(seen={1},pending={1:2},records=[{'game_id':'dragonbound'}])
            app=SimpleNamespace(source_epoch='old',pending_fire=(1,'old'),fire_cancel=threading.Event(),fire_busy=True,
                active_fire_id='old-worker',compute_generation=4,calculations=Mock(),s=Settings(),player_tracker=Mock(),
                trails=Mock(),book=book,shot_review=review,learned_launches=SimpleNamespace(lock=threading.RLock(),in_game=True,episode='old',live={1:2}),
                hide_overlay=Mock(),hide_power_guide=Mock(),target_name=Mock(),target_box=Mock(),base=pathlib.Path(folder),clone_id='dragonbound')
            reset_source(app,'new')
            self.assertTrue(app.fire_cancel.is_set());self.assertIsNone(app.pending_fire)
            self.assertTrue(app.fire_busy);self.assertEqual(app.active_fire_id,'old-worker')
            self.assertEqual(app.compute_generation,5);self.assertEqual(app.source_epoch,'new')
            self.assertIsNone(book.release);self.assertFalse(book.seen);self.assertFalse(review.pending)
            self.assertEqual(len(review.records),1);self.assertFalse(app.learned_launches.live)
            self.assertEqual(app.live_players,[]);self.assertFalse(event_current(app,{'sourceEpoch':'old'}))
            self.assertTrue(event_current(app,{'sourceEpoch':'new'}))

    def test_profile_namespace_is_game_mobile_and_shot_with_read_only_legacy_fallback(self):
        app=SimpleNamespace(clone_id='dragonbound',s=Settings(),profiles={'dragonbound:ARMOR':{'gravity':70},'dragonbound:ARMOR:1':{'gravity':80},'gunbound-world:ARMOR:1':{'gravity':392}})
        app.s.selected_shot=1;self.assertEqual(App.custom_profile(app)['gravity'],80)
        app.s.selected_shot=0;self.assertEqual(App.custom_profile(app)['gravity'],70)
        app.clone_id='gunbound-world';self.assertEqual(App.custom_profile(app),{})
        app.s.selected_shot=1;self.assertEqual(App.custom_profile(app)['gravity'],392)
        self.assertEqual(len(app.profiles),3)

    def test_metrics_cache_and_closed_numeric_roster(self):
        now=[10.];cpu=[1.];reads=[]
        sample=RuntimeMetrics(clock=lambda:now[0],cpu=lambda:cpu[0],memory=lambda:(reads.append(1) or (20,30)))
        app=SimpleNamespace(last_live=9,clone_id='dragonbound',roster_diagnostics={'valid':32,'enemy':28,'token':'secret','unknown':2})
        now[0]=12;cpu[0]=1.5
        with patch('native_solver.diagnostics',return_value={'engine':'rust'}),patch('native_overlay.diagnostics',return_value={'renderer':'rust','counters':{'presentations':10}}):
            result=sample.sample(app);self.assertEqual(result['cpu_one_core_percent'],25)
            self.assertEqual(result['roster'],{'valid':32,'enemy':28,'unknown':2})
            self.assertEqual(sample.sample(app),result);self.assertEqual(len(reads),1)

    def test_bounded_diagnostics_never_export_free_text(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(note(folder,'source-reset',game='dragonbound',version='0.20.0',password='secret',epoch='private-native-token',players=32))
            value=json.loads((pathlib.Path(folder)/'diagnostico-eventos.jsonl').read_text())
            self.assertNotIn('password',value);self.assertNotIn('epoch',value);self.assertEqual(value['players'],32)
            self.assertFalse(note(folder,'arbitrary raw text'))

    def test_geometry_uses_viewport_not_world_bounds_and_rejects_hidden_or_partial_bar(self):
        meta={'active':True,'game':[900,10,800,600],'bar':[1000,560,400,14],'inner':[1800,900],'dpr':1.25}
        area,points=screen_geometry(meta,(-1920,0))
        self.assertEqual(area,(-795,12,205,762));self.assertEqual(points[0][0],-670)
        self.assertEqual(points[1][0]-points[0][0],500)
        meta['bar']=[1700,560,400,14];self.assertIsNone(screen_geometry(meta,(-1920,0))[1])
        meta['game'][0]=float('nan');self.assertEqual(screen_geometry(meta,(0,0)),(None,None))

if __name__=='__main__':unittest.main()
