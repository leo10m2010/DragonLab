import copy,unittest
from mobile_tactics import mobile_intent,terrain_vulnerability


def state(terrain):return {'heroId':0,'players':[{'id':0,'team':0,'x':20,'y':100},{'id':1,'team':1,'x':100,'y':100}],'terrain':terrain}
def slab(bottom=110,right=200):
    return {'width':200,'height':200,'rows':[([0,right] if 100<=y<bottom else []) for y in range(200)],'rowsSorted':True}


class MobileTacticsTests(unittest.TestCase):
    def test_reference_roles_and_delays_never_authorize_a_shot(self):
        for mobile,shot,role,delay in (('ARMOR',1,'two-warheads',430),('NAK',1,'underground-return',400),('NAK',2,'terrain-ignoring',800),('ADUKA',0,'direct-electric',250),('ADUKA',1,'thor-tracers',400)):
            with self.subTest(mobile=mobile,shot=shot):
                note=mobile_intent(mobile,shot)
                self.assertEqual(note['role'],role);self.assertEqual(note['reference_delay'],delay);self.assertFalse(note['authorizes_action'])
                self.assertNotIn('power',note);self.assertNotIn('damage',note);self.assertNotIn('gravity',note)
    def test_special_mechanisms_remain_pending_without_measurements(self):
        for mobile,shot in (('NAK',1),('ADUKA',1),('KALSIDDON',0),('KALSIDDON',1),('KALSIDDON',2),('TRICO',1)):
            self.assertTrue(mobile_intent(mobile,shot)['mechanism_pending'])
        self.assertIsNone(mobile_intent('KALSIDDON',1)['reference_delay'])
    def test_aduka_information_distinguishes_quick_shot_and_thor_charge(self):
        first=mobile_intent('Aduka',0);second=mobile_intent('Aduka',1)
        self.assertTrue(first['quick_reference']);self.assertEqual(first['intent'],'quick-attack')
        self.assertFalse(second['quick_reference']);self.assertEqual(second['intent'],'charge-thor')
    def test_thin_volume_is_a_bunge_candidate_not_a_claim_of_falling(self):
        scene=state(slab());original=copy.deepcopy(scene);target=scene['players'][1]
        metric=terrain_vulnerability(scene,target)
        self.assertTrue(metric['support_known']);self.assertEqual(metric['thickness_px'],10);self.assertEqual(metric['reason'],'thin-support')
        note=mobile_intent('ARMOR',0,scene,{'target_id':1})
        self.assertEqual(note['candidate_goal'],'bunge');self.assertFalse(note['authorizes_action']);self.assertEqual(scene,original)
        self.assertNotIn('fall_probability',metric)
    def test_thick_volume_is_not_called_thin_at_scan_cap(self):
        scene=state(slab(bottom=195));metric=terrain_vulnerability(scene,scene['players'][1])
        self.assertIsNone(metric['thickness_px']);self.assertFalse(metric['weak_support']);self.assertEqual(metric['reason'],'support-present')
    def test_surface_only_has_unknown_thickness_but_can_report_ledge(self):
        scene=state({'heights':[100]*200});metric=terrain_vulnerability(scene,scene['players'][1])
        self.assertTrue(metric['support_known']);self.assertIsNone(metric['thickness_px']);self.assertFalse(metric['weak_support'])
        scene['terrain']['heights'][108:]=[None]*92;metric=terrain_vulnerability(scene,scene['players'][1])
        self.assertEqual(metric['near_ledge_px'],8);self.assertEqual(metric['reason'],'near-ledge');self.assertTrue(metric['weak_support'])
    def test_airborne_missing_or_malformed_ground_is_unknown(self):
        for terrain in ({},{'heights':[None]*200},{'width':200,'height':200,'rows':[[0,200]]*101,'rowsSorted':True}):
            scene=state(terrain);metric=terrain_vulnerability(scene,scene['players'][1]);self.assertFalse(metric['support_known']);self.assertFalse(metric['weak_support'])
    def test_terrain_world_origin_and_camera_do_not_change_measurement(self):
        original=state(slab());expected=terrain_vulnerability(original,original['players'][1])
        moved=state({**slab(),'originX':1000,'originY':-200});moved['players'][1].update(x=1100,y=-100);moved['camera']={'x':10000,'y':8000,'scale':3}
        actual=terrain_vulnerability(moved,moved['players'][1]);self.assertEqual(actual['thickness_px'],expected['thickness_px']);self.assertEqual(actual['weak_support'],expected['weak_support'])
    def test_explicit_opening_action_is_labeled_without_changing_aim(self):
        scene=state(slab());plan={'action':'abrir paso','target':[100,100],'power':123,'angle':50};original=copy.deepcopy(plan)
        note=mobile_intent('NAK',0,scene,plan);self.assertEqual(note['intent'],'clear-line');self.assertEqual(plan,original)
    def test_target_resolution_excludes_ally_and_unknown_targets(self):
        scene=state(slab());scene['players'].append({'id':2,'team':0,'x':30,'y':100})
        self.assertEqual(mobile_intent('ARMOR',0,scene,{'target':[30,100]})['candidate_goal'],'bunge')
        self.assertFalse(mobile_intent('ARMOR',0,scene,{'target_id':2})['terrain']['support_known'])
    def test_unknown_mobile_or_invalid_mode_never_invents_a_profile(self):
        for mobile,shot in (('unknown',0),('ARMOR',3),('ARMOR',True),('NAK',1.5)):
            note=mobile_intent(mobile,shot);self.assertEqual(note['role'],'unknown');self.assertIsNone(note['reference_delay']);self.assertFalse(note['authorizes_action'])

if __name__=='__main__':unittest.main()
