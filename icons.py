"""Tabler Icons shared by DragonLab's native controls.

All icons use the official Tabler outline family at the control's size.
Original upstream PNGs are bundled locally; no font or network is needed.
"""
import tkinter as tk
from tkinter import font as tkfont
from rounded_widgets import RoundedButton,rounded
from theme import BG,FIELD,TEXT,MUTED,GREEN,LINE,DISABLED

ICON_NAMES=frozenset(('play','pause','stop','game','catalog','settings','shortcuts',
    'help','performance','support','account','update','external','logout',
    'minimize','maximize','restore','close','chevron_down','check'))

# Exact upstream Tabler PNG assets, pinned in assets/icons/tabler/SOURCE.json.
from pathlib import Path
from functools import lru_cache
from collections import OrderedDict
from PIL import Image,ImageTk,ImageColor
ICON_DIRECTORY=Path(__file__).resolve().parent/'assets'/'icons'/'tabler'

@lru_cache(maxsize=128)
def icon_pixels(name,size,color):
    if name not in ICON_NAMES:raise ValueError('Icono desconocido: '+str(name))
    with Image.open(ICON_DIRECTORY/(name+'.png')) as source:
        alpha=source.convert('RGBA').getchannel('A').resize((size,size),Image.Resampling.LANCZOS)
    image=Image.new('RGBA',(size,size),ImageColor.getcolor(color,'RGBA'));image.putalpha(alpha)
    return image

def draw_icon(canvas,name,x,y,size=16,color=TEXT,stroke=1.5,tags=()):
    size=max(1,round(size));key=(name,size,color)
    photos=getattr(canvas,'_tabler_photos',None)
    if photos is None:photos=canvas._tabler_photos=OrderedDict()
    if key not in photos:
        photos[key]=ImageTk.PhotoImage(icon_pixels(*key),master=canvas)
        if len(photos)>12:photos.popitem(last=False)
    photos.move_to_end(key)
    return canvas.create_image(x,y,image=photos[key],anchor='nw',tags=tags)

class Icon(tk.Canvas):
    def __init__(self,master,name,size=16,color=MUTED,**options):
        if name not in ICON_NAMES:raise ValueError('Icono desconocido: '+str(name))
        self.icon_name=name;self.icon_size=size;self.icon_color=color
        super().__init__(master,width=size,height=size,bg=options.pop('bg',master.cget('bg')),highlightthickness=0,takefocus=False,**options)
        draw_icon(self,name,0,0,size,color)

class IconButton(RoundedButton):
    """The existing functional button contract, with an optional leading icon."""
    def __init__(self,master,icon=None,icon_size=16,**options):
        if icon is not None and icon not in ICON_NAMES:raise ValueError('Icono desconocido: '+str(icon))
        self.icon_name=icon;self.icon_size=icon_size;self.icon_gap=8
        super().__init__(master,**options)
    def configure(self,cnf=None,**options):
        if cnf:options.update(cnf)
        if 'icon' in options:
            value=options.pop('icon')
            if value is not None and value not in ICON_NAMES:raise ValueError('Icono desconocido: '+str(value))
            self.icon_name=value
        result=super().configure(**options)
        o=self.options;font=tkfont.Font(self,font=o['font'])
        width=font.measure(o['text'])+o['padx']*2+4
        if self.icon_name:width+=self.icon_size+(self.icon_gap if o['text'] else 0)
        tk.Canvas.configure(self,width=width)
        self.draw();return result
    config=configure
    def cget(self,key):
        if key=='icon':return self.icon_name
        return super().cget(key)
    def draw(self):
        if not hasattr(self,'options'):return
        o=self.options;w=max(1,self.winfo_width());h=max(1,self.winfo_height())
        stamp=(w,h,o['text'],str(o['font']),o['bg'],o['fg'],o['activebackground'],o['activeforeground'],o['state'],o['disabledbackground'],o['disabledforeground'],o['focuscolor'],self.icon_name,self.icon_size,self.hover,self.focused)
        if getattr(self,'draw_stamp',None)==stamp:return
        self.draw_stamp=stamp;self.delete('all')
        bg=o['activebackground'] if self.hover else o['bg'];fg=o['activeforeground'] if self.hover else o['fg']
        if o['state']=='disabled':bg=o['disabledbackground'] or o['bg'];fg=o['disabledforeground']
        rounded(self,1,1,w-2,h-2,9,fill=bg,outline=o['focuscolor'] if self.focused else '',width=1)
        font=tkfont.Font(self,font=o['font']);text_width=font.measure(o['text'])
        total=text_width+(self.icon_size+(self.icon_gap if o['text'] else 0) if self.icon_name else 0)
        left=(w-total)/2
        if self.icon_name:
            draw_icon(self,self.icon_name,left,(h-self.icon_size)/2,self.icon_size,fg)
            left+=self.icon_size+(self.icon_gap if o['text'] else 0)
        if o['text']:self.create_text(left,h/2,text=o['text'],anchor='w',font=o['font'],fill=fg)
