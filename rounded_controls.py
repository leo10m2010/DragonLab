"""Rounded, keyboard-accessible native controls with event-only rendering."""
import tkinter as tk
from tkinter import font as tkfont
from rounded_widgets import rounded,RoundedButton,RoundedPanel
TEXT='#edf4f1';MUTED='#a4b6b2';GREEN='#72dfba';FIELD='#25383e'

class RoundedChoice(tk.Canvas):
    def __init__(self,master,textvariable=None,values=(),width=18,font=('Bahnschrift',11),state='readonly',**kwargs):
        self.variable=textvariable or tk.StringVar(master);self.values=list(values);self.typeface=font;self.units=width;self.state=state;self.popup=None;self.focused=False
        super().__init__(master,bg=master.cget('bg'),highlightthickness=0,takefocus=True,cursor='hand2',height=38)
        self.configure(width=width,font=font)
        self.trace=self.variable.trace_add('write',lambda *args:self.draw())
        self.bind('<Configure>',lambda e:self.draw());self.bind('<Button-1>',lambda e:self.open())
        self.bind('<Return>',lambda e:self.open());self.bind('<space>',lambda e:self.open());self.bind('<Down>',lambda e:self.open())
        self.bind('<FocusIn>',lambda e:self.focus(True));self.bind('<FocusOut>',lambda e:self.focus(False))
        self.bind('<Destroy>',self.destroyed)
    def destroyed(self,event):
        if event.widget is self:
            self.close(restore=False)
            try:self.variable.trace_remove('write',self.trace)
            except tk.TclError:pass
    def focus(self,on):self.focused=on;self.draw()
    def configure(self,cnf=None,**kwargs):
        if cnf:kwargs.update(cnf)
        for k in ('values','font','state','width'):
            if k in kwargs:
                v=kwargs.pop(k)
                if k=='values':
                    new=list(v)
                    if new!=self.values and self.popup:self.close(restore=False)
                    self.values=new
                elif k=='font':self.typeface=v
                elif k=='width':self.units=v
                else:self.state=v
        super().configure(width=tkfont.Font(self,font=self.typeface).measure('0')*self.units+36,**kwargs)
        self.draw()
    config=configure
    def cget(self,key):
        if key=='values':return tuple(self.values)
        if key=='font':return self.typeface
        if key=='state':return self.state
        return super().cget(key)
    def get(self):return self.variable.get()
    def set(self,value):self.variable.set(value)
    def draw(self):
        if not self.winfo_exists():return
        self.delete('all');w=max(2,self.winfo_width());h=max(2,self.winfo_height())
        rounded(self,1,1,w-2,h-2,18,fill=FIELD,outline=GREEN if self.focused else '')
        text=self.variable.get();font=tkfont.Font(self,font=self.typeface)
        while text and font.measure(text)>w-47:text=text[:-1]
        if text!=self.variable.get():text=text[:-1]+'…'
        self.create_text(14,h/2,text=text,anchor='w',fill=TEXT if self.state!='disabled' else MUTED,font=self.typeface)
        self.create_line(w-24,h/2-2,w-19,h/2+3,w-14,h/2-2,fill=MUTED,width=2)
    def close(self,restore=True):
        if self.popup:
            popup=self.popup;self.popup=None
            try:popup.grab_release();popup.destroy()
            except tk.TclError:pass
            if restore and self.winfo_exists():self.focus_set()
    def open(self):
        if self.state=='disabled' or not self.values:return 'break'
        if self.popup:self.close();return 'break'
        self.active=self.values.index(self.get()) if self.get() in self.values else 0;self.start=max(0,self.active-3)
        win=tk.Toplevel(self);self.popup=win;win.withdraw();win.overrideredirect(True);win.configure(bg='#010203')
        try:win.wm_attributes('-transparentcolor','#010203')
        except tk.TclError:pass
        win.transient(self.winfo_toplevel());width=max(self.winfo_width(),150);self.row_height=36;self.visible_count=min(7,len(self.values))
        height=self.visible_count*self.row_height+16
        x=min(self.winfo_rootx(),self.winfo_screenwidth()-width-8);y=self.winfo_rooty()+self.winfo_height()+5
        if y+height>self.winfo_screenheight()-35:y=max(8,self.winfo_rooty()-height-5)
        win.geometry(f'{width}x{height}+{max(8,x)}+{y}')
        canvas=tk.Canvas(win,bg='#010203',highlightthickness=0);canvas.pack(fill='both',expand=True);self.menu_canvas=canvas;self.menu_width=width
        win.bind('<Escape>',lambda e:self.close());win.bind('<Down>',lambda e:self.move(1));win.bind('<Up>',lambda e:self.move(-1));win.bind('<Return>',lambda e:self.choose())
        win.bind('<Home>',lambda e:self.move(-len(self.values)));win.bind('<End>',lambda e:self.move(len(self.values)))
        win.bind('<MouseWheel>',lambda e:self.move(-1 if e.delta>0 else 1))
        canvas.bind('<Motion>',self.hover);canvas.bind('<ButtonRelease-1>',self.clicked)
        def outside(event):
            if not x<=event.x_root<x+width or not y<=event.y_root<y+height:self.close()
        win.bind('<Button-1>',outside,add='+')
        def lost(event):
            def check():
                if self.popup is win:
                    focus=win.focus_get()
                    if focus is None or focus.winfo_toplevel()!=win:self.close(restore=False)
            win.after_idle(check)
        win.bind('<FocusOut>',lost);self.render_menu();win.deiconify();win.grab_set();win.focus_set();return 'break'
    def render_menu(self):
        c=self.menu_canvas;c.delete('all');height=self.visible_count*self.row_height+16;w=self.menu_width
        self.start=max(0,min(self.start,len(self.values)-self.visible_count))
        rounded(c,0,0,w,height,18,fill='#17282e',outline='#3b555c')
        for row,index in enumerate(range(self.start,self.start+self.visible_count)):
            y=8+row*self.row_height
            if index==self.active:rounded(c,6,y,w-12,self.row_height,14,fill='#2b454b',outline='')
            value=str(self.values[index]);font=tkfont.Font(self,font=self.typeface)
            while value and font.measure(value)>w-44:value=value[:-1]
            if value!=str(self.values[index]):value=value[:-1]+'…'
            c.create_text(16,y+self.row_height/2,text=value,anchor='w',fill=GREEN if self.values[index]==self.get() else TEXT,font=self.typeface)
        if len(self.values)>self.visible_count:
            thumb=max(12,(height-24)*self.visible_count/len(self.values));offset=(height-24-thumb)*self.start/max(1,len(self.values)-self.visible_count)
            rounded(c,w-7,12+offset,3,thumb,2,fill=MUTED,outline='')
    def move(self,delta):
        self.active=max(0,min(len(self.values)-1,self.active+delta))
        if self.active<self.start:self.start=self.active
        if self.active>=self.start+self.visible_count:self.start=self.active-self.visible_count+1
        self.render_menu();return 'break'
    def hover(self,event):
        row=int((event.y-8)/self.row_height)
        if 8<=event.y<8+self.visible_count*self.row_height:
            index=self.start+row
            if index!=self.active:self.active=index;self.render_menu()
    def clicked(self,event):
        if 8<=event.y<8+self.visible_count*self.row_height:self.active=self.start+int((event.y-8)/self.row_height);self.choose()
    def choose(self):
        if not 0<=self.active<len(self.values):self.close();return 'break'
        self.variable.set(self.values[self.active]);self.close();self.event_generate('<<ComboboxSelected>>');return 'break'

