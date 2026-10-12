import unittest
from weather_validation import crossing_evidence
class WeatherEvidenceTests(unittest.TestCase):
    def case(self,kind,xs):return {'zones':[{'kind':kind,'x':100,'size':100}],'path':[{'x':x,'y':-100,'t':i*.05} for i,x in enumerate(xs)]}
    def test_shot_away_from_mirror_is_not_a_validation(self):self.assertEqual(crossing_evidence(self.case('mirror',[0,-20,-40]))[0]['status'],'no-crossing')
    def test_short_tornado_entry_does_not_certify_all_passes(self):self.assertEqual(crossing_evidence(self.case('tornado',[60,80,100,120]))[0]['status'],'partial-crossing')
    def test_measured_mirror_reflection(self):self.assertEqual(crossing_evidence(self.case('mirror',[40,60,75,60,40]))[0]['status'],'complete-crossing')
    def test_full_tornado_requires_two_reversals_and_exit(self):self.assertEqual(crossing_evidence(self.case('tornado',[60,80,100,125,100,75,100,125,150]))[0]['status'],'complete-crossing')
    def test_isolated_nonuniform_impact_is_not_a_reflection(self):
        c=self.case('mirror',[40,60,75,60,40]);c['path'][2]['t']=.051
        self.assertEqual(crossing_evidence(c)[0]['status'],'partial-crossing')
