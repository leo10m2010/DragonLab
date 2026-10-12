"""Bounded, owned shot observer. Never sends game controls or account data."""
import math,uuid

INSTALL=r"""function(owner){
 if(this.destroyed||this.renderSurface!=="live")return false;
 if(this.__dragonlabLearning)return this.__dragonlabLearning.owner===owner;
 const c=this, priorSubmit=this.onShotSubmitted,priorSettle=this.onShotSettled;
 const store={owner,buffer:[],pending:null,priorSubmit,priorSettle};
 store.submit=function(e){try{const s=c.room.state,p=s.players.get(c.myId);
 store.pending={mobile:p?.mobileId,shot:e?.selectedShot,wind:s.windPower,wind_angle:s.windAngleDeg,item:!!p?.armedItem,at:Date.now()};
 }catch{store.pending=null}return typeof priorSubmit==='function'?priorSubmit.apply(this,arguments):undefined};
 store.settle=function(r){try{const release=store.pending;
 if(release&&r?.shooterId===c.myId){store.pending=null;
 const projectile=r.projectiles?.find(p=>p.sourceShotProjectileIndex===0&&p.path?.[0]?.t===0);
 if(!release.item&&projectile&&r.shot===release.shot){store.buffer.push({...release,power:c.lastPower,id:owner+':'+release.at,path:projectile.path.slice(0,8).map(p=>({x:p.x,y:p.y,t:p.t}))});if(store.buffer.length>24)store.buffer.shift()}}
 }catch{}return typeof priorSettle==='function'?priorSettle.apply(this,arguments):undefined};
 this.__dragonlabLearning=store;this.onShotSubmitted=store.submit;this.onShotSettled=store.settle;return true;
}"""
DRAIN='function(owner){const s=this.__dragonlabLearning;return s?.owner===owner?s.buffer.splice(0):[]}'
REMOVE='function(owner){const s=this.__dragonlabLearning;if(s?.owner===owner){if(this.onShotSubmitted===s.submit)this.onShotSubmitted=s.priorSubmit;if(this.onShotSettled===s.settle)this.onShotSettled=s.priorSettle;delete this.__dragonlabLearning}return true}'

def measurement(event):
    from calibration_book import mobile_name
    mobile=mobile_name(event.get('mobile'));shot={'shot1':0,'shot2':1,'ss':2}.get(event.get('shot'))
    points=event.get('path',[])
    if not mobile or shot is None or event.get('item') or len(points)<5:return None
    points=points[:8]
    if not all(all(isinstance(p.get(k),(int,float)) and math.isfinite(p[k]) for k in ('x','y','t')) for p in points):return None
    if points[0]['t']!=0:return None
    dt=points[1]['t'];power=event.get('power');wind=event.get('wind');angle=event.get('wind_angle')
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (power,wind,angle)):return None
    if not 1<=power<=100 or not 0<=wind<=100 or abs(dt-.05)>1e-6:return None
    if any(abs(p['t']-i*dt)>1e-6 for i,p in enumerate(points)):return None
    ax=(points[2]['x']-2*points[1]['x']+points[0]['x'])/dt**2
    ay=(points[2]['y']-2*points[1]['y']+points[0]['y'])/dt**2
    vx=(points[1]['x']-points[0]['x'])/dt;vy=(points[1]['y']-points[0]['y'])/dt
    # Observed native explicit-Euler convention: first interval uses launch velocity.
    for i,q in enumerate(points):
        predicted=(points[0]['x']+vx*i*dt+ax*dt**2*i*(i-1)/2,points[0]['y']+vy*i*dt+ay*dt**2*i*(i-1)/2)
        if math.dist(predicted,(q['x'],q['y']))>1:return None
    if math.hypot(vx,vy)<1 or abs(ax)>2000 or not 1<ay<4000:return None
    return {'mobile':mobile,'selected_shot':shot,'sample_id':event['id'],'power':power,'vx':vx,'vy':vy,'ax':ax,'ay':ay,'wind':wind,'wind_angle':angle,'native_euler_step':dt,'source':'gunbound-own-shot-path'}

class GunBoundLearning:
    def __init__(self,client):self.client=client;self.owner=uuid.uuid4().hex;self.handle=None;self.error=''
    def call(self,code):return self.client.call('Runtime.callFunctionOn',{'objectId':self.handle,'functionDeclaration':code,'arguments':[{'value':self.owner}],'returnByValue':True}).get('result',{}).get('value')
    def drain(self):
        return [m for e in self.call(DRAIN) or [] if (m:=measurement(e)) is not None] if self.handle else []
    def remove(self):
        if self.handle:
            try:self.call(REMOVE)
            finally:
                self.client.call('Runtime.releaseObjectGroup',{'objectGroup':'dragonlab-learning'});self.handle=None
    def poll(self):
        samples=[]
        try:
            if self.handle:
                samples=self.drain()
                valid=self.call('function(){return !this.destroyed&&this.renderSurface==="live"}')
                if not valid:self.remove()
            if not self.handle and self.client.controller:
                result=self.client.call('Runtime.callFunctionOn',{'objectId':self.client.controller,'functionDeclaration':'function(){return this}','objectGroup':'dragonlab-learning'}).get('result',{})
                self.handle=result.get('objectId')
                if self.handle and not self.call(INSTALL):self.remove()
            self.error=''
        except Exception as e:self.error=str(e)[:180]
        return samples
    def close(self):
        try:self.remove()
        except Exception:pass
