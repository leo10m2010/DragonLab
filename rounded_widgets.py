"""Rounded native canvases, redrawn only when their appearance changes."""
import tkinter as tk,math
from tkinter import font as tkfont

def rounded(canvas,x,y,w,h,r,**options):
    r=min(r,w/2,h/2)
    points=[]
    for cx,cy,start in ((x+w-r,y+r,-90),(x+w-r,y+h-r,0),(x+r,y+h-r,90),(x+r,y+r,180)):
        for i in range(9):
            angle=math.radians(start+i*90/8);points.extend((cx+r*math.cos(angle),cy+r*math.sin(angle)))
    return canvas.create_polygon(*points,smooth=True,splinesteps=8,**options)

def mask_corners(canvas,color,radius=20):
    w=canvas.winfo_width();h=canvas.winfo_height();r=min(radius,w/2,h/2)
    base=[(0,0),(r,0)]+[(r+r*math.cos(math.radians(-90-i*90/16)),r+r*math.sin(math.radians(-90-i*90/16))) for i in range(1,17)]
    for flip_x,flip_y in ((False,False),(True,False),(False,True),(True,True)):
        points=[v for x,y in base for v in (w-x if flip_x else x,h-y if flip_y else y)]
        canvas.create_polygon(*points,fill=color,outline='')

class RoundedPanel(tk.Frame):
    def __init__(self,master,color,radius=22,padding=8):
        super().__init__(master,bg=master.cget('bg'))
        self.color=color;self.radius=radius;self.padding=padding
        self.surface=tk.Canvas(self,bg=self.cget('bg'),highlightthickness=0,height=1)
        self.surface.pack(fill='both',expand=True)
        self.body=tk.Frame(self.surface,bg=color)
        self.item=self.surface.create_window(padding,padding,window=self.body,anchor='nw')
        self.body.bind('<Configure>',self.resize)
        self.surface.bind('<Configure>',self.resize)
    def resize(self,event=None):
        p=self.padding;w=max(1,self.surface.winfo_width());h=self.body.winfo_reqheight()+p*2
        if int(float(self.surface.cget('height')))!=h:self.surface.configure(height=h)
        self.surface.itemconfigure(self.item,width=max(1,w-2*p))
        stamp=(w,h,self.radius,self.color)
        if getattr(self,'shape_stamp',None)!=stamp:
            self.shape_stamp=stamp;self.surface.delete('shape')
            rounded(self.surface,0,0,w,h,self.radius,fill=self.color,outline='',tags='shape')
            self.surface.tag_lower('shape')

class RoundedButton(tk.Canvas):
    def __init__(self,master,text='',command=None,**options):
        self.options={'text':text,'command':command,'bg':'#233b4b','fg':'#edf4f1','activebackground':'#305368','activeforeground':'#72dfba','font':('Bahnschrift',10),'padx':14,'pady':10,'state':'normal','takefocus':True}
        self.options.update({'disabledbackground':None,'disabledforeground':'#718a91','focuscolor':'#72dfba'})
        self.options.update(options);self.hover=False;self.focused=False;self.pressed=False
        super().__init__(master,bg=master.cget('bg'),highlightthickness=0,cursor='hand2',takefocus=self.options['takefocus'])
        self.bind('<Configure>',lambda e:self.draw())
        self.bind('<Enter>',lambda e:self.set_hover(True));self.bind('<Leave>',lambda e:self.set_hover(False))
        self.bind('<ButtonPress-1>',self.press);self.bind('<ButtonRelease-1>',self.click)
        self.bind('<FocusIn>',lambda e:self.focus(True));self.bind('<FocusOut>',lambda e:self.focus(False))
        self.bind('<space>',self.key_activate);self.bind('<Return>',self.key_activate)
        self.configure(**self.options)
    def configure(self,cnf=None,**kw):
        if cnf:kw.update(cnf)
        native={k:v for k,v in kw.items() if k not in self.options and k not in ('relief','highlightbackground','highlightcolor')}
        self.options.update({k:v for k,v in kw.items() if k in self.options})
        if self.options['state']=='disabled':self.pressed=False
        if native:super().configure(**native)
        super().configure(takefocus=self.options['takefocus'] if self.options['state']!='disabled' else False)
        font=tkfont.Font(self,font=self.options['font'])
        width=font.measure(self.options['text'])+self.options['padx']*2+4
        height=font.metrics('linespace')+self.options['pady']*2+4
        super().configure(width=width,height=height);self.draw()
    config=configure
    def cget(self,key):
        return self.options[key] if key in self.options else super().cget(key)
    def set_hover(self,on):self.hover=on;self.draw()
    def focus(self,on):self.focused=on;self.draw()
    def draw(self):
        o=self.options;w=max(1,self.winfo_width());h=max(1,self.winfo_height())
        stamp=(w,h,o['text'],str(o['font']),o['bg'],o['fg'],o['activebackground'],o['activeforeground'],o['state'],o['disabledbackground'],o['disabledforeground'],o['focuscolor'],self.hover,self.focused)
        if getattr(self,'draw_stamp',None)==stamp:return
        self.draw_stamp=stamp;self.delete('all')
        bg=o['activebackground'] if self.hover else o['bg'];fg=o['activeforeground'] if self.hover else o['fg']
        if o['state']=='disabled':bg=o['disabledbackground'] or o['bg'];fg=o['disabledforeground']
        rounded(self,1,1,w-2,h-2,20,fill=bg,outline=o['focuscolor'] if self.focused else '',width=1)
        self.create_text(w/2,h/2,text=o['text'],font=o['font'],fill=fg)
    def press(self,event):
        self.pressed=self.options['state']!='disabled'
        if self.pressed:self.focus_set()
        return 'break'
    def click(self,event):
        pressed=self.pressed;self.pressed=False
        if pressed and 0<=event.x<self.winfo_width() and 0<=event.y<self.winfo_height():self.invoke()
        return 'break'
    def key_activate(self,event=None):
        self.invoke();return 'break'
    def invoke(self):
        if self.options['state']!='disabled' and self.options['command']:return self.options['command']()

class RoundedProgress(tk.Canvas):
    """A percentage with explicit bounds; redraw only when size/value changes."""
    def __init__(self,master,**kwargs):
        self.value=0
        super().__init__(master,bg=master.cget('bg'),height=10,highlightthickness=0,**kwargs)
        self.bind('<Configure>',lambda e:self.draw())
    def set(self,value):
        value=max(0,min(100,float(value)))
        if value!=self.value:self.value=value;self.draw()
    def draw(self):
        w=max(2,self.winfo_width());h=max(2,self.winfo_height());stamp=(w,h,self.value)
        if getattr(self,'stamp',None)==stamp:return
        self.stamp=stamp;self.delete('all');rounded(self,0,0,w,h,h/2,fill='#2b4147',outline='')
        if self.value:rounded(self,0,0,max(2,w*self.value/100),h,h/2,fill='#72dfba',outline='')
