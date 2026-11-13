import os,unittest,tkinter as tk
from unittest.mock import patch
from trajectories import TrajectoryOverlay,actor_label_layout
@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'requires desktop')
class HiddenEnemyOverlayTests(unittest.TestCase):
    def setUp(self):
        if os.name!='nt':
            # Xvfb exercises the drawing assertions without a Windows-only
            # color-key attribute. Windows runs retain the real attribute.
            original=tk.Toplevel.wm_attributes
            def attributes(window,*args):
                if args and args[0]=='-transparentcolor':return None
                return original(window,*args)
            stub=patch.object(tk.Toplevel,'wm_attributes',attributes)
            stub.start();self.addCleanup(stub.stop)
    def test_enemy_is_marked_without_a_reachable_path_and_below_view(self):
        root=tk.Tk();root.withdraw();overlay=TrajectoryOverlay(root)
        try:
            players=[{'id':1,'x':100,'y':100,'team':1},{'id':2,'x':500,'y':900,'team':2}]
            overlay.update((0,0,800,600),(800,600),lambda x,y:(x,y),[],{},True,players=players,target_id=2,hero_id=1)
            self.assertIn('player:2',overlay.labels)
            self.assertIn('fuera de vista',overlay.canvas.itemcget(overlay.labels['player:2'],'text'))
            players[1]['y']=300
            overlay.update((0,0,800,600),(800,600),lambda x,y:(x,y),[],{},True,players=players,target_id=2,hero_id=1)
            self.assertIn('ENEMIGO 1',overlay.canvas.itemcget(overlay.labels['player:2'],'text'))
            self.assertIn('player:2',overlay.label_backgrounds)
        finally:overlay.close();root.destroy()

    def test_weather_columns_and_current_name_are_visible(self):
        from gunbound_weather import normalize_weather
        root=tk.Tk();root.withdraw();overlay=TrajectoryOverlay(root)
        try:
            weather=normalize_weather('mirror',[{'kind':'mirror','x':350,'size':92},{'kind':'tornado','x':550,'size':140}])
            overlay.update((0,0,800,600),(800,600),lambda x,y:(x,y),[],{},True,weather=weather,style={'weather_name':'mirror'})
            self.assertEqual(overlay.canvas.itemcget(overlay.labels['current-weather'],'text'),'Clima: Mirror')
            self.assertIn('climate:0',overlay.marks);self.assertIn('climate:1',overlay.marks)
        finally:overlay.close();root.destroy()

    def test_crowded_edge_labels_keep_all_roles_and_actor_membership(self):
        root=tk.Tk();root.withdraw();overlay=TrajectoryOverlay(root)
        try:
            players=[{'id':0,'x':100,'y':200,'team':0},{'id':1,'x':100,'y':900,'team':0},
                     *({'id':i,'x':1200,'y':900,'team':1} for i in range(2,18))]
            overlay.update((0,0,800,600),(800,600),lambda x,y:(x,y),[],{},True,players=players,target_id=17,hero_id=0)
            members={ident for values in overlay.actor_label_groups.values() for ident in values}
            self.assertEqual(members,set(range(18)))
            self.assertTrue(all('player:'+str(i) in overlay.marks for i in range(18)))
            texts=[overlay.canvas.itemcget(overlay.labels[key],'text') for key in overlay.actor_label_groups]
            self.assertTrue(any(text.startswith('▶ E16') for text in texts))
            self.assertIn('TÚ',texts);self.assertIn('A2',texts)
            boxes=[overlay.canvas.bbox(overlay.label_backgrounds[key]) for key in overlay.actor_label_groups]
            for index,(left,top,right,bottom) in enumerate(boxes):
                for l,t,r,b in boxes[index+1:]:self.assertTrue(right<=l or r<=left or bottom<=t or b<=top)
        finally:overlay.close();root.destroy()


class ActorLayoutTests(unittest.TestCase):
    def test_overflow_is_grouped_without_actor_cap_or_mutating_input(self):
        import copy
        actors=[{'id':i,'key':'player:'+str(i),'x':780,'y':490,'label':'ENEMIGO '+str(i),'short':('▶ ' if i==299 else '')+'E'+str(i),
                 'color':'#FFFFFF','selected':i==299} for i in range(300)]
        before=copy.deepcopy(actors);labels=actor_label_layout(actors,800,516,12)
        self.assertEqual({i for item in labels for i in item['members']},set(range(300)))
        self.assertTrue(any(item['text'].startswith('▶ E299') for item in labels));self.assertEqual(actors,before)
