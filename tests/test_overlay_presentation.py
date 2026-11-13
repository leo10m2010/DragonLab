import copy,json,time,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from app import App
from core import Settings
from native_overlay import NativeScene,NativeGuide,NativeTrajectory,frame_batch
from strength_guide import compact_guide_label

class StablePresentationTests(unittest.TestCase):
    def scene(self):
        scene=NativeScene.__new__(NativeScene);scene.dll=Mock();scene.dll.dl_overlay_update_json.return_value=0;scene.dll.dl_overlay_status.return_value=3
        scene.frame={'box':[0,0,800,600],'viewport':[800,600],'planned':[],'observed':{},'players':[],'annotations':[],'style':{},'guide':{'visible':False},'visible':False}
        scene.trajectory_visible=False;scene.guide_visible=False;scene.last=None;scene.closed=False;scene.owners=set();return scene
    def test_one_complete_frame_contains_latest_path_and_power(self):
        scene=self.scene();guide=NativeGuide(None,(20,550),(420,550),scene);overlay=NativeTrajectory(None,scene)
        with patch('native_overlay._scene',scene):
            with frame_batch():
                guide.draw({'reachable':True,'power':100},400)
                overlay.update([0,0,800,600],[800,600],lambda x,y:(x,y),[[(1,2),(3,4)]],{},True)
                guide.draw({'reachable':True,'power':321},400)
                scene.dll.dl_overlay_update_json.assert_not_called()
            self.assertEqual(scene.dll.dl_overlay_update_json.call_count,1)
            payload=json.loads(scene.dll.dl_overlay_update_json.call_args.args[0]);self.assertEqual(payload['guide']['power'],321);self.assertEqual(payload['planned'],[[[1,2],[3,4]]])
        guide.close();overlay.close()
    def test_failed_ui_tick_does_not_publish_half_updated_scene(self):
        scene=self.scene()
        with patch('native_overlay._scene',scene):
            with self.assertRaises(ValueError):
                with frame_batch():scene.submit();raise ValueError('invalid current frame')
        scene.dll.dl_overlay_update_json.assert_not_called();self.assertFalse(scene.pending)
    def test_suspend_and_resume_keeps_native_owner_and_message_thread(self):
        scene=self.scene();guide=NativeGuide(None,(20,550),(420,550),scene)
        guide.draw({'reachable':True,'power':321},400);guide.hide();count=scene.dll.dl_overlay_update_json.call_count
        guide.draw({'reachable':True,'power':100},400);self.assertEqual(scene.dll.dl_overlay_update_json.call_count,count)
        scene.dll.dl_overlay_close.assert_not_called();self.assertEqual(len(scene.owners),1)
        guide.show();guide.draw({'reachable':True,'power':321},400);self.assertTrue(scene.frame['guide']['visible']);guide.close()
    def test_force_label_fits_small_game_bar_without_vehicle_and_long_diagnostics(self):
        result={'reachable':True,'power':321,'guide_label':'Trico · Tiro 2 · APROXIMADO','guide_notice':None}
        self.assertEqual(compact_guide_label(result,400),'321 · 80.2%')
        self.assertLessEqual(len(compact_guide_label({**result,'guide_notice':'x'*500},400)),26)
        self.assertEqual(compact_guide_label({'blocked':True,'guide_power':321},400),'Bloqueado · 321 · 80.2%')
        self.assertEqual(compact_guide_label({**result,'guide_state':'approximate'},400),'≈321 · 80.2%')
    def app(self):
        app=SimpleNamespace(root=None,auto_enabled=True,auto_guide_enabled=True,game_window=None,capture_dpr=1,screen_box=None,auto_points=None,guide_points=None,power_guide=None,image=None,consume_fire_gesture=lambda event:False)
        return app
    def sample(self,points=True):
        return {'status':'live','heroId':0,'players':[{'id':0,'x':10,'y':20,'team':0},{'id':1,'x':100,'y':20,'team':1}], '_auto':{'geometry':{'active':True,'focused':True,'windowHandle':5,'dpr':1},'screen_box':[0,0,800,600],'guide_points':[[20,550],[420,550]] if points else None}}
    def test_transient_bar_loss_suspends_without_recreating_or_authorizing_q(self):
        app=self.app();guide=Mock()
        with patch('app.create_guide',return_value=guide) as factory:
            App.apply_auto(app,self.sample());self.assertTrue(app.guide_geometry_fresh)
            App.apply_auto(app,self.sample(False));self.assertFalse(app.guide_geometry_fresh);guide.hide.assert_called_once();guide.close.assert_not_called()
            App.apply_auto(app,self.sample());self.assertTrue(app.guide_geometry_fresh);factory.assert_called_once();self.assertIs(app.power_guide,guide)
    def test_q_is_rejected_while_bar_geometry_is_unknown(self):
        app=SimpleNamespace(training_session=None,fire_busy=False,auto_shot_enabled=True,clone_id='dragonbound',auto_enabled=True,last_live=time.monotonic(),guide_geometry_fresh=False,fire_notice=Mock())
        App.trigger_auto_fire(app);self.assertIn('barra',app.fire_notice.call_args.args[0]);self.assertFalse(app.fire_busy)
    def test_visual_grace_uses_change_time_and_never_authorizes_pending_q(self):
        app=SimpleNamespace(autonomous_training=lambda:False,live_input_issue='',result_context=('same',),visual_context=lambda:('same',),dirty=False,computing=False,last_computed=time.monotonic()-10,compute_generation=1,calculations=Mock(),result={'reachable':True,'power':321})
        App.mark(app);self.assertFalse(App.visual_updating(app));self.assertEqual(App.display_result(app)['power'],321)
        app.visual_dirty_since-=.13;self.assertTrue(App.visual_updating(app));app.visual_dirty_since-=.1;self.assertEqual(App.display_result(app),{})

if __name__=='__main__':unittest.main()
