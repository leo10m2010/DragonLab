import copy,unittest
from unittest.mock import Mock
from training_movement import walking_step,choose_reposition


def scene():
    return {'heroId':0,'players':[{'id':0,'x':120,'y':100,'body':0},{'id':1,'x':400,'y':100}], 'terrain':{'heights':[100]*700}}

def exposure(low):
    return {'estimate':.1 if low else .9,'low':.02 if low else .7,'high':.25 if low else .98,'samples':12,'episodes':3}


class AdaptiveMovementTests(unittest.TestCase):
    def test_walking_step_honors_requested_world_pixel_distance(self):
        self.assertEqual(walking_step(scene(),400)['distance'],14)
        self.assertEqual(walking_step(scene(),400,distance=32)['distance'],32)
        self.assertEqual(walking_step(scene(),400,distance=6)['expected_to'],[126,100])
    def test_small_clear_solution_does_not_walk_full_budget(self):
        evaluate=Mock(return_value=True)
        step=choose_reposition(scene(),400,'angle-unavailable',movement_budget=72,time_left=25,evaluate=evaluate)
        self.assertEqual(step['distance'],2);self.assertEqual(step['direction'],'right');self.assertLessEqual(evaluate.call_count,4)
    def test_long_walk_can_be_selected_when_shorter_distances_do_not_clear(self):
        checked=[]
        def evaluate(state,step):checked.append((step['direction'],step['distance']));return step['distance']>=48 and step['direction']=='left'
        step=choose_reposition(scene(),400,'terrain-blocked',movement_budget=60,time_left=25,evaluate=evaluate)
        self.assertEqual(step['direction'],'left');self.assertGreaterEqual(step['distance'],48);self.assertLess(step['distance'],60)
        self.assertTrue(step['distance_refined']);self.assertEqual(step['selection'],'predicted-clear-path');self.assertLessEqual(len(checked),8)
        self.assertIn(('left',8),checked);self.assertIn(('left',28),checked)
    def test_mid_distance_is_selected_instead_of_larger_clear_solution(self):
        step=choose_reposition(scene(),400,'angle-unavailable',movement_budget=72,time_left=25,evaluate=lambda state,step:step['distance']>=14)
        self.assertEqual(step['distance'],16)
    def test_remaining_time_and_world_budget_bound_every_candidate(self):
        for options,cap in (({'movement_budget':9,'time_left':25},9),({'movement_budget':72,'time_left':7},12)):
            with self.subTest(options=options):
                seen=[]
                step=choose_reposition(scene(),400,'terrain-blocked',evaluate=lambda state,step:seen.append(step['distance']) or False,**options)
                self.assertTrue(seen);self.assertLessEqual(max(seen),cap);self.assertLessEqual(step['distance'],cap)
        self.assertIsNone(choose_reposition(scene(),400,'angle-unavailable',movement_budget=72,time_left=6.5,evaluate=lambda *_:True))
        self.assertIsNone(choose_reposition(scene(),400,'angle-unavailable',movement_budget=1,time_left=25))
    def test_cliff_shortens_proposal_and_retains_three_pixel_stopping_margin(self):
        state=scene();state['terrain']['heights'][128:]=[None]*(700-128)
        step=choose_reposition(state,400,'angle-unavailable',avoid='left',movement_budget=72,time_left=25,evaluate=lambda *_:True)
        self.assertIsNotNone(step);self.assertEqual(step['direction'],'right')
        self.assertLess(step['expected_to'][0],128-2);self.assertGreaterEqual(step['distance'],2)
        self.assertEqual(step['clearance_margin'],3)
    def test_one_pixel_hole_and_cliff_margin_cannot_be_skipped_by_long_plan(self):
        state=scene();state['terrain']['heights'][127]=None
        self.assertIsNone(walking_step(state,400,avoid='left',distance=30))
        step=walking_step(state,400,avoid='left',distance=30,allow_shorter=True)
        self.assertEqual(step['distance'],3);self.assertEqual(step['expected_to'][0],123)
    def test_unknown_weather_escape_uses_distance_to_escape_target(self):
        step=choose_reposition(scene(),142,'unknown-weather',movement_budget=60,time_left=25,evaluate=lambda state,step:state['players'][0]['x']>=142)
        self.assertEqual(step['direction'],'right');self.assertEqual(step['distance'],22)
    def test_visited_or_stalled_direction_is_not_revisited_or_forced(self):
        step=choose_reposition(scene(),400,'angle-unavailable',movement_budget=30,time_left=25,avoid='right',visited=[[116,100],[104,100]],evaluate=lambda *_:True)
        self.assertEqual(step['direction'],'left');self.assertNotIn(step['expected_to'],[[116,100],[104,100]])
        self.assertEqual(step['distance'],30)
    def test_opponent_risk_only_ties_equal_length_clear_supported_positions(self):
        state=scene();original=copy.deepcopy(state)
        step=choose_reposition(state,400,'angle-unavailable',movement_budget=60,time_left=25,evaluate=lambda *_:True,position_risk=lambda point:exposure(point[0]<120))
        self.assertEqual(step['direction'],'left');self.assertEqual(step['distance'],2);self.assertEqual(step['selection'],'lower-observed-exposure');self.assertEqual(state,original)
        # A much safer longer step is not a tie with a clear short solution.
        risk=Mock(side_effect=AssertionError('Do not rank longer or blocked alternatives'))
        step=choose_reposition(state,400,'angle-unavailable',movement_budget=60,time_left=25,evaluate=lambda state,step:step['direction']=='right',position_risk=risk)
        self.assertEqual(step['distance'],2);self.assertEqual(step['direction'],'right');risk.assert_not_called()
    def test_clear_bracket_is_refined_instead_of_using_a_fixed_middle_tier(self):
        seen=[]
        def evaluate(state,step):seen.append(step['distance']);return step['direction']=='left' and step['distance']>=20
        step=choose_reposition(scene(),400,'terrain-blocked',movement_budget=72,time_left=25,evaluate=evaluate)
        self.assertGreaterEqual(step['distance'],20);self.assertLess(step['distance'],28);self.assertTrue(step['distance_refined']);self.assertLessEqual(len(seen),8)
    def test_missing_ground_and_invalid_budgets_never_propose_motion(self):
        state=scene();state.pop('terrain')
        self.assertIsNone(choose_reposition(state,400,'angle-unavailable',movement_budget=60,time_left=25))
        for budget,time in ((float('nan'),25),(72,float('inf')),(-1,25),(True,25)):
            with self.subTest(budget=budget,time=time):self.assertIsNone(choose_reposition(scene(),400,'angle-unavailable',movement_budget=budget,time_left=time))

if __name__=='__main__':unittest.main()
