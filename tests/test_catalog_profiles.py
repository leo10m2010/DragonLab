import copy
import math
import tkinter as tk
import unittest
from types import SimpleNamespace

from core import PROFILES,Settings
from game_catalog import GAMES,game_by_id
from game_profiles import get_profile,registered_profiles
from mobile_catalog import MANUAL_MOBILES,catalog_records,mode_record,filter_records,recommendations
from calibration_ui import review_snapshot


def fixture(records=None):
    return SimpleNamespace(clone_id='dragonbound',s=Settings(),book=SimpleNamespace(records=records or {}),
        learned_launches=SimpleNamespace(profiles={},coverage={},live={}),shot_review=SimpleNamespace(records=[]))


def checked_record(game='dragonbound'):
    fit={'gravity':390.,'wind_scale':4.,'power_scale':2.4,'speed_offset':0.,'wind_mode':'smooth',
         'wind_observed':True,'power_range':[80,320],'wind_range':[0,0],'validation_count':3}
    powers=(80,160,240,320,120,200,280) if game=='dragonbound' else (20,40,60,80,25,50,75)
    if game=='gunbound-world':fit['power_range']=[20,80]
    samples=[{'sample_id':f'own:{i}','power':power,'vx':2.4*power,'vy':0.,'ax':0.,'ay':390.,
              'wind':0.,'wind_angle':90.,'source':'native-shot-start' if game=='dragonbound' else 'gunbound-own-shot-path'}
             for i,power in enumerate(powers)]
    checks=[{'id':s['sample_id'],'power':s['power'],'candidate':{'speed':0.,'acceleration':0.,'trajectory':None,'score':0.}}
            for s in samples[4:]]
    return {'samples':samples,'fit':fit,'accepted_validation':checks}


