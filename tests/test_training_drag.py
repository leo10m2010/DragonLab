import copy,threading,unittest
from unittest.mock import Mock,patch
from training_drag import prepare_drag,charge_drag
from training_browser import TrainingBrowser,TurnExpired,FocusPause


GEOMETRY={'x':16,'y':100,'right':790,'left':0,'top':0,'width':800,'height':600,'scrollX':0,'scrollY':0,'viewportWidth':800,'viewportHeight':600}

class DragFixture:
    def __init__(self):
        self.events=[];self.pressed=False;self.power=222;self.sensitivity=1.3;self.revision=90;self.point=16;self.reads=0;self.stale=0;self.bias=0;self.error=None;self.mutate=None
    def call(self,method,args):
        if method=='Runtime.evaluate':return {'result':{'value':dict(GEOMETRY)}}
        self.events.append(dict(args));kind=args['type']
        if kind=='mousePressed':
            self.pressed=True;self.sensitivity=1.67;self.revision=0;self.origin=args['x'];self.point=args['x']
            if self.error:raise self.error
        elif kind=='mouseMoved' and self.pressed:
            self.point=args['x'];self.revision+=1;self.power=round((self.point-self.origin)/self.sensitivity)+self.bias
        elif kind=='mouseReleased':self.pressed=False
        return {}
    def read(self):
        self.reads+=1
        value={'power':self.power,'busy':self.pressed,'mode':'drag','dragSens':self.sensitivity,'dragStartX':getattr(self,'origin',16),'dragUpdates':self.revision,'dragPointX':self.point}
        if self.pressed and self.revision and self.stale:
            value.update(power=222,dragUpdates=0,dragPointX=16);self.stale-=1
        if self.mutate:self.mutate(value,self)
        return value


