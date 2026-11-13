"""The supplied DragonLab artwork, with event-driven state indicators."""
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
import tkinter as tk
from PIL import Image,ImageTk
from theme import PANEL,TEXT,MUTED,GREEN,ORANGE

ASSET_PATH=Path(__file__).resolve().parent/'assets'/'head-dragon.webp'

@lru_cache(maxsize=1)
def mascot_source():
    """Decode the bundled, unmodified WebP once and retain its alpha channel."""
    with Image.open(ASSET_PATH) as source:return source.convert('RGBA')

@lru_cache(maxsize=8)
def mascot_image(width,height):
    """Contain the entire artwork without cropping, stretching or recoloring."""
    source=mascot_source();scale=min(max(1,width)/source.width,max(1,height)/source.height)
    size=(max(1,round(source.width*scale)),max(1,round(source.height*scale)))
    return source.resize(size,Image.Resampling.LANCZOS)

@lru_cache(maxsize=32)
def dragon_shapes(width,height,state):
    """Legacy vector geometry retained for existing callers; the UI uses WebP."""
    scale=min(width/92,height/84);dx=(width-92*scale)/2;dy=(height-84*scale)/2
    def points(*coords):return tuple(dx+v*scale if i%2==0 else dy+v*scale for i,v in enumerate(coords))
    accent=ORANGE if state=='error' else GREEN if state=='active' else MUTED
    shapes=[
        ('polygon',points(15,51,5,30,25,37,32,16,46,30,62,13,63,35,79,39,86,54,77,68,49,75,26,68),{'fill':'#30332C','outline':'#727A62','width':1.5,'joinstyle':'round'}),
        ('polygon',points(27,39,34,25,40,39),{'fill':'#889874','outline':''}),
        ('polygon',points(51,34,59,21,58,40),{'fill':'#889874','outline':''}),
        ('polygon',points(11,37,27,44,23,57),{'fill':'#444C37','outline':''}),
        ('polygon',points(48,63,62,48,79,45,83,56,75,65,59,68),{'fill':'#424A34','outline':''}),
        ('oval',points(73,51,76,54),{'fill':TEXT,'outline':''}),
        ('line',points(57,62,65,63,75,60),{'fill':accent,'width':2,'capstyle':'round'}),
        ('polygon',points(24,65,34,66,30,74,23,71),{'fill':'#727A62','outline':''}),
    ]
    if state=='loading':
        shapes.append(('line',points(39,48,45,47,49,49),{'fill':TEXT,'width':2.5,'capstyle':'round'}))
    elif state=='error':
        shapes.append(('line',points(38,43,49,46),{'fill':ORANGE,'width':2,'capstyle':'round'}))
        shapes.append(('oval',points(42,47,46,52),{'fill':TEXT,'outline':''}))
    else:
        shapes.append(('oval',points(39,43,49,53),{'fill':TEXT,'outline':''}))
        shapes.append(('oval',points(44,44,48,51),{'fill':GREEN if state=='active' else '#141711','outline':''}))
    return tuple(shapes)

class DragonMascot(tk.Canvas):
    STATES=('ready','active','loading','error')
    def __init__(self,master,state='ready',**options):
        if state not in self.STATES:raise ValueError('Estado de mascota desconocido.')
        super().__init__(master,width=92,height=84,bg=options.pop('bg',PANEL),highlightthickness=0,takefocus=False,**options)
        self.state_name=state;self.stamp=None;self._photos=OrderedDict();self._photo=None
        self._image_id=self.create_image(46,42,anchor='center',tags=('mascot-artwork',))
        self._indicator_id=self.create_oval(0,0,0,0,tags=('mascot-state',))
        self.bind('<Configure>',lambda event:self.draw())
        self.draw()
    def set_state(self,state):
        if state not in self.STATES:raise ValueError('Estado de mascota desconocido.')
        if state!=self.state_name:self.state_name=state;self.draw()
    def draw(self):
        width=self.winfo_width();height=self.winfo_height()
        if width<=1:width=int(self.cget('width'))
        if height<=1:height=int(self.cget('height'))
        stamp=(width,height,self.state_name)
        if stamp==self.stamp:return
        self.stamp=stamp;size=(width,height)
        if size not in self._photos:
            self._photos[size]=ImageTk.PhotoImage(mascot_image(*size),master=self)
            if len(self._photos)>4:self._photos.popitem(last=False)
        self._photos.move_to_end(size);self._photo=self._photos[size]
        self.coords(self._image_id,width/2,height/2)
        self.itemconfig(self._image_id,image=self._photo)
        scale=min(width/92,height/84);radius=3*scale;x=width-8*scale;y=height-8*scale
        self.coords(self._indicator_id,x-radius,y-radius,x+radius,y+radius)
        accent={'ready':MUTED,'active':GREEN,'loading':TEXT,'error':ORANGE}[self.state_name]
        self.itemconfig(self._indicator_id,fill=accent,outline=self.cget('bg'),width=2*scale)