class CatalogMetadataTests(unittest.TestCase):
    def test_legacy_games_and_native_ids_stay_stable(self):
        self.assertEqual(list(GAMES),['DragonBound','GunBound World'])
        self.assertEqual(game_by_id('gunbound-world')['host'],'play.gunbound.world')
        rows=catalog_records(None,'dragonbound')
        self.assertEqual(len(rows),66);self.assertEqual(len(MANUAL_MOBILES),22)
        self.assertEqual({r['native_id'] for r in rows},set(range(23))-{7})
        self.assertEqual({r['mobile']:r['native_id'] for r in rows},{m:i for i,m in enumerate(PROFILES) if m!='RANDOM'})

    def test_metadata_cannot_enable_experimental_connector(self):
        profiles=registered_profiles()
        self.assertEqual([p['name'] for p in profiles if p['status']=='experimental'],['iGunsFire','ShotBound','WorldBound'])
        for profile in profiles[2:]:
            self.assertFalse(profile['hosts']);self.assertIsNone(profile['adapter_id']);self.assertIsNone(profile['url'])
            self.assertFalse(any(profile['capabilities'].values()));self.assertEqual(catalog_records(None,profile['id']),[])
        self.assertEqual(get_profile('worldbound')['observed_hosts'],['world-bound.net'])
        self.assertTrue(get_profile('dragonbound')['capabilities']['shortcut_shot'])
        self.assertTrue(get_profile('gunbound-world')['capabilities']['shortcut_shot'])
        self.assertTrue(get_profile('dragonbound')['capabilities']['autonomous_training'])
        self.assertFalse(get_profile('gunbound-world')['capabilities']['autonomous_training'])
        profiles[0]['hosts'].clear();self.assertEqual(get_profile('dragonbound')['hosts'],['dragonbound.net'])

    def test_game_parameters_and_three_shots_are_independent(self):
        records={'dragonbound:ARMOR:0':checked_record()}
        app=fixture(records);before=copy.deepcopy(records)
        first=mode_record(app,'dragonbound','ARMOR',0)
        second=mode_record(app,'dragonbound','ARMOR',1);ss=mode_record(app,'dragonbound','ARMOR',2)
        self.assertEqual(first['quality'],'validated');self.assertEqual(second['quality'],'base');self.assertEqual(ss['quality'],'base')
        self.assertEqual(second['sample_count'],0);self.assertEqual(ss['validation_count'],0)
        gb=mode_record(app,'gunbound-world','ARMOR',0)
        self.assertEqual(gb['power_range'],[25,100]);self.assertEqual(gb['native_power_range'],[1,100])
        self.assertGreater(gb['parameters']['power_scale'],9);self.assertFalse(gb['baseline'])
        self.assertEqual(mode_record(app,'gunbound-world','ICE',0)['parameters'],{})
        first['parameters']['gravity']=999;self.assertEqual(records,before)

    def test_no_baseline_measured_counter_or_candidate_becomes_a_recommendation(self):
        app=fixture({'dragonbound:ICE:0':{'fit':{'power_scale':2.4,'gravity':390,'validation_count':100}},
                     'dragonbound:FOX:0':{'candidate':{'fit':checked_record()['fit'],'validation':[{}, {}, {}]}}})
        self.assertEqual(recommendations(app,'dragonbound'),[])
        self.assertEqual(recommendations(app,'gunbound-world'),[])
        self.assertTrue(all(r['quality']!='validated' for r in catalog_records(app,'dragonbound')))

    def test_recommendations_require_live_evidence_and_exclude_drift_and_special(self):
        app=fixture({'dragonbound:ARMOR:0':checked_record(),'dragonbound:NAK:1':checked_record(),
                     'dragonbound:KALSIDDON:0':checked_record(),'dragonbound:ICE:0':{**checked_record(),'drift_pending':[{}]}})
        result=recommendations(app,'dragonbound')
        self.assertEqual([r['key'] for r in result],['dragonbound:ARMOR:0'])
        self.assertEqual(result[0]['validation_count'],3);self.assertFalse(result[0]['full_path_validated'])
        self.assertTrue(mode_record(app,'dragonbound','NAK',1)['special_pending'])
        app.book.records['dragonbound:ARMOR:0']['fit']['gravity']=900
        self.assertEqual(recommendations(app,'dragonbound'),[])

    def test_future_check_ids_and_native_sources_cannot_be_reused_or_invented(self):
        for damage in ('duplicate','no-sample','foreign-source','no-training','no-range'):
            record=checked_record()
            if damage=='duplicate':record['accepted_validation']=[record['accepted_validation'][0]]*3
            if damage=='no-sample':record['accepted_validation'][0]['id']='fake'
            if damage=='foreign-source':record['samples'][-1]['source']='synthetic'
            if damage=='no-training':record['samples']=record['samples'][4:]
            if damage=='no-range':record['fit'].pop('power_range')
            with self.subTest(damage=damage):self.assertEqual(recommendations(fixture({'dragonbound:ARMOR:0':record}),'dragonbound'),[])

    def test_gunbound_local_validation_uses_its_own_source_and_native_scale(self):
        app=fixture({'gunbound-world:ARMOR:0':checked_record('gunbound-world')})
        self.assertEqual([r['key'] for r in recommendations(app,'gunbound-world')],['gunbound-world:ARMOR:0'])
        self.assertEqual(recommendations(app,'dragonbound'),[])
        app.book.records['gunbound-world:ARMOR:0']=checked_record()
        self.assertEqual(recommendations(app,'gunbound-world'),[])

    def test_disjoint_learned_launch_certificate_is_eligible_until_live_drift(self):
        from manual_learning import certificate
        rows=[{'id':str(i),'source':'owned-native-launch','episode':'123','simple':True,'power':p,'speed':2.4*p,'ax':0.,'ay':390.,
               'wind':0.,'wind_angle':90.,'heading':45.,'duration_s':.6}
              for i,p in enumerate((80,160,240,320,120,260,200))]
        proof=certificate('dragonbound:ARMOR:0',rows,'123');self.assertIsNotNone(proof)
        app=fixture();app.learned_launches.profiles['dragonbound:ARMOR:0']=[proof]
        self.assertEqual([r['key'] for r in recommendations(app,'dragonbound')],['dragonbound:ARMOR:0'])
        app.learned_launches.live['dragonbound:ARMOR:0']=[{**rows[-1],'speed':1000.}]
        self.assertEqual(recommendations(app,'dragonbound'),[])

    def test_review_snapshot_freezes_scope_and_excludes_unattributed_other_game(self):
        app=fixture({'dragonbound:ARMOR:0':checked_record()})
        app.shot_review.records=[{'game_id':'dragonbound','mobile':'ARMOR','shot':0,'endpoint_error':4},
            {'game_id':'gunbound-world','mobile':'ARMOR','shot':0,'endpoint_error':1},
            {'mobile':'ARMOR','shot':0,'endpoint_error':2}, {'game_id':'dragonbound','mobile':'ARMOR','shot':1,'endpoint_error':3}]
        snapshot=review_snapshot(app,'dragonbound','ARMOR',0)
        self.assertEqual(len(snapshot['reviews']),1);self.assertEqual(snapshot['reviews'][0]['endpoint_error'],4)
        app.book.records['dragonbound:ARMOR:0']['fit']['gravity']=999
        self.assertEqual(snapshot['accepted']['gravity'],390)

    def test_search_filters_actual_mode_without_selecting_current_car(self):
        app=fixture();before=copy.deepcopy(vars(app.s))
        result=filter_records(catalog_records(app),'armor',game_id='gunbound-world',shot=2)
        self.assertEqual([r['key'] for r in result],['gunbound-world:ARMOR:2']);self.assertEqual(vars(app.s),before)


class CatalogUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:cls.root=tk.Tk();cls.root.withdraw()
        except tk.TclError as exc:raise unittest.SkipTest(str(exc))

    @classmethod
    def tearDownClass(cls):cls.root.destroy()

    def test_catalog_filters_real_table_and_never_changes_active_game_or_mode(self):
        from catalog_ui import open_catalog
        app=fixture();app.root=self.root;before=copy.deepcopy(vars(app.s))
        win=open_catalog(app);win.withdraw();win.update_idletasks()
        try:
            self.assertEqual(len(win.catalog_table.get_children()),66)
            win.catalog_game.set('GunBound World');win.catalog_search.set('Armor');win.catalog_shot.set('SS')
            self.root.update_idletasks()
            self.assertEqual(win.catalog_table.get_children(),('gunbound-world:ARMOR:2',))
            win.catalog_table.selection_set('gunbound-world:ARMOR:2');win.catalog_table.event_generate('<<TreeviewSelect>>')
            self.root.update()
            self.assertIn('ARMOR_SS',win.catalog_detail.get('1.0','end'))
            self.assertEqual(app.clone_id,'dragonbound');self.assertEqual(vars(app.s),before)
            win.catalog_game.set('WorldBound');self.assertEqual(len(win.catalog_table.get_children()),0)
            self.assertEqual(win.catalog_review_button.cget('state'),'disabled')
            self.assertIn('world-bound.net',win.catalog_detail.get('1.0','end'))
        finally:win.destroy()

    def test_calibration_freezes_metadata_in_memory_and_does_not_write_or_send(self):
        from calibration_ui import open_calibration
        app=fixture({'dragonbound:ARMOR:0':checked_record()});app.root=self.root
        before=copy.deepcopy(app.book.records)
        win=open_calibration(app,'dragonbound','ARMOR',0);win.withdraw();win.update_idletasks()
        try:
            self.assertEqual(len(win.sample_table.get_children()),7)
            win.freeze_comparison();self.assertEqual(win.frozen_snapshot['scope']['game_id'],'dragonbound')
            app.book.records['dragonbound:ARMOR:0']['fit']['gravity']=999;win.refresh_review()
            self.assertEqual(win.current_snapshot['accepted']['gravity'],390)
            win.review_shot.set('2');self.assertIsNone(win.frozen_snapshot);self.assertEqual(len(win.sample_table.get_children()),0)
            self.assertFalse(hasattr(app,'training_session'));self.assertFalse(hasattr(app,'pending_fire'))
            app.book.records['dragonbound:ARMOR:0']['fit']['gravity']=390
            self.assertEqual(app.book.records,before)
        finally:win.destroy()

    def test_validated_filter_uses_recommendation_evidence(self):
        from catalog_ui import open_catalog
        app=fixture({'dragonbound:ARMOR:0':checked_record(),'dragonbound:NAK:1':checked_record()});app.root=self.root
        win=open_catalog(app);win.withdraw();win.update_idletasks()
        try:
            win.catalog_validated.set(True)
            self.assertEqual(win.catalog_table.get_children(),tuple(r['key'] for r in recommendations(app,'dragonbound')))
            self.assertIn('1 validadas',win.catalog_count.cget('text'))
            win.catalog_game.set('GunBound World');self.assertEqual(win.catalog_table.get_children(),())
            self.assertIn('0 validadas',win.catalog_count.cget('text'))
        finally:win.destroy()


if __name__=='__main__':unittest.main()