class DragTests(unittest.TestCase):
    def run_drag(self,fixture=None,**kwargs):
        f=fixture or DragFixture();guard=kwargs.pop('guard',Mock());validate=kwargs.pop('validate',Mock());pressed=kwargs.pop('on_press',Mock())
        result=charge_drag(f,f,dict(GEOMETRY),kwargs.pop('power',222),kwargs.pop('cancel',threading.Event()),guard,validate,pressed)
        return f,result,guard,validate,pressed
    def test_uses_fresh_sensitivity_css_coordinates_and_releases_at_last_point(self):
        f,result,guard,validate,pressed=self.run_drag()
        self.assertEqual(result['power'],222);self.assertEqual(result['sensitivity'],1.67)
        self.assertAlmostEqual(f.events[-1]['x'],16+222*1.67,places=2)
        self.assertEqual([e['type'] for e in f.events],['mouseMoved','mousePressed','mouseMoved','mouseReleased'])
        self.assertEqual(f.events[2]['buttons'],1);self.assertEqual(f.events[-1]['buttons'],0);self.assertFalse(f.pressed);pressed.assert_called_once()
    def test_stale_equal_power_must_wait_for_new_native_move(self):
        f=DragFixture();f.stale=3
        f,result,*_=self.run_drag(f)
        self.assertGreaterEqual(f.reads,7);self.assertEqual(result['power'],222)
        self.assertEqual(len([e for e in f.events if e['type']=='mouseMoved' and e['buttons']==1]),1)
    def test_corrects_using_actual_power_and_stores_actual_force(self):
        f=DragFixture();f.bias=-5
        f,result,*_=self.run_drag(f)
        self.assertEqual(result['corrections'],1);self.assertLessEqual(abs(result['power']-222),1)
    def test_cancellation_always_releases_same_target(self):
        cancel=threading.Event();f=DragFixture()
        def guard(_):
            if f.revision==1 and f.pressed:cancel.set()
        with self.assertRaisesRegex(RuntimeError,'detenido'):self.run_drag(f,cancel=cancel,guard=guard)
        self.assertEqual(f.events[-1]['type'],'mouseReleased');self.assertFalse(f.pressed)
    def test_modal_or_turn_change_after_press_releases_without_retry(self):
        for failure in (FocusPause('modal'),TurnExpired('turno')):
            with self.subTest(failure=failure):
                f=DragFixture()
                def validate(state,**kw):
                    if f.pressed:raise failure
                with self.assertRaises(type(failure)):self.run_drag(f,validate=validate)
                self.assertEqual([e['type'] for e in f.events].count('mousePressed'),1)
                self.assertEqual(f.events[-1]['type'],'mouseReleased')
    def test_ambiguous_press_timeout_still_releases(self):
        f=DragFixture();f.error=TimeoutError('transport')
        with self.assertRaises(TimeoutError):self.run_drag(f)
        self.assertEqual(f.events[-1]['type'],'mouseReleased');self.assertFalse(f.pressed)
    def test_unknown_sensitivity_is_not_guessed_or_retried(self):
        f=DragFixture();f.mutate=lambda s,f:s.update(dragSens=2) if f.pressed else None
        with self.assertRaisesRegex(RuntimeError,'sensibilidad'):self.run_drag(f)
        self.assertEqual(len([e for e in f.events if e['type']=='mousePressed']),1)
        self.assertEqual(f.events[-1]['type'],'mouseReleased')
    def test_geometry_change_during_charge_releases(self):
        f=DragFixture();original=f.call
        def call(method,args):
            if method=='Runtime.evaluate' and f.pressed:return {'result':{'value':{**GEOMETRY,'scrollX':20}}}
            return original(method,args)
        f.call=call
        with self.assertRaisesRegex(RuntimeError,'zona'):self.run_drag(f)
        self.assertEqual(f.events[-1]['type'],'mouseReleased')
    def test_no_space_never_presses_before_fallback(self):
        f=DragFixture();f.call=Mock(return_value={'result':{'value':{**GEOMETRY,'right':200}}})
        self.assertIsNone(prepare_drag(f,222));self.assertTrue(all(c.args[0]=='Runtime.evaluate' for c in f.call.call_args_list))
    def test_unconfirmed_move_cannot_accept_previous_power(self):
        f=DragFixture();f.mutate=lambda s,f:s.update(dragUpdates=0,dragPointX=16) if f.pressed else None
        with patch('training_drag.time.monotonic',side_effect=[0,.1,.2,.3,1.1]):
            with self.assertRaisesRegex(RuntimeError,'movimiento'):self.run_drag(f)
        self.assertEqual(f.events[-1]['type'],'mouseReleased')
    def test_full_native_autorelease_requires_acknowledged_move(self):
        f=DragFixture()
        def mutate(state,f):
            if f.revision==1 and f.pressed:state['busy']=False
        f.mutate=mutate
        _,result,_,validate,_=self.run_drag(f,power=400)
        self.assertEqual(result['power'],400);self.assertTrue(validate.call_args.kwargs['allow_released'])
    def test_preexisting_charge_does_not_receive_mouse_press(self):
        f=DragFixture();f.pressed=True
        with self.assertRaisesRegex(RuntimeError,'otra carga'):self.run_drag(f)
        self.assertFalse(any(e['type']=='mousePressed' for e in f.events))


