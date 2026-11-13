"""Input checks use the same browser identity as acquisition, without a browser."""
import json
import shutil
import subprocess
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from adapters import AdapterClient
from auto_fire import POWER_READ_JS, PowerReader, execute
from cdp import CDP
from gunbound_fire import GUNBOUND_POWER_READ_JS, GunBoundPowerReader, execute_gunbound
from session_lifecycle import SourceLifecycle


class Backend:
    def __init__(self):self.actions=[];self.held=False;self.position=(100,100)
    def foreground(self):return 1,2,'Fixture'
    def window_rect(self,window):return 0,0,800,600
    def input_busy(self):return False
    def escaped(self):return False
    def cursor(self):return self.position
    def point_in_window(self,x,y,window):return True
    def key(self,down):self.actions.append(('key',down));self.held=down
    def mouse(self,down):self.actions.append(('mouse',down));self.held=down
    def move(self,x,y):self.actions.append(('move',x,y));self.position=(x,y)


def plan(power=50):
    return {'power':power,'window':1,'sourceEpoch':'current','hero':0,'target':1,
            'shot':0,'wind':1,'windAngle':30,'heroState':{'x':10,'y':20,'rawAngle':60},
            'targetState':{'x':400,'y':20},'dpr':1,'screenBox':(0,0,800,600)}


class Reader:
    def __init__(self,backend,changes=()):self.backend=backend;self.changes=changes;self.count=0
    def drag_start(self,window):return 100,100
    def read(self):
        state={'sourceEpoch':'current','hero':0,'turn':0,'shot':0,'wind':1,'windAngle':30,
               'focused':True,'chat':False,'over':False,'moving':False,'mode':'space',
               'power':50,'busy':self.backend.held,'blocked':False,'armedItem':False,
               'players':[{'id':0,'x':10,'y':20,'rawAngle':60},{'id':1,'x':400,'y':20}]}
        if self.count<len(self.changes):state.update(self.changes[self.count])
        self.count+=1
        return state


class InputEpochTests(unittest.TestCase):
    def test_changed_or_missing_epoch_rejects_every_input_method_before_input(self):
        for executor in (execute,execute_gunbound):
            for epoch in ('old',None):
                for mode in ('space','drag'):
                    with self.subTest(executor=executor.__name__,epoch=epoch,mode=mode):
                        backend=Backend();reader=Reader(backend,[{'sourceEpoch':epoch,'mode':mode}])
                        with self.assertRaisesRegex(RuntimeError,'sesión'):
                            executor(plan(),reader,threading.Event(),backend)
                        self.assertEqual(backend.actions,[])

    def test_matching_epoch_allows_one_charge_and_release(self):
        for executor in (execute,execute_gunbound):
            with self.subTest(executor=executor.__name__):
                backend=Backend()
                result=executor(plan(),Reader(backend),threading.Event(),backend)
                self.assertEqual(result['power'],50)
                self.assertEqual(backend.actions,[('key',True),('key',False)])

    def test_changed_epoch_during_charge_releases_once_and_never_retries(self):
        for executor in (execute,execute_gunbound):
            for mode in ('space','drag'):
                with self.subTest(executor=executor.__name__,mode=mode):
                    backend=Backend();reader=Reader(backend,[{'mode':mode}, {'mode':mode,'sourceEpoch':'replacement'}])
                    with self.assertRaisesRegex(RuntimeError,'sesión'):
                        executor(plan(),reader,threading.Event(),backend)
                    expected=[('key',True),('key',False)] if mode=='space' else [('move',100,100),('mouse',True),('mouse',False)]
                    self.assertEqual(backend.actions,expected)
                    self.assertFalse(backend.held)

    def test_full_charge_completion_cannot_bypass_epoch_validation(self):
        cases=((execute,400,390,{'turn':1,'power':400,'busy':False}),
               (execute_gunbound,100,90,{'power':100,'lastPower':100,'busy':False}))
        for executor,power,charging,completed in cases:
            with self.subTest(executor=executor.__name__):
                backend=Backend();reader=Reader(backend,[{}, {'power':charging},
                    {**completed,'sourceEpoch':'replacement'}])
                with patch('auto_fire.time.sleep'),patch('gunbound_fire.time.sleep'):
                    with self.assertRaisesRegex(RuntimeError,'sesión'):
                        executor(plan(power),reader,threading.Event(),backend)
                self.assertEqual(backend.actions,[('key',True),('key',False)])

    def test_navigation_received_during_native_read_discards_the_old_result(self):
        for reader_type in (PowerReader,GunBoundPowerReader):
            with self.subTest(reader=reader_type.__name__):
                lifecycle=SourceLifecycle('fixture','127.0.0.1','fixture')
                def call(method,params):
                    lifecycle.invalidate('contexts-cleared',True)
                    return {'result':{'value':{'sourceEpoch':'old'}}}
                reader=object.__new__(reader_type)
                reader.client=SimpleNamespace(lifecycle=lifecycle,game='game',renderer=None,
                                              controller='controller',call=Mock(side_effect=call))
                with self.assertRaisesRegex(RuntimeError,'sesión'):reader.read()
                self.assertEqual(reader.client.call.call_count,1)


def sampler_client(kind):
    client=object.__new__(kind)
    client.game='game';client.renderer='renderer';client.discovery_clock=time.monotonic()
    client.discovery_interval=3600;client.terrain_clock=time.monotonic();client.terrain_interval=60
    client.terrain_cache=None;client.terrain_turn=0;client.terrain_inflight=False
    return client


