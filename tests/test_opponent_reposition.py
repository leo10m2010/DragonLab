import copy,unittest
from unittest.mock import Mock
from training_movement import choose_reposition


def scene():
    return {'heroId':0,'players':[{'id':0,'x':100,'y':100,'body':0},{'id':1,'x':300,'y':100}], 'terrain':{'heights':[100]*500}}

def risk(estimate,low,high,**changes):return {'estimate':estimate,'low':low,'high':high,'samples':12,'episodes':3,**changes}


class OpponentRepositionTests(unittest.TestCase):
    def test_confident_lower_exposure_only_selects_between_two_safe_clear_paths(self):
        state=scene();original=copy.deepcopy(state);seen=[]
        def evaluate(hypothetical,step):
            seen.append((step['direction'],hypothetical['players'][0]['x']));return True
        learned=lambda point:risk(.1,.02,.25) if point[0]<100 else risk(.9,.7,.98)
        result=choose_reposition(state,300,'angle-unavailable',evaluate=evaluate,position_risk=learned)
        self.assertEqual(result['direction'],'left');self.assertEqual(result['selection'],'lower-observed-exposure')
        self.assertEqual(set(seen),{('right',114),('left',86)});self.assertEqual(state,original)
        self.assertTrue(result['opponent_evidence']['changed_preference']);self.assertEqual(result['opponent_evidence']['chosen']['samples'],12)
    def test_low_exposure_cannot_override_a_blocked_path(self):
        learned=Mock(side_effect=AssertionError('Must not rank unless both paths clear'))
        result=choose_reposition(scene(),300,'angle-unavailable',evaluate=lambda state,step:step['direction']=='right',position_risk=learned)
        self.assertEqual(result['direction'],'right');self.assertEqual(result['selection'],'predicted-clear-path');learned.assert_not_called()
    def test_low_exposure_never_selects_a_cliff(self):
        state=scene();state['terrain']['heights'][:100]=[None]*100;learned=Mock()
        result=choose_reposition(state,300,'angle-unavailable',evaluate=lambda state,step:True,position_risk=learned)
        self.assertEqual(result['direction'],'right');learned.assert_not_called()
    def test_no_terrain_or_no_predicted_clear_path_never_uses_learned_risk(self):
        learned=Mock(side_effect=AssertionError('Risk is not a safety substitute'))
        state=scene();state.pop('terrain')
        self.assertIsNone(choose_reposition(state,300,'angle-unavailable',evaluate=lambda *_:True,position_risk=learned))
        fallback=choose_reposition(scene(),300,'terrain-blocked',evaluate=lambda *_:False,position_risk=learned)
        self.assertEqual(fallback['direction'],'left');self.assertEqual(fallback['selection'],'retreat-from-obstruction');learned.assert_not_called()
    def test_without_path_evaluator_learned_risk_cannot_enable_a_new_choice(self):
        learned=Mock(side_effect=AssertionError('No clear-path proof'))
        result=choose_reposition(scene(),300,'angle-unavailable',position_risk=learned)
        self.assertEqual(result['direction'],'right');self.assertNotIn('opponent_evidence',result);learned.assert_not_called()
    def test_sparse_invalid_or_overlapping_evidence_preserves_default_preference(self):
        invalid=[None,{},risk(.1,.02,.25,samples=7),risk(.1,.02,.25,episodes=1),risk(.1,.02,.25,samples=True),risk(float('nan'),0,.25),risk(.2,.3,.1),risk(.2,-.1,.5),risk(.8,.5,1.1),risk(.1,.02,.25,episodes=13)]
        for row in invalid:
            with self.subTest(row=row):
                result=choose_reposition(scene(),300,'angle-unavailable',evaluate=lambda *_:True,position_risk=lambda point:row if point[0]<100 else risk(.9,.7,.98))
                self.assertEqual(result['direction'],'right');self.assertEqual(result['selection'],'predicted-clear-path')
        result=choose_reposition(scene(),300,'angle-unavailable',evaluate=lambda *_:True,position_risk=lambda point:risk(.3,.1,.6) if point[0]<100 else risk(.7,.5,.9))
        self.assertEqual(result['direction'],'right');self.assertNotIn('opponent_evidence',result)
    def test_callback_failure_cannot_block_a_valid_existing_reposition(self):
        learned=Mock(side_effect=RuntimeError('Passive data unavailable'))
        result=choose_reposition(scene(),300,'angle-unavailable',evaluate=lambda *_:True,position_risk=learned)
        self.assertEqual(result['selection'],'predicted-clear-path');self.assertEqual(result['direction'],'right')
    def test_visited_and_avoided_positions_remain_excluded(self):
        for changes in ({'visited':[[86,100]]},{'avoid':'left'}):
            with self.subTest(changes=changes):
                learned=Mock(side_effect=AssertionError('Excluded direction must not compete'))
                result=choose_reposition(scene(),300,'angle-unavailable',evaluate=lambda *_:True,position_risk=learned,**changes)
                self.assertEqual(result['direction'],'right');learned.assert_not_called()
    def test_confirmed_default_direction_is_distinguished_from_changed_preference(self):
        result=choose_reposition(scene(),300,'angle-unavailable',evaluate=lambda *_:True,position_risk=lambda point:risk(.1,.02,.25) if point[0]>100 else risk(.9,.7,.98))
        self.assertEqual(result['direction'],'right');self.assertEqual(result['selection'],'lower-observed-exposure');self.assertFalse(result['opponent_evidence']['changed_preference'])

if __name__=='__main__':unittest.main()
