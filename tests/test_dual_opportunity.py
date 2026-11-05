import unittest
from weapon_policy import dual_decision


class DualOpportunityTests(unittest.TestCase):
    def decide(self,rows=None,remaining=400,enabled=True,shot=1,phase='evaluation',**changes):
        checks={'under_pressure':True,'trajectory_verified':True,'verified_check_count':3};checks.update(changes)
        return dual_decision(rows or [],remaining,enabled,shot,phase,**checks)
    def rows(self,damage=100):return [{'path_error_px':5,'health_window_known':True,'enemy_health_drop':damage} for _ in range(5)]
    def test_critical_life_can_use_verified_flight_without_claiming_a_finisher(self):
        decision,reason=self.decide()
        self.assertTrue(decision);self.assertIn('vida propia crítica',reason);self.assertIn('no garantiza remate',reason)
    def test_pressure_cannot_authorize_calibration_recovery_ss_or_disabled_item(self):
        for changes in ({'phase':'calibration'},{'phase':'recovery'},{'shot':2},{'shot':True},{'enabled':False}):
            with self.subTest(changes=changes):self.assertFalse(self.decide(**changes)[0])
    def test_pressure_requires_explicit_proof_and_three_future_checks(self):
        for changes in ({'under_pressure':False},{'under_pressure':'yes'},{'trajectory_verified':False},{'trajectory_verified':1},{'verified_check_count':2},{'verified_check_count':True},{'verified_check_count':3.0}):
            with self.subTest(changes=changes):self.assertFalse(self.decide(**changes)[0])
    def test_unknown_nonfinite_or_dead_enemy_health_never_uses_dual(self):
        for remaining in (None,float('nan'),float('inf'),-1,0,True):
            with self.subTest(remaining=remaining):
                self.assertFalse(self.decide(remaining=remaining)[0]);self.assertFalse(dual_decision(self.rows(),remaining,True,1,'evaluation')[0])
    def test_known_normal_shot_sufficient_conserves_dual_even_under_pressure(self):
        decision,reason=self.decide(rows=self.rows(),remaining=80)
        self.assertFalse(decision);self.assertIn('normal suficiente',reason)
    def test_without_pressure_normal_empirical_finishing_rules_are_preserved(self):
        self.assertTrue(dual_decision(self.rows(),150,True,1,'evaluation')[0])
        self.assertFalse(dual_decision(self.rows(),900,True,1,'evaluation')[0]);self.assertFalse(dual_decision(self.rows()[:2],150,True,1,'evaluation')[0])
        self.assertFalse(self.decide(under_pressure=False)[0])

if __name__=='__main__':unittest.main()
