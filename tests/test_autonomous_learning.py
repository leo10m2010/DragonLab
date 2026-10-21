import math,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from autonomous_learning import AutonomousLearner,fit
from training_orientation import desired_look,heading,raw_angle,up_increases_raw

def measurement(n,power,wind=0):
    angle=30;coupling=.7
    return {'id':str(n),'power':power,'speed':2*power+20,'ax':coupling*wind*math.cos(math.radians(angle)),'ay':300-coupling*wind*math.sin(math.radians(angle)),'wind':wind,'wind_angle':angle}

class OrientationTests(unittest.TestCase):
    def test_normal_and_reverse_ranges_point_to_target_on_both_slopes_and_sides(self):
        for minimum,maximum in [(10,70),(110,170)]:
            for body in [-15,0,15]:
                for right in [False,True]:
                    player={'rawAngle':(minimum+maximum)/2,'minAngle':minimum,'maxAngle':maximum,'body':body,'look':1}
                    look=desired_look(player,right);raw=raw_angle(45,body,look,right)
                    self.assertGreaterEqual(raw,minimum);self.assertLessEqual(raw,maximum)
                    self.assertEqual(math.cos(math.radians(heading(raw,body,look)))>0,right)
                    self.assertEqual(look,int(right) if minimum<90 else int(not right))
    def test_aduka_observed_native_range_does_not_use_normal_facing(self):
        player={'rawAngle':155,'minAngle':110,'maxAngle':170,'body':-10,'look':1}
        self.assertEqual(desired_look(player,True),0)
        self.assertEqual(desired_look(player,False),1)
        self.assertFalse(up_increases_raw(player))
    def test_curriculum_does_not_receive_null_candidates_during_cold_start(self):
        from training_policy import next_probe
        with tempfile.TemporaryDirectory() as tmp:
            learner=AutonomousLearner(Path(tmp)/'learn.json')
            learner.add('dragonbound:ADUKA:0',measurement(0,100))
            self.assertEqual(next_probe(learner.curriculum_records(),'ADUKA',0)['shot'],1)

