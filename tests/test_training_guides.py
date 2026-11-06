import copy,json,math,sqlite3,tempfile,unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from training_guides import TrainingGuideStore,FILENAME,MAX_PAYLOAD
from manual_learning import LearnedLaunchLibrary
from training_controller import TrainingController
from training_session import TrainingSession
from autonomous_learning import AutonomousLearner

def example(power=100,index=1,mobile='ARMOR',shot=0):
    model={'scale':2.42,'offset':-.4,'gravity':390,'wind_scale':4,'wind_mode':'floor'}
    plan={'power':power,'origin':[0,0],'target':[400,100],'heading':45,'raw_angle':45,'evaluation_phase':'calibration','stage':'calibración dirigida provisional','guide_prediction':{'model':model,'duration_s':.7}}
    release={'hero':0,'shot':shot,'power':power,'angle':45,'x':0,'y':0,'wind':0,'windAngle':90,'turn_serial':index,'baseline':[],'learner':plan}
    state={'status':'live','heroId':0,'activePlayer':0,'turnSerial':index,'wind':0,'windAngle':90,'weather':[],
           'players':[{'id':0,'x':0,'y':0,'mobile':mobile,'hp':1000,'shield':0},{'id':1,'x':500,'y':0,'mobile':'ICE','hp':1000,'shield':0}],
           'shots':[{'id':index,'native':True,'elapsed':40,'duration':700,'start':[0,0,45,math.floor(2.42*power-.4),0,390],'shotType':shot,'metadata':{'player':0,'power':power}}]}
    return {'mobile':mobile,'shot':shot,'power':power,'turn_serial':index},release,state

def cases(store):
    if not store.path.exists():return []
    with closing(sqlite3.connect(store.path)) as connection:return [json.loads(r[0]) for r in connection.execute('SELECT payload FROM guides ORDER BY created')]

