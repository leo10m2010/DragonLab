import copy,json,tempfile,unittest
from pathlib import Path
from adaptive_training import AdaptiveTrial
from autonomous_learning import AutonomousLearner
from native_paths import position


class ContinuationOwnershipTests(unittest.TestCase):
    def fixture(self,folder,mobile='ICE',mode=1):
        learner=AutonomousLearner(Path(folder)/'learner.json')
        hero={'id':0,'x':0,'y':0,'mobile':1 if mobile=='ICE' else 11}
        parent={'id':1,'native':True,'start':[0,0,45,200,0,100],'duration':500,'elapsed':0,'shotType':mode,'metadata':{'player':0,'power':100}}
        state={'status':'live','heroId':0,'activePlayer':0,'players':[hero,{'id':1,'x':500,'y':0}], 'shots':[parent],'selectedShot':mode,'currentPower':100,'wind':0,'windAngle':90}
        release={'hero':0,'x':0,'y':0,'power':100,'shot':mode,'wind':0,'windAngle':90,'baseline':[],'learner':{'target':[500,0],'elevation':45}}
        learner.observe({'mobile':mobile,'shot':mode},release,state)
        end=position(parent,.5)
        child={'id':2,'native':True,'start':[end[0],end[1],90,100,0,-500],'duration':400,'elapsed':500,'delay':500}
        return learner,state,child,learner.records[f'dragonbound:{mobile}:{mode}']

    def test_auxiliary_zero_motion_and_foreign_owner_cannot_poison_normal_bullet(self):
        for change in ({'auxiliary':True},{'start':[70,0,270,0,0,0]},{'metadata':{'player':1},'shotType':1},{'metadata':{'player':0},'shotType':2}):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as folder:
                learner,state,child,record=self.fixture(folder)
                state['shots']=[{**child,**change}];before=copy.deepcopy(record['cases'][0]['ends'])
                learner.track(state)
                self.assertFalse(record['multi_projectile']);self.assertFalse(record.get('observed_phases'))
                self.assertEqual(record['cases'][0]['ends'],before)

    def test_moving_child_without_owner_is_kept_apart_without_banning_ice(self):
        with tempfile.TemporaryDirectory() as folder:
            learner,state,child,record=self.fixture(folder);state['shots']=[child]
            before=copy.deepcopy(record['cases'][0]['ends']);learner.track(state)
            self.assertEqual(len(record['quarantined_phases']),1);self.assertFalse(record['quarantined_phases'][0]['verified'])
            self.assertFalse(record['multi_projectile']);self.assertEqual(record['cases'][0]['ends'],before)
            self.assertEqual(len(record['samples']),1)

    def test_owner_and_modality_proof_accepts_a_genuine_followup(self):
        with tempfile.TemporaryDirectory() as folder:
            learner,state,child,record=self.fixture(folder,mobile='NAK')
            state['shots']=[{**child,'shotType':1,'metadata':{'player':0,'mobile':11}}];learner.track(state)
            self.assertTrue(record['observed_phases'][0]['verified']);self.assertTrue(record['multi_projectile'])
            self.assertTrue(record['cases'][0]['continuation_verified']);self.assertEqual(len(record['samples']),1)

    def test_nak_unattributed_followup_stays_pending_and_can_later_receive_proof(self):
        with tempfile.TemporaryDirectory() as folder:
            learner,state,child,record=self.fixture(folder,mobile='NAK');state['shots']=[child]
            before=copy.deepcopy(record['cases'][0]['ends']);learner.track(state)
            self.assertTrue(record['special_continuation_pending']);self.assertTrue(record['multi_projectile'])
            self.assertFalse(record['observed_phases'][0]['verified']);self.assertEqual(record['cases'][0]['ends'],before)
            child.update(shotType=None,metadata={'player':0,'selectedShot':1})
            learner.track(state)
            self.assertTrue(record['observed_phases'][0]['verified']);self.assertFalse(record['special_continuation_pending'])
            self.assertTrue(record['quarantined_phases'][0]['resolved_with_owner_proof'])

    def test_pending_parents_cannot_cross_match_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            learner,state,child,record=self.fixture(folder);state['shots']=[{**child,'shotType':1,'metadata':{'player':0}}]
            learner.episode='another-match';learner.track(state)
            self.assertFalse(learner.pending);self.assertFalse(record.get('observed_phases'))

    def test_nonfinite_child_delay_is_rejected_without_polluting_storage(self):
        with tempfile.TemporaryDirectory() as folder:
            learner,state,child,record=self.fixture(folder)
            state['shots']=[{**child,'delay':float('nan'),'metadata':{'player':0},'shotType':1}]
            learner.track(state)
            self.assertFalse(record.get('observed_phases'));self.assertFalse(record.get('quarantined_phases'))

    def test_unrelated_existing_projectile_cannot_be_linked_as_followup(self):
        with tempfile.TemporaryDirectory() as folder:
            learner,state,child,record=self.fixture(folder)
            from shot_attribution import identity
            next(iter(learner.pending.values()))['baseline']=[identity(child)]
            state['shots']=[{**child,'shotType':1,'metadata':{'player':0}}];learner.track(state)
            self.assertFalse(record.get('observed_phases'))