class RoundedSwitch(tk.Canvas):
    def __init__(self,master,text='',variable=None,font=('Bahnschrift',12),**kwargs):
        self.variable=variable or tk.BooleanVar(master);self.text=text;self.typeface=font;self.focused=False
        super().__init__(master,bg=master.cget('bg'),height=34,width=tkfont.Font(master,font=font).measure(text)+64,highlightthickness=0,takefocus=True,cursor='hand2')
        self.trace=self.variable.trace_add('write',lambda *a:self.draw())
        self.bind('<Configure>',lambda e:self.draw());self.bind('<ButtonRelease-1>',lambda e:self.toggle());self.bind('<space>',lambda e:self.toggle());self.bind('<Return>',lambda e:self.toggle())
        self.bind('<FocusIn>',lambda e:self.focus(True));self.bind('<FocusOut>',lambda e:self.focus(False));self.bind('<Destroy>',self.destroyed)
    def destroyed(self,e):
        if e.widget is self:
            try:self.variable.trace_remove('write',self.trace)
            except tk.TclError:pass
    def focus(self,on):self.focused=on;self.draw()
    def toggle(self):self.variable.set(not self.variable.get());return 'break'
    def draw(self):
        self.delete('all');on=self.variable.get()
        rounded(self,2,5,42,24,12,fill=GREEN if on else '#3b5057',outline=TEXT if self.focused else '')
        x=31 if on else 15;self.create_oval(x-8,9,x+8,25,fill='#11191c' if on else TEXT,outline='')
        self.create_text(56,17,text=self.text,anchor='w',fill=TEXT,font=self.typeface)

