import os,unittest,tkinter as tk
from trajectories import TrajectoryOverlay
@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'requires desktop')
class HiddenEnemyOverlayTests(unittest.TestCase):
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
