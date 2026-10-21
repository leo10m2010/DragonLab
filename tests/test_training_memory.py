import unittest,tempfile,json
from pathlib import Path
from training_memory import ActionMemory

class MemoryTests(unittest.TestCase):
    def example(self,n=1):
        return {'mobile':'ARMOR','shot':1,'angle':55,'turn_serial':n},{'hero':0,'x':100,'y':100,'shot':1,'power':180,'wind':10,'windAngle':45,'lab':{'angle':55,'target':[600,100],'action':'apuntar'}},{'target_distance':10,'observed_end':[590,100]}
    def live(self,wind=10):return {'heroId':0,'wind':wind,'windAngle':45,'players':[{'id':0,'x':100,'y':100},{'id':1,'x':600,'y':100}]}
    def test_old_data_can_seed_and_new_independent_observations_change_preferences(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'memory.json';memory=ActionMemory(path);probe,release,feedback=self.example()
            self.assertTrue(memory.learn(probe,release,feedback))
            candidate={'mobile':'ARMOR','shot':0,'angle':35}
            self.assertEqual(memory.recommend(candidate,self.live(),[0,1])['shot'],0)
            memory.learn(*self.example(2));restored=ActionMemory(path)
            self.assertEqual(restored.recommend(candidate,self.live(),[0,1])['shot'],1)
    def test_deduplication_and_unavailable_modes_or_other_wind_are_respected(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory=ActionMemory(Path(tmp)/'memory.json');example=self.example()
            memory.learn(*example);self.assertFalse(memory.learn(*example));memory.learn(*self.example(2))
            candidate={'mobile':'ARMOR','shot':0,'angle':35}
            self.assertEqual(memory.recommend(candidate,self.live(),[0])['shot'],0)
            self.assertEqual(memory.recommend(candidate,self.live(30),[0,1])['shot'],0)
    def test_excavation_does_not_count_as_failed_aim_or_a_hit(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory=ActionMemory(Path(tmp)/'memory.json');p,r,f=self.example();r['lab']['action']='abrir paso'
            self.assertFalse(memory.learn(p,r,f));self.assertFalse(memory.cells)
    def test_corrupt_local_memory_does_not_break_the_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'memory.json';path.write_text(json.dumps({'schema':1,'cells':{'bad':{'count':'bad'},'null':None},'seen':None}))
            self.assertFalse(ActionMemory(path).cells)
    def test_memory_is_bounded_even_when_many_contexts_are_observed(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory=ActionMemory(Path(tmp)/'memory.json',limit=4)
            for n in range(20):
                p,r,f=self.example(n);r['lab']['angle']=n*5
                memory.learn(p,r,f)
            self.assertLessEqual(len(memory.cells),4)
