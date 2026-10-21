import tempfile,unittest
from pathlib import Path
from autonomous_learning import AutonomousLearner
from calibration_book import CalibrationBook
from training_progress import share_observation

class TrainingProgressTests(unittest.TestCase):
    def feed(self,book,n,power,scale=2,owner=0):
        shot={'id':n,'native':True,'elapsed':0,'duration':1000,'start':[0,0,0,power*scale,0,400],'shotType':0,'metadata':{'player':owner,'power':power}}
        state={'status':'live','heroId':0,'activePlayer':0,'selectedShot':0,'currentPower':power,'wind':0,'windAngle':90,'players':[{'id':0,'x':0,'y':0,'mobile':0},{'id':1,'x':500,'y':0}], 'shots':[shot]}
        release={'hero':0,'x':0,'y':0,'shot':0,'power':power,'wind':0,'windAngle':90,'baseline':[]}
        return share_observation(book,state,release)
    def test_real_observation_bridge_needs_future_checks_before_improving_lab(self):
        with tempfile.TemporaryDirectory() as tmp:
            book=CalibrationBook(Path(tmp)/'book.json')
            for n,power in enumerate([100,180,260,340]):self.feed(book,n,power)
            self.assertIsNone(book.profile('dragonbound','ARMOR',0,0))
            for n,power in enumerate([120,220,320],10):progress=self.feed(book,n,power)
            self.assertAlmostEqual(book.profile('dragonbound','ARMOR',0,0)['power_scale'],2)
            self.assertEqual(progress['validated_lab_modes'],1)
            self.feed(book,12,320)
            self.assertEqual(len(book.records['dragonbound:ARMOR:0']['samples']),7)
            restored=CalibrationBook(book.path);self.assertEqual(len(restored.records['dragonbound:ARMOR:0']['accepted_validation']),3)
    def test_bridge_replaces_incumbent_only_after_measured_future_improvement(self):
        with tempfile.TemporaryDirectory() as tmp:
            book=CalibrationBook(Path(tmp)/'book.json');key='dragonbound:ARMOR:0'
            book.records[key]={'samples':[],'fit':{'power_scale':2.3,'speed_offset':0,'gravity':400,'wind_scale':None,'wind_observed':False}}
            for n,power in enumerate([100,180,260,340]):self.feed(book,n,power)
            self.assertAlmostEqual(book.records[key]['fit']['power_scale'],2.3)
            for n,power in enumerate([120,220,320],10):progress=self.feed(book,n,power)
            self.assertAlmostEqual(book.records[key]['fit']['power_scale'],2)
            self.assertAlmostEqual(book.records[key]['rollback_fit']['power_scale'],2.3)
            self.assertEqual(progress['measured_lab_improvements'],1)
    def test_bridge_rejects_another_players_shot(self):
        with tempfile.TemporaryDirectory() as tmp:
            book=CalibrationBook(Path(tmp)/'book.json');progress=self.feed(book,1,100,owner=1)
            self.assertEqual(progress['lab_observations'],0);self.assertEqual(progress['validated_lab_modes'],0)
    def test_focused_curriculum_repeats_car_for_at_most_three_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=AutonomousLearner(Path(tmp)/'learn.json');options=[{'name':'Armor','id':0},{'name':'Ice','id':1}];counts={}
            for _ in range(3):
                chosen=learner.choose_mobile(options,counts);self.assertEqual(chosen['name'],'Armor');counts['ARMOR']=counts.get('ARMOR',0)+1
            self.assertEqual(learner.choose_mobile(options,counts)['name'],'Ice')
    def test_new_mode_gets_concentrated_measurements_and_learned_mode_is_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=AutonomousLearner(Path(tmp)/'learn.json')
            self.assertEqual(learner.choose_probe('ARMOR',0,2,[0,1,2])['shot'],0)
            learner.records['dragonbound:ARMOR:0']={'samples':[],'model':{'scale':2}}
            self.assertEqual(learner.choose_probe('ARMOR',0,2,[0,1,2])['shot'],0)
            self.assertEqual(learner.choose_probe('ARMOR',0,3,[0,1,2])['shot'],1)
    def test_empirical_aim_interpolates_only_comparable_bracketing_outcomes(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=AutonomousLearner(Path(tmp)/'learn.json');hero={'x':0,'y':0};target=(600,0)
            state={'wind':10,'windAngle':0,'weather':[]};player={'look':1,'body':0,'rawAngle':45,'minAngle':10,'maxAngle':70}
            base={'episode':learner.episode,'origin':[0,0],'target':[600,0],'weather':[],'angle':45,'wind':10,'wind_angle':0}
            record={'cases':[{**base,'id':'a','power':100,'ends':[[400,0]]},{**base,'id':'b','power':300,'ends':[[800,0]]}]}
            plan=learner.bracketed(record,hero,target,state,player,True)
            self.assertEqual(plan['power'],200);self.assertEqual(plan['supporting_cases'],['a','b'])
            self.assertIsNone(learner.bracketed(record,hero,(900,0),state,player,True))
            other={**record,'cases':[{**c,'episode':'another-room'} for c in record['cases']]}
            self.assertIsNone(learner.bracketed(other,hero,target,state,player,True))
            self.assertIsNone(learner.bracketed(record,hero,target,{**state,'weather':[{'typeId':5}]},player,True))
            self.assertIsNone(learner.bracketed({**record,'multi_projectile':True},hero,target,state,player,True))
            self.assertIsNone(learner.bracketed(record,hero,target,{**state,'wind':20},player,True))
    def test_progress_never_confuses_measured_launches_with_proven_aiming_improvement(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner=AutonomousLearner(Path(tmp)/'learn.json')
            learner.records['dragonbound:ARMOR:0']={'samples':[{'id':'a'},{'id':'seed:b'}],'cases':[{'stage':'apuntar con modelo propio'},{'stage':'explorar fuerzas y ángulos'}]}
            progress=learner.progress();self.assertEqual(progress['measured_launches'],1)
            self.assertEqual(progress['retained_aimed_shots'],1);self.assertFalse(progress['accuracy_improvement_proven'])