class RoundedEntry(RoundedPanel):
    def __init__(self,master,textvariable=None,width=15,**kwargs):
        color=kwargs.pop('bg',FIELD);super().__init__(master,color,radius=16,padding=8)
        kwargs.pop('relief',None);kwargs.pop('highlightthickness',None)
        self.entry=tk.Entry(self.body,textvariable=textvariable,width=width,bg=color,fg=kwargs.pop('fg',TEXT),insertbackground=kwargs.pop('insertbackground',TEXT),relief='flat',highlightthickness=0,**kwargs)
        self.entry.pack(fill='x',padx=4,pady=2)
    def insert(self,*a):return self.entry.insert(*a)
    def get(self):return self.entry.get()
    def select_range(self,*a):return self.entry.select_range(*a)

class RoundedText(RoundedPanel):
    def __init__(self,master,**kwargs):
        color=kwargs.pop('bg',FIELD);super().__init__(master,color,radius=20,padding=12)
        kwargs.pop('relief',None);kwargs.pop('highlightthickness',None);kwargs.pop('borderwidth',None);kwargs.pop('bd',None)
        self.text=tk.Text(self.body,bg=color,relief='flat',highlightthickness=0,borderwidth=0,**kwargs);self.text.pack(fill='both',expand=True,padx=3,pady=3)
    def insert(self,*a):return self.text.insert(*a)
    def get(self,*a):return self.text.get(*a)
    def delete(self,*a):return self.text.delete(*a)

class RoundedScroll(tk.Canvas):
    def __init__(self,master,orient='vertical',command=None):
        self.command=command;self.first=0;self.last=1
        super().__init__(master,bg=master.cget('bg'),width=12,highlightthickness=0,takefocus=False)
        self.bind('<Configure>',lambda e:self.draw());self.bind('<Button-1>',self.move);self.bind('<B1-Motion>',self.move)
    def set(self,first,last):self.first=float(first);self.last=float(last);self.draw()
    def draw(self):
        self.delete('all');h=self.winfo_height()
        if self.last-self.first<.999:rounded(self,4,max(3,h*self.first),4,max(18,h*(self.last-self.first)-6),2,fill='#607b82',outline='')
    def move(self,event):
        if self.command:self.command('moveto',max(0,min(1,event.y/max(1,self.winfo_height())-(self.last-self.first)/2)))

