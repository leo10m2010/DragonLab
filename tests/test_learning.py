import sys,pathlib,tempfile,unittest,math,json,threading
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from learning_guard import update
from calibration_book import CalibrationBook
from shot_attribution import attributed_start
from shot_confirmation import wait_for_shot
from replay_store import ReplayStore
from core import Settings,solve
from performance import Governor
from app import App
from calibration_validation import validated_fit
from physics_extensions import segments
from types import SimpleNamespace
from ui_shell import refresh

def sample(power,index,scale=2):return {'power':power,'vx':power*scale,'vy':0,'ax':0,'ay':400,'wind':0,'wind_angle':90,'sample_id':str(index)}
def fit(scale=2):return {'power_scale':scale,'speed_offset':0,'gravity':400,'wind_scale':None,'wind_observed':False}
def feed(record,power,index,scale=2):
    value=sample(power,index,scale);record.setdefault('samples',[]).append(value);return update(record,value)
def shot(index=1,owner=None,power=None):
    metadata={} if owner is None else {'player_n':owner}
    if power is not None:metadata['power']=power
    return {'id':index,'native':True,'start':[10,20,60,300,0,400],'elapsed':100,'duration':1000,'shotType':0,'metadata':metadata}
def state(projectiles=None):return {'status':'live','heroId':0,'activePlayer':0,'selectedShot':0,'currentPower':150,'wind':0,'windAngle':90,'players':[{'id':0,'x':10,'y':20,'mobile':0,'isHero':True},{'id':1,'x':500,'y':20,'mobile':0}],'shots':projectiles or []}

class LearningTests(unittest.TestCase):
    def test_disabling_drifted_fit_resets_previously_applied_values(self):
        class Var:
            def __init__(self,v):self.v=str(v)
            def get(self):return self.v
            def set(self,v):self.v=str(v)
        with tempfile.TemporaryDirectory() as d:
            b=CalibrationBook(pathlib.Path(d)/'book.json');record={'samples':[],'fit':fit(2)};b.records['dragonbound:ARMOR:0']=record
            app=type('Fixture',(),{'s':Settings(),'clone_id':'dragonbound','book':b,'profiles':{},'profile_stamp':None,'vars':{k:Var(v) for k,v in [('gravity',73.5),('wind_scale',.74),('power_scale',1)]},'profile_key':lambda self:'fixture'})()
            App.apply_measured_profile(app);self.assertEqual(app.s.power_scale,2)
            record['drift_pending']=[{}];app.profile_stamp=None
            App.apply_measured_profile(app);self.assertEqual(app.s.power_scale,1);self.assertEqual(app.s.gravity,73.5)
    def trained(self,active=None):
        r={'samples':[]}
        if active:r['fit']=active
        for i,p in enumerate((100,180,260,340)):feed(r,p,i)
        self.assertIn('candidate',r);return r
    def test_candidate_does_not_leak_into_active_profile(self):
        r=self.trained();self.assertNotIn('fit',r)
        with tempfile.TemporaryDirectory() as d:
            b=CalibrationBook(pathlib.Path(d)/'book.json');b.records['dragonbound:ARMOR:0']=r
            self.assertIsNone(b.profile('dragonbound','ARMOR',0,0))
            self.assertIsNone(b.provisional('dragonbound','ARMOR',0,0,90))
            self.assertIsNone(b.acceleration('dragonbound','ARMOR',0,0,90))
    def test_promotion_requires_three_future_diverse_shots(self):
        r=self.trained()
        for i,p in enumerate((120,220,320),10):
            activated=feed(r,p,i)
            if i<12:self.assertIsNone(activated);self.assertNotIn('fit',r)
        self.assertAlmostEqual(r['fit']['power_scale'],2)
        self.assertEqual(len(r['accepted_validation']),3)
        self.assertTrue(set(x['id'] for x in r['accepted_validation']).isdisjoint({'0','1','2','3'}))
    def test_training_repeats_do_not_count_as_validation(self):
        r=self.trained()
        for _ in range(10):update(r,r['samples'][-1])
        self.assertEqual(r['candidate']['validation'],[]);self.assertNotIn('fit',r)
    def test_one_bad_sample_preserves_incumbent(self):
        r={'fit':fit(),'samples':[sample(p,i) for i,p in enumerate((100,180,260,340))]}
        feed(r,200,10,3)
        self.assertEqual(r['fit'],fit());self.assertNotIn('drift_pending',r)
    def test_failed_challenger_preserves_incumbent(self):
        r=self.trained(fit(1.8))
        for i,p in enumerate((120,220,320),10):feed(r,p,i,2.7)
        self.assertEqual(r['fit']['power_scale'],1.8)
        self.assertNotIn('candidate',r)
    def test_rollback_only_when_previous_fit_matches_new_evidence(self):
        r=self.trained(fit(1.8))
        for i,p in enumerate((120,220,320),10):feed(r,p,i)
        self.assertAlmostEqual(r['fit']['power_scale'],2)
        for i,p in enumerate((130,230,330),20):feed(r,p,i,1.8)
        self.assertEqual(r['fit']['power_scale'],1.8)
        self.assertEqual(r['status'],'Ajuste anterior recuperado')
    def test_two_bad_models_are_not_blindly_rolled_back(self):
        r={'fit':fit(2),'rollback_fit':fit(1.8),'samples':[]}
        for i,p in enumerate((130,230,330)):feed(r,p,i,3)
        self.assertEqual(r['fit']['power_scale'],2);self.assertIn('drift_pending',r)
    def test_new_wind_without_measured_coupling_is_not_validation(self):
        r=self.trained();value=sample(200,30);value['wind']=10
        update(r,value);self.assertEqual(r['candidate']['validation'],[])