class ChargeIntegrationTests(unittest.TestCase):
    def full_shoot(self,fixture):
        b=TrainingBrowser.__new__(TrainingBrowser);b.client=fixture;fixture.endpoint='http://127.0.0.1:9223';fixture.target={'id':'exact-tab'}
        b.guard=Mock(return_value={'controls':{},'selectedItems':[]});b.adjust_angle=Mock(return_value={'before':60,'after':60});b.key=Mock()
        native=fixture.read
        def read():return {**native(),'hero':0,'turn':0,'turnNumber':9,'shot':0,'wind':0,'windAngle':90,'players':[{'id':0,'x':10,'y':20,'rawAngle':60,'look':0,'body':0},{'id':1,'x':300,'y':20}]}
        reader=Mock();reader.read.side_effect=read
        shot={'id':9,'native':True,'elapsed':0,'duration':1000,'start':[10,20,60,220,0,300],'shotType':0,'metadata':{'player':0,'power':222}}
        b.sample=lambda:{'status':'live','heroId':0,'activePlayer':0,'players':[{'id':0,'x':10,'y':20},{'id':1,'x':300,'y':20}],'shots':[shot] if any(e['type']=='mouseReleased' for e in fixture.events) else []}
        reservations=[]
        def reserve():reservations.append(len(fixture.events))
        with patch('training_browser.PowerReader',return_value=reader):
            result=b.shoot({'shot':0,'angle':60,'power':222,'turn_serial':9},threading.Event(),before_fire=reserve)
        return b,result,reservations
    def test_full_shoot_reserves_once_and_keeps_native_confirmation_and_timing(self):
        f=DragFixture();b,(release,observed),reservations=self.full_shoot(f)
        self.assertEqual(release['method'],'drag');self.assertEqual(release['power'],222);self.assertEqual(release['requested_power'],222)
        self.assertEqual(release['timing']['input_method'],'drag');self.assertGreaterEqual(release['timing']['charge_ms'],0)
        self.assertEqual(len(reservations),1);self.assertLessEqual(reservations[0],next(i for i,e in enumerate(f.events) if e['type']=='mousePressed'))
        b.key.assert_not_called();self.assertIsNone(b.reader)
    def test_failed_drag_does_not_attempt_space_or_reserve_twice(self):
        f=DragFixture();f.error=TimeoutError('accepted press but lost reply')
        with self.assertRaises(TimeoutError):self.full_shoot(f)
        self.assertEqual([e['type'] for e in f.events].count('mousePressed'),1)
        self.assertEqual([e['type'] for e in f.events].count('mouseReleased'),1)
    def test_space_fallback_selected_before_any_charge_if_drag_does_not_fit(self):
        b=TrainingBrowser.__new__(TrainingBrowser);b.client=Mock();b.guard=Mock(return_value={'controls':{'slice_drag_button':{'x':1,'y':1}}});b.click=Mock();b.confirm_setting=Mock()
        reader=Mock();reader.read.return_value={'mode':'drag'}
        with patch('training_browser.prepare_drag',return_value=None):method,geometry=b.prepare_charge(reader,9,350,threading.Event())
        self.assertEqual(method,'space');self.assertIsNone(geometry);b.click.assert_called_once();b.confirm_setting.assert_called_once()
    def test_mode_toggle_geometry_failure_falls_back_before_press(self):
        b=TrainingBrowser.__new__(TrainingBrowser);b.client=Mock();b.guard=Mock(return_value={'controls':{'slice_drag_button':{}}});b.click=Mock();b.confirm_setting=Mock()
        reader=Mock();reader.read.return_value={'mode':'space'}
        with patch('training_browser.prepare_drag',side_effect=[GEOMETRY,None]):method,geometry=b.prepare_charge(reader,9,350,threading.Event())
        self.assertEqual(method,'space');self.assertEqual(b.confirm_setting.call_count,2)
    def test_native_mode_and_pose_rechecked_during_charge(self):
        b=TrainingBrowser.__new__(TrainingBrowser)
        release={'hero':0,'turn_serial':1,'method':'drag','shot':1,'x':10,'y':20,'pose':{'look':0,'body':0},'angle':60,'wind':5,'windAngle':90}
        state={'turn':0,'turnNumber':1,'mode':'drag','shot':1,'wind':5,'windAngle':90,'players':[{'id':0,'x':10,'y':20,'look':0,'body':0,'rawAngle':60}]}
        b.validate_charge(state,release)
        changed=copy.deepcopy(state);changed['players'][0]['rawAngle']=61
        with self.assertRaises(RuntimeError):b.validate_charge(changed,release)
        changed=copy.deepcopy(state);changed['mode']='space'
        with self.assertRaises(RuntimeError):b.validate_charge(changed,release)
        changed=copy.deepcopy(state);changed['turnNumber']=2
        with self.assertRaises(TurnExpired):b.validate_charge(changed,release)

if __name__=='__main__':unittest.main()
