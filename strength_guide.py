"""Original force scale and click-through guide aligned to a game's power bar."""
import tkinter as tk
import ctypes,os,math

GREEN='#72dfba';ORANGE='#ffb86c';BG='#101c26';MUTED='#96acb9'

def draw_force(canvas,result,maximum=400,current=None):
    canvas.delete('all');w=max(120,canvas.winfo_width());left,right=18,w-18;y=28
    canvas.create_line(left,y,right,y,fill='#294353',width=11)
    for i in range(5):
        x=left+(right-left)*i/4;canvas.create_line(x,y-8,x,y+8,fill='#708591')
        canvas.create_text(x,y+21,text=f'{maximum*i/4:g}',fill=MUTED,font=('Consolas',9))
    if result.get('reachable'):
        power=result['power'];fraction=max(0,min(1,power/maximum));x=left+(right-left)*fraction
        canvas.create_line(left,y,x,y,fill=GREEN,width=9)
        canvas.create_line(x,y-15,x,y+13,fill=ORANGE,width=3)
        canvas.create_polygon(x-5,y-17,x+5,y-17,x,y-10,fill=ORANGE)
        label=f'SUELTA AQUÍ · {power:g} / {maximum:g} · {fraction*100:.1f}%'
        label_x=max(150,min(w-150,x));canvas.create_text(label_x,9,text=label,fill=ORANGE,font=('Consolas',10,'bold'))
    else:canvas.create_text(w/2,9,text='SIN POTENCIA VÁLIDA',fill=MUTED,font=('Consolas',10))
    if current is not None and isinstance(current,(int,float)) and math.isfinite(current) and 0<=current<=maximum:
        x=left+(right-left)*current/maximum;canvas.create_oval(x-4,y-4,x+4,y+4,fill='white',outline=BG)

def clickthrough(win):
    if os.name!='nt':return
    user=ctypes.windll.user32;user.GetParent.restype=ctypes.c_void_p
    hwnd=user.GetParent(win.winfo_id());user.GetWindowLongW.argtypes=[ctypes.c_void_p,ctypes.c_int]
    user.SetWindowLongW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_long]
    user.SetWindowLongW(hwnd,-20,user.GetWindowLongW(hwnd,-20)|0x20|0x80000|0x08000000)

class PowerGuide:
    def __init__(self,root,start,end):
        self.win=tk.Toplevel(root);self.win.withdraw();self.win.overrideredirect(True)
        self.win.attributes('-topmost',True);self.win.configure(bg='#010203')
        self.win.wm_attributes('-transparentcolor','#010203')
        self.canvas=tk.Canvas(self.win,bg='#010203',highlightthickness=0);self.canvas.pack(fill='both',expand=True)
        self.items=[self.canvas.create_line(0,0,0,0,fill=GREEN,width=2),self.canvas.create_line(0,0,0,0,fill=ORANGE,width=3),self.canvas.create_polygon(0,0,0,0,0,0,fill=ORANGE),self.canvas.create_text(0,0,text='',fill=ORANGE,font=('Bahnschrift',13,'bold'))]
        self.last_draw=None;self.points=None;self.update_position(start,end)
        self.win.update_idletasks();clickthrough(self.win)
        if os.name=='nt':
            # Disabled transparent guide can paint, but cannot take keyboard focus.
            self.win.wm_attributes('-disabled',True)
        self.win.deiconify()
    def update_position(self,start,end):
        points=(tuple(start),tuple(end))
        if points==self.points:return
        self.points=points;self.start,self.end=points
        self.x=min(start[0],end[0])-16;self.y=min(start[1],end[1])-45
        width=max(320,abs(end[0]-start[0])+32);height=max(65,abs(end[1]-start[1])+65)
        self.win.geometry(f'{width}x{height}{self.x:+d}{self.y:+d}');self.last_draw=None
    def draw(self,result,maximum):
        power=result.get('power') if result.get('reachable') else None
        key=(power,maximum,self.points)
        if key==self.last_draw:return
        self.last_draw=key;c=self.canvas
        if power is None:
            for item in self.items:c.itemconfigure(item,state='hidden')
            return
        a=[self.start[0]-self.x,self.start[1]-self.y];b=[self.end[0]-self.x,self.end[1]-self.y]
        fraction=max(0,min(1,power/maximum));px=a[0]+(b[0]-a[0])*fraction;py=a[1]+(b[1]-a[1])*fraction
        for item in self.items:c.itemconfigure(item,state='normal')
        c.coords(self.items[0],*a,*b);c.coords(self.items[1],px,py-22,px,py+12)
        c.coords(self.items[2],px-7,py-24,px+7,py-24,px,py-15)
        c.coords(self.items[3],(a[0]+b[0])/2,min(a[1],b[1])-35)
        c.itemconfigure(self.items[3],text=f'SUELTA EN {power:g} / {maximum:g} · {fraction*100:.1f}%')
    def close(self):self.win.destroy()

def select_game_bar(app):
    app.hide_power_guide();app.root.withdraw()
    def select():
        win=tk.Toplevel(app.root);win.overrideredirect(True);win.attributes('-topmost',True);win.attributes('-alpha',.55)
        if os.name=='nt':
            u=ctypes.windll.user32;x,y,w,h=[u.GetSystemMetrics(k) for k in (76,77,78,79)]
        else:x,y,w,h=0,0,win.winfo_screenwidth(),win.winfo_screenheight()
        win.geometry(f'{w}x{h}{x:+d}{y:+d}');cv=tk.Canvas(win,bg='black',highlightthickness=0,cursor='crosshair');cv.pack(fill='both',expand=True)
        prompt=cv.create_text(35,35,anchor='nw',text='Haz clic en el inicio de la barra (0). Después en el final (400). Esc cancela.',fill='white',font=('Bahnschrift',19));points=[]
        def cancel(e=None):win.destroy();app.root.deiconify()
        def click(e):
            points.append((e.x_root,e.y_root));cv.create_oval(e.x-6,e.y-6,e.x+6,e.y+6,outline=ORANGE,width=3)
            if len(points)==1:cv.itemconfigure(prompt,text=f'Ahora haz clic en el final de la barra ({app.s.max_power:g}).')
            else:
                if math.dist(points[0],points[1])<30:points.pop();cv.itemconfigure(prompt,text='Los extremos deben estar separados al menos 30 píxeles. Marca el final.');return
                app.guide_points=points[:];win.destroy();app.root.deiconify();app.toggle_power_guide()
        cv.bind('<Button-1>',click);win.bind('<Escape>',cancel)
    app.root.after(200,select)
