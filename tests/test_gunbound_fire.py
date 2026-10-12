import unittest,threading
from gunbound_fire import execute_gunbound
class Backend:
    def __init__(self):self.held=False;self.position=(100,100);self.actions=[];self.window=1
    def input_busy(self):return False
    def foreground(self):return (self.window,2,'GunBound World')
    def window_rect(self,h):return (0,0,800,600)
    def escaped(self):return False
    def cursor(self):return self.position
    def point_in_window(self,x,y,h):return True
    def move(self,x,y):self.position=(x,y);self.actions.append(('move',x,y))
    def mouse(self,down):self.held=down;self.actions.append(('mouse',down))
    def key(self,down):self.held=down;self.actions.append(('space',down))
class Reader:
    def __init__(self,backend,mode='drag'):
        self.backend=backend;self.mode=mode;self.power=0;self.turn='hero';self.armed=False
    def drag_start(self,window):self.drag_box=(0,0,800,600);return (100,100)
    def read(self):
        if self.backend.held:self.power=abs(self.backend.position[0]-100)/2.5 if self.mode=='drag' else self.power+10
        return dict(power=self.power,hero='hero',turn=self.turn,shot=0,wind=0,windAngle=0,focused=True,chat=False,mode=self.mode,moving=False,over=False,blocked=False,armedItem=self.armed,busy=self.backend.held,sensitivity=100,canvasWidth=800,stageWidth=800,players=[{'id':'hero','x':0},{'id':'enemy','x':500}])
class GunBoundFireTests(unittest.TestCase):
    def plan(self,power=50):return dict(power=power,hero='hero',target='enemy',window=1,shot=0,wind=0,windAngle=0,heroState={'x':0},targetState={'x':500},screenBox=(0,0,800,600),dpr=1)
    def test_drag_confirms_live_power_and_releases_once(self):
        b=Backend();r=Reader(b);out=execute_gunbound(self.plan(),r,threading.Event(),backend=b)
        self.assertEqual(out['power'],50);self.assertEqual([a for a in b.actions if a[0]=='mouse'],[('mouse',True),('mouse',False)])
    def test_slice_reads_charge_instead_of_using_a_fixed_delay(self):
        b=Backend();r=Reader(b,'space');out=execute_gunbound(self.plan(),r,threading.Event(),backend=b)
        self.assertEqual(out['power'],50);self.assertEqual(b.actions,[('space',True),('space',False)])
    def test_enemy_turn_sends_no_input(self):
        b=Backend();r=Reader(b);r.turn='enemy'
        with self.assertRaises(RuntimeError):execute_gunbound(self.plan(),r,threading.Event(),backend=b)
        self.assertEqual(b.actions,[])
    def test_armed_item_sends_no_input(self):
        b=Backend();r=Reader(b);r.armed=True
        with self.assertRaises(RuntimeError):execute_gunbound(self.plan(),r,threading.Event(),backend=b)
        self.assertEqual(b.actions,[])
    def test_lost_focus_sends_no_input(self):
        b=Backend();b.window=2;r=Reader(b)
        with self.assertRaises(RuntimeError):execute_gunbound(self.plan(),r,threading.Event(),backend=b)
        self.assertEqual(b.actions,[])
