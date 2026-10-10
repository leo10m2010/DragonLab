import tkinter as tk
from tkinter import ttk,filedialog,messagebox
import math,json,pathlib,threading,queue,time,sys,os,socket,secrets,webbrowser,ctypes
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
from dataclasses import asdict
from core import Settings,PROFILES,REVERSE,solve,calibrated_profile,launch
from cdp import CDP
from adapters import AdapterClient,built_in_profiles
from PIL import Image,ImageTk,ImageGrab
from strength_guide import draw_force,PowerGuide,select_game_bar
from trajectories import TrajectoryOverlay,ObservedTrails
from projection import project,unproject
from calibration_book import CalibrationBook,mobile_name

BASE=pathlib.Path(sys.executable).parent if getattr(sys,'frozen',False) else pathlib.Path(__file__).parent
ASSETS=pathlib.Path(getattr(sys,'_MEIPASS',BASE))
BG='#101c26'; PANEL='#162735'; TEXT='#ecf3f7'; MUTED='#96acb9'; GREEN='#72dfba'; ORANGE='#ffb86c'

class App:
    def __init__(self,root):
        self.root=root;root.title('DragonLab · Laboratorio de trayectorias');root.geometry('1080x760');root.minsize(900,640);root.configure(bg=BG)
        self.s=Settings();self.vars={};self.image=None;self.photo=None;self.mode='target';self.result={};self.overlay=None
        self.screen_box=None;self.events=queue.Queue();self.live_stop=threading.Event();self.worker=None;self.live_players=[];self.last_live=0;self.live_camera=None
        self.profiles={};self.server=None;self.share_token=secrets.token_urlsafe(24);self.shared={};self.dirty=True;self.last_input='';self.selected_target=None;self.target_ids={}
        self.base=BASE;self.clone_id='dragonbound';self.adapter_config=None;self.browser_target=None;self.viewport=(800,600);self.last_fingerprint=None;self.last_computed=0;self.compute_generation=0;self.computing=False;self.direction='Auto'
        self.power_guide=None;self.guide_points=None;self.current_game_power=None;self.auto_visible=False;self.auto_enabled=True;self.auto_points=None;self.auto_guide_enabled=True;self.auto_target_id=None;self.target_hero_id=None
        self.preferences_path=BASE/'preferencias.json'
        self.book=CalibrationBook(BASE/'calibraciones.json');self.trails=ObservedTrails();self.observed_paths={};self.game_visible=False;self.has_position_data=False;self.live_look=None;self.profile_stamp=None;self.live_launch_offset=None
        try:
            prefs=json.loads(self.preferences_path.read_text(encoding='utf-8'));self.clone_id=prefs.get('clone','dragonbound');self.adapter_config=prefs.get('adapter')
            self.viewport=tuple(prefs.get('viewport',[800,600]))
        except (OSError,ValueError,TypeError):pass
        if os.name=='nt':
            try:ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except:pass
        style=ttk.Style();style.theme_use('clam')
        style.configure('TCombobox',fieldbackground=PANEL,background=PANEL,foreground=TEXT,arrowcolor=GREEN)
        style.map('TCombobox',fieldbackground=[('readonly',PANEL)],foreground=[('readonly',TEXT)],selectbackground=[('readonly',PANEL)],selectforeground=[('readonly',TEXT)])
        self.mobile=tk.StringVar(value='ARMOR');self.weather=tk.StringVar(value='Normal');self.muzzle=tk.BooleanVar(value=True)
        for key,value in [('angle',46),('wind',0),('wind_angle',90),('body_angle',0),('gravity',73.5),('wind_scale',.74),('power_scale',1)]:
            var=tk.StringVar(value=str(value));var.trace_add('write',lambda *args:self.mark());self.vars[key]=var
        self.endpoint=tk.StringVar(value='http://127.0.0.1:9222')
        self.weather.trace_add('write',lambda *args:self.mark())
        header=tk.Frame(root,bg=BG);header.pack(fill='x',padx=24,pady=(18,12))
        tk.Label(header,text='DRAGON / LAB',font=('Bahnschrift',25,'bold'),fg=TEXT,bg=BG).pack(side='left')
        self.status=tk.Label(header,text='BUSCANDO JUEGO',font=('Consolas',10),fg=ORANGE,bg=BG);self.status.pack(side='left',padx=20)
        self.button(header,'Ajustes',self.open_settings).pack(side='right')
        self.connect=self.button(header,'Pausar captura',self.toggle_live);self.connect.pack(side='right',padx=8)
        self.button(header,'Abrir juego',self.open_game_browser).pack(side='right')
        controls=tk.Frame(root,bg=PANEL);controls.pack(fill='x',padx=24,pady=(0,12))
        self.vehicle_label=tk.Label(controls,text='VEHÍCULO AUTOMÁTICO',bg=PANEL,fg=TEXT,font=('Bahnschrift',12));self.vehicle_label.pack(side='left',padx=14,pady=12)
        self.trajectory_enabled=tk.BooleanVar(value=True);self.guide_enabled=tk.BooleanVar(value=True)
        for label,var,cmd in [('Trayectorias',self.trajectory_enabled,self.refresh_visibility),('Marca de fuerza',self.guide_enabled,self.refresh_visibility)]:
            tk.Checkbutton(controls,text=label,variable=var,command=cmd,bg=PANEL,fg=TEXT,selectcolor=BG,activebackground=PANEL,activeforeground=GREEN,font=('Bahnschrift',11)).pack(side='left',padx=6)
        self.target_name=tk.StringVar(value='Objetivo automático');self.target_box=ttk.Combobox(controls,textvariable=self.target_name,values=['Objetivo automático'],state='readonly',width=21);self.target_box.pack(side='right',padx=14);self.target_box.bind('<<ComboboxSelected>>',lambda e:self.select_target())
        self.canvas=tk.Canvas(root,bg='#0c151d',highlightthickness=1,highlightbackground='#294353');self.canvas.pack(fill='both',expand=True,padx=24);self.canvas.bind('<Button-1>',self.click);self.canvas.bind('<Configure>',lambda e:self.draw())
        summary=tk.Frame(root,bg=PANEL);summary.pack(fill='x',padx=24,pady=(12,0))
        self.power=tk.Label(summary,text='—',font=('Bahnschrift',44,'bold'),bg=PANEL,fg=GREEN);self.power.pack(side='left',padx=20,pady=4)
        self.details=tk.Label(summary,text='Entra a una partida para ver la guía',font=('Bahnschrift',12),bg=PANEL,fg=TEXT,justify='left');self.details.pack(side='left',padx=4)
        self.force_canvas=tk.Canvas(summary,width=350,height=64,bg=PANEL,highlightthickness=0);self.force_canvas.pack(side='right',fill='x',expand=True,padx=18);self.force_canvas.bind('<Configure>',lambda e:self.draw_force())
        self.footer=tk.Label(root,text='Verde: trayectoria prevista · Azul: recorrido observado · Naranja: fuerza',bg=BG,fg=MUTED,font=('Bahnschrift',10),anchor='w');self.footer.pack(fill='x',padx=24,pady=(9,14))
        self.root.protocol('WM_DELETE_WINDOW',self.close)
        root.bind('<Control-s>',lambda e:self.save_session());root.bind('<Escape>',lambda e:(self.hide_overlay(),self.hide_power_guide()))
        self.profile_path=BASE/'perfiles.json'
        try:self.profiles=json.loads(self.profile_path.read_text(encoding='utf-8'))
        except (OSError,ValueError):pass
        self.change_mobile();self.tick()
        if '--smoke' not in sys.argv and '--no-auto' not in sys.argv and '--check' not in sys.argv:root.after(300,self.toggle_live)

    def open_settings(self):
        from settings_panel import open_settings
        return open_settings(self)
    def apply_measured_profile(self):
        fit=self.book.profile(self.clone_id,self.s.mobile,self.s.selected_shot,self.s.wind)
        observed=self.book.acceleration(self.clone_id,self.s.mobile,self.s.selected_shot,self.s.wind,self.s.wind_angle) if fit else None
        if observed:self.s.environment['observedAcceleration']=observed
        else:self.s.environment.pop('observedAcceleration',None)
        stamp=(self.clone_id,self.s.mobile,self.s.selected_shot,tuple((k,fit.get(k)) for k in ('gravity','power_scale','wind_scale','speed_offset')) if fit else None)
        if stamp==self.profile_stamp:return
        previous=self.profile_stamp;self.profile_stamp=stamp
        if not fit:
            if previous and previous[-1] is not None:
                name=self.s.mobile;g,w,p,*_=PROFILES[name];custom=self.profiles.get(self.profile_key(),{})
                for key,value in [('gravity',g),('wind_scale',w),('power_scale',p)]:
                    value=custom.get(key,value);setattr(self.s,key,value)
                    if float(self.vars[key].get())!=value:self.vars[key].set(str(value))
                self.s.speed_offset=custom.get('speed_offset',0)
            return
        for key in ('gravity','power_scale','wind_scale'):
            value=fit.get(key)
            if value is not None:
                setattr(self.s,key,value)
                if abs(float(self.vars[key].get())-value)>1e-6:self.vars[key].set(str(round(value,6)))
        self.s.speed_offset=fit['speed_offset']
    def heading(self,parent,text):tk.Label(parent,text=text,bg=PANEL,fg=GREEN,font=('Consolas',10,'bold')).pack(anchor='w',padx=16,pady=(15,10))
    def button(self,parent,text,cmd):return tk.Button(parent,text=text,command=cmd,bg='#233b4b',fg=TEXT,activebackground='#305368',activeforeground=GREEN,relief='flat',font=('Bahnschrift',10),padx=9,pady=8,cursor='hand2')
    def field(self,p,label,key,value,row,minimum,maximum):
        tk.Label(p,text=label,bg=PANEL,fg=TEXT,font=('Bahnschrift',10)).grid(row=row,column=0,sticky='w',pady=4)
        v=tk.StringVar(value=str(value));self.vars[key]=v;v.trace_add('write',lambda *a:self.mark())
        tk.Spinbox(p,textvariable=v,from_=minimum,to=maximum,increment=.1 if key in ('power_scale','wind_scale') else 1,width=9,bg=BG,fg=TEXT,insertbackground=TEXT,buttonbackground='#294353',relief='flat').grid(row=row,column=1,sticky='e',padx=(10,0),ipady=4)
        p.columnconfigure(1,weight=1)
    def mark(self):self.dirty=True
    def persist_preferences(self):
        self.preferences_path.write_text(json.dumps({'clone':self.clone_id,'adapter':self.adapter_config,'viewport':self.viewport},indent=2),encoding='utf-8')
    def profile_key(self):return self.clone_id+':'+self.mobile.get()
    def change_mobile(self):
        name=self.mobile.get();g,w,p,*_=PROFILES[name];custom=self.profiles.get(self.profile_key(),self.profiles.get(name,{}) if self.clone_id=='dragonbound' else {})
        if self.clone_id=='gunbound-world':
            g={'MAGE':360,'LIGHTNING':360,'ADUKA':376,'FROG':368,'DRAGON':360}.get(name,392)
            self.s.max_power=100
        else:self.s.max_power=400
        for k,val in [('gravity',g),('wind_scale',w),('power_scale',p)]:self.vars[k].set(str(custom.get(k,val)))
        for key in ('speed_offset','angle_offset','quantize_power','launch_offset'):setattr(self.s,key,custom.get(key,getattr(Settings(),key)))
        self.profile_stamp=None;self.vehicle_label.config(text=name if self.has_position_data else 'Vehículo automático');self.mark()
    def read(self):
        for key,v in self.vars.items():setattr(self.s,key,float(v.get()))
        self.s.mobile=self.mobile.get();self.s.muzzle=self.muzzle.get();self.s.weather=self.weather.get()
        self.s.look=(self.live_look if self.live_look in (0,1) and self.last_live else int(self.s.target_x>=self.s.hero_x)) if self.direction=='Auto' else int(self.direction=='Derecha')
        self.apply_measured_profile()
        if self.last_live and self.live_launch_offset is not None:self.s.launch_offset=self.live_launch_offset
        return self.s
    def transform(self):
        cw=max(1,self.canvas.winfo_width());ch=max(1,self.canvas.winfo_height());vw,vh=self.viewport;scale=min(cw/vw,ch/vh)
        return scale,(cw-vw*scale)/2,(ch-vh*scale)/2
    def projected(self,x,y):return project(x,y,self.live_camera,self.viewport)
    def unprojected(self,x,y):return unproject(x,y,self.live_camera,self.viewport)
    def planned_paths(self):
        if self.result.get('reachable'):return self.result.get('projectile_paths',[self.result.get('path',[])])
        return self.result.get('preview_paths',[])
    def draw(self):
        c=self.canvas;c.delete('all');scale,ox,oy=self.transform();vw,vh=self.viewport
        def xy(x,y):
            x,y=self.projected(x,y);return ox+x*scale,oy+y*scale
        if self.image:
            size=(max(1,round(vw*scale)),max(1,round(vh*scale)))
            self.photo=ImageTk.PhotoImage(self.image.resize(size,Image.Resampling.LANCZOS));c.create_image(ox,oy,image=self.photo,anchor='nw')
        else:
            for x in range(0,vw+1,50):c.create_line(ox+x*scale,oy,ox+x*scale,oy+vh*scale,fill='#1a2b38')
            for y in range(0,vh+1,50):c.create_line(ox,oy+y*scale,ox+vw*scale,oy+y*scale,fill='#1a2b38')
            c.create_text(ox+vw/2*scale,oy+35*scale,text='El mapa aparecerá al comenzar la partida',font=('Consolas',10),fill=MUTED)
        if self.has_position_data and self.trajectory_enabled.get() and self.planned_paths():
            for index,path in enumerate(self.planned_paths()):
                points=[v for p in path for v in xy(*p)]
                if len(points)>=4:c.create_line(*points,fill=GREEN if index==0 else '#559f90',width=2.5 if index==0 else 1.5,dash=(5,4) if self.result.get('approximate') else None)
            if self.result.get('reachable'):
                end=self.result['end'];x,y=xy(*end);c.create_oval(x-5,y-5,x+5,y+5,outline=GREEN,width=2)
        if self.trajectory_enabled.get():
            for path in self.observed_paths.values():
                pts=[v for point in path for v in xy(*point)]
                if len(pts)>=4:c.create_line(*pts,fill='#73bcff',width=2)
        positions=[(self.s.hero_x,self.s.hero_y,'TÚ',GREEN),(self.s.target_x,self.s.target_y,'OBJETIVO',ORANGE)] if self.has_position_data else []
        for x,y,label,color in positions:
            px,py=xy(x,y);c.create_oval(px-7,py-7,px+7,py+7,fill=BG,outline=color,width=2);c.create_line(px-14,py,px+14,py,fill=color);c.create_line(px,py-14,px,py+14,fill=color)
            c.create_text(px,py+23,text=f'{label} · {round(x)}, {round(y)}',fill=color,font=('Consolas',10))
    def set_mode(self,mode):self.has_position_data=True;self.mode=mode;self.footer.config(text='Haz clic para marcar '+('tu posición' if mode=='hero' else 'el objetivo'))
    def click(self,e):
        scale,ox,oy=self.transform();x=(e.x-ox)/scale;y=(e.y-oy)/scale
        vw,vh=self.viewport
        if not(0<=x<=vw and 0<=y<=vh):return
        x,y=self.unprojected(x,y)
        self.has_position_data=True
        if self.mode=='hero':self.s.hero_x=x;self.s.hero_y=y;self.set_mode('target')
        else:self.s.target_x=x;self.s.target_y=y
        self.mark()
    def clear_image(self):self.image=None;self.screen_box=None;self.draw()
    def open_image(self):
        p=filedialog.askopenfilename(filetypes=[('Imágenes','*.png *.jpg *.jpeg *.bmp')])
        if p:
            try:self.image=Image.open(p).convert('RGB');self.screen_box=None;self.draw()
            except Exception as e:messagebox.showerror('Imagen',str(e))
    def capture_area(self):
        self.hide_overlay();self.root.withdraw();self.root.after(250,self.select_area)
    def select_area(self):
        win=tk.Toplevel(self.root);win.overrideredirect(True);win.attributes('-topmost',True);win.attributes('-alpha',.3);win.configure(bg='black');win.geometry(f'{win.winfo_screenwidth()}x{win.winfo_screenheight()}+0+0');win.config(cursor='crosshair')
        cv=tk.Canvas(win,bg='black',highlightthickness=0);cv.pack(fill='both',expand=True)
        cv.create_text(35,35,anchor='nw',text='Arrastra un rectángulo sobre el área de juego · Esc para cancelar',fill='white',font=('Bahnschrift',20))
        start=[];rect=[]
        def down(e):start[:]=[e.x_root,e.y_root];rect[:]=[cv.create_rectangle(e.x,e.y,e.x,e.y,outline=GREEN,width=3)]
        def move(e):
            if start and rect:cv.coords(rect[0],start[0],start[1],e.x_root,e.y_root)
        def up(e):
            if not start:return
            box=(min(start[0],e.x_root),min(start[1],e.y_root),max(start[0],e.x_root),max(start[1],e.y_root))
            win.destroy()
            def snap():
                try:
                    if box[2]-box[0]<50 or box[3]-box[1]<50:raise ValueError('Selecciona un área de al menos 50 × 50')
                    self.image=ImageGrab.grab(bbox=box);self.screen_box=box
                except Exception as ex:messagebox.showerror('Captura',str(ex))
                self.root.deiconify();self.draw()
            self.root.after(180,snap)
        cv.bind('<ButtonPress-1>',down);cv.bind('<B1-Motion>',move);cv.bind('<ButtonRelease-1>',up)
        win.bind('<Escape>',lambda e:(win.destroy(),self.root.deiconify()))
    def refresh_visibility(self):
        self.auto_guide_enabled=self.guide_enabled.get()
        if not self.auto_guide_enabled:self.hide_power_guide()
        if not self.trajectory_enabled.get():self.hide_overlay()
        self.draw_overlay();self.draw()
    def toggle_overlay(self):
        self.trajectory_enabled.set(not self.trajectory_enabled.get());self.refresh_visibility()
    def draw_overlay(self):
        enabled=self.trajectory_enabled.get()
        visible=enabled and self.game_visible and self.last_live and time.monotonic()-self.last_live<4
        if not visible:
            if self.overlay:self.overlay.update(self.screen_box,self.viewport,self.projected,[],{},False)
            return
        if not self.overlay:self.overlay=TrajectoryOverlay(self.root)
        planned=self.planned_paths()
        self.overlay.update(self.screen_box,self.viewport,self.projected,planned,self.observed_paths,True,players=self.live_players,target_id=self.auto_target_id,hero_id=self.target_hero_id,weather=self.s.environment.get('activeWeathers',[]))
    def hide_overlay(self):
        if self.overlay:self.overlay.close();self.overlay=None
    def copy_power(self):
        if self.result.get('reachable'):self.root.clipboard_clear();self.root.clipboard_append(str(self.result['power']))
    def draw_force(self):
        if hasattr(self,'force_canvas'):draw_force(self.force_canvas,self.result,self.s.max_power,self.current_game_power)
        if self.power_guide:self.power_guide.draw(self.result,self.s.max_power)
    def hide_power_guide(self):
        if self.power_guide:self.power_guide.close();self.power_guide=None
    def toggle_power_guide(self):
        if self.auto_enabled and self.worker and self.worker.is_alive():
            self.auto_guide_enabled=not self.auto_guide_enabled
            if not self.auto_guide_enabled:self.hide_power_guide()
            return
        if self.power_guide:self.hide_power_guide();return
        if not self.guide_points:select_game_bar(self);return
        self.power_guide=PowerGuide(self.root,*self.guide_points);self.draw_force()
    def save_profile(self):
        try:
            self.read();solve(self.s);self.profiles[self.profile_key()]={k:getattr(self.s,k) for k in ('gravity','wind_scale','power_scale','speed_offset','angle_offset','quantize_power','launch_offset')};self.profile_path.write_text(json.dumps(self.profiles,indent=2),encoding='utf-8');self.footer.config(text='Perfil guardado para '+self.clone_id+' / '+self.s.mobile)
        except Exception as e:messagebox.showerror('Perfil',str(e))
    def calibrate(self):
        from tkinter.simpledialog import askfloat
        observed=askfloat('Calibrar','Con estas posiciones, ángulo y viento, ¿qué potencia real alcanzó el objetivo?',minvalue=1,maxvalue=400,parent=self.root)
        if observed is None:return
        try:self.vars['power_scale'].set(str(round(calibrated_profile(self.read(),observed),6)));self.footer.config(text='Velocidad ajustada. Guarda el perfil para conservarla.')
        except Exception as e:messagebox.showerror('Calibración',str(e))
    def save_session(self):
        p=filedialog.asksaveasfilename(defaultextension='.json',initialfile='dragonlab-sesion.json',filetypes=[('Sesión','*.json')])
        if not p:return
        try:self.read();pathlib.Path(p).write_text(json.dumps({'schema':2,'clone':self.clone_id,'viewport':self.viewport,'adapter':self.adapter_config,'settings':asdict(self.s)},indent=2),encoding='utf-8')
        except Exception as e:messagebox.showerror('Sesión',str(e))
    def load_session(self):
        p=filedialog.askopenfilename(filetypes=[('Sesión','*.json')])
        if not p:return
        try:
            d=json.loads(pathlib.Path(p).read_text(encoding='utf-8'));s=Settings(**d['settings']);solve(s)
            self.has_position_data=True;self.s=s;self.clone_id=d.get('clone','dragonbound');self.viewport=tuple(d.get('viewport',[800,600]));self.adapter_config=d.get('adapter');self.mobile.set(s.mobile);self.weather.set(s.weather);self.muzzle.set(s.muzzle)
            for k,v in self.vars.items():v.set(str(getattr(s,k)))
            self.mark()
        except Exception as e:messagebox.showerror('Sesión',str(e))
    def open_game_browser(self):
        import subprocess
        candidates=[pathlib.Path(os.environ.get('PROGRAMFILES','C:/Program Files'))/'Google/Chrome/Application/chrome.exe',pathlib.Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Google/Chrome/Application/chrome.exe',pathlib.Path(os.environ.get('LOCALAPPDATA',''))/'Google/Chrome/Application/chrome.exe',pathlib.Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Microsoft/Edge/Application/msedge.exe']
        browser=next((p for p in candidates if p.is_file()),None)
        if browser is None:messagebox.showerror('Navegador','No se encontró Chrome o Edge.');return
        profile=pathlib.Path(os.environ.get('LOCALAPPDATA',str(BASE)))/'DragonLab/Browser'
        subprocess.Popen([str(browser),'--remote-debugging-port=9223','--user-data-dir='+str(profile),'https://dragonbound.net/'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.endpoint.set('http://127.0.0.1:9223');self.live_stop.set()
        def restart():
            if self.worker and self.worker.is_alive():self.root.after(200,restart)
            else:self.toggle_live()
        self.root.after(200,restart)
    def toggle_live(self):
        if self.worker and self.worker.is_alive():
            self.live_stop.set();self.auto_enabled=False;self.auto_visible=False;self.hide_overlay();self.hide_power_guide();self.live_camera=None;self.last_live=0
            self.status.config(text='AUTOMÁTICO PAUSADO');self.connect.config(text='Activar captura automática');return
        self.auto_enabled=True;stop=threading.Event();self.live_stop=stop
        endpoint=self.endpoint.get();clone=self.clone_id;config=self.adapter_config;target=self.browser_target
        self.connect.config(text='Pausar captura automática')
        def run():
            from automatic import AutoCapture
            while not stop.is_set():
                client=None
                try:
                    try:client=AdapterClient(endpoint,target,clone,config)
                    except Exception:
                        if endpoint=='http://127.0.0.1:9222' and target is None:client=AdapterClient('http://127.0.0.1:9223',target,clone,config)
                        else:raise
                    capture=AutoCapture(client)
                    while not stop.is_set():
                        auto=capture.read() if clone=='dragonbound' else {}
                        sample=client.sample()
                        if clone=='dragonbound' and not auto.get('geometry',{}).get('active'):
                            sample={'status':'waiting','reason':'Navegador conectado. La captura aparecerá al empezar la partida.'}
                            client.game=None;client.renderer=None
                        sample['_auto']=auto;self.events.put(sample);stop.wait(.25)
                except Exception as e:
                    if not stop.is_set():self.events.put({'status':'waiting','reason':'Buscando el navegador del juego… '+str(e)})
                finally:
                    if client:
                        try:client.close()
                        except Exception:pass
                stop.wait(2)
        self.worker=threading.Thread(target=run,daemon=True);self.worker.start()
    def apply_auto(self,data):
        auto=data.pop('_auto',{});meta=auto.get('geometry',{})
        self.game_visible=bool(self.auto_enabled and meta.get('active') and meta.get('focused') and data.get('status')=='live')
        if data.get('camera'):self.live_camera=data['camera']
        if auto.get('image') is not None:self.image=auto['image'];self.draw()
        players=[p for p in data.get('players',[]) if p.get('x') is not None and p.get('y') is not None]
        hero=next((p for p in players if p.get('isHero') or p.get('id')==data.get('heroId')),None)
        has_target=hero is not None and any(p!=hero and (hero.get('team') is None or p.get('team')!=hero.get('team')) for p in players)
        self.auto_visible=bool(self.auto_enabled and self.auto_guide_enabled and has_target and meta.get('active') and meta.get('focused') and data.get('status')=='live')
        area=auto.get('screen_box');points=auto.get('guide_points')
        if area:self.screen_box=area
        if not self.auto_visible or not points:
            self.hide_power_guide();return
        if self.auto_points!=points:
            if self.power_guide:self.power_guide.update_position(*points)
            self.auto_points=points
        self.guide_points=points
        if not self.power_guide:self.power_guide=PowerGuide(self.root,*points)
        self.draw_force()
    def apply_live(self,d):
        self.observed_paths=self.trails.update(d.get('shots',[]))
        try:changed=self.book.observe(d,self.clone_id)
        except (OSError,ValueError,TypeError):changed=[];self.book.message='No se pudo guardar la medición; el perfil actual se conserva'
        if changed:self.profile_stamp=None;self.last_fingerprint=None;self.mark()
        self.apply_auto(d)
        if d['status']!='live':
            self.last_live=0;self.live_camera=None;self.live_look=None;self.live_launch_offset=None;self.s.launch_offset=None;self.has_position_data=False;self.game_visible=False;self.current_game_power=None;self.hide_overlay();self.trails.reset();self.observed_paths={};self.last_fingerprint=None;self.auto_target_id=None;self.target_hero_id=None
            if self.power_guide:self.power_guide.draw({},self.s.max_power)
            if d['status']=='error':self.connect.config(text='Conectar lectura experimental')
            self.status.config(text='ESPERANDO PARTIDA' if d['status']=='waiting' else 'SIN CONEXIÓN');self.footer.config(text=d.get('reason',''));return
        self.last_live=time.monotonic();self.status.config(text='CAPTURA AUTOMÁTICA')
        self.current_game_power=d.get('currentPower');self.draw_force()
        self.live_camera=d.get('camera');self.draw();self.draw_overlay()
        fingerprint=json.dumps({k:v for k,v in d.items() if k not in ('currentPower','shots','camera','turn','adapter','compatibility')},sort_keys=True)
        if fingerprint==self.last_fingerprint:return
        self.last_fingerprint=fingerprint
        ps=[p for p in d.get('players',[]) if p.get('x') is not None and p.get('y') is not None]
        hero=next((p for p in ps if p.get('isHero') or p.get('id')==d.get('heroId')),None)
        if not hero:self.footer.config(text='Se leen jugadores; identificación del jugador pendiente. Usa el modo manual.');return
        self.has_position_data=True;self.live_players=ps
        targets=[p for p in ps if p!=hero and not p.get('dead',False) and (hero.get('team') is None or p.get('team')!=hero.get('team'))]
        if not targets:
            self.has_position_data=False;self.result={};self.auto_target_id=None;self.hide_power_guide();self.draw_overlay();self.show_result();return
        self.target_ids={f'{p["name"]} / {p["id"]}':p['id'] for p in targets}
        self.target_box.config(values=['Objetivo automático']+list(self.target_ids))
        if self.target_hero_id!=hero['id']:self.auto_target_id=None;self.target_hero_id=hero['id']
        wanted=self.selected_target if self.selected_target is not None else self.auto_target_id
        target=next((p for p in targets if p['id']==wanted),None) or min(targets,key=lambda p:math.hypot(p['x']-hero['x'],p['y']-hero['y']))
        self.auto_target_id=target['id']
        self.live_camera=d.get('camera')
        self.live_look=hero.get('look');self.s.hero_x=hero['x'];self.s.hero_y=hero['y']
        self.s.target_x=target['x'];self.s.target_y=target['y']
        mid=hero.get('mobile')
        detected_mobile=mobile_name(mid)
        if detected_mobile and self.mobile.get()!=detected_mobile:self.mobile.set(detected_mobile);self.change_mobile()
        if hero.get('angle') is not None and -180<hero['angle']<180:self.vars['angle'].set(str(hero['angle']))
        if d.get('wind') is not None:self.vars['wind'].set(str(d['wind']))
        if d.get('windAngle') is not None:self.vars['wind_angle'].set(str(d['windAngle']))
        if hero.get('body') is not None:self.vars['body_angle'].set(str(hero['body']))
        if d.get('selectedShot') in (0,1,2):self.s.selected_shot=d['selectedShot']
        muzzles=hero.get('muzzles',[]);shot=self.s.selected_shot;self.live_launch_offset=None
        if len(muzzles)>shot:
            muzzle=muzzles[shot];angle=muzzle.get('angle');radius=muzzle.get('radius')
            if isinstance(angle,(int,float)) and isinstance(radius,(int,float)) and hero.get('look') in (0,1) and hero.get('body') is not None:
                face=hero['look'] if self.mobile.get() not in REVERSE else 1-hero['look']
                a=math.radians((angle if face else 180-angle)-hero['body']);self.live_launch_offset=(round(math.cos(a)*radius),-round(math.sin(a)*radius))
        terrain=d.get('terrain')
        self.s.environment={}
        if isinstance(terrain,dict):
            if terrain.get('surface'):self.s.environment['terrain']={'heights':terrain['surface'],'originX':terrain.get('originX',0),'originY':terrain.get('originY',0)}
            elif terrain.get('rows'):self.s.environment['terrain']=terrain
        self.s.environment['activeWeathers']=d.get('weather',[]) if isinstance(d.get('weather'),list) else []
        self.s.environment['hitTolerance']=18
        self.vehicle_label.config(text=self.mobile.get())
        self.footer.config(text=f'Objetivo: {target["name"]} · Verde: prevista · Azul: observada · {self.book.message}')
        self.mark()
    def select_target(self):
        self.selected_target=self.target_ids.get(self.target_name.get());self.last_fingerprint=None;self.mark()
    def share(self):
        if not self.server:
            app=self
            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    p=urlparse(self.path);token=parse_qs(p.query).get('token',[''])[0]
                    if not secrets.compare_digest(token,app.share_token):self.send_error(403);return
                    if p.path=='/state':body=json.dumps(app.shared).encode();mime='application/json'
                    elif p.path=='/':body=(ASSETS/'viewer.html').read_bytes();mime='text/html; charset=utf-8'
                    else:self.send_error(404);return
                    self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
                def log_message(self,*a):pass
            self.server=ThreadingHTTPServer(('0.0.0.0',0),Handler);threading.Thread(target=self.server.serve_forever,daemon=True).start()
        try:
            sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.connect(('192.0.2.1',1));ip=sock.getsockname()[0];sock.close()
        except OSError:ip='127.0.0.1'
        url=f'http://{ip}:{self.server.server_port}/?token={self.share_token}'
        win=tk.Toplevel(self.root);win.title('Visor · DragonLab');win.configure(bg=BG);win.geometry('600x220')
        tk.Label(win,text='Abre este enlace en el celular, en la misma red Wi-Fi.',bg=BG,fg=TEXT,font=('Bahnschrift',13)).pack(pady=20)
        entry=tk.Entry(win,font=('Consolas',10));entry.insert(0,url);entry.pack(fill='x',padx=20,ipady=7);entry.select_range(0,'end')
        self.button(win,'Copiar enlace',lambda:(self.root.clipboard_clear(),self.root.clipboard_append(url))).pack(pady=12)
        self.button(win,'Abrir visor aquí',lambda:webbrowser.open(url)).pack()
    def tick(self):
        while not self.events.empty():
            event=self.events.get_nowait()
            if event.get('status')=='calculated':
                self.computing=False
                if event['generation']==self.compute_generation and not self.dirty:
                    self.result=event['result'];self.show_result(event.get('error'))
            else:self.apply_live(event)
        if self.last_live and time.monotonic()-self.last_live>4:
            self.status.config(text='ESPERANDO DATOS');self.auto_visible=False;self.hide_overlay();self.hide_power_guide()
            if self.power_guide:self.power_guide.draw({},self.s.max_power)
        if self.dirty and not self.computing:
            self.dirty=False;self.compute_generation+=1
            try:
                settings=Settings(**asdict(self.read()));generation=self.compute_generation;self.computing=True
                self.power.config(text='…')
                self.result={};self.draw_force()
                if self.overlay:self.draw_overlay()
                preview_power=self.current_game_power if isinstance(self.current_game_power,(int,float)) and 1<=self.current_game_power<=settings.max_power else None
                def calculate(settings=settings,generation=generation,preview_power=preview_power):
                    try:
                        result=solve(settings)
                        if not result.get('reachable') and preview_power:
                            from physics_extensions import trajectory
                            preview=trajectory(settings,preview_power,step=.06)
                            result['preview_paths']=[[(p[0],p[1]) for p in path] for path in preview['projectile_paths']];result['preview_power']=preview_power
                        self.events.put({'status':'calculated','generation':generation,'result':result})
                    except Exception as e:self.events.put({'status':'calculated','generation':generation,'result':{},'error':str(e)})
                threading.Thread(target=calculate,daemon=True).start()
            except Exception as e:self.result={};self.show_result(str(e))
        self.shared['updated']=time.time()
        self.shared['source']='experimental' if self.last_live and time.monotonic()-self.last_live<4 else 'manual'
        if '--diagnostics' in sys.argv and time.monotonic()-getattr(self,'diagnostic_clock',0)>1:
            self.diagnostic_clock=time.monotonic()
            health={'version':'0.5','updated':time.time(),'connected':bool(self.last_live and time.monotonic()-self.last_live<4),'map_detected':bool(self.s.environment.get('terrain')),'camera_detected':bool(self.live_camera and self.live_camera.get('renderWidth')),'weather':[w.get('resolvedTypeId') or w.get('typeId') for w in self.s.environment.get('activeWeathers',[])],'players_detected':len(self.live_players),'overlay_visible':bool(self.overlay and self.overlay.visible),'power':self.result.get('power'),'computing':self.computing}
            try:(BASE/'estado-live.json').write_text(json.dumps(health,indent=2),encoding='utf-8')
            except OSError:pass
        self.root.after(150,self.tick)
    def compute(self):
        self.compute_generation+=1;self.result=solve(self.read());self.show_result();return self.result
    def show_result(self,error=None):
        if not self.has_position_data and self.auto_enabled:
            self.result={};self.power.config(text='—');self.details.config(text='Esperando partida\nLas trayectorias aparecen al entrar al juego');self.draw();self.draw_force();return
        if error:
            self.result={};self.power.config(text='—');self.details.config(text=error);self.shared={'error':error,'updated':time.time()}
        else:
            self.last_computed=time.monotonic()
            if self.result.get('reachable'):
                r=self.result
                if self.clone_id=='gunbound-world' and self.profile_key() not in self.profiles:r['quality']='GunBound World: perfil sin calibrar · '+r['quality'];r['approximate']=True
                self.power.config(text=str(r['power']),fg=ORANGE if r['approximate'] else GREEN)
                self.details.config(text=f'FUERZA / {self.s.max_power:g} · {self.s.mobile}\nÁngulo {self.s.angle:g}° · Viento {self.s.wind:g} · Tiro {self.s.selected_shot+1 if self.s.selected_shot<2 else "SS"}')
            else:
                self.power.config(text='—');text='Este ángulo no alcanza el objetivo'
                if self.result.get('preview_power'):text+=f'\nVista de trayectoria a fuerza {self.result["preview_power"]:g}'
                self.details.config(text=text)
            self.shared={'settings':asdict(self.s),'result':self.result,'camera':self.live_camera,'viewport':self.viewport,'clone':self.clone_id,'updated':time.time()}
        self.draw();self.draw_overlay();self.draw_force()
    def close(self):
        self.live_stop.set();self.hide_overlay();self.hide_power_guide()
        if hasattr(self,'fire_controller'):self.fire_controller.cancel()
        if self.server:self.server.shutdown();self.server.server_close()
        self.root.destroy()

if __name__=='__main__':
    root=tk.Tk()
    if '--check' in sys.argv:root.withdraw()
    if '--minimized' in sys.argv:root.iconify()
    app=App(root)
    if '--check' in sys.argv:root.after(500,app.close)
    if '--smoke' in sys.argv:
        root.attributes('-topmost',True);root.lift()
        root.after(700,lambda:ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(BASE/'vista-previa.png'))
        root.after(1100,app.close)
    root.mainloop()