class HistoricalContinuationTests(unittest.TestCase):
    def saved(self,folder,mobile='ICE',mode=1,extra=None):
        path=Path(folder)/'learner.json';key=f'dragonbound:{mobile}:{mode}'
        phase={'id':'visual','parent':'original','start':[1076,70,270,0,0,0],'delay':2400,'end':[1076,70]}
        record={'multi_projectile':True,'model':{'scale':2},'samples':[],'observed_phases':[phase],'cases':[{'id':'original','has_continuation':True,'ends':[[1076,70]]}]}
        record.update(extra or {});path.write_text(json.dumps({'schema':1,'records':{key:record}}))
        return path,key,phase

    def test_legacy_weather_effect_no_longer_disables_ice_normal_or_ss_profiles(self):
        for mode in (0,1,2):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as folder:
                path,key,phase=self.saved(folder,mode=mode);learner=AutonomousLearner(path);record=learner.records[key]
                self.assertFalse(record['multi_projectile']);self.assertFalse(record['observed_phases'])
                self.assertEqual(record['quarantined_phases'][0]['id'],phase['id']);self.assertTrue(record['cases'][0]['continuation_unverified'])
                adaptive=AdaptiveTrial(Path(folder)/'report.json',learner)
                self.assertTrue(adaptive.supported('ICE',mode))
                self.assertEqual(adaptive.probe('ICE',{'heroId':0,'players':[],'wind':0,'windAngle':0},[mode])['shot'],mode)
                reloaded=AutonomousLearner(path);self.assertEqual(len(reloaded.records[key]['quarantined_phases']),1)

    def test_raw_patterns_and_verified_phases_still_block_fixed_single_bullet_models(self):
        for extra in ({'patterns':[{'starts':[[0,0,45,200,0,400],[0,0,45,250,0,400]]}]},{'intrinsic_pattern':True},{'observed_phases':[{'id':'owned','verified':True}]}):
            with tempfile.TemporaryDirectory() as folder:
                path,key,_=self.saved(folder,extra=extra);learner=AutonomousLearner(path)
                self.assertTrue(learner.records[key]['multi_projectile'])

    def test_known_special_continuation_is_preserved_as_pending(self):
        with tempfile.TemporaryDirectory() as folder:
            path,key,_=self.saved(folder,mobile='NAK');learner=AutonomousLearner(path);record=learner.records[key]
            self.assertTrue(record['multi_projectile']);self.assertTrue(record['special_continuation_pending'])
            self.assertFalse(record['observed_phases'][0]['verified']);self.assertEqual(len(record['quarantined_phases']),1)

    def test_unexplained_legacy_multi_flag_does_not_permanently_ban_ordinary_ice(self):
        for mode in (0,1,2):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as folder:
                path,key,_=self.saved(folder,mode=mode,extra={'observed_phases':[]})
                learner=AutonomousLearner(path);record=learner.records[key]
                self.assertTrue(record['legacy_unverified_multi_projectile']);self.assertFalse(record['multi_projectile'])
                self.assertTrue(AdaptiveTrial(Path(folder)/'report.json',learner).supported('ICE',mode))

    def test_unexplained_legacy_special_flag_stays_pending_without_discarding_it(self):
        with tempfile.TemporaryDirectory() as folder:
            path,key,_=self.saved(folder,mobile='NAK',extra={'observed_phases':[]})
            learner=AutonomousLearner(path);record=learner.records[key]
            self.assertTrue(record['legacy_unverified_multi_projectile']);self.assertTrue(record['special_continuation_pending'])
            self.assertTrue(record['multi_projectile'])
