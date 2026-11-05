import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
from training_evaluation import measured_prior,EvaluationTrial


def rows(episode,scale,powers=(90,170,260,340)):
    return [{'id':episode+':'+str(p),'episode':episode,'simple':True,'power':p,'speed':scale*p+20,'ax':0,'ay':390,'wind':0,'wind_angle':90,'heading':45,'duration_s':1} for p in powers]


class CoherentPriorTests(unittest.TestCase):
    def test_short_matches_cannot_be_pooled_into_a_fictitious_regime(self):
        mixed=rows('one',2,(100,200,300))+rows('two',3,(110,210,310))
        self.assertIsNone(measured_prior(mixed))
    def test_latest_complete_context_beats_mixture_and_incomplete_tail(self):
        values=rows('old',2)+rows('recent',3)+rows('short',4,(100,200))
        self.assertAlmostEqual(measured_prior(values)['scale'],3)
    def test_new_match_refreshes_hypothesis_without_moving_baseline_or_fit_membership_mid_match(self):
        with tempfile.TemporaryDirectory() as folder:
            learner=Mock();learner.episode='game-a';record={'samples':rows('old',2),'model':{'scale':1}}
            learner.records={'dragonbound:ARMOR:0':record}
            trial=EvaluationTrial(Path(folder)/'trial.json',learner);trial.reset_episode()
            self.assertAlmostEqual(trial.prior['scale'],2)
            baseline=trial.baseline.copy();initial_ids=trial.prior_training_ids.copy()
            record['samples']+=rows('game-a',3)
            trial.reset_episode()
            self.assertAlmostEqual(trial.prior['scale'],2)
            self.assertEqual(trial.prior_training_ids,initial_ids)
            learner.episode='game-b';trial.reset_episode()
            self.assertAlmostEqual(trial.prior['scale'],3)
            self.assertEqual(trial.baseline,baseline)
            self.assertEqual(trial.prior_training_ids,{r['id'] for r in record['samples']})


if __name__=='__main__':unittest.main()
