"""Adapt capture frequency to this process's measured CPU workload."""
import os,time
class Governor:
    def __init__(self):self.wall=time.monotonic();self.cpu=sum(os.times()[:2]);self.level=0;self.high=0;self.low=0
    def sample(self):
        wall=time.monotonic();cpu=sum(os.times()[:2]);dt=wall-self.wall
        if dt<2:return self.level
        load=max(0,(cpu-self.cpu)/dt);self.wall=wall;self.cpu=cpu
        self.high=self.high+1 if load>.35 else 0;self.low=self.low+1 if load<.12 else 0
        if self.high>=2:self.level=min(2,self.level+1);self.high=0
        if self.low>=4:self.level=max(0,self.level-1);self.low=0
        return self.level
    def intervals(self,mode,active=True,own_turn=True):
        if mode=='Normal':base=(.25,1.5,2)
        elif mode=='Ligero':base=(.35,3,5)
        else:
            level=self.sample();base=((.25,3,3),(.35,4,4),(.5,6,6))[level]
        if not active:return 1,6,8
        if not own_turn:return max(.5,base[0]),max(4,base[1]),max(5,base[2])
        return base