@unittest.skipUnless(shutil.which('node'),'Node is required for the isolated JavaScript fixture')
class BrowserIdentityTests(unittest.TestCase):
    def test_native_readers_match_acquisition_identity_and_preserve_live_fields(self):
        dragon=sampler_client(CDP)
        dragon.call=Mock(return_value={'result':{'value':{'status':'live','turn':0}}})
        dragon.sample()
        dragon_sample_js=dragon.call.call_args.args[1]['functionDeclaration']

        gunbound=sampler_client(AdapterClient)
        gunbound.profile={'id':'gunbound-world'};gunbound.controller='controller'
        gunbound.gunbound_terrain_stamp=('controller',1);gunbound.gunbound_terrain_clock=time.monotonic()
        gunbound.call=Mock(side_effect=[{'result':{'value':{'status':'live','phase':'TURN','turn':1,'players':[]}}},
                                       {'result':{'value':{}}}])
        gunbound._generic_sample()
        gunbound_sample_js=gunbound.call.call_args_list[1].args[1]['functionDeclaration']
        scripts={'dragonSample':dragon_sample_js,'dragonRead':POWER_READ_JS,
                 'gunboundSample':gunbound_sample_js,'gunboundRead':GUNBOUND_POWER_READ_JS}
        harness=r'''
const fs=require('fs'),assert=require('assert/strict');
const scripts=JSON.parse(fs.readFileSync(0,'utf8'));
const functions=Object.fromEntries(Object.entries(scripts).map(([k,v])=>[k,eval('('+v+')')]));
global.window={};global.performance={timeOrigin:100};global.location={pathname:'/'};
global.document={hasFocus:()=>true,visibilityState:'visible',activeElement:{tagName:'BODY'},
  getElementById:id=>id==='slice_drag_button'?{classList:{contains:()=>true}}:
    id==='powerMarkArea'?{getBoundingClientRect:()=>({width:400})}:
    id==='powerBar'?{getBoundingClientRect:()=>({width:150})}:null};
const hero={n:'0',x:10,y:20,ang:60,body:0,look:0,is_alive:true};
const target={n:'1',x:400,y:20,ang:30,body:0,look:1,is_alive:true};
const game={players:[hero,target],my_player_number:'0',turn:'0',selectedShot:0,
  curUIPower:12,windPower:1,windAngle:30,dragSens:1.37,drag_start_x:16,stat:[[0,16],[1,222]]};
const sample=()=>functions.dragonSample.call(game,null,false,false);
const read=()=>functions.dragonRead.call(game,null);
let acquired=sample(),live=read();
assert.equal(live.sourceEpoch,acquired.sourceEpoch);
assert.equal(read().sourceEpoch,live.sourceEpoch);
assert.equal(live.hero,0);assert.equal(live.power,150);assert.equal(live.dragSens,1.37);
assert.equal(live.dragStartX,16);assert.equal(live.dragUpdates,1);assert.equal(live.dragPointX,222);
assert.deepEqual(live.players.map(p=>p.id),[0,1]);
game.players=new Map([['0',hero],['1',target]]);
game.players.get=()=>{throw new Error('page get must not run')};
assert.equal(read().sourceEpoch,live.sourceEpoch);
game.players.set('0',{...hero});
assert.notEqual(read().sourceEpoch,live.sourceEpoch);
assert.equal(read().sourceEpoch,sample().sourceEpoch);

const me={x:0,y:40,mobileId:'armor',facing:'right',aimAngle:60,bodyTilt:0,alive:true,hp:100,selectedShot:'shot1'};
const enemy={x:500,y:40,mobileId:'armor',facing:'left',aimAngle:50,bodyTilt:0,alive:true,hp:100};
const state={players:{$items:new Map([['hero',me],['enemy',enemy]])},phase:'TURN',activePlayerId:'hero',windPower:2,windAngleDeg:20};
state.players.get=()=>{throw new Error('page get must not run')};
const controller={room:{state},myId:'hero',power:55,lastPower:51,inputMode:'drag',
  roomConnected:true,renderSurface:'live',shot:'shot1',angle:60,stageSize:{width:800,height:600},
  graphicsSettings:{dragSensitivity:100},app:{canvas:{getBoundingClientRect:()=>({width:800})}}};
const gbSample=()=>functions.gunboundSample.call(controller);
const gbRead=()=>functions.gunboundRead.call(controller);
acquired=gbSample();live=gbRead();
assert.equal(live.sourceEpoch,acquired.sourceEpoch);
assert.equal(gbRead().sourceEpoch,live.sourceEpoch);
assert.equal(live.power,55);assert.equal(live.lastPower,51);assert.equal(live.sensitivity,100);
assert.equal(live.canvasWidth,800);assert.equal(live.stageWidth,800);assert.equal(live.hero,'hero');
assert.deepEqual(live.players.map(p=>p.id),['hero','enemy']);
assert.equal(live.players[0].rawAngle,60);
state.players.$items.set('hero',{...me});
assert.notEqual(gbRead().sourceEpoch,live.sourceEpoch);
assert.equal(gbRead().sourceEpoch,gbSample().sourceEpoch);
controller.room.state={...state};
assert.notEqual(gbRead().sourceEpoch,live.sourceEpoch);
assert.equal(gbRead().sourceEpoch,gbSample().sourceEpoch);
process.stdout.write(JSON.stringify({ok:true}));
'''
        result=subprocess.run([shutil.which('node'),'-e',harness],input=json.dumps(scripts),
                              capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),{'ok':True})


if __name__=='__main__':unittest.main()
