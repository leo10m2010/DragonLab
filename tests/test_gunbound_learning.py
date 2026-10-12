import unittest,tempfile
from pathlib import Path
from gunbound_learning import measurement,GunBoundLearning
from calibration_book import CalibrationBook

def event(power=30,shot='shot2',ident='one',wind=0,angle=0):
    import math
    dt=.05;vx=power*9.2;vy=0;ax=wind*3.8*math.cos(math.radians(angle));ay=391-wind*3.8*math.sin(math.radians(angle))
    return {'mobile':'armor','shot':shot,'id':ident,'power':power,'wind':wind,'wind_angle':angle,'path':[{'x':100+vx*i*dt+ax*dt**2*i*(i-1)/2,'y':100+vy*i*dt+ay*dt**2*i*(i-1)/2,'t':i*dt} for i in range(8)]}
class LearningTests(unittest.TestCase):
    def test_explicit_euler_launch_is_recovered(self):
        m=measurement(event());self.assertAlmostEqual(m['vx'],276);self.assertAlmostEqual(m['ay'],391);self.assertEqual(m['selected_shot'],1)
    def test_item_and_nonballistic_paths_rejected(self):
        e=event();e['item']=True;self.assertIsNone(measurement(e))
        e=event();e['path'][4]['x']+=30;self.assertIsNone(measurement(e))
    def test_ss_is_kept_separate(self):self.assertEqual(measurement(event(shot='ss'))['selected_shot'],2)
    def test_waiting_final_shots_persist_and_deduplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=CalibrationBook(Path(tmp)/'book.json');m=measurement(event())
            b.observe({'status':'waiting','measurements':[m,m]},'gunbound-world')
            self.assertEqual(len(b.records['gunbound-world:ARMOR:1']['samples']),1)
            self.assertEqual(len(CalibrationBook(b.path).records['gunbound-world:ARMOR:1']['samples']),1)
    def test_training_does_not_activate_before_future_shots(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=CalibrationBook(Path(tmp)/'book.json')
            for i,p in enumerate([25,50,75,95]):b.observe({'measurements':[measurement(event(p,ident=str(i),wind=[5,5,5,22][i]))]},'gunbound-world')
            r=b.records['gunbound-world:ARMOR:1'];self.assertNotIn('fit',r);self.assertIn('candidate',r)
            for i,p in enumerate([30,60,90]):b.observe({'measurements':[measurement(event(p,ident='v'+str(i),wind=[1,1,0][i]))]},'gunbound-world')
            self.assertEqual(r['fit']['native_euler_step'],.05);self.assertEqual(len(r['accepted_validation']),3);self.assertEqual(r['fit']['wind_range'],[0,22])
    def test_independent_modes_are_not_combined(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=CalibrationBook(Path(tmp)/'book.json')
            b.observe({'measurements':[measurement(event(shot='shot1')),measurement(event(shot='ss',ident='two'))]},'gunbound-world')
            self.assertEqual(set(b.records),{'gunbound-world:ARMOR:0','gunbound-world:ARMOR:2'})
    def test_remove_restores_only_owned_callbacks(self):
        from gunbound_learning import REMOVE
        self.assertIn('this.onShotSubmitted===s.submit',REMOVE);self.assertIn('this.onShotSettled===s.settle',REMOVE)
