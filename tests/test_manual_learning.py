import copy,json,math,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from manual_learning import LearnedLaunchLibrary,certificate
from test_local_launch_window import record,row
from test_guide_wind_model import app_fixture
from app import App
from core import Settings,point,solve
from product_status import calibration_label

KEY='dragonbound:ARMOR:0'

def write_source(directory,records,session=None):
    target=Path(directory)/(f'entrenamiento-paralelo/sesion-{session}/aprendizaje-autonomo.json' if session else 'aprendizaje-autonomo.json')
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps({'schema':1,'records':records}),encoding='utf-8')
    return target

def manual_state(power,index,speed_delta=0,shot=0,hero=0):
    r=row(power,index);speed=r['speed']+speed_delta
    return {'status':'live','over':False,'heroId':hero,'activePlayer':hero,'currentPower':power,'wind':0,'windAngle':90,'selectedShot':shot,
            'players':[{'id':0,'x':100,'y':200,'mobile':'ARMOR'},{'id':1,'x':600,'y':200,'mobile':'ICE'}],
            'shots':[{'id':index,'native':True,'elapsed':50,'duration':700,'shotType':shot,'metadata':{'player':hero,'power':power},'start':[100,200,45,speed,0,390]}]}

class ManualLearningTests(unittest.TestCase):
    def test_checked_history_imports_without_copying_a_saved_model_or_mutating_source(self):
        with tempfile.TemporaryDirectory() as folder:
            parent=record();parent['model']={'scale':999};source=write_source(folder,{KEY:parent});before=source.read_bytes()
            library=LearnedLaunchLibrary(folder);self.assertTrue(library.refresh());fit=library.profile(KEY,0,90)
            self.assertIsNotNone(fit);self.assertAlmostEqual(fit['power_scale'],2.42,delta=.1)
            self.assertEqual(fit['learned_launch']['power_range'],[84,104]);self.assertEqual(fit['learned_launch']['checks'],3)
            self.assertEqual(source.read_bytes(),before);self.assertEqual(library.summary()['available_modes'],1)
            self.assertIsNone(library.profile(KEY,1,90));self.assertFalse(library.refresh())
    def test_broad_training_and_disjoint_future_rows_produce_a_bounded_certificate(self):
        values=[row(p,i,duration=.6) for i,p in enumerate((80,160,240,320,120,260,200))]
        proof=certificate(KEY,values,'game');self.assertIsNotNone(proof)
        self.assertEqual(proof['scope'],'checked-launch-window');self.assertEqual(proof['power_range'],[120,260])
        self.assertTrue(set(proof['training_ids']).isdisjoint(proof['validation_ids']))
        broken=copy.deepcopy(values);broken[-1]['speed']+=20
        self.assertIsNone(certificate(KEY,broken,'game'))
    def test_incomplete_episodes_and_workers_cannot_be_combined_into_fake_checks(self):
        for separate_sources in (True,False):
            with self.subTest(separate_sources=separate_sources),tempfile.TemporaryDirectory() as folder:
                data=record()['samples']
                if separate_sources:
                    write_source(folder,{KEY:{'samples':data[:3]}},1);write_source(folder,{KEY:{'samples':data[3:]}},2)
                else:
                    for r in data[3:]:r['episode']='another'
                    write_source(folder,{KEY:{'samples':data}})
                library=LearnedLaunchLibrary(folder);library.refresh();self.assertIsNone(library.profile(KEY,0,90))
    def test_two_copies_of_the_same_history_do_not_duplicate_a_certificate(self):
        with tempfile.TemporaryDirectory() as folder:
            for i in (1,2):write_source(folder,{KEY:record()},i)
            library=LearnedLaunchLibrary(folder);library.refresh()
            self.assertEqual(len(library.profiles[KEY]),1);self.assertEqual(library.profile(KEY,0,90)['learned_launch']['checks'],3)
    def test_seed_rows_special_families_and_patterns_do_not_become_ordinary_models(self):
        for key,flags in ((KEY,{'multi_projectile':True}),('dragonbound:NAK:1',{}),('dragonbound:KALSIDDON:0',{}),('gunbound-world:ARMOR:0',{})):
            with self.subTest(key=key),tempfile.TemporaryDirectory() as folder:
                write_source(folder,{key:{**record(),**flags}});library=LearnedLaunchLibrary(folder);library.refresh()
                self.assertFalse(library.profiles)
        with tempfile.TemporaryDirectory() as folder:
            parent=record()
            for r in parent['samples']:r['id']='seed:'+r['id']
            write_source(folder,{KEY:parent});library=LearnedLaunchLibrary(folder);library.refresh();self.assertFalse(library.profiles)
    def test_conflicting_duplicate_launch_is_not_reused_as_evidence(self):
        parent=record();other=copy.deepcopy(parent['samples'][0]);other['power']+=1;parent['samples'].append(other)
        self.assertIsNone(certificate(KEY,parent['samples'],'game'))
    def test_saved_library_is_immediately_available_after_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            write_source(folder,{KEY:record()});library=LearnedLaunchLibrary(folder);library.refresh()
            restored=LearnedLaunchLibrary(folder);self.assertIsNotNone(restored.profile(KEY,0,90));self.assertFalse(restored.error)
    def test_unreadable_source_preserves_previous_checked_profiles(self):
        with tempfile.TemporaryDirectory() as folder:
            source=write_source(folder,{KEY:record()});library=LearnedLaunchLibrary(folder);library.refresh()
            source.write_text('broken');library.refresh()
            self.assertIsNotNone(library.profile(KEY,0,90));self.assertTrue(library.error)
    def test_normal_manual_shots_create_persistent_learning_without_a_training_session(self):
        with tempfile.TemporaryDirectory() as folder:
            library=LearnedLaunchLibrary(folder)
            for i,power in enumerate((82,95,107,84,104,92)):
                state=manual_state(power,i);self.assertTrue(library.observe(state));self.assertFalse(library.observe(state))
            fit=library.profile(KEY,0,90);self.assertIsNotNone(fit);self.assertTrue(fit['learned_launch']['current_match_checked'])
            self.assertEqual(len(library.manual[KEY]['samples']),6)
            self.assertIsNotNone(LearnedLaunchLibrary(folder).profile(KEY,0,90))
    def test_new_manual_launch_invalidates_an_incompatible_historical_choice(self):
        with tempfile.TemporaryDirectory() as folder:
            write_source(folder,{KEY:record()});library=LearnedLaunchLibrary(folder);library.refresh()
            self.assertIsNotNone(library.profile(KEY,0,90));library.observe(manual_state(90,100,speed_delta=30))
            self.assertIsNone(library.profile(KEY,0,90));self.assertTrue(library.profiles[KEY])
    def test_foreign_projectile_and_unconfirmed_items_cannot_train_the_manual_library(self):
        with tempfile.TemporaryDirectory() as folder:
            library=LearnedLaunchLibrary(folder);state=manual_state(90,100)
            foreign=copy.deepcopy(state);foreign['shots'][0]['metadata']['player']=1
            self.assertFalse(library.observe(foreign));self.assertFalse(library.observe(state,{'item':'dual'}))
            multiple=copy.deepcopy(state);multiple['shots'].append(copy.deepcopy(multiple['shots'][0]));multiple['shots'][-1]['id']=101
            self.assertFalse(library.observe(multiple));self.assertFalse(library.manual)
    def test_application_uses_the_learned_force_profile_and_clears_it_on_weapon_change(self):
        with tempfile.TemporaryDirectory() as folder:
            write_source(folder,{KEY:record()});library=LearnedLaunchLibrary(folder);library.refresh()
            app=app_fixture(None);app.learned_launches=library
            App.apply_measured_profile(app)
            self.assertAlmostEqual(app.s.power_scale,2.42,delta=.1);self.assertEqual(app.s.environment['learnedLaunch']['key'],KEY)
            self.assertIn('APRENDIDA',calibration_label(app)[0]);stamp=app.profile_stamp
            app.s.selected_shot=2;App.apply_measured_profile(app)
            self.assertIsNone(app.active_learned_profile);self.assertNotIn('learnedLaunch',app.s.environment)
            self.assertNotEqual(app.profile_stamp,stamp);self.assertEqual(app.s.gravity,73.5)
    def test_solver_and_terrain_preview_cannot_extrapolate_the_learned_window(self):
        settings=Settings(mobile='ARMOR',angle=45,wind=0,gravity=390,power_scale=2.42,speed_offset=-.4,hero_x=0,hero_y=0,muzzle=False,quantize_power=True)
        settings.target_x,settings.target_y=point(settings,90,.5)
        metadata={'key':KEY,'power_range':[84,104],'max_flight_seconds':.7}
        settings.environment={'learnedLaunch':metadata,'hitTolerance':1}
        result=solve(settings);self.assertTrue(result['reachable']);self.assertTrue(84<=result['power']<=104);self.assertLessEqual(result['time'],.7)
        settings.target_x,settings.target_y=point(settings,200,.5)
        result=solve(settings);self.assertFalse(result['reachable']);self.assertTrue(84<=result.get('power',90)<=104)
        metadata['key']='dragonbound:ICE:0';self.assertFalse(solve(settings)['reachable'])
    def test_catalog_does_not_label_special_or_unmeasured_shots_as_learned(self):
        with tempfile.TemporaryDirectory() as folder:
            write_source(folder,{KEY:record()});library=LearnedLaunchLibrary(folder);library.refresh();rows={r[0]:r for r in library.rows()}
            self.assertIn('1: aprendida',rows['ARMOR'][1]);self.assertIn('2: mecanismo pendiente',rows['ARMOR'][1])
            self.assertIn('SS: sin tiros útiles',rows['ARMOR'][1]);self.assertIn('proyectil variable',rows['RANDOMIZER'][1])

if __name__=='__main__':unittest.main()