class TrainingGuideTests(unittest.TestCase):
    def test_prior_prediction_and_native_reconstruction_are_separate_and_persist(self):
        with tempfile.TemporaryDirectory() as folder:
            store=TrainingGuideStore(folder);probe,release,state=example()
            release['learner']['guide_prediction']['model']['scale']=3
            self.assertTrue(store.record('one',probe,release,state,'game','battle'))
            row=cases(store)[0]
            self.assertEqual(row['phase'],'calibration');self.assertFalse(row['physics_approved_by_archive'])
            self.assertEqual(row['prediction']['model']['scale'],3);self.assertNotEqual(row['prediction']['path'][-1],row['native'][0]['path'][-1])
            self.assertGreater(row['comparison']['mean_error_px'],10);self.assertFalse(row['comparison']['certifies_aim'])
            self.assertEqual(len(row['native'][0]['path']),65);self.assertEqual(row['native'][0]['source'],'native-path-reconstruction')
            self.assertEqual(len(cases(TrainingGuideStore(folder))),1)
    def test_missing_pre_shot_model_never_uses_the_observed_shot_as_a_fake_prediction(self):
        with tempfile.TemporaryDirectory() as folder:
            store=TrainingGuideStore(folder);probe,release,state=example();release['learner'].pop('guide_prediction')
            self.assertTrue(store.record('one',probe,release,state,'game'));row=cases(store)[0]
            self.assertIsNone(row['prediction']);self.assertIsNone(row['comparison']);self.assertTrue(row['native'])
    def test_foreign_release_and_old_baseline_are_not_archived_as_own_guides(self):
        from shot_attribution import identity
        with tempfile.TemporaryDirectory() as folder:
            store=TrainingGuideStore(folder);probe,release,state=example();state['shots'][0]['metadata']['player']=1
            self.assertFalse(store.record('foreign',probe,release,state,'game'))
            probe,release,state=example();release['baseline']=[identity(state['shots'][0])]
            self.assertFalse(store.record('old',probe,release,state,'game'));self.assertFalse(cases(store))
    def test_duplicate_token_cannot_create_another_case(self):
        with tempfile.TemporaryDirectory() as folder:
            store=TrainingGuideStore(folder);args=example()
            self.assertTrue(store.record('one',*args,'game'));self.assertFalse(store.record('one',*args,'game'))
            self.assertEqual(len(cases(store)),1);self.assertEqual(store.summary()['saved_this_run'],1)
    def test_limits_preserve_a_bounded_number_per_mode_and_globally(self):
        with tempfile.TemporaryDirectory() as folder:
            store=TrainingGuideStore(folder,per_mode=2,limit=3)
            for i in range(5):self.assertTrue(store.record(str(i),*example(index=i),'game'))
            self.assertEqual(len(cases(store)),2)
            for i in (5,6):self.assertTrue(store.record(str(i),*example(index=i,mobile='ICE'),'game'))
            rows=cases(store);self.assertEqual(len(rows),3)
            self.assertLessEqual(max(sum(r['profile']==key for r in rows) for key in {r['profile'] for r in rows}),2)
    def test_health_and_game_result_update_the_same_case_and_unknown_stays_unknown(self):
        with tempfile.TemporaryDirectory() as folder:
            store=TrainingGuideStore(folder);store.record('one',*example(),'game','battle')
            self.assertTrue(store.update_health({'token':'one','game':'battle','known':True,'reward_eligible':True,'enemy_health_drop':150,'own_health_drop':0,'secret':'DROP'}))
            self.assertTrue(store.update_outcome({'id':'battle','outcome_known':False,'outcome':'loss'}));self.assertEqual(cases(store)[0]['outcome'],'unknown')
            self.assertTrue(store.update_outcome({'id':'battle','outcome_known':True,'outcome':'win','source':'native-survival-at-gameover'}))
            row=cases(store)[0];self.assertEqual(row['outcome'],'win');self.assertEqual(row['health']['enemy_health_drop'],150);self.assertNotIn('secret',row['health']);self.assertEqual(len(cases(store)),1)
            store.update_outcome({'id':'battle','outcome_known':False});self.assertEqual(cases(store)[0]['outcome'],'win')
    def test_only_numeric_allowlisted_fields_reach_the_database(self):
        with tempfile.TemporaryDirectory() as folder:
            store=TrainingGuideStore(folder);probe,release,state=example();marker='PRIVATE-MARKER'
            release.update(email=marker,password=marker,url=marker);release['learner']['name']=marker;state['chat']=marker;state['players'][0]['name']=marker
            self.assertTrue(store.record('one',probe,release,state,'game'))
            self.assertNotIn(marker,store.path.read_bytes().decode('latin1'));self.assertNotIn(marker,json.dumps(cases(store)))
    def test_archive_samples_feed_the_manual_library_without_promoting_predictions(self):
        with tempfile.TemporaryDirectory() as folder:
            store=TrainingGuideStore(folder)
            for i,power in enumerate((82,95,107,84,104,92)):
                self.assertTrue(store.record(str(i),*example(power,i),'game'))
            library=LearnedLaunchLibrary(folder);self.assertTrue(library.refresh());fit=library.profile('dragonbound:ARMOR:0',0,90)
            self.assertIsNotNone(fit);self.assertAlmostEqual(fit['power_scale'],2.42,delta=.1)
            self.assertEqual(fit['learned_launch']['checks'],3)
    def test_clipped_or_multiple_projectiles_cannot_become_an_ordinary_manual_fit(self):
        with tempfile.TemporaryDirectory() as folder:
            store=TrainingGuideStore(folder)
            for i,power in enumerate((82,95,107,84,104,92)):
                probe,release,state=example(power,i)
                for j in range(1,8):
                    child=copy.deepcopy(state['shots'][0]);child['id']=100*i+j;child['start'][3]+=j;state['shots'].append(child)
                self.assertTrue(store.record(str(i),probe,release,state,'game'))
            records,_=TrainingGuideStore.read_records(store.path)
            self.assertTrue(records['dragonbound:ARMOR:0']['multi_projectile'])
            self.assertTrue(all(not s['simple'] for s in records['dragonbound:ARMOR:0']['samples']))
            library=LearnedLaunchLibrary(folder);library.refresh();self.assertIsNone(library.profile('dragonbound:ARMOR:0',0,90))
            self.assertTrue(all(len(json.dumps(r,separators=(',',':')).encode())<=MAX_PAYLOAD for r in cases(store)))
    def test_later_special_evidence_disables_a_previously_imported_ordinary_choice(self):
        with tempfile.TemporaryDirectory() as folder:
            store=TrainingGuideStore(folder)
            for i,power in enumerate((82,95,107,84,104,92)):store.record(str(i),*example(power,i),'game')
            library=LearnedLaunchLibrary(folder);library.refresh();self.assertIsNotNone(library.profile('dragonbound:ARMOR:0',0,90))
            probe,release,state=example(index=100);release['learner']['prefix_only']=True
            store.record('prefix',probe,release,state,'another');library.refresh()
            self.assertIsNone(library.profile('dragonbound:ARMOR:0',0,90));self.assertTrue(library.profiles['dragonbound:ARMOR:0'])
    def test_database_failure_reports_an_error_without_raising_a_control_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            blocker=Path(folder)/'blocker';blocker.write_text('file');store=TrainingGuideStore(blocker)
            self.assertFalse(store.record('one',*example(),'game'));self.assertTrue(store.error)
    def test_unverified_continuation_is_excluded_and_verified_one_is_saved(self):
        from shot_attribution import identity
        with tempfile.TemporaryDirectory() as folder:
            store=TrainingGuideStore(folder);probe,release,state=example();store.record('one',probe,release,state,'game')
            child=copy.deepcopy(state['shots'][0]);child.update(id=20,delay=700);child['start']=[120,100,90,100,0,-900]
            phase={'id':identity(child),'parent':identity(state['shots'][0]),'verified':False}
            learner=SimpleNamespace(records={'dragonbound:ARMOR:0':{'observed_phases':[phase]}});state['shots'].append(child)
            store.follow(state,learner);self.assertEqual(len(cases(store)[0]['native']),1)
            phase['verified']=True;store.follow(state,learner);row=cases(store)[0]
            self.assertEqual(len(row['native']),2);self.assertEqual(row['native'][1]['phase'],'verified-continuation');self.assertFalse(row['launch_samples'][0]['simple'])
            with patch.object(store,'connect',side_effect=AssertionError('A repeated frame must not rewrite the database')):store.follow(state,learner)
            self.assertEqual(len(cases(store)[0]['native']),2)
    def test_controller_links_confirmed_release_feedback_and_current_block(self):
        with tempfile.TemporaryDirectory() as folder:
            session=TrainingSession('',None,Path(folder)/'book.json',Mock(),autonomous=True,objective='adaptive')
            controller=TrainingController(session);controller.trial=Mock();controller.trial.record.return_value='one';controller.battle.game={'id':'battle'}
            controller.sync_report=Mock();controller.learner=Mock();controller.learner.episode='game'
            controller.observe(*example())
            self.assertEqual(len(cases(controller.guides)),1);self.assertEqual(session.guide_progress['saved_this_run'],1)
            next_trial=Mock();controller.trial=next_trial
            controller.health_result({'token':'one','game':'battle','known':True,'enemy_health_drop':120,'own_health_drop':0,'reward_eligible':True})
            next_trial.health_result.assert_called_once();self.assertEqual(cases(controller.guides)[0]['health']['enemy_health_drop'],120)
    def test_planner_snapshot_is_pre_shot_and_does_not_change_with_the_original_model(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=AutonomousLearner(Path(folder)/'learn.json');model={'scale':2,'offset':0,'gravity':300,'wind_scale':0}
            state={'heroId':0,'players':[{'id':0,'x':0,'y':0},{'id':1,'x':400,'y':0}],'wind':0,'windAngle':0,'weather':[]}
            player={'look':1,'body':0,'rawAngle':45,'minAngle':20,'maxAngle':55};probe={'mobile':'ARMOR','shot':0,'angle':45,'power':200}
            plan=learner.plan(state,player,probe,model_override=model)
            self.assertIn('guide_prediction',plan);model['scale']=20
            self.assertEqual(plan['guide_prediction']['model']['scale'],2)

if __name__=='__main__':unittest.main()
