import math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

from autonomous_learning import AutonomousLearner,launch_origin,predicted_path


MODEL={'scale':2,'offset':0,'gravity':400,'wind_scale':0}


class TrainingLaunchOriginTests(unittest.TestCase):
    def scenario(self):
        hero={'id':0,'mobile':0,'x':100,'y':1000,'look':1,'body':0,'muzzleX':0,'muzzleY':0,
              'muzzles':[{'angle':0,'radius':40},{'angle':90,'radius':20},{'angle':0,'radius':60}]}
        state={'status':'live','heroId':0,'activePlayer':0,'players':[hero,{'id':1,'x':600,'y':1000}], 'wind':0,'windAngle':0,'weather':[]}
        player={'x':100,'y':1000,'look':1,'body':0,'rawAngle':45,'minAngle':45,'maxAngle':45}
        probe={'mobile':'ARMOR','shot':0,'angle':45,'power':100}
        return state,player,probe

    def test_native_shot_origin_overrides_legacy_center_and_corrects_inverse_power(self):
        with tempfile.TemporaryDirectory() as directory:
            learner=AutonomousLearner(Path(directory)/'learner.json');state,player,probe=self.scenario()
            with patch('core.solve',side_effect=AssertionError('Lab solver must not teach autonomous shots')):
                result=learner.plan(state,player,probe,actual=True,model_override=MODEL)
            self.assertEqual(result['origin'],[140,1000]);self.assertEqual(result['origin_source'],'native-shot-muzzle')
            self.assertEqual(result['power'],214)
            # Native time of flight and launch origin must reach the target;
            # the old center-based 224 charge misses this same target.
            duration=2*(2*result['power'])*math.sin(math.pi/4)/400
            end=predicted_path(MODEL,result['origin'],45,result['power'],0,0,duration)[-1]
            self.assertLess(math.dist(end,(600,1000)),3)
            old_duration=2*448*math.sin(math.pi/4)/400
            old_end=predicted_path(MODEL,result['origin'],45,224,0,0,old_duration)[-1]
            self.assertGreater(math.dist(old_end,(600,1000)),35)

    def test_ice_second_shot_uses_its_own_native_definition(self):
        with tempfile.TemporaryDirectory() as directory:
            learner=AutonomousLearner(Path(directory)/'learner.json');state,player,probe=self.scenario()
            first=learner.plan(state,player,{**probe,'mobile':'ICE','shot':0},actual=True,model_override=MODEL)
            second=learner.plan(state,player,{**probe,'mobile':'ICE','shot':1},actual=True,model_override=MODEL)
            self.assertEqual(first['origin'],[140,1000]);self.assertEqual(second['origin'],[100,980])
            self.assertNotEqual(first['power'],second['power'])

    def test_body_slope_facing_and_reverse_mobile_transform_the_muzzle(self):
        hero=self.scenario()[0]['players'][0]
        cases=[('ARMOR',1,0,(140,1000)),('ARMOR',0,0,(60,1000)),
               ('ARMOR',1,30,(135,1020)),('ARMOR',0,30,(65,980)),
               ('ADUKA',1,0,(60,1000)),('ADUKA',0,0,(140,1000)),
               ('NAK',1,30,(65,980))]
        for mobile,look,body,expected in cases:
            with self.subTest(mobile=mobile,look=look,body=body):
                self.assertEqual(launch_origin({**hero,'look':look,'body':body},mobile,0),(expected,'native-shot-muzzle'))

    def test_fresh_pose_overrides_older_serialized_position_and_facing(self):
        with tempfile.TemporaryDirectory() as directory:
            learner=AutonomousLearner(Path(directory)/'learner.json');state,player,probe=self.scenario()
            state['players'][0].update(look=0,body=0)
            player.update(x=120,y=1100,look=1,body=30,rawAngle=75,minAngle=75,maxAngle=75)
            result=learner.plan(state,player,probe,actual=True,model_override=MODEL)
            self.assertEqual(result['origin'],[155,1120]);self.assertEqual(result['heading'],45)

    def test_actual_replan_after_movement_does_not_reuse_previous_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            learner=AutonomousLearner(Path(directory)/'learner.json');state,player,probe=self.scenario()
            initial=learner.plan(state,player,probe,model_override=MODEL)
            player.update(x=130,y=1010,body=30,rawAngle=75,minAngle=75,maxAngle=75)
            actual=learner.plan(state,player,probe,actual=True,previous=initial,model_override=MODEL)
            self.assertEqual(initial['origin'],[140,1000]);self.assertEqual(actual['origin'],[165,1030])
            self.assertEqual(actual['origin_source'],'native-shot-muzzle');self.assertEqual(actual['heading'],45)

    def test_collision_starts_at_native_muzzle_not_at_a_wall_behind_it(self):
        with tempfile.TemporaryDirectory() as directory:
            learner=AutonomousLearner(Path(directory)/'learner.json');state,player,probe=self.scenario()
            ground=[None]*800;ground[110:132]=[0]*22;state['terrain']={'heights':ground}
            result=learner.plan(state,player,probe,actual=True,model_override=MODEL)
            self.assertEqual(result['stage'],'evaluación con modelo congelado')
            del state['players'][0]['muzzles']
            legacy=learner.plan(state,player,probe,actual=True,model_override=MODEL)
            self.assertEqual(legacy['unavailable_reason'],'terrain-blocked')

    def test_blocked_and_weather_candidates_retain_their_planned_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            learner=AutonomousLearner(Path(directory)/'learner.json');state,player,probe=self.scenario()
            ground=[None]*800;ground[220:232]=[0]*12;state['terrain']={'heights':ground}
            blocked=learner.plan(state,player,probe,actual=True,model_override=MODEL)
            self.assertTrue(blocked['blocked_plans'])
            self.assertEqual(blocked['blocked_plans'][0]['origin'],[140,1000])
            state.pop('terrain');state['weather']=[{'typeId':5,'x':200,'size':20}]
            weather=learner.plan(state,player,probe,actual=True,model_override=MODEL)
            self.assertEqual(weather['weather_probes'][0]['origin'],[140,1000])
            self.assertEqual(weather['weather_probes'][0]['origin_source'],'native-shot-muzzle')

    def test_older_or_invalid_muzzle_readers_keep_explicit_fallback_sources(self):
        hero=self.scenario()[0]['players'][0]
        for invalid in (None,3,[None],[{'angle':None,'radius':40}],[{'angle':0,'radius':400}]):
            with self.subTest(invalid=invalid):
                legacy={**hero,'muzzles':invalid,'muzzleX':12,'muzzleY':-8}
                self.assertEqual(launch_origin(legacy,'ARMOR',0),((112,992),'legacy-muzzle-offset'))
                self.assertEqual(launch_origin({**legacy,'muzzleX':float('nan')},'ARMOR',0),((100,1000),'hero-center'))

    def test_confirmed_native_start_keeps_geometry_error_separate_from_aim_error(self):
        with tempfile.TemporaryDirectory() as directory:
            learner=AutonomousLearner(Path(directory)/'learner.json');state,player,probe=self.scenario()
            plan=learner.plan(state,player,probe,actual=True,model_override=MODEL)
            release={'hero':0,'x':100,'y':1000,'power':plan['power'],'angle':45,'shot':0,'wind':0,'windAngle':0,'baseline':[],'learner':plan}
            state['shots']=[{'id':1,'native':True,'elapsed':0,'duration':1000,'start':[140,1000,45,plan['power']*2,0,400],'shotType':0,'metadata':{'player':0,'power':plan['power']}}]
            self.assertTrue(learner.observe(probe,release,state))
            geometry=learner.records['dragonbound:ARMOR:0']['last_launch_geometry']
            self.assertEqual(geometry['planned_origin'],[140,1000]);self.assertEqual(geometry['native_origin'],[140,1000])
            self.assertEqual(geometry['origin_error_px'],0)


if __name__=='__main__':unittest.main()
