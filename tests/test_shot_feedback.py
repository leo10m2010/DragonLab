import unittest
from types import SimpleNamespace
from shot_feedback import corrected_hypothesis
from product_status import capture_status

class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.model=dict(scale=2,offset=0,gravity=400,wind_scale=4)
        self.player=dict(rawAngle=50,look=1,body=0,minAngle=10,maxAngle=80)
        self.sample=dict(id='a',episode='one',simple=True,power=100,speed=220,ax=0,ay=400,wind=0,wind_angle=0,raw_angle=50,pose={k:self.player[k] for k in ('look','body','minAngle','maxAngle')})
        self.record={'samples':[self.sample]};self.state=dict(wind=0,windAngle=0,weather=[])
    def correction(self):return corrected_hypothesis(self.model,self.record,'one',self.state,self.player)
    def test_overspeed_reduces_required_force_without_changing_original(self):
        result=self.correction();self.assertAlmostEqual(200/result['scale'],90.909,places=2);self.assertEqual(self.model['scale'],2)
    def test_underspeed_increases_force(self):
        self.sample['speed']=180;self.assertGreater(200/self.correction()['scale'],100)
    def test_different_episode_slope_weather_and_large_drift_are_rejected(self):
        for key,value in [('episode','old'),('simple',False),('speed',400),('raw_angle',70),('ay',500)]:
            old=self.sample[key];self.sample[key]=value;self.assertIsNone(self.correction());self.sample[key]=old
        self.state['weather']=[{'typeId':1}];self.assertIsNone(self.correction())
    def test_training_status_has_priority_over_stale_capture_and_errors(self):
        session=SimpleNamespace(running=True,status='Esperando tu turno',shots=8)
        app=SimpleNamespace(training_session=session,last_live=0,last_error='old')
        self.assertEqual(capture_status(app),('Entrenando','Esperando tu turno · 8 tiros'))
        session.running=False;session.status='Sesión finalizada'
        self.assertEqual(capture_status(app),('Entrenamiento detenido','Sesión finalizada'))
