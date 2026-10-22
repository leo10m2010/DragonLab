import tkinter as tk
from tkinter import ttk,filedialog,messagebox
import math,json,pathlib,threading,queue,time,sys,os,socket,secrets,webbrowser,ctypes
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
from dataclasses import asdict,replace
from core import Settings,PROFILES,REVERSE,solve,calibrated_profile,launch
from cdp import CDP
from app_version import PROGRAM_VERSION
from adapters import AdapterClient,built_in_profiles
from PIL import Image,ImageTk,ImageGrab
from strength_guide import draw_force,PowerGuide,select_game_bar
from trajectories import TrajectoryOverlay,ObservedTrails
from projection import project,unproject
from calibration_book import CalibrationBook,mobile_name
from targeting import enemies,next_target,normalize_players,find_hero,PlayerTracker
from shortcuts import GameShortcuts

BASE=pathlib.Path(sys.executable).parent if getattr(sys,'frozen',False) else pathlib.Path(__file__).parent
ASSETS=pathlib.Path(getattr(sys,'_MEIPASS',BASE))
BG='#11191c'; PANEL='#1a262b'; TEXT='#edf4f1'; MUTED='#a4b6b2'; GREEN='#72dfba'; ORANGE='#ffb86c'

class App:
    def __init__(self,root,embedded=False):
        self.root=root;root.title('DragonLab');root.geometry('760x620');root.minsize(680,620);root.configure(bg=BG)
        self.s=Settings();self.vars={};self.image=None;self.photo=None;self.mode='target';self.result={};self.overlay=None
        self.screen_box=None;self.events=queue.Queue();self.live_stop=threading.Event();self.worker=None;self.live_players=[];self.last_live=0;self.live_camera=None
        self.profiles={};self.server=None;self.share_token=secrets.token_urlsafe(24);self.shared={};self.dirty=True;self.last_input='';self.selected_target=None;self.target_ids={}
        self.base=BASE;self.clone_id='dragonbound';self.adapter_config=None;self.browser_target=None;self.viewport=(800,600);self.last_fingerprint=None;self.last_computed=0;self.compute_generation=0;self.computing=False;self.direction='Auto'
        self.power_guide=None;self.guide_points=None;self.current_game_power=None;self.auto_visible=False;self.auto_enabled=True;self.auto_points=None;self.auto_guide_enabled=True;self.auto_target_id=None;self.target_hero_id=None
        self.training_session=None;self.preferences_path=BASE/'preferencias.json';self.target_key='Ctrl';self.fire_key='Q';self.auto_shot_enabled=True;self.performance='Ligero';self.map_expanded=False;self.fire_busy=False;self.pending_fire=None;self.result_context=None;self.fire_shortcut_count=0;self.page_shortcuts_active=False;self.last_page_gesture=None;self.last_fire_message=None;self.fire_cancel=threading.Event();self.capture_dpr=1
        self.player_tracker=PlayerTracker();self.compact=False;self.large_text=False;self.path_color='Menta';self.path_width=3
        from shot_review import ShotReview
        self.shot_review=ShotReview(BASE/'revision-tiros.json')
        from replay_store import ReplayStore
        self.replays=ReplayStore(BASE/'casos-regresion')
        self.book=CalibrationBook(BASE/'calibraciones.json');self.trails=ObservedTrails();self.observed_paths={};self.game_visible=False;self.has_position_data=False;self.live_look=None;self.profile_stamp=None;self.live_launch_offset=None;self.terrain_revision=0
        prefs={}
        try:
            prefs=json.loads(self.preferences_path.read_text(encoding='utf-8'));self.clone_id=prefs.get('clone','dragonbound');self.adapter_config=prefs.get('adapter')
            self.viewport=tuple(prefs.get('viewport',[800,600]));self.target_key=prefs.get('target_key','Ctrl');self.fire_key=prefs.get('fire_key','Q');self.auto_shot_enabled=bool(prefs.get('auto_shot',True));self.performance=prefs.get('performance','Ligero');self.compact=bool(prefs.get('compact',False));self.large_text=bool(prefs.get('large_text',False));self.path_color=prefs.get('path_color','Menta');self.path_width=max(1,min(5,int(prefs.get('path_width',3))))
            from shortcuts import validate_bindings
            validate_bindings(self.target_key,self.fire_key)
        except (OSError,ValueError,TypeError):self.target_key='Ctrl';self.fire_key='Q'
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
        from ui_shell import build
        build(self,prefs)
        self.root.protocol('WM_DELETE_WINDOW',self.close)
        root.bind('<Control-s>',lambda e:self.save_session());root.bind('<Escape>',lambda e:(self.cancel_actions(),self.hide_overlay(),self.hide_power_guide()))
        self.profile_path=BASE/'perfiles.json'
        try:self.profiles=json.loads(self.profile_path.read_text(encoding='utf-8'))
        except (OSError,ValueError):pass
        self.game_window=None;self.shortcut_count=0;self.preview_visible=False;self.terrain_revision=0;self.last_terrain=None;self.change_mobile();self.tick()
        if not (embedded and '--check' in sys.argv):self.start_target_shortcut()
        if not embedded and '--smoke' not in sys.argv and '--no-auto' not in sys.argv and '--check' not in sys.argv:root.after(300,self.toggle_live)

    def open_settings(self):
        from simple_settings import open_settings
        return open_settings(self)
    def toggle_preview(self):
        self.map_expanded=not self.map_expanded
        if self.map_expanded:self.canvas.pack(fill='both',expand=True,padx=24,before=self.summary_panel);self.root.geometry('760x820')
        else:self.canvas.pack_forget();self.root.geometry('760x540' if self.compact else '760x620')
        self.preview_button.config(text='Ocultar mapa' if self.map_expanded else 'Ver mapa');self.draw()
    def fire_context(self):
        # A pending key press cannot survive another angle, target or map change.
        return (self.last_fingerprint,self.auto_target_id,self.target_hero_id,self.clone_id,
                tuple((k,v.get()) for k,v in self.vars.items()))
    def fire_notice(self,text):
        self.last_fire_message=text
        self.notice_until=time.monotonic()+4;self.footer.config(text=text,fg=ORANGE)
    def process_pending_fire(self):
        if self.pending_fire:
            until,context=self.pending_fire
            if time.monotonic()>until or context!=self.fire_context() or not self.auto_shot_enabled or not self.auto_enabled:
                self.pending_fire=None;self.fire_notice('El cálculo cambió; vuelve a pulsar el atajo')
            elif not self.dirty and not self.computing:
                self.pending_fire=None;self.trigger_auto_fire()
    def cancel_actions(self):
        from control_lifecycle import cancel_actions
        cancel_actions(self)
    def trigger_auto_fire(self):
        if getattr(self,'training_session',None) and self.training_session.running:
            self.fire_notice('Entrenamiento activo: detén la sesión para usar el atajo');return
        if self.fire_busy or not self.auto_shot_enabled:return
        if self.clone_id not in ('dragonbound','gunbound-world') or not self.auto_enabled or not self.last_live or time.monotonic()-self.last_live>1.5:
            self.fire_notice('Espera la conexión con el juego');return
        if self.clone_id=='gunbound-world' and not self.s.environment.get('terrain'):
            self.fire_notice('Espera a detectar el terreno antes de disparar');return
        if self.computing or self.dirty:
            if self.pending_fire is None:self.pending_fire=(time.monotonic()+.8,self.fire_context())
            self.fire_notice('Esperando el cálculo actual para este tiro…');return
        if self.clone_id=='gunbound-world' and any(e.get('kind')=='unresolved-weather' for e in self.display_result().get('interactions',[])):
            self.fire_notice('Clima aleatorio sin revelar: recorrido sin confirmar');return
        from strength_guide import guide_power
        chosen_power=guide_power(self.display_result())
        if chosen_power is None:
            self.fire_notice(self.display_result().get('reason') or 'Ese ángulo no tiene una fuerza válida');return
        hero=next((p for p in self.live_players if p['id']==self.target_hero_id),None)
        target=next((p for p in self.live_players if p['id']==self.auto_target_id),None)
        if hero and target and (hero.get('stale') or target.get('stale')):
            self.fire_notice('Espera a confirmar las posiciones');return
        if not hero or not target or not self.game_window or not self.screen_box:
            self.fire_notice('Espera a detectar el jugador y la ventana del juego');return
        plan={'power':round(chosen_power),'window':self.game_window,'hero':hero['id'],'target':target['id'],'shot':self.s.selected_shot,'wind':self.s.wind,'windAngle':self.s.wind_angle,'barStart':self.guide_points[0] if self.guide_points else None,'dpr':self.capture_dpr,'screenBox':self.screen_box,'heroState':{k:hero[k] for k in ('x','y','rawAngle','body','look') if k in hero},'targetState':{k:target[k] for k in ('x','y')}}
        self.pending_fire=None;self.fire_busy=True;self.fire_cancel.clear();self.footer.config(text='Aplicando fuerza…')
        clone=self.clone_id
        endpoint=self.endpoint.get();target_id=self.browser_target;snapshot=replace(self.s,environment=dict(self.s.environment))
        if self.book.profile(self.clone_id,self.s.mobile,self.s.selected_shot,self.s.wind):
            speed=plan['power']*snapshot.power_scale+snapshot.speed_offset
            plan['expectedSpeed']=math.trunc(speed) if snapshot.quantize_power else speed
        def run():
            from auto_fire import PowerReader,execute
            if clone=='gunbound-world':
                from gunbound_fire import GunBoundPowerReader,execute_gunbound
                PowerReader,execute=GunBoundPowerReader,execute_gunbound
            reader=None;attempt={'version':PROGRAM_VERSION,'started':time.time(),'requestedPower':plan['power'],'events':[]}
            try:
                try:reader=PowerReader(endpoint,target_id)
                except Exception:
                    if endpoint!='http://127.0.0.1:9222':raise
                    reader=PowerReader('http://127.0.0.1:9223',target_id)
                result=execute(plan,reader,self.fire_cancel,trace=lambda event:attempt['events'].append(event) if len(attempt['events'])<32 else None)
                attempt['result']=result
                from shot_confirmation import wait_for_shot
                try:
                    if clone=='gunbound-world':
                        from gunbound_fire import confirm_release
                        confirmation=confirm_release(reader,result,attempt['started'],self.fire_cancel)
                    else:
                        reader.client.terrain_interval=60;reader.client.terrain_clock=time.monotonic()
                        confirmation=wait_for_shot(reader,plan,result,self.fire_cancel)
                except Exception:
                    confirmation={'status':'unconfirmed','reason':'La lectura se interrumpió después de soltar; no se repite el tiro'}
                attempt['confirmation']=confirmation
                outcome=confirmation['status']
                message=(f"Tiro confirmado · Fuerza {confirmation['actualPower']:g}" if outcome=='confirmed' else f"Revisar tiro · marcaba {plan['power']:g}, barra final {confirmation['actualPower']:g}" if outcome=='mismatch' else 'Proyectil observado · fuerza de barra confirmada' if outcome=='observed' and confirmation.get('observedPower') is not None else 'Tiro enviado · no se pudo confirmar la fuerza final')
                self.events.put({'status':'fire-confirmed','confirmation':confirmation})
                try:self.replays.record(snapshot,outcome,confirmation)
                except (OSError,ValueError,TypeError):pass
            except Exception as error:
                message=str(error);attempt['error']=message
            finally:
                if reader:reader.close()
                attempt['finished']=time.time()
                try:(BASE/'ultimo-autotiro.json').write_text(json.dumps(attempt,indent=2),encoding='utf-8')
                except OSError:pass
            self.events.put({'status':'fire-finished','message':message})
        threading.Thread(target=run,daemon=True).start()
    def apply_measured_profile(self):
        fit=self.book.profile(self.clone_id,self.s.mobile,self.s.selected_shot,self.s.wind)
        if not fit and getattr(self,'cloud_profiles',None):
            from cloud_profiles import compatible_fit
            fit=compatible_fit(self.cloud_profiles,self.book,self.clone_id,self.s.mobile,self.s.selected_shot,self.s.wind)
        if fit and self.clone_id=='gunbound-world' and fit.get('native_euler_step') and not fit.get('wind_range',[0,100])[0]<=self.s.wind<=fit.get('wind_range',[0,100])[1]:fit=None
        if not fit and self.clone_id=='gunbound-world' and not self.book.records.get(self.book.key(self.clone_id,self.s.mobile,self.s.selected_shot),{}).get('drift_pending'):
            from gunbound_profiles import measured_profile
            fit=measured_profile(self.s.mobile,self.s.selected_shot,self.s.wind)
        if self.s.mobile=='RANDOMIZER':fit=None
        self.active_measured_profile=bool(fit)
        self.profile_required=self.s.mobile=='RANDOMIZER' or self.clone_id=='gunbound-world' and not fit
        self.profile_missing_reason='Camaleón: el proyectil cambia; no está identificado antes del tiro.' if self.s.mobile=='RANDOMIZER' else 'GunBound World: falta calibrar fuerza para este vehículo, tiro y viento.'
        if fit and fit.get('native_euler_step'):self.s.environment['nativeEulerStep']=fit['native_euler_step']
        else:self.s.environment.pop('nativeEulerStep',None)
        if not fit:fit=self.book.provisional(self.clone_id,self.s.mobile,self.s.selected_shot,self.s.wind,self.s.wind_angle)
        observed=self.book.acceleration(self.clone_id,self.s.mobile,self.s.selected_shot,self.s.wind,self.s.wind_angle)
        if observed:self.s.environment['observedAcceleration']=observed
        else:self.s.environment.pop('observedAcceleration',None)
        stamp=(self.clone_id,self.s.mobile,self.s.selected_shot,tuple((k,fit.get(k)) for k in ('gravity','power_scale','wind_scale','speed_offset')) if fit else None)
        if stamp==self.profile_stamp:return
        previous=getattr(self,'last_applied_profile',self.profile_stamp);self.profile_stamp=stamp;self.last_applied_profile=stamp
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
    def button(self,parent,text,cmd):
        from rounded_widgets import RoundedButton
        return RoundedButton(parent,text=text,command=cmd)
    def field(self,p,label,key,value,row,minimum,maximum):
        tk.Label(p,text=label,bg=PANEL,fg=TEXT,font=('Bahnschrift',10)).grid(row=row,column=0,sticky='w',pady=4)
        v=tk.StringVar(value=str(value));self.vars[key]=v;v.trace_add('write',lambda *a:self.mark())
        tk.Spinbox(p,textvariable=v,from_=minimum,to=maximum,increment=.1 if key in ('power_scale','wind_scale') else 1,width=9,bg=BG,fg=TEXT,insertbackground=TEXT,buttonbackground='#294353',relief='flat').grid(row=row,column=1,sticky='e',padx=(10,0),ipady=4)
        p.columnconfigure(1,weight=1)
    def mark(self):self.dirty=True
    def persist_preferences(self):
        self.preferences_path.write_text(json.dumps({'clone':self.clone_id,'adapter':self.adapter_config,'viewport':self.viewport,'target_key':self.target_key,'fire_key':self.fire_key,'auto_shot':self.auto_shot_enabled,'performance':self.performance,'trajectories':self.trajectory_enabled.get(),'guide':self.guide_enabled.get(),'compact':self.compact,'large_text':self.large_text,'path_color':self.path_color,'path_width':self.path_width},indent=2),encoding='utf-8')
    def profile_key(self):return self.clone_id+':'+self.mobile.get()
    def change_mobile(self):
        name=self.mobile.get();g,w,p,*_=PROFILES[name];custom=self.profiles.get(self.profile_key(),self.profiles.get(name,{}) if self.clone_id=='dragonbound' else {})
        if self.clone_id=='gunbound-world':
            g={'MAGE':360,'LIGHTNING':360,'ADUKA':376,'FROG':368,'DRAGON':360}.get(name,392)
            self.s.max_power=100
        else:self.s.max_power=400
        for k,val in [('gravity',g),('wind_scale',w),('power_scale',p)]:self.vars[k].set(str(custom.get(k,val)))
        for key in ('speed_offset','angle_offset','quantize_power','launch_offset'):setattr(self.s,key,custom.get(key,getattr(Settings(),key)))
        self.profile_stamp=None;self.vehicle_label.config(text=name if self.has_position_data else 'Por detectar');self.mark()
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
    def visual_context(self):
        return (self.clone_id,self.mobile.get(),self.s.selected_shot,self.target_hero_id,self.auto_target_id,
                self.s.hero_x,self.s.hero_y,self.s.target_x,self.s.target_y,self.terrain_revision)
    def display_result(self):
        if self.autonomous_training():return {}
        if getattr(self,'result_context',None)!=self.visual_context():return {}
        if (self.dirty or self.computing) and time.monotonic()-self.last_computed>1.5:return {}
        return self.result
    def planned_paths(self):
        r=self.display_result()
        if r.get('reachable'):return r.get('display_paths',r.get('projectile_paths',[r.get('path',[])]))
        return r.get('preview_paths',[])
    def draw(self):
        if self.root.state()!='normal' or not self.map_expanded:return
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
        if self.has_position_data:
            for i,p in enumerate(enemies(self.live_players,self.target_hero_id),1):
                if p['id']==self.auto_target_id:continue
                px,py=xy(p['x'],p['y']);c.create_oval(px-6,py-6,px+6,py+6,outline=MUTED,width=2)
                c.create_text(px,py-18,text=str(i),fill=TEXT,font=('Consolas',10,'bold'))
        for x,y,label,color in positions:
            px,py=xy(x,y);c.create_oval(px-7,py-7,px+7,py+7,fill=BG,outline=color,width=2);c.create_line(px-14,py,px+14,py,fill=color);c.create_line(px,py-14,px,py+14,fill=color)
            c.create_text(px,py+23,text=f'{label} · {round(x)}, {round(y)}',fill=color,font=('Consolas',10))
        from rounded_widgets import mask_corners
        mask_corners(c,BG)
    def set_mode(self,mode):
        if not self.map_expanded:self.toggle_preview()
        self.has_position_data=True;self.mode=mode;self.footer.config(text='Haz clic para marcar '+('tu posición' if mode=='hero' else 'el objetivo'))
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
            try:
                self.image=Image.open(p).convert('RGB');self.screen_box=None
                if not self.map_expanded:self.toggle_preview()
                self.draw()
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
        if not self.overlay:self.overlay=TrajectoryOverlay(getattr(self,'ui_parent',self.root))
        planned=self.planned_paths()
        self.overlay.update(self.screen_box,self.viewport,self.projected,planned,self.observed_paths,True,players=self.live_players,target_id=self.auto_target_id,hero_id=self.target_hero_id,weather=self.s.environment.get('activeWeathers',[]),style={'color':MUTED if self.dirty or self.computing else '#80cfff' if self.path_color=='Azul' else GREEN,'width':self.path_width,'font_size':13 if self.large_text else 11,'target_key':self.target_key,'events':self.display_result().get('interactions',[]),'weather_name':getattr(self,'weather_current','')})
    def hide_overlay(self):
        if self.overlay:self.overlay.close();self.overlay=None
    def copy_power(self):
        if self.result.get('reachable'):self.root.clipboard_clear();self.root.clipboard_append(str(self.result['power']))
    def autonomous_training(self):
        session=getattr(self,'training_session',None)
        return bool(session and getattr(session,'autonomous',False) and session.running)
    def draw_force(self):
        if self.autonomous_training():self.hide_power_guide();return
        from product_status import calibration_label
        label,state=calibration_label(self)
        r={**self.display_result(),'guide_label':label,'guide_state':state};updating=self.dirty or self.computing
        if hasattr(self,'force_canvas'):draw_force(self.force_canvas,r,self.s.max_power,self.current_game_power,updating)
        if self.clone_id=='gunbound-world' and getattr(self,'profile_required',True) and not r.get('reachable') and not r.get('blocked') and not updating:
            from product_status import pending_calibration
            title,message=pending_calibration(self);r={**r,'guide_message':title+' · '+message}
        if time.monotonic()<getattr(self,'notice_until',0) and getattr(self,'last_fire_message',''):r['guide_notice']=self.last_fire_message
        if self.power_guide:self.power_guide.draw(r,self.s.max_power,updating)
    def hide_power_guide(self):
        if self.power_guide:self.power_guide.close();self.power_guide=None
    def toggle_power_guide(self):
        if self.auto_enabled and self.worker and self.worker.is_alive():
            self.auto_guide_enabled=not self.auto_guide_enabled
            if not self.auto_guide_enabled:self.hide_power_guide()
            return
        if self.power_guide:self.hide_power_guide();return
        if not self.guide_points:select_game_bar(self);return
        self.power_guide=PowerGuide(getattr(self,'ui_parent',self.root),*self.guide_points);self.draw_force()
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
        parent=getattr(self,'ui_parent',self.root)
        if browser is None:messagebox.showerror('Navegador','Instala Chrome o Edge para abrir el juego.',parent=parent);return False
        profile=pathlib.Path(os.environ.get('LOCALAPPDATA',str(BASE)))/'DragonLab/Browser'
        from game_startup import activate_existing_game
        from game_catalog import game_by_id
        game=game_by_id(self.clone_id)
        if not game:messagebox.showerror('Juego','Selecciona un juego disponible.',parent=parent);return False
        if not activate_existing_game(host=game['host']):
            try:subprocess.Popen([str(browser),'--remote-debugging-port=9223','--user-data-dir='+str(profile),game['url']],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            except OSError:
                messagebox.showerror('Navegador','No se pudo abrir el navegador. Vuelve a intentarlo.',parent=parent);return False
        self.endpoint.set('http://127.0.0.1:9223');self.live_stop.set()
        def restart():
            if self.worker and self.worker.is_alive():self.root.after(200,restart)
            else:self.toggle_live()
        self.root.after(200,restart)
        return True
    def toggle_live(self):
        if self.worker and self.worker.is_alive():
            if getattr(self,'training_session',None):self.training_session.stop()
            self.live_stop.set();self.auto_enabled=False;self.auto_visible=False;self.hide_overlay();self.hide_power_guide();self.live_camera=None;self.last_live=0
            self.status.config(text='●  Captura pausada',fg=ORANGE);self.connect.config(text='Activar captura automática');return
        self.auto_enabled=True;stop=threading.Event();self.live_stop=stop
        endpoint=self.endpoint.get();clone=self.clone_id;config=self.adapter_config;target=self.browser_target
        self.connect.config(text='Pausar captura automática')
        def run():
            from automatic import AutoCapture
            from performance import Governor
            governor=Governor();sample={}
            while not stop.is_set():
                client=None;shot_events=None;learning=None
                try:
                    try:client=AdapterClient(endpoint,target,clone,config)
                    except Exception:
                        if endpoint=='http://127.0.0.1:9222' and target is None:client=AdapterClient('http://127.0.0.1:9223',target,clone,config)
                        else:raise
                    if clone=='gunbound-world':
                        from gunbound_learning import GunBoundLearning
                        learning=GunBoundLearning(client)
                    capture=AutoCapture(client);capture.capture_interval=3 if self.performance=='Ligero' else 1.5;client.terrain_interval=5 if self.performance=='Ligero' else 2
                    self.live_endpoint=client.endpoint
                    if clone in ('dragonbound','gunbound-world'):
                        from browser_shortcuts import BrowserShotEvents
                        shot_events=BrowserShotEvents(client.endpoint,client.target['id'],capture.gesture_owner,lambda:self.fire_key,lambda gesture:self.events.put({'status':'fire-gesture','gesture':gesture}))
                        shot_events.start();self.browser_shot_events=shot_events
                    while not stop.is_set():
                        interval,capture.capture_interval,client.terrain_interval=governor.intervals(self.performance,active=sample.get('status')=='live',own_turn=str(sample.get('activePlayer'))==str(sample.get('heroId')))
                        auto=capture.read(capture=self.preview_visible,fire_key=self.fire_key) if clone in ('dragonbound','gunbound-world') else {}
                        if clone=='dragonbound' and not auto.get('geometry',{}).get('active'):
                            sample={'status':'waiting','reason':'Navegador conectado. La captura aparecerá al empezar la partida.'}
                            client.game=None;client.renderer=None
                        else:sample=client.sample()
                        if learning:
                            sample['measurements']=learning.poll();sample['learning_error']=learning.error;sample['weather_cases']=learning.cases;sample['gunbound_paths']=learning.paths
                        sample['_auto']=auto;self.events.put(sample);stop.wait(interval)
                except Exception as e:
                    if not stop.is_set():self.events.put({'status':'waiting','reason':'Buscando el navegador del juego… '+str(e)})
                finally:
                    if learning:learning.close()
                    if shot_events:shot_events.close()
                    if client:
                        try:client.close()
                        except Exception:pass
                stop.wait(2)
        self.worker=threading.Thread(target=run,daemon=True);self.worker.start()
    def apply_auto(self,data):
        auto=data.pop('_auto',{});meta=auto.get('geometry',{})
        gesture=auto.get('fire_gesture');self.page_shortcuts_active=isinstance(gesture,dict)
        if self.consume_fire_gesture(gesture):self.events.put({'status':'fire-shortcut','hero':data.get('heroId')})
        if meta.get('windowHandle'):self.game_window=meta['windowHandle']
        self.capture_dpr=meta.get('dpr',1)
        self.game_visible=bool(self.auto_enabled and meta.get('active') and meta.get('focused') and data.get('status')=='live')
        if data.get('camera'):self.live_camera=data['camera']
        if auto.get('image') is not None:self.image=auto['image'];self.draw()
        players=normalize_players(data.get('players',[]))
        hero=find_hero(players,data.get('heroId'))
        has_target=hero is not None and bool(enemies(players,hero['id']))
        self.auto_visible=bool(self.auto_enabled and self.auto_guide_enabled and has_target and meta.get('active') and meta.get('focused') and data.get('status')=='live')
        area=auto.get('screen_box');points=auto.get('guide_points')
        if area:self.screen_box=area
        if not self.auto_visible or not points:
            self.hide_power_guide();return
        if self.auto_points!=points:
            if self.power_guide:self.power_guide.update_position(*points)
            self.auto_points=points
        self.guide_points=points
        if not self.power_guide:self.power_guide=PowerGuide(getattr(self,'ui_parent',self.root),*points)
        self.draw_force()
    def consume_fire_gesture(self,gesture):
        if not isinstance(gesture,dict) or not isinstance(gesture.get('owner'),str) or not isinstance(gesture.get('count'),int) or not isinstance(gesture.get('at'),(int,float)):return False
        stamp=(gesture['owner'],gesture.get('key'),gesture.get('document'),gesture['count']);previous=self.last_page_gesture
        if previous and stamp[:3]==previous[:3] and stamp[3]<=previous[3]:return False
        self.last_page_gesture=stamp
        return stamp[3]>0 and -.05<=time.time()-gesture['at']/1000<.8
    def apply_live(self,d):
        self.learning_error=d.get('learning_error','');self.reader_status=d.get("status");self.reader_reason=d.get("reason","");self.weather_current=d.get('weatherCurrent','')
        if d.get('status')=='live':d['players']=self.player_tracker.update(d.get('players',[]))
        else:self.player_tracker.reset()
        try:
            if not self.autonomous_training():self.shot_review.observe(d,replace(self.s,environment=dict(self.s.environment)))
        except (OSError,ValueError,TypeError,KeyError):pass
        self.observed_paths=self.trails.update(d.get('shots',[]))
        if self.clone_id=='gunbound-world':
            if d.get('gunbound_paths'):self.gunbound_observed=d['gunbound_paths'];self.gunbound_observed_until=time.monotonic()+5
            if time.monotonic()<getattr(self,'gunbound_observed_until',0):self.observed_paths.update(getattr(self,'gunbound_observed',{}))
            if d.get('weather_cases'):
                try:
                    from local_storage import atomic_write
                    evidence_path=BASE/'climas-gunbound.json'
                    try:cases=json.loads(evidence_path.read_text(encoding='utf-8'))
                    except (OSError,ValueError):cases=[]
                    from weather_validation import crossing_evidence
                    new_cases=[{**case,'evidence':crossing_evidence(case)} for case in d['weather_cases']]
                    self.weather_validation=[e for case in new_cases for e in case['evidence']]
                    cases=(cases+new_cases)[-12:]
                    atomic_write(evidence_path,json.dumps(cases,allow_nan=False).encode())
                except (OSError,ValueError,TypeError):pass
        revision=self.book.revision
        try:changed=[] if self.autonomous_training() else self.book.observe(d,self.clone_id)
        except (OSError,ValueError,TypeError):changed=[];self.book.message='No se pudo guardar la medición; el perfil actual se conserva'
        if changed or self.book.revision!=revision:self.profile_stamp=None;self.last_fingerprint=None;self.mark()
        self.apply_auto(d)
        if d['status']!='live':
            self.last_page_gesture=None;self.page_shortcuts_active=False
            self.result={};self.power.config(text='—');self.details.config(text='Abre el juego e inicia una partida.\nLa guía aparecerá automáticamente.');self.s.environment={};self.draw_force()
            self.last_live=0;self.live_camera=None;self.live_look=None;self.live_launch_offset=None;self.s.launch_offset=None;self.has_position_data=False;self.game_visible=False;self.current_game_power=None;self.hide_overlay();self.trails.reset();self.observed_paths={};self.last_fingerprint=None;self.auto_target_id=None;self.target_hero_id=None;self.selected_target=None;self.live_players=[];self.target_ids={};self.target_name.set('Objetivo automático');self.target_box.config(values=['Objetivo automático'])
            if self.power_guide:self.power_guide.draw({},self.s.max_power)
            if d['status']=='error':self.connect.config(text='Conectar lectura experimental')
            self.status.config(text='●  Esperando partida' if d['status']=='waiting' else '●  Sin conexión',fg=MUTED);self.footer.config(text='Entra a una partida en el navegador conectado.' if d['status']=='waiting' else 'Abre el juego para conectar la guía.');return
        self.last_live=time.monotonic();self.status.config(text='●  En partida',fg=GREEN)
        self.current_game_power=d.get('currentPower');self.draw_force()
        self.live_camera=d.get('camera')
        ps=normalize_players(d.get('players',[]))
        hero=find_hero(ps,d.get('heroId'))
        if not hero:
            self.has_position_data=False;self.result={};self.live_players=ps;self.hide_power_guide();self.hide_overlay();self.footer.config(text='Esperando identificar tu jugador; no se elige otro en su lugar.');return
        self.has_position_data=True;self.live_players=ps
        targets=enemies(ps,hero['id'])
        if not targets:
            self.has_position_data=False;self.result={};self.auto_target_id=None;self.hide_power_guide();self.draw_overlay();self.show_result();return
        self.target_ids={f'{i}. {p["name"]}':p['id'] for i,p in enumerate(targets,1)}
        self.target_box.config(values=['Objetivo automático']+list(self.target_ids))
        if self.target_hero_id!=hero['id']:self.auto_target_id=None;self.selected_target=None;self.target_hero_id=hero['id']
        wanted=self.selected_target if self.selected_target is not None else self.auto_target_id
        target=next((p for p in targets if p['id']==wanted),None) or min(targets,key=lambda p:math.hypot(p['x']-hero['x'],p['y']-hero['y']))
        self.auto_target_id=target['id']
        if self.selected_target is not None:
            self.selected_target=target['id'];self.target_name.set(next(k for k,v in self.target_ids.items() if v==target['id']))
        self.live_camera=d.get('camera')
        self.live_look=hero.get('look');self.s.hero_x=hero['x'];self.s.hero_y=hero['y']
        self.s.target_x=target['x'];self.s.target_y=target['y']
        mid=hero.get('mobile')
        detected_mobile=mobile_name(mid)
        if detected_mobile and self.mobile.get()!=detected_mobile:self.mobile.set(detected_mobile);self.change_mobile()
        if isinstance(hero.get('angle'),(int,float)) and math.isfinite(hero['angle']):self.set_live_value('angle',(hero['angle']+180)%360-180)
        if d.get('wind') is not None:self.set_live_value('wind',d['wind'])
        if d.get('windAngle') is not None:self.set_live_value('wind_angle',d['windAngle'])
        if hero.get('body') is not None:self.set_live_value('body_angle',hero['body'])
        if d.get('selectedShot') in (0,1,2):self.s.selected_shot=d['selectedShot']
        from launch_geometry import muzzle_offset
        self.live_launch_offset=muzzle_offset(hero,self.mobile.get(),self.s.selected_shot)
        terrain=d.get('terrain')
        self.s.environment={}
        if isinstance(terrain,dict):
            if terrain.get('rows'):self.s.environment['terrain']=terrain
            elif terrain.get('surface'):self.s.environment['terrain']={'heights':terrain['surface'],'height':terrain.get('height',1200),'originX':terrain.get('originX',0),'originY':terrain.get('originY',0)}
        self.s.environment['activeWeathers']=d.get('weather',[]) if isinstance(d.get('weather'),list) else []
        if self.clone_id=='gunbound-world':self.s.environment['weatherModel']='gunbound-world'
        self.s.environment['hitTolerance']=18
        self.s.environment['players']=[{k:p[k] for k in ('id','x','y','dead') if k in p} for p in ps if p['id']!=hero['id']]
        self.s.environment['targetId']=target['id']
        underground=self.book.underground_gravity(self.clone_id)
        if underground:self.s.environment['nakUndergroundGravity']=underground
        if isinstance(terrain,dict):self.s.environment['mapHeight']=terrain.get('height',len(terrain.get('surface',[]))) or 1200
        self.vehicle_label.config(text=self.mobile.get())
        black=any((w.get('resolvedTypeId') or w.get('typeId'))==5 for w in self.s.environment['activeWeathers'])
        if not self.fire_busy and time.monotonic()>getattr(self,'notice_until',0):
            self.footer.config(text='Negro: reduce el daño del tiro.' if black else 'La guía se muestra sobre la ventana del juego.',fg=MUTED)
        terrain=d.get('terrain')
        if terrain is not self.last_terrain:
            if terrain!=self.last_terrain:self.terrain_revision+=1
            self.last_terrain=terrain
        fingerprint=(tuple(hero.get(k) for k in ('id','x','y','angle','body','look','mobile')),target['id'],target['x'],target['y'],self.s.selected_shot,d.get('wind'),d.get('windAngle'),self.terrain_revision,json.dumps(self.s.environment['activeWeathers'],sort_keys=True),self.profile_stamp)
        if self.s.mobile=='NAK' and self.s.selected_shot==2:fingerprint+=(tuple((p['id'],p['x'],p['y'],p.get('dead')) for p in ps),)
        if fingerprint!=self.last_fingerprint:self.last_fingerprint=fingerprint;self.mark()
        self.draw();self.draw_overlay()
    def set_live_value(self,key,value):
        try:
            if float(self.vars[key].get())==float(value):return
        except (ValueError,TypeError):pass
        self.vars[key].set(str(value))
    def select_target(self):
        self.selected_target=self.target_ids.get(self.target_name.get());self.last_fingerprint=None;self.mark()
    def cycle_target(self):
        if self.fire_busy:return
        target=next_target(self.live_players,self.target_hero_id,self.auto_target_id)
        if target is None:return
        self.selected_target=target;self.auto_target_id=target
        p=next(p for p in self.live_players if p.get('id')==target)
        self.s.target_x=p['x'];self.s.target_y=p['y'];self.result={}
        for label,value in self.target_ids.items():
            if value==target:self.target_name.set(label);break
        self.last_fingerprint=None;self.mark();self.draw_overlay()
    def start_target_shortcut(self):
        self.shortcuts=GameShortcuts(lambda:(bool(self.auto_enabled and self.has_position_data and self.last_live and time.monotonic()-self.last_live<4),self.game_window,self.target_hero_id),lambda hero:self.events.put({'status':'target-shortcut','hero':hero}),lambda hero:None if self.page_shortcuts_active else self.events.put({'status':'fire-shortcut','hero':hero}),self.target_key,self.fire_key,lambda hero:self.events.put({'status':'cancel-shortcut','hero':hero}))
        self.shortcuts.start()
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
        from rounded_controls import RoundedEntry
        entry=RoundedEntry(win,font=('Consolas',10));entry.insert(0,url);entry.pack(fill='x',padx=20,ipady=7);entry.select_range(0,'end')
        self.button(win,'Copiar enlace',lambda:(self.root.clipboard_clear(),self.root.clipboard_append(url))).pack(pady=12)
        self.button(win,'Abrir visor aquí',lambda:webbrowser.open(url)).pack()
    def tick(self):
        try:self.tick_once()
        except Exception as error:
            import traceback
            self.last_error=type(error).__name__+': '+str(error)[:180]
            try:(BASE/'ultimo-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
            except OSError:pass
            self.result={};self.computing=False;self.dirty=True
        finally:
            self.root.after(40 if self.game_visible else 150,self.tick)
    def tick_once(self):
        from control_lifecycle import sync_control_mode
        sync_control_mode(self)
        pending=[]
        while not self.events.empty():pending.append(self.events.get_nowait())
        live=[e for e in pending if e.get('status') not in ('calculated','target-shortcut','fire-shortcut','fire-gesture','fire-finished','fire-confirmed','cancel-shortcut','training-observation','training-settings')]
        # Consume the latest state before results/shortcuts; old frames must not
        # delay the game or allow an obsolete calculation to replace a new one.
        pending=([live[-1]] if live else [])+[e for e in pending if e.get('status') in ('calculated','target-shortcut','fire-shortcut','fire-gesture','fire-finished','fire-confirmed','cancel-shortcut','training-observation','training-settings')]
        for event in pending:
            if event.get('status')=='training-settings':
                try:
                    self.apply_live(event['state'])
                    if not self.has_position_data:raise ValueError('El Lab espera las posiciones del jugador y objetivo')
                    event['response']['settings']=replace(self.read(),environment=dict(self.s.environment))
                except Exception as error:event['response']['error']=str(error)
                finally:event['ready'].set()
                continue
            if event.get('status')=='training-observation':
                try:
                    from training_progress import share_observation
                    progress=share_observation(self.book,event.get('observation'),event.get('release'))
                    if self.training_session:self.training_session.lab_progress=progress
                except (OSError,ValueError,TypeError,KeyError):self.book.message='La medición no pudo incorporarse; se conserva el ajuste anterior'
                self.profile_stamp=None;self.mark();continue
            if event.get('status')=='fire-gesture':
                if self.consume_fire_gesture(event.get('gesture')):
                    self.fire_shortcut_count+=1;self.trigger_auto_fire()
                continue
            if event.get('status')=='cancel-shortcut':
                self.cancel_actions()
                continue
            if event.get('status')=='fire-shortcut':
                self.fire_shortcut_count+=1
                if event.get('hero')==self.target_hero_id:self.trigger_auto_fire()
                continue
            if event.get('status')=='fire-confirmed':
                confirmation=event['confirmation'];self.last_shot_confirmation=confirmation
                if confirmation['status']=='confirmed' and confirmation.get('release'):self.book.note_release(confirmation['release'])
                continue
            if event.get('status')=='fire-finished':
                self.fire_busy=False;self.last_fire_message=event['message'];self.notice_until=time.monotonic()+4;self.footer.config(text=event['message'],fg=GREEN if event['message'].startswith('Tiro confirmado') else ORANGE);continue
            if event.get('status')=='target-shortcut':
                if event.get('hero')==self.target_hero_id and self.auto_enabled and self.has_position_data and self.last_live and time.monotonic()-self.last_live<4:self.shortcut_count+=1;self.cycle_target()
                continue
            if event.get('status')=='calculated':
                self.computing=False
                if event['generation']==self.compute_generation and not self.dirty:
                    self.result=event['result'];self.result_context=event['context'];self.last_solve_seconds=event.get('solve_seconds');self.show_result(event.get('error'))
                    if self.result.get('blocked'):
                        try:self.replays.record(self.s,'blocked',self.result)
                        except (OSError,ValueError,TypeError):pass
            else:self.apply_live(event)
        if self.last_live and time.monotonic()-self.last_live>4:
            self.status.config(text='●  Esperando datos',fg=MUTED);self.auto_visible=False;self.hide_overlay();self.hide_power_guide()
            if self.power_guide:self.power_guide.draw({},self.s.max_power)
        if self.dirty and not self.computing and not self.autonomous_training():
            self.dirty=False;self.compute_generation+=1
            try:
                settings=replace(self.read(),environment=dict(self.s.environment));profile_required=getattr(self,'profile_required',False);missing_reason=getattr(self,'profile_missing_reason','Falta un perfil aplicable.');generation=self.compute_generation;context=self.visual_context();self.computing=True
                self.power.config(text='…')
                self.draw_force()
                if self.overlay:self.draw_overlay()
                preview_power=self.current_game_power if isinstance(self.current_game_power,(int,float)) and 1<=self.current_game_power<=settings.max_power else None
                def calculate(settings=settings,generation=generation,preview_power=preview_power,context=context,profile_required=profile_required,missing_reason=missing_reason):
                    try:
                        started=time.perf_counter();result={'reachable':False,'reason':missing_reason} if profile_required else solve(settings);solve_seconds=time.perf_counter()-started
                        if not result.get('reachable') and not result.get('blocked') and preview_power:
                            from physics_extensions import trajectory
                            preview=trajectory(settings,preview_power,step=.06,include_deployment=True)
                            result['preview_paths']=[[(p[0],p[1]) for p in path] for path in preview['display_paths']];result['preview_power']=preview_power
                        self.events.put({'status':'calculated','generation':generation,'context':context,'result':result,'solve_seconds':solve_seconds})
                    except Exception as e:self.events.put({'status':'calculated','generation':generation,'context':context,'result':{},'error':str(e)})
                threading.Thread(target=calculate,daemon=True).start()
            except Exception as e:self.result={};self.show_result(str(e))
        self.process_pending_fire()
        if (self.dirty or self.computing) and time.monotonic()-self.last_computed>1.5:
            self.draw_force();self.draw_overlay()
        self.preview_visible=self.root.state()=='normal' and self.map_expanded
        self.shared['updated']=time.time()
        self.shared['source']='experimental' if self.last_live and time.monotonic()-self.last_live<4 else 'manual'
        if '--diagnostics' in sys.argv and time.monotonic()-getattr(self,'diagnostic_clock',0)>1:
            self.diagnostic_clock=time.monotonic()
            health={'version':PROGRAM_VERSION,'training':{'active':bool(self.training_session and self.training_session.running),'message':self.training_session.status if self.training_session else '', 'shots':self.training_session.shots if self.training_session else 0},'weather_validation':getattr(self,'weather_validation',[]),'learning_error':getattr(self,'learning_error',''),'learning_status':self.book.message,'learning_samples':len(self.book.records.get(self.book.key(self.clone_id,self.s.mobile,self.s.selected_shot),{}).get('samples',[])),'reader_status':getattr(self,'reader_status',None),'reader_reason':getattr(self,'reader_reason',''),'result_reason':self.result.get('reason'),'guide_visible':bool(self.power_guide and self.power_guide.win.winfo_viewable()),'game_visible':self.game_visible,'bar_detected':bool(self.guide_points),'updated':time.time(),'connected':bool(self.last_live and time.monotonic()-self.last_live<4),'map_detected':bool(self.s.environment.get('terrain')),'camera_detected':bool(self.live_camera and self.live_camera.get('renderWidth')),'weather':[w.get('resolvedTypeId') or w.get('typeId') for w in self.s.environment.get('activeWeathers',[])],'players_detected':len(self.live_players),'overlay_visible':bool(self.overlay and self.overlay.visible),'power':self.result.get('power'),'computing':self.computing,'last_error':getattr(self,'last_error',None),'target':self.auto_target_id,'enemies_detected':len(enemies(self.live_players,self.target_hero_id)),'preview_capture':self.preview_visible,'solve_seconds':getattr(self,'last_solve_seconds',None),'shortcut_events':self.shortcut_count,'fire_shortcut_events':self.fire_shortcut_count,'fire_busy':self.fire_busy,'fire_pending':bool(self.pending_fire),'last_fire_message':self.last_fire_message,'page_shortcuts_active':self.page_shortcuts_active,'shortcut_ready':bool(getattr(self,'shortcuts',None) and self.shortcuts.ready),'shortcut_error':getattr(getattr(self,'shortcuts',None),'error',None)}
            try:(BASE/'estado-live.json').write_text(json.dumps(health,indent=2),encoding='utf-8')
            except OSError:pass

    def compute(self):
        self.compute_generation+=1;self.result={'reachable':False,'reason':getattr(self,'profile_missing_reason','Falta un perfil aplicable.')} if getattr(self,'profile_required',False) else solve(self.read());self.result_context=self.visual_context();self.show_result();return self.result
    def show_result(self,error=None):
        if not self.has_position_data and self.auto_enabled:
            self.result={};self.power.config(text='—');self.details.config(text='Abre el juego e inicia una partida.\nLa guía aparecerá automáticamente.');self.draw();self.draw_force();return
        if error:
            self.result={};self.power.config(text='—');self.details.config(text=error);self.shared={'error':error,'updated':time.time()}
        else:
            self.last_computed=time.monotonic()
            if self.result.get('reachable'):
                r=self.result
                if self.clone_id=='gunbound-world':r['quality']='Salida medida · viento aproximado' if not getattr(self,'profile_required',True) else 'GunBound World: perfil sin calibrar';r['approximate']=True
                self.power.config(text=str(r['power']),fg=ORANGE if r['approximate'] else GREEN)
                cluster=f' · {r.get("cluster_hits",0)}/{r.get("projectile_count",3)} bolas próximas' if self.s.mobile=="TRICO" and self.s.selected_shot==1 else ""
                self.details.config(text=f'{"Fuerza aproximada" if r["approximate"] else "Fuerza recomendada"}\n{self.s.mobile} · Tiro {self.s.selected_shot+1 if self.s.selected_shot<2 else "SS"}{cluster}')
            else:
                blocked=self.result.get('blocked');reference=self.result.get('guide_power')
                self.power.config(text=str(reference) if reference is not None else '—',fg=ORANGE)
                text='Terreno bloquea el tiro · ajusta el ángulo' if blocked else 'Ajusta el ángulo para alcanzar el objetivo'
                if self.result.get('preview_power'):text+=f'\nReferencia a fuerza {self.result["preview_power"]:g}'
                self.details.config(text=text)
            if self.server:self.shared={'settings':asdict(self.s),'result':self.result,'camera':self.live_camera,'viewport':self.viewport,'clone':self.clone_id,'updated':time.time()}
        from ui_shell import refresh
        refresh(self)
        self.draw();self.draw_overlay();self.draw_force()
    def close(self):
        if getattr(self,'training_session',None):
            self.training_session.stop()
            if self.training_session.thread:self.training_session.thread.join(timeout=1)
        if getattr(self,'cloud_runtime',None):self.cloud_runtime.stopped=True
        if hasattr(self,'shortcuts'):self.shortcuts.close()
        self.pending_fire=None;self.fire_cancel.set();self.live_stop.set();self.hide_overlay();self.hide_power_guide()
        if hasattr(self,'fire_controller'):self.fire_controller.cancel()
        if self.server:self.server.shutdown();self.server.server_close()
        self.root.destroy()

if __name__=='__main__':
    from desktop_shell import SingleInstance
    instance=SingleInstance('DragonLab.LocalCompanion') if '--check' not in sys.argv else None
    if instance and not instance.primary:instance.close();sys.exit(3)
    root=tk.Tk()
    if '--check' in sys.argv:root.withdraw()
    if '--minimized' in sys.argv:root.iconify()
    app=App(root)
    if '--check' in sys.argv:root.after(500,app.close)
    elif '--open-game' in sys.argv:root.after(200,app.open_game_browser)
    if '--smoke' in sys.argv:
        root.attributes('-topmost',True);root.lift()
        root.after(700,lambda:ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(BASE/'vista-previa.png'))
        root.after(1100,app.close)
    root.mainloop()
    if instance:instance.close()