class RoundedTabs(tk.Frame):
    def __init__(self,master,**kwargs):
        super().__init__(master,bg=master.cget('bg'));self.buttons=[];self.pages=[];self.current=None
        self.header=tk.Frame(self,bg=self.cget('bg'));self.header.pack(fill='x',pady=(0,10))
        self.surface=tk.Canvas(self,bg=self.cget('bg'),highlightthickness=0);self.surface.pack(fill='both',expand=True)
        self.content=tk.Frame(self.surface,bg='#1a262b');self.content_id=self.surface.create_window(12,12,window=self.content,anchor='nw')
        self.surface.bind('<Configure>',self.resize)
    def resize(self,event=None):
        w=max(25,self.surface.winfo_width());h=max(25,self.surface.winfo_height());color=self.pages[self.current].cget('bg') if self.current is not None else '#1a262b'
        self.content.configure(bg=color);self.surface.itemconfigure(self.content_id,width=w-24,height=h-24)
        stamp=(w,h,color)
        if getattr(self,'shape_stamp',None)!=stamp:
            self.shape_stamp=stamp;self.surface.delete('shape');rounded(self.surface,0,0,w,h,22,fill=color,outline='',tags='shape');self.surface.tag_lower('shape')
    def add(self,page,text=''):
        index=len(self.pages);self.pages.append(page)
        button=RoundedButton(self.header,text=text,command=lambda:self.select(index),font=('Bahnschrift',10),padx=12,pady=7)
        button.pack(side='left',padx=(0,6));self.buttons.append(button)
        if self.current is None:self.select(index)
    def select(self,index):
        if self.current is not None:self.pages[self.current].pack_forget();self.buttons[self.current].config(bg=FIELD,fg=TEXT)
        self.current=index;self.pages[index].pack(in_=self.content,fill='both',expand=True);self.buttons[index].config(bg=GREEN,fg='#11191c')
        self.resize()

class RoundedTable(tk.Frame):
    """Scrollable rounded rows with Treeview's small API used by the tools."""
    def __init__(self,master,columns=(),show=None,height=12,**kwargs):
        super().__init__(master,bg=master.cget('bg'));self.columns=columns;self.rows={};self.order=[];self.selected=();self.labels={}
        self.head=tk.Frame(self,bg=self.cget('bg'));self.head.pack(fill='x')
        self.viewport=tk.Canvas(self,bg=self.cget('bg'),highlightthickness=0,height=min(270,height*28));self.viewport.pack(side='left',fill='both',expand=True)
        scroll=RoundedScroll(self,command=self.viewport.yview);scroll.pack(side='right',fill='y');self.viewport.configure(yscrollcommand=scroll.set)
        self.content=tk.Frame(self.viewport,bg=self.cget('bg'));self.item_id=self.viewport.create_window(0,0,window=self.content,anchor='nw')
        self.viewport.bind('<Configure>',lambda e:self.viewport.itemconfigure(self.item_id,width=e.width))
        self.content.bind('<Configure>',lambda e:self.viewport.configure(scrollregion=self.viewport.bbox('all')))
        self.bind('<MouseWheel>',lambda e:self.viewport.yview_scroll(-int(e.delta/120),'units'))
    def heading(self,key,text=''):
        label=tk.Label(self.head,text=text,bg=self.cget('bg'),fg=MUTED,font=('Bahnschrift',10),anchor='w');label.pack(side='left',fill='x',expand=True,padx=10,pady=8)
        self.labels[key]=label
    def column(self,*args,**kwargs):pass
    def exists(self,iid):return iid in self.rows
    def item(self,iid,values=()):
        row=self.rows[iid];row.config(text='  ·  '.join(str(v) for v in values))
    def insert(self,parent,index,iid=None,values=()):
        iid=iid if iid is not None else str(len(self.order));self.order.append(iid)
        row=RoundedButton(self.content,text='  ·  '.join(str(v) for v in values),command=lambda:self.choose(iid),font=('Bahnschrift',10),pady=7,padx=12,bg=FIELD)
        row.pack(fill='x',pady=3,padx=2);row.bind('<MouseWheel>',lambda e:self.viewport.yview_scroll(-int(e.delta/120),'units'));self.rows[iid]=row;return iid
    def choose(self,iid):
        for key in self.selected:
            if key in self.rows:self.rows[key].config(bg=FIELD,fg=TEXT)
        self.selected=(iid,);self.rows[iid].config(bg='#37544e',fg=GREEN)
    def selection(self):return self.selected
    def get_children(self):return tuple(self.order)
    def delete(self,*ids):
        for iid in ids:
            if iid in self.rows:self.rows.pop(iid).destroy();self.order.remove(iid)
        self.selected=tuple(i for i in self.selected if i in self.rows)