class AttributionTests(unittest.TestCase):
    def test_enemy_turn_cannot_reuse_hero_bar(self):
        s=state([shot()]);s['activePlayer']=1
        self.assertIsNone(attributed_start(s,s['shots'][0]))
    def test_nearby_shooters_are_ambiguous_without_metadata(self):
        s=state([shot()]);s['players'][1]['x']=35
        self.assertIsNone(attributed_start(s,s['shots'][0]))
    def test_metadata_owns_power_even_when_ui_changed(self):
        s=state([shot(owner=0,power=120)]);s['activePlayer']=1;s['currentPower']=320
        self.assertEqual(attributed_start(s,s['shots'][0])['power'],120)
    def test_metadata_of_an_enemy_never_enters_hero_profile(self):
        s=state([shot(owner=1,power=120)])
        self.assertIsNone(attributed_start(s,s['shots'][0]))
    def test_delayed_special_projectile_is_not_a_primary_launch(self):
        s=state([shot()]);s['shots'][0]['delay']=300
        self.assertIsNone(attributed_start(s,s['shots'][0]))

class ConfirmationTests(unittest.TestCase):
    def test_uncalibrated_ui_is_not_claimed_as_native_force_confirmation(self):
        self.assertEqual(self.verify(state([shot()]))['status'],'observed')
    def verify(self,s,baseline=None):
        client=type('Client',(),{'sample':lambda self:s})()
        reader=type('Reader',(),{'client':client,'initial':state(baseline)})()
        plan={'power':150,'hero':0,'shot':0,'heroState':{'x':10,'y':20}}
        return wait_for_shot(reader,plan,{'power':150},threading.Event(),timeout=.01)
    def test_actual_native_power_confirms_or_reports_mismatch(self):
        self.assertEqual(self.verify(state([shot(owner=0,power=150)]))['status'],'confirmed')
        mismatch=self.verify(state([shot(owner=0,power=1)]))
        self.assertEqual(mismatch['status'],'mismatch');self.assertEqual(mismatch['actualPower'],1)
    def test_preexisting_projectile_is_not_confirmation(self):
        existing=shot(owner=0,power=150)
        self.assertEqual(self.verify(state([existing]),[existing])['status'],'unconfirmed')
    def test_changed_turn_without_power_is_observed_only(self):
        s=state([shot()]);s['activePlayer']=1
        self.assertEqual(self.verify(s)['status'],'observed')

