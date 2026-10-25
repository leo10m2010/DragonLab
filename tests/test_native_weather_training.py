import copy,json,tempfile,unittest
from pathlib import Path
from autonomous_learning import AutonomousLearner,weather_training_case,near_weather_escape


class WeatherTrainingTests(unittest.TestCase):
    def release(self):return {'hero':0,'x':0,'y':0,'power':100,'shot':0,'wind':0,'windAngle':90,'baseline':[],'learner':{'target':[500,0],'elevation':0}}
    def state(self,shot,kind=7):
        return {'status':'live','heroId':0,'activePlayer':0,'players':[{'id':0,'x':0,'y':0,'mobile':0},{'id':1,'x':500,'y':0}], 'selectedShot':0,'currentPower':100,'wind':0,'windAngle':90,'shots':[shot],'weather':[{'typeId':kind,'x':100,'size':100}]}
    def shot(self,kind=7,complete=True):
        shot={'id':1,'native':True,'elapsed':0,'duration':1000,'start':[0,0,0,200,0,0],'shotType':0,'metadata':{'player':0,'power':100}}
        if complete and kind==7:shot['jumps']=[[500,100,0,-200,0,0,0]]
        elif complete:
            shot['start'][3]=400;shot['duration']=800;shot['jumps']=[[300,120,0,-400,0,0,0],[400,80,0,400,0,0,0]]
        else:shot['duration']=500
        return shot

    def test_complete_native_mirror_and_tornado_paths_are_evidence_not_model_activation(self):
        for kind in (7,8):
            with self.subTest(kind=kind):
                shot=self.shot(kind);case=weather_training_case(shot,self.state(shot,kind),self.release(),'episode')
                self.assertGreaterEqual(len(case['path']),32);self.assertLessEqual(len(case['path']),160)
                self.assertEqual(case['crossings'][0]['status'],'complete-crossing')
                self.assertFalse(case['validated_for_aiming']);self.assertEqual(case['origin'],[0,0])

    def test_three_obstructed_partial_column_paths_cannot_certify_harmless_weather(self):
        for kind in (7,8):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as folder:
                learner=AutonomousLearner(Path(folder)/'learn.json')
                for i in range(3):
                    shot=self.shot(kind,False);shot['id']=i
                    learner.observe({'mobile':'ARMOR','shot':0},self.release(),self.state(shot,kind))
                record=learner.records['dragonbound:ARMOR:0'];effect=record['weather_effects'][str(kind)]
                self.assertEqual(effect['checked'],0);self.assertEqual(effect['partial_checked'],3)
                self.assertEqual(len(record['weather_training']),3)
                self.assertTrue(all(c['crossings'][0]['status']=='partial-crossing' for c in record['weather_training']))

    def test_complete_crossing_records_altered_flight_without_promoting_a_model(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=AutonomousLearner(Path(folder)/'learn.json');shot=self.shot()
            learner.observe({'mobile':'ARMOR','shot':0},self.release(),self.state(shot))
            record=learner.records['dragonbound:ARMOR:0']
            self.assertEqual(record['weather_effects']['7']['checked'],1);self.assertEqual(record['weather_effects']['7']['altered'],1)
            self.assertNotIn('model',record);self.assertFalse(record['multi_projectile'])

    def test_weather_evidence_is_bounded_and_retains_native_parameters(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=AutonomousLearner(Path(folder)/'learn.json')
            for i in range(35):
                shot=self.shot();shot['id']=i
                learner.observe({'mobile':'ARMOR','shot':0},self.release(),self.state(shot))
            rows=learner.records['dragonbound:ARMOR:0']['weather_training']
            self.assertEqual(len(rows),32);self.assertEqual(rows[-1]['power'],100)
            self.assertEqual(rows[-1]['shot'],0);self.assertEqual(rows[-1]['source'],'owned-native-path-reconstruction')

    def test_old_unqualified_column_checks_are_preserved_but_not_used_as_certification(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'learn.json';path.write_text(json.dumps({'schema':1,'records':{'dragonbound:ICE:1':{'samples':[],'weather_effects':{'7':{'checked':12,'altered':0},'8':{'checked':3,'altered':2}}}}}))
            learner=AutonomousLearner(path);effects=learner.records['dragonbound:ICE:1']['weather_effects']
            self.assertEqual(effects['7']['checked'],0);self.assertEqual(effects['7']['legacy_unverified_checked'],12)
            self.assertEqual(effects['8']['altered'],2)
            learner=AutonomousLearner(path);self.assertEqual(learner.records['dragonbound:ICE:1']['weather_effects']['7']['legacy_unverified_checked'],12)


class WeatherEscapeTests(unittest.TestCase):
    def proposal(self,kind=7,x=100,size=100):return [{'weather_crossings':[{'typeId':kind,'x':x,'size':size}]}]
    def test_escape_uses_vehicle_displacement_for_an_offset_muzzle(self):
        hero={'x':60};origin=(110,100)
        plan=near_weather_escape(hero,origin,self.proposal())
        self.assertEqual(plan['weather_escape_x'],76);self.assertEqual(plan['weather_escape_origin_x'],126)
        self.assertEqual(plan['weather_escape_distance'],16)

    def test_large_column_interior_and_remote_columns_do_not_authorize_walking(self):
        self.assertFalse(near_weather_escape({'x':100},(100,0),self.proposal(8,100,400)))
        self.assertFalse(near_weather_escape({'x':0},(0,0),self.proposal(7,500)))

    def test_nearby_outside_column_steps_away_instead_of_entering_it(self):
        plan=near_weather_escape({'x':50},(60,0),self.proposal())
        self.assertEqual(plan['weather_escape_x'],36);self.assertEqual(plan['weather_escape_distance'],14)

    def test_actual_replan_after_supported_escape_is_no_longer_inside_mirror(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=AutonomousLearner(Path(folder)/'learn.json')
            state={'heroId':0,'wind':0,'windAngle':0,'players':[{'id':0,'x':60,'y':0,'muzzleX':50,'muzzleY':0},{'id':1,'x':500,'y':0}], 'weather':[{'typeId':7,'x':100,'size':100}]}
            player={'look':1,'body':0,'rawAngle':45,'minAngle':10,'maxAngle':80};probe={'mobile':'ARMOR','shot':0,'power':100,'angle':45}
            model={'scale':2,'offset':0,'gravity':400,'wind_scale':4}
            blocked=learner.plan(state,player,probe,actual=True,model_override=model)
            self.assertEqual(blocked['unavailable_reason'],'unknown-weather');self.assertTrue(blocked['reposition_allowed'])
            self.assertEqual(blocked['weather_escape_x'],76)
            state['players'][0]['x']=88
            escaped=learner.plan(state,player,probe,actual=True,model_override=model)
            self.assertEqual(escaped['stage'],'evaluación con modelo congelado')
