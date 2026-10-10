"""Local calibrated visual measurements; no external AI or model downloads.
Images use pixel coordinates. Color-based terrain/tracking needs user-selected colors;
OCR must be taught screenshots from the current game's font/theme/scale.
"""
import math,time,json
from PIL import Image

def _distance(a,b):return sum((a[i]-b[i])**2 for i in range(3))

def detect_terrain(image,color,tolerance=35,min_run=3,step=2):
    im=image.convert('RGB');w,h=im.size;p=im.load();limit=tolerance*tolerance
    points=[]
    for x in range(0,w,max(1,int(step))):
        count=0
        for y in range(h):
            count=count+1 if _distance(p[x,y],color)<=limit else 0
            if count>=min_run:
                points.append([x,y-min_run+1]);break
    return {'points':points,'confidence':len(points)/max(1,math.ceil(w/max(1,step))),
            'width':w,'height':h,'method':'calibrated-color-surface'}

class ColorTracker:
    def __init__(self,color,tolerance=35,min_pixels=2,max_pixels=300,search_radius=100):
        self.color=tuple(color);self.tolerance=tolerance;self.min_pixels=min_pixels;self.max_pixels=max_pixels
        self.search_radius=search_radius;self.samples=[]
    def sample(self,image,timestamp=None):
        im=image.convert('RGB');w,h=im.size;p=im.load();hits=set();limit=self.tolerance**2
        # Search entire frame initially, then around last measured projectile.
        last=self.samples[-1] if self.samples else None
        x1,x2,y1,y2=0,w,0,h
        if last:
            x1=max(0,int(last['x']-self.search_radius));x2=min(w,int(last['x']+self.search_radius)+1)
            y1=max(0,int(last['y']-self.search_radius));y2=min(h,int(last['y']+self.search_radius)+1)
        for y in range(y1,y2):
            for x in range(x1,x2):
                if _distance(p[x,y],self.color)<=limit:hits.add((x,y))
        groups=[]
        while hits:
            seed=hits.pop();group=[seed];stack=[seed]
            while stack:
                x,y=stack.pop()
                for n in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if n in hits:hits.remove(n);group.append(n);stack.append(n)
            if self.min_pixels<=len(group)<=self.max_pixels:groups.append(group)
        if not groups:return None
        if last:group=min(groups,key=lambda g:(sum(x for x,y in g)/len(g)-last['x'])**2+(sum(y for x,y in g)/len(g)-last['y'])**2)
        else:group=max(groups,key=len)
        sample={'t':time.monotonic() if timestamp is None else timestamp,'x':sum(x for x,y in group)/len(group),
                'y':sum(y for x,y in group)/len(group),'pixels':len(group),'confidence':1/len(groups)}
        self.samples.append(sample);return sample
    def fit(self):
        """Least-squares measured x/y acceleration, in screen pixels/second²."""
        if len(self.samples)<5:raise ValueError('Se necesitan al menos cinco medidas')
        start=self.samples[0]['t'];ts=[s['t']-start for s in self.samples]
        def fit_axis(key):
            a=[[sum(t**(i+j) for t in ts) for j in range(3)]+[sum(s[key]*t**i for s,t in zip(self.samples,ts))] for i in range(3)]
            for i in range(3):
                pivot=max(range(i,3),key=lambda j:abs(a[j][i]));a[i],a[pivot]=a[pivot],a[i]
                d=a[i][i]
                if abs(d)<1e-10:raise ValueError('Tiempos de medida insuficientes')
                a[i]=[v/d for v in a[i]]
                for j in range(3):
                    if j!=i:
                        q=a[j][i];a[j]=[v-q*u for v,u in zip(a[j],a[i])]
            c=[a[i][3] for i in range(3)]
            rms=math.sqrt(sum((s[key]-sum(c[i]*t**i for i in range(3)))**2 for s,t in zip(self.samples,ts))/len(ts))
            return c,rms
        cx,rx=fit_axis('x');cy,ry=fit_axis('y')
        return {'origin':[cx[0],cy[0]],'velocity':[cx[1],cy[1]],'acceleration':[2*cx[2],2*cy[2]],'rms_pixels':math.hypot(rx,ry),'samples':len(ts)}

class DigitOCR:
    def __init__(self):self.templates={}
    def _mask(self,image,foreground=None,tolerance=70):
        im=image.convert('RGB');w,h=im.size;p=im.load()
        if foreground is None:
            # Border background estimate; user can select foreground for mixed backgrounds.
            border=[p[x,0] for x in range(w)]+[p[x,h-1] for x in range(w)]
            bg=tuple(sorted(v[i] for v in border)[len(border)//2] for i in range(3))
            values=[1 if _distance(p[x,y],bg)>tolerance**2 else 0 for y in range(h) for x in range(w)]
        else:values=[1 if _distance(p[x,y],foreground)<tolerance**2 else 0 for y in range(h) for x in range(w)]
        mask=Image.new('L',(w,h));mask.putdata([v*255 for v in values]);return mask
    def _glyphs(self,mask):
        w,h=mask.size;p=mask.load();columns=[any(p[x,y] for y in range(h)) for x in range(w)];runs=[];start=None
        for x,v in enumerate(columns+[False]):
            if v and start is None:start=x
            if not v and start is not None:
                crop=mask.crop((start,0,x,h));box=crop.getbbox()
                if box:runs.append(crop.crop(box).resize((20,32),Image.Resampling.NEAREST))
                start=None
        return runs
    def learn(self,label,image,foreground=None):
        if not label or any(c not in '0123456789-' for c in label):raise ValueError('Etiqueta: solo dígitos y signo menos')
        glyphs=self._glyphs(self._mask(image,foreground))
        if len(glyphs)!=len(label):raise ValueError('Recorta solo el número, dejando separación entre dígitos')
        for c,g in zip(label,glyphs):self.templates.setdefault(c,[]).append(list(g.getdata()))
    def read(self,image,foreground=None,min_confidence=.80):
        if not self.templates:raise ValueError('Primero enseña ejemplos de los dígitos')
        glyphs=self._glyphs(self._mask(image,foreground));text='';scores=[]
        for g in glyphs:
            pixels=list(g.getdata());matches=[]
            for c,templates in self.templates.items():
                score=max(1-sum(abs(a-b) for a,b in zip(pixels,t))/(255*len(pixels)) for t in templates)
                matches.append((score,c))
            matches.sort(reverse=True);best,c=matches[0];margin=best-matches[1][0] if len(matches)>1 else best
            scores.append({'character':c,'confidence':best,'margin':margin});text+=c if best>=min_confidence and margin>=.015 else '?'
        return {'text':text,'value':int(text) if text and '?' not in text and text!='-' else None,'confidence':min((s['confidence'] for s in scores),default=0),'digits':scores,'method':'user-calibrated-local-templates'}
    def save(self,path):
        with open(path,'w',encoding='utf-8') as f:json.dump(self.templates,f)
    def load(self,path):
        with open(path,encoding='utf-8-sig') as f:templates=json.load(f)
        if not isinstance(templates,dict) or any(k not in '0123456789-' or not isinstance(v,list) or not v or len(v)>100 or any(not isinstance(t,list) or len(t)!=640 or any(not isinstance(p,(int,float)) or not 0<=p<=255 for p in t) for t in v) for k,v in templates.items()):raise ValueError('Plantillas OCR inválidas')
        self.templates=templates
