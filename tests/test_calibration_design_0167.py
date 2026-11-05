import math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from autonomous_learning import AutonomousLearner,occupied,predicted_path


MODEL={'scale':2,'offset':0,'gravity':300,'wind_scale':0}


class CalibrationDesignTests(unittest.TestCase):
    def fixture(self,tmp):
        learner=AutonomousLearner(Path(tmp)/'learning.json');learner.episode='match'
        learner.records['dragonbound:ARMOR:0']={'samples':[]}
        state={'heroId':0,'players':[{'id':0,'x':100,'y':200,'team':0},{'id':1,'x':700,'y':200,'team':1}],'wind':0,'windAngle':0,'weather':[]}
        player={'look':1,'body':0,'rawAngle':45,'minAngle':10,'maxAngle':55}
        probe={'mobile':'ARMOR','shot':0,'angle':75,'power':100}
        return learner,state,player,probe

    def test_research_force_ranks_real_clear_solutions_instead_of_first_valid_arc(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner,state,player,probe=self.fixture(tmp)
            low=learner.plan(state,player,probe,model_override=MODEL,calibration_search=True)
            high=learner.plan(state,player,{**probe,'power':360},model_override=MODEL,calibration_search=True)
            self.assertGreater(high['power']-low['power'],40)
            for plan in (low,high):
                self.assertTrue(1<=plan['power']<=400)
                self.assertGreater(plan['calibration_design']['candidate_count'],2)
                self.assertFalse(plan['calibration_design']['actual_revalidated'])
                solved=learner.solve_observed(MODEL,tuple(plan['origin']),tuple(plan['target']),plan['heading'],0,0,details=True)
                self.assertEqual(plan['power'],solved[0])
                endpoint=predicted_path(MODEL,tuple(plan['origin']),plan['heading'],plan['power'],0,0,solved[1])[-1]
                self.assertLess(math.dist(endpoint,plan['target']),1)

    def test_research_prefers_a_new_force_when_the_requested_force_was_already_measured(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner,state,player,probe=self.fixture(tmp)
            first=learner.plan(state,player,probe,model_override=MODEL,calibration_search=True)
            learner.records['dragonbound:ARMOR:0']['samples']=[{'id':'native-one','episode':'match','simple':True,'power':first['power'],'wind':0,'wind_angle':0}]
            next_plan=learner.plan(state,player,probe,model_override=MODEL,calibration_search=True)
            self.assertGreaterEqual(abs(next_plan['power']-first['power']),40)
            self.assertEqual(next_plan['calibration_design']['native_context_samples'],1)

    def test_only_clear_paths_are_research_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner,state,player,probe=self.fixture(tmp)
            # A wall blocks the low flat arcs that would require the most force.
            heights=[None]*1000
            for x in range(170,195):heights[x]=170
            state['terrain']={'heights':heights}
            plan=learner.plan(state,player,{**probe,'power':360},model_override=MODEL,calibration_search=True)
            solution=learner.solve_observed(MODEL,tuple(plan['origin']),tuple(plan['target']),plan['heading'],0,0,details=True)
            path=predicted_path(MODEL,tuple(plan['origin']),plan['heading'],plan['power'],0,0,solution[1])
            self.assertFalse(any(occupied(state['terrain'],*point) and math.dist(point,plan['target'])>20 for point in path[1:]))
            self.assertLess(plan['power'],280)

    def test_actual_reverification_is_pinned_even_with_research_flag_and_desired_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner,state,player,probe=self.fixture(tmp)
            player['rawAngle']=42
            planned=learner.plan(state,player,{**probe,'power':360},model_override=MODEL,calibration_search=True)
            actual=learner.plan(state,player,{**probe,'power':360},actual=True,previous=planned,model_override=MODEL,calibration_search=True)
            self.assertEqual(actual['raw_angle'],42)
            self.assertTrue(actual['calibration_design']['actual_revalidated'])
            self.assertEqual(actual['calibration_design']['solved_power'],actual['power'])
            self.assertNotEqual(actual['power'],360)

    def test_frozen_default_keeps_first_clear_arc_and_does_not_gain_research_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner,state,player,probe=self.fixture(tmp)
            a=learner.plan(state,player,probe,model_override=MODEL)
            b=learner.plan(state,player,{**probe,'power':360},model_override=MODEL)
            self.assertEqual(a['power'],b['power']);self.assertEqual(a['raw_angle'],b['raw_angle'])
            self.assertNotIn('calibration_design',a)

    def test_old_wrong_wind_and_seed_samples_do_not_supply_power_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner,state,player,probe=self.fixture(tmp)
            learner.records['dragonbound:ARMOR:0']['samples']=[{'id':'old','episode':'old','simple':True,'power':210,'wind':0,'wind_angle':0},{'id':'wrongwind','episode':'match','simple':True,'power':210,'wind':20,'wind_angle':0},{'id':'seed:hypothesis','episode':'match','simple':True,'power':210,'wind':0,'wind_angle':0}]
            plan=learner.plan(state,player,probe,model_override=MODEL,calibration_search=True)
            self.assertEqual(plan['calibration_design']['native_context_samples'],0)

    def test_research_angle_work_remains_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner,state,player,probe=self.fixture(tmp);player.update(minAngle=-180,maxAngle=180)
            with patch.object(learner,'solve_observed',wraps=learner.solve_observed) as solve:
                learner.plan(state,player,probe,model_override=MODEL,calibration_search=True)
            self.assertLessEqual(solve.call_count,64)

    def test_research_ranking_cannot_extrapolate_a_prefix_force_or_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner,state,player,probe=self.fixture(tmp);probe={**probe,'shot':1,'power':360}
            view={'prefix_only':True,'samples':[],'weather_effects':{},'prefix_horizon_s':20,'prefix_power_range':[200,240]}
            result=learner.plan(state,player,probe,model_override=MODEL,record_override=view,calibration_search=True)
            self.assertTrue(200<=result['power']<=240)
            self.assertGreater(result['calibration_design']['candidate_count'],0)
            view['prefix_horizon_s']=.1
            result=learner.plan(state,player,probe,model_override=MODEL,record_override=view,calibration_search=True)
            self.assertEqual(result['unavailable_reason'],'prefix-range-unchecked')
            self.assertNotIn('calibration_design',result)

    def test_unknown_weather_never_becomes_a_ranked_research_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner,state,player,probe=self.fixture(tmp)
            state['weather']=[{'typeId':7,'x':400,'size':100}]
            result=learner.plan(state,player,probe,model_override=MODEL,calibration_search=True)
            self.assertEqual(result['unavailable_reason'],'unknown-weather')
            self.assertNotIn('calibration_design',result)


if __name__=='__main__':unittest.main()