class LearnerTests(unittest.TestCase):
    def test_learns_speed_gravity_and_wind_without_any_lab_profile(self):
        model=fit([measurement(i,p,10+i*3) for i,p in enumerate([90,170,270,350])])
        self.assertAlmostEqual(model['scale'],2);self.assertAlmostEqual(model['offset'],20)
        self.assertAlmostEqual(model['gravity'],300);self.assertAlmostEqual(model['wind_scale'],.7)
    def test_requires_future_observations_before_using_a_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=AutonomousLearner(Path(tmp)/'learn.json');key='dragonbound:ARMOR:0'
            for i,p in enumerate([90,170,270,350]):learner.add(key,measurement(i,p))
            self.assertNotIn('model',learner.records[key]);self.assertIn('candidate',learner.records[key])
            for i,p in enumerate([120,230,330],start=10):learner.add(key,measurement(i,p))
            self.assertIn('model',learner.records[key]);self.assertNotIn('candidate',learner.records[key])
    def test_bad_future_shot_does_not_promote_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=AutonomousLearner(Path(tmp)/'learn.json');key='dragonbound:ARMOR:0'
            for i,p in enumerate([90,170,270,350]):learner.add(key,measurement(i,p))
            bad=measurement(10,200);bad['speed']+=80;learner.add(key,bad)
            self.assertNotIn('model',learner.records[key])
    def test_existing_fit_is_ignored_and_only_real_raw_samples_are_imported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);seed=root/'legacy.json'
            seed.write_text(json.dumps({'records':{'dragonbound:ARMOR:0':{'fit':{'gravity':999999,'power_scale':9999},'samples':[{'source':'invented','power':100}]}}}))
            learner=AutonomousLearner(root/'learn.json',seed)
            self.assertFalse(learner.records)
    def test_plan_works_when_the_entire_lab_solver_is_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=AutonomousLearner(Path(tmp)/'learn.json')
            learner.records['dragonbound:ARMOR:0']={'samples':[],'model':{'scale':2,'offset':20,'gravity':300,'wind_scale':0}}
            state={'heroId':0,'players':[{'id':0,'x':0,'y':0,'muzzleX':None,'muzzleY':None},{'id':1,'x':600,'y':0}],'wind':0,'windAngle':0,'weather':[]}
            player={'look':1,'body':0,'rawAngle':45,'minAngle':10,'maxAngle':70}
            with patch('core.solve',side_effect=AssertionError('Lab cannot be called')):
                plan=learner.plan(state,player,{'mobile':'ARMOR','shot':0,'angle':45,'power':100})
            self.assertEqual(plan['stage'],'apuntar con modelo propio');self.assertGreater(plan['power'],190);self.assertLess(plan['power'],220)
    def test_unknown_model_explores_instead_of_inventing_a_calibration(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=AutonomousLearner(Path(tmp)/'learn.json')
            state={'heroId':0,'players':[{'id':0,'x':0,'y':0},{'id':1,'x':600,'y':0}],'wind':0,'windAngle':0}
            player={'look':0,'body':0,'rawAngle':135,'minAngle':110,'maxAngle':170}
            plan=learner.plan(state,player,{'mobile':'NAK','shot':0,'angle':45,'power':170})
            self.assertEqual(plan['power'],170);self.assertEqual(plan['raw_angle'],135)
            self.assertIn('explorar',plan['stage']);self.assertFalse(learner.records)
    def test_no_wind_data_is_not_treated_as_a_learned_wind_model(self):
        model=fit([measurement(i,p) for i,p in enumerate([90,170,270,350])])
        self.assertIsNone(model['wind_scale'])
        self.assertIsNone(AutonomousLearner.solve_observed(model,(0,0),(600,0),45,10,0))
    def test_delayed_native_phase_is_kept_separate_from_launch_fit(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=AutonomousLearner(Path(tmp)/'learn.json')
            parent={'id':1,'native':True,'start':[0,0,45,200,0,100],'duration':500,'elapsed':0,'shotType':1,'metadata':{'player':0,'power':100}}
            state={'status':'live','heroId':0,'activePlayer':0,'players':[{'id':0,'x':0,'y':0,'mobile':11},{'id':1,'x':500,'y':0}],'shots':[parent],'selectedShot':1,'currentPower':100,'wind':0,'windAngle':90}
            release={'hero':0,'x':0,'y':0,'power':100,'shot':1,'wind':0,'windAngle':90,'baseline':[],'learner':{'target':[500,0],'elevation':45}}
            self.assertTrue(learner.observe({'mobile':'NAK'},release,state))
            from native_paths import position
            end=position(parent,.5)
            child={'id':2,'native':True,'start':[end[0],end[1],90,100,0,-500],'duration':400,'elapsed':500,'delay':500}
            state['shots']=[child];learner.track(state)
            record=learner.records['dragonbound:NAK:1']
            self.assertEqual(len(record['samples']),1);self.assertEqual(len(record['observed_phases']),1)
            self.assertTrue(record['multi_projectile']);self.assertTrue(record['cases'][0]['has_continuation'])
    def test_native_samples_can_seed_candidate_but_saved_lab_fit_cannot_activate_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows=[]
            for i,p in enumerate([90,170,270,350]):
                s=measurement(i,p);rows.append({'source':'native-shot-start','sample_id':str(i),'power':p,'vx':s['speed'],'vy':0,'ax':s['ax'],'ay':s['ay'],'wind':s['wind'],'wind_angle':s['wind_angle']})
            root=Path(tmp);seed=root/'seed.json';seed.write_text(json.dumps({'records':{'dragonbound:ARMOR:0':{'fit':{'gravity':999999},'samples':rows}}}))
            learner=AutonomousLearner(root/'learn.json',seed);record=learner.records['dragonbound:ARMOR:0']
            self.assertNotIn('model',record);self.assertAlmostEqual(record['candidate']['model']['gravity'],300)
    def test_inconsistent_historical_seeds_cannot_block_fresh_independent_learning(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=AutonomousLearner(Path(tmp)/'learn.json');key='dragonbound:NAK:0'
            for i,p in enumerate([90,170,270,350]):
                wrong=measurement('seed:'+str(i),p);wrong['speed']+=500;learner.add(key,wrong,seed=True)
            for i,p in enumerate([90,170,270,350],start=10):learner.add(key,measurement(i,p))
            candidate=learner.records[key]['candidate']
            self.assertTrue(all(not ident.startswith('seed:') for ident in candidate['trained_ids']))
            self.assertAlmostEqual(candidate['model']['offset'],20)
            for i,p in enumerate([120,230,330],start=20):learner.add(key,measurement(i,p))
            self.assertAlmostEqual(learner.records[key]['model']['offset'],20)
    def test_default_product_training_does_not_install_a_lab_settings_provider(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from training_ui import start_training
        app=SimpleNamespace(clone_id='dragonbound',training_session=None,endpoint=Mock(),last_live=0,browser_target=None,book=SimpleNamespace(path=Path('book.json')),events=Mock())
        with patch('training_session.TrainingSession') as factory:
            start_training(app)
            self.assertTrue(factory.call_args.kwargs['autonomous'])
            self.assertNotIn('settings_provider',factory.call_args.kwargs)
    def test_full_autonomous_shot_never_calls_lab_teacher_or_solver(self):
        from unittest.mock import Mock
        import threading
        from training_browser import TrainingBrowser
        with tempfile.TemporaryDirectory() as tmp:
            learner=AutonomousLearner(Path(tmp)/'learn.json');control={'raw':155,'held':False,'released':False}
            def reading():return {'turnNumber':1,'turn':0,'hero':0,'mode':'space','shot':0,'power':100 if control['held'] else 0,'busy':control['held'],'over':False,'moving':False,'wind':0,'windAngle':0,'players':[{'id':0,'x':500,'y':0,'rawAngle':control['raw'],'minAngle':110,'maxAngle':170,'body':0,'look':1}]}
            shot={'id':9,'native':True,'elapsed':0,'duration':1000,'start':[500,0,125,220,0,300],'shotType':0,'metadata':{'player':0,'power':100}}
            def sample():return {'status':'live','heroId':0,'activePlayer':0,'wind':0,'windAngle':0,'weather':[],'players':[{'id':0,'x':500,'y':0,'mobile':2},{'id':1,'x':0,'y':0}], 'shots':[shot] if control['released'] else []}
            reader=Mock();reader.read.side_effect=reading
            browser=TrainingBrowser.__new__(TrainingBrowser);browser.client=Mock();browser.client.endpoint='http://127.0.0.1:9223';browser.client.target={'id':'tab'}
            browser.guard=Mock(return_value={'controls':{}});browser.sample=sample
            def adjust(*args,**kwargs):control['raw']=125;return {'before':155,'after':125}
            browser.adjust_angle=adjust
            def key(name,down):
                if name=='space':control['held']=down;control['released']=not down
            browser.key=key;teacher=Mock(side_effect=AssertionError('teacher forbidden'))
            with patch('training_browser.PowerReader',return_value=reader),patch('core.solve',side_effect=AssertionError('solver forbidden')),patch('training_aim.choose_aim',side_effect=AssertionError('Lab aim forbidden')):
                release,state=browser.shoot({'mobile':'ADUKA','shot':0,'power':100,'angle':55,'turn_serial':1},threading.Event(),settings_provider=teacher,autonomous=learner)
            teacher.assert_not_called();self.assertNotIn('lab',release)
            self.assertEqual(release['learner']['heading'],125);self.assertEqual(release['power'],100)