class ReplayTests(unittest.TestCase):
    def test_concurrent_writers_keep_complete_bounded_cases(self):
        with tempfile.TemporaryDirectory() as d:
            store=ReplayStore(d,limit=3);errors=[]
            def save(offset):
                try:
                    for i in range(8):store.record(Settings(angle=40+offset+i),'unconfirmed',{'status':'unconfirmed'})
                except Exception as error:errors.append(error)
            threads=[threading.Thread(target=save,args=(j*10,)) for j in range(2)]
            for t in threads:t.start()
            for t in threads:t.join()
            self.assertFalse(errors)
            files=list(pathlib.Path(d).glob('*.json'));self.assertEqual(len(files),3)
            self.assertTrue(all(json.loads(p.read_text())['schema']==1 for p in files))
    def test_controlled_fixture_suite(self):
        fixtures=json.loads((pathlib.Path(__file__).parent/'fixtures/ballistics.json').read_text())
        for index,case in enumerate(fixtures):
            with self.subTest(case=index):
                settings=Settings(**case['settings']);result=solve(settings)
                for key,value in case.get('expected',{}).items():self.assertEqual(result.get(key),value)
                if case.get('traceKinds'):
                    _,events=segments(settings,case['tracePower'])
                    for kind,count in case['traceKinds'].items():self.assertEqual(sum(e['kind']==kind for e in events),count)
    def test_tornado_size_is_preserved_in_recorded_case(self):
        with tempfile.TemporaryDirectory() as d:
            s=Settings(environment={'activeWeathers':[{'typeId':8,'x':400,'size':160}]})
            ReplayStore(d).record(s,'unconfirmed',{'status':'unconfirmed'})
            payload=json.loads(next(pathlib.Path(d).glob('*.json')).read_text())
            self.assertEqual(payload['settings']['environment']['activeWeathers'][0]['size'],160)
    def test_replay_is_bounded_deduplicated_and_excludes_names(self):
        with tempfile.TemporaryDirectory() as d:
            store=ReplayStore(d,limit=3)
            s=Settings(environment={'players':[{'id':1,'x':400,'y':30,'name':'private'}]})
            self.assertTrue(store.record(s,'blocked',{'blocked':True}))
            self.assertFalse(store.record(s,'blocked',{'blocked':True}))
            for i in range(5):s.angle=40+i;store.record(s,'blocked',{'blocked':True})
            files=list(pathlib.Path(d).glob('case-*.json'));self.assertEqual(len(files),3)
            self.assertNotIn('private',''.join(p.read_text() for p in files))
            self.assertFalse(store.record(s,'confirmed',{}))
    def test_blocked_case_replays_with_same_reference(self):
        with tempfile.TemporaryDirectory() as d:
            s=Settings(angle=60,hero_x=150,hero_y=400,target_x=700,target_y=400,gravity=396,power_scale=2.45,muzzle=False,environment={'terrain':{'polygon':[(100,370),(200,370),(200,430),(100,430)]},'hitTolerance':18})
            result=solve(s);ReplayStore(d).record(s,'blocked',result)
            payload=json.loads(next(pathlib.Path(d).glob('*.json')).read_text());again=solve(Settings(**payload['settings']))
            self.assertFalse(again['reachable']);self.assertEqual(again['guide_power'],result['guide_power'])
    def test_restart_overwrites_oldest_slot_without_growth(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(5):ReplayStore(d,limit=2).record(Settings(angle=40+i),'unconfirmed',{'status':'unconfirmed'})
            self.assertEqual(len(list(pathlib.Path(d).glob('*.json'))),2)

class GovernorTests(unittest.TestCase):
    def test_lobby_and_other_turn_use_less_polling(self):
        g=Governor();own=g.intervals('Ligero');other=g.intervals('Ligero',own_turn=False);lobby=g.intervals('Ligero',active=False)
        self.assertGreater(other[0],own[0]);self.assertGreater(lobby[0],other[0])
        self.assertEqual(g.intervals('Normal')[0],.25)

class UIAndDataTests(unittest.TestCase):
    def test_three_simple_states_and_special_vehicle_stays_learning(self):
        class Widget:
            def config(self,**values):self.values=values
        with tempfile.TemporaryDirectory() as d:
            b=CalibrationBook(pathlib.Path(d)/'book.json');b.records['dragonbound:ARMOR:0']={'fit':fit(),'samples':[]}
            result={'reachable':True}
            a=SimpleNamespace(book=b,clone_id='dragonbound',s=Settings(),result=result,display_result=lambda:result,has_position_data=True,confidence=Widget(),target_hint=Widget(),fire_hint=Widget(),target_key='Ctrl',fire_key='Q',auto_shot_enabled=True)
            refresh(a);self.assertTrue(a.confidence.values['text'].startswith('Listo'))
            result['blocked']=True;refresh(a);self.assertTrue(a.confidence.values['text'].startswith('Bloqueado'))
            result.pop('blocked');a.s.mobile='KALSIDDON';refresh(a);self.assertTrue(a.confidence.values['text'].startswith('Aprendiendo'))
    def test_invalid_numbers_cannot_enter_calibration(self):
        values=[sample(p,i) for i,p in enumerate((100,180,260,340))];values[-1]['power']=math.nan
        with self.assertRaisesRegex(ValueError,'no finita'):validated_fit(values)

if __name__=='__main__':unittest.main()
