import unittest,tempfile
from pathlib import Path
from unittest.mock import Mock
from weapon_policy import enemy_for,comparable,dual_decision
from adaptive_training import AdaptiveTrial

class WeaponPolicyTests(unittest.TestCase):
    def rows(self,damage=100):return [dict(episode='a',target_id=2,wind=4,wind_angle=90,path_error_px=5,health_window_known=True,enemy_health_drop=damage) for _ in range(5)]
    def state(self):return dict(heroId=0,wind=4,windAngle=90,players=[dict(id=0,team=0,x=0,y=0,hp=800,shield=0),dict(id=1,team=0,x=90,y=0,hp=900,shield=0),dict(id=2,team=1,x=100,y=0,hp=150,shield=0)])
    def test_target_resolution_never_selects_nearer_ally(self):
        self.assertEqual(enemy_for(self.state(),[90,0])['id'],2)
    def test_measurements_do_not_cross_match_target_or_wind(self):
        rows=self.rows();state=self.state();enemy=state['players'][2]
        self.assertEqual(len(comparable(rows,'a',state,enemy)),5)
        self.assertFalse(comparable(rows,'old',state,enemy));self.assertFalse(comparable(rows,'a',state,{'id':9}))
        self.assertFalse(comparable(rows,'a',{**state,'wind':10},enemy))
        self.assertFalse(comparable(rows,'a',{**state,'windAngle':180},enemy))
    def test_dual_only_for_supported_finishing_opportunity(self):
        self.assertTrue(dual_decision(self.rows(),150,True,1,'evaluation')[0])
        for remaining in (50,900,None):self.assertFalse(dual_decision(self.rows(),remaining,True,1,'evaluation')[0])
        for shot,phase in ((2,'evaluation'),(1,'calibration'),(0,'recovery')):self.assertFalse(dual_decision(self.rows(),150,True,shot,phase)[0])
        self.assertFalse(dual_decision(self.rows()[:2],150,True,1,'evaluation')[0])
        rows=self.rows();rows[0]['path_error_px']=200;rows[1]['path_error_px']=100
        self.assertFalse(dual_decision(rows,150,True,1,'evaluation')[0])
    def test_bullet_two_is_selected_when_measured_to_finish(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=Mock();learner.episode='a';learner.records={f'dragonbound:ARMOR:{s}':{'model':{'scale':2}} for s in (0,1,2)};learner.applicable_model.return_value=({'scale':2},'known')
            trial=AdaptiveTrial(Path(folder)/'report.json',learner)
            for shot,damage in ((0,60),(1,160),(2,400)):trial.profile('ARMOR',shot).tests=self.rows(damage)
            self.assertEqual(trial.probe('ARMOR',self.state(),[0,1,2])['shot'],1)
            self.assertEqual(trial.probe('ARMOR',self.state(),[0,2])['shot'],2)
