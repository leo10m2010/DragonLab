"""Native launcher: explicit license, installed versions and verified updates."""
import json,pathlib,subprocess,sys,threading,queue,urllib.request,webbrowser,tkinter as tk,re,hashlib,time
from tkinter import messagebox
from datetime import datetime
from rounded_widgets import RoundedButton,RoundedPanel
from rounded_controls import RoundedEntry,RoundedSwitch,RoundedChoice,RoundedScroll
from mascot import DragonMascot
from cloud_client import CloudClient,CloudError,download_verified
from local_storage import atomic_write
from app_version import LAUNCHER_VERSION,PROGRAM_VERSION,DEMO_ALLOWED
from engine_host import EngineHost
from game_catalog import GAMES
from desktop_shell import style_window,enable_high_dpi,monitor_work_area,place_in_work_area,SingleInstance,restore_launcher
from theme import BG,PANEL,FIELD,TEXT,MUTED,GREEN,GREEN_HOVER,DISABLED,LINE,FONT,MONO
BASE=pathlib.Path(sys.executable).parent if getattr(sys,'frozen',False) else pathlib.Path(__file__).parent
INK=TEXT;ACCENT=GREEN;REPO='leo10m2010/DragonLab'

class LauncherButton(RoundedButton):
    def __init__(self,master,**options):
        defaults={'disabledbackground':DISABLED,'disabledforeground':MUTED,'focuscolor':ACCENT}
        defaults.update(options);super().__init__(master,**defaults)

class ConsentSwitch(RoundedSwitch):
    def __init__(self,master,command=None,state='normal',**options):
        self.command=command;self.enabled=state!='disabled';super().__init__(master,**options);self.configure(state=state)
    def configure(self,cnf=None,**options):
        if 'state' in options:self.enabled=options['state']!='disabled'
        return super().configure(cnf,**options)
    config=configure
    def toggle(self):
        if self.enabled:
            self.variable.set(not self.variable.get())
            if self.command:self.command()
        return 'break'

def calibration_revision(path):
    try:
        data=json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
        if not isinstance(data,list) or not data:return 'Sin sincronizar'
        return 'rev. '+hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:8]
    except (OSError,ValueError,TypeError):return 'Sin sincronizar'

def installed_version(directory):
    try:
        data=json.loads((pathlib.Path(directory)/'installed-release.json').read_text(encoding='utf-8'))
        version=data['version'];name='DragonLab-Cloud-'+version+'.exe'
        if re.fullmatch(r'\d+\.\d+\.\d+',version) and (pathlib.Path(directory)/name).is_file():return version
    except (OSError,ValueError,TypeError,KeyError):pass
    return None

def fetch_manifest(repo=REPO):
    if repo!=REPO:raise CloudError('Repositorio no autorizado.')
    req=urllib.request.Request('https://api.github.com/repos/'+repo+'/releases/latest',headers={'User-Agent':'DragonLabLauncher','Accept':'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(req,timeout=15) as response:release=json.load(response)
        asset=next((a for a in release.get('assets',[]) if a['name']=='dragonlab-release.json'),None)
        prefix='https://github.com/'+repo+'/releases/download/'
        if not asset or not asset['browser_download_url'].startswith(prefix):raise CloudError('Todavía no hay una versión Cloud compatible publicada.')
        with urllib.request.urlopen(asset['browser_download_url'],timeout=15) as response:manifest=json.load(response)
    except CloudError:raise
    except Exception:raise CloudError('No se pudo comprobar la actualización en GitHub.') from None
    if manifest.get('schema')!=1 or manifest.get('asset')!='DragonLab-Cloud.exe' or not re.fullmatch(r'\d+\.\d+\.\d+',manifest.get('version','')) or not re.fullmatch(r'[0-9a-f]{64}',manifest.get('sha256','')) or not manifest.get('url','').startswith(prefix):raise CloudError('Manifest de actualización inválido.')
    return manifest

class Launcher:
    def __init__(self,root,demo=False):
        demo=bool(demo and DEMO_ALLOWED)
        self.training_mode=requested_training_mode(sys.argv,sys.executable,getattr(sys,'frozen',False))
        self.root=root;root.title('DragonLab · '+('Automático' if self.training_mode else 'Manual')+' · Launcher '+LAUNCHER_VERSION)
        root.configure(bg=BG);root.resizable(True,True);root.minsize(600,480)
        # Choose the initial client size once. State/messages never resize it.
        root.geometry('720x750')
        self.busy=False;self.client=None;self.closed=False;self.events=queue.Queue();self.manifest=None;self.demo=demo;self.engine=None;self.dialog=None;self.opening_until=0
        self.authenticated=False;self.access_active=False;self.details_open=False;self.scroll_job=None
        self.email=tk.StringVar();self.password=tk.StringVar();self.share=tk.BooleanVar();self.game=tk.StringVar(value='DragonBound')
        requested=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--clone=')),None)
        if requested:self.game.set(next((name for name,g in GAMES.items() if g['id']==requested),'DragonBound'))
        header=tk.Frame(root,bg=BG);header.pack(fill='x',padx=26,pady=(20,16));header.columnconfigure(0,weight=1)
        brand_column=tk.Frame(header,bg=BG);brand_column.grid(row=0,column=0,sticky='w')
        brand_row=tk.Frame(brand_column,bg=BG);brand_row.pack(anchor='w')
        tk.Label(brand_row,text='DragonLab',font=(FONT,-25,'bold'),bg=BG,fg=INK).pack(side='left')
        tk.Label(brand_row,text='  /  '+LAUNCHER_VERSION,font=(MONO,-11),bg=BG,fg=MUTED).pack(side='left',pady=(6,0))
        self.mode_label=tk.Label(brand_column,text='AUTOMÁTICO · EXPERIMENTAL' if self.training_mode else 'COMPAÑERO DE JUEGO · MANUAL',font=(MONO,-10),bg=BG,fg=MUTED);self.mode_label.pack(anchor='w',pady=(4,0))
        selection=tk.Frame(header,bg=BG);selection.grid(row=0,column=1,sticky='e',padx=(16,0))
        tk.Label(selection,text='JUEGO',font=(MONO,-10),bg=BG,fg=MUTED).pack(anchor='w',padx=10,pady=(0,4))
        self.game_choice=RoundedChoice(selection,textvariable=self.game,values=list(GAMES),width=21,font=(FONT,-13));self.game_choice.pack(fill='x')
        self.footer=tk.Frame(root,bg=BG)
        self.settings_button=LauncherButton(self.footer,text='Atajos',command=self.open_settings,bg=BG,fg=MUTED,font=(FONT,-12),pady=7,padx=10);self.settings_button.pack(side='left')
        self.help_button=LauncherButton(self.footer,text='Cómo usarlo',command=self.help,bg=BG,fg=MUTED,font=(FONT,-12),pady=7,padx=10);self.help_button.pack(side='left')
        self.performance_button=LauncherButton(self.footer,text='Rendimiento',command=self.open_performance,bg=BG,fg=MUTED,font=(FONT,-12),pady=7,padx=10);self.performance_button.pack(side='left')
        self.support_button=LauncherButton(self.footer,text='Soporte',command=self.open_support,bg=BG,fg=MUTED,font=(FONT,-12),pady=7,padx=10);self.support_button.pack(side='right')
        self.viewport_shell=tk.Frame(root,bg=BG);self.viewport_shell.pack(fill='both',expand=True)
        self.viewport=tk.Canvas(self.viewport_shell,bg=BG,highlightthickness=0,takefocus=False)
        self.viewport.pack(side='left',fill='both',expand=True)
        self.scrollbar=RoundedScroll(self.viewport_shell,command=self.viewport.yview)
        self.viewport.configure(yscrollcommand=self.scrollbar.set)
        self.content=tk.Frame(self.viewport,bg=BG);self.content_item=self.viewport.create_window(0,0,window=self.content,anchor='nw')
        self.viewport.bind('<Configure>',self.resize_content);self.content.bind('<Configure>',self.schedule_scroll)
        root.bind('<MouseWheel>',self.scroll_wheel,add='+')
        self.login_page=tk.Frame(self.content,bg=BG);self.dashboard_page=tk.Frame(self.content,bg=BG)
        login_panel=RoundedPanel(self.login_page,PANEL,radius=24,padding=26);login_panel.pack(fill='x',padx=26,pady=(4,0))
        form=login_panel.body
        tk.Label(form,text='Bienvenido a tu guía.',font=(FONT,-28,'bold'),bg=PANEL,fg=INK,justify='left').pack(anchor='w',pady=(4,10))
        tk.Label(form,text='Inicia sesión para abrir tu juego.',font=(FONT,-14),bg=PANEL,fg=MUTED).pack(anchor='w',pady=(0,22))
        self.login_area=tk.Frame(form,bg=PANEL);self.login_area.pack(fill='x')
        for title,var,secret in [('Correo',self.email,False),('Contraseña',self.password,True)]:
            tk.Label(self.login_area,text=title,font=(FONT,-13),bg=PANEL,fg=MUTED).pack(anchor='w',pady=(0,6))
            entry=RoundedEntry(self.login_area,textvariable=var,show='●' if secret else '',font=(FONT,-15),bg=FIELD,fg=INK,insertbackground=INK,selectbackground=ACCENT,selectforeground=BG);entry.pack(fill='x',pady=(0,16));entry.entry.bind('<Return>',lambda e:self.login())
        self.login_button=LauncherButton(form,text='Iniciar sesión  →',command=self.login,bg=ACCENT,fg=BG,activebackground=GREEN_HOVER,activeforeground=BG,font=(FONT,-15,'bold'),pady=13);self.login_button.pack(fill='x',pady=(4,6))
        self.login_status=tk.Label(self.login_page,text='Tu cuenta es personal. Entra con tu correo y contraseña.',wraplength=510,justify='center',bg=BG,fg=MUTED,font=(FONT,-13));self.login_status.pack(fill='x',padx=34,pady=20)
        panel=RoundedPanel(self.dashboard_page,PANEL,radius=24,padding=20);self.hero_panel=panel;panel.pack(fill='x',padx=26,pady=(4,0))
        body=panel.body
        top=tk.Frame(body,bg=PANEL);top.pack(fill='x')
        tk.Label(top,text='SESIÓN INDEPENDIENTE' if self.training_mode else 'TU GUÍA',font=(MONO,-10),bg=PANEL,fg=MUTED).pack(side='left')
        self.account_button=LauncherButton(top,text='Cuenta y versión',command=self.open_details,bg=PANEL,fg=MUTED,font=(FONT,-12),padx=8,pady=4);self.account_button.pack(side='right')
        self.headline=tk.Label(body,text='Practica por separado.' if self.training_mode else 'Todo listo para jugar.',font=(FONT,-29,'bold'),bg=PANEL,fg=INK);self.headline.pack(anchor='w',pady=(12,8))
        self.license_title=tk.Label(body,font=(FONT,-12,'bold'),bg=PANEL,fg=TEXT,wraplength=590,justify='left');self.license_title.pack(anchor='w')
        self.license_detail=tk.Label(body,font=(FONT,-12),bg=PANEL,fg=MUTED,wraplength=590,justify='left');self.license_detail.pack(anchor='w',pady=(4,0))
        status_row=tk.Frame(body,bg=PANEL);status_row.pack(fill='x',pady=(14,10))
        self.mascot=DragonMascot(status_row);self.mascot.pack(side='left',padx=(0,14))
        state_text=tk.Frame(status_row,bg=PANEL);state_text.pack(side='left',fill='both',expand=True)
        self.dashboard_status=tk.Label(state_text,wraplength=460,justify='left',anchor='w',bg=PANEL,fg=TEXT,font=(FONT,-14,'bold'));self.dashboard_status.pack(fill='x',pady=(8,6))
        self.shortcut_hint=tk.Label(state_text,text='Dos sesiones de prueba independientes' if self.training_mode else 'Ctrl · cambiar objetivo',font=(MONO,-11),bg=PANEL,fg=MUTED,anchor='w',justify='left',wraplength=460);self.shortcut_hint.pack(fill='x')
        self.play_button=LauncherButton(body,text=self.start_caption(),command=self.toggle_game,bg=ACCENT,fg=BG,activebackground=GREEN_HOVER,activeforeground=BG,font=(FONT,-17,'bold'),pady=13,state='disabled');self.play_button.pack(fill='x',pady=(4,4))
        self.game_note=tk.Label(body,bg=PANEL,fg=MUTED,font=(FONT,-12),wraplength=590,justify='left');self.game_note.pack(anchor='w',pady=(9,2))
        recommended=RoundedPanel(self.dashboard_page,PANEL,radius=24,padding=18);recommended.pack(fill='x',padx=26,pady=(12,0))
        recommendation_row=tk.Frame(recommended.body,bg=PANEL);recommendation_row.pack(fill='x');recommendation_row.columnconfigure(0,weight=1)
        tk.Label(recommendation_row,text='Carros para tu próxima partida',bg=PANEL,fg=TEXT,font=(FONT,-15,'bold')).grid(row=0,column=0,sticky='w')
        self.catalog_button=LauncherButton(recommendation_row,text='Ver carros  →',command=self.open_catalog,bg=FIELD,fg=TEXT,font=(FONT,-12),pady=8,padx=12);self.catalog_button.grid(row=0,column=1,rowspan=2,padx=(12,0),sticky='e')
        self.recommended_text=tk.Label(recommendation_row,text='Consulta cada carro, sus balas y lo que queda por aprender.',bg=PANEL,fg=MUTED,font=(FONT,-12),wraplength=410,justify='left');self.recommended_text.grid(row=1,column=0,sticky='w',pady=(6,0))
        versions=RoundedPanel(self.dashboard_page,PANEL,radius=22,padding=18);self.versions_panel=versions
        row=tk.Frame(versions.body,bg=PANEL);row.pack(fill='x')
        self.program_label=tk.Label(row,text='Motor integrado · v'+PROGRAM_VERSION,font=(FONT,-13,'bold'),bg=PANEL,fg=INK);self.program_label.pack(side='left')
        self.update_button=LauncherButton(row,text='Buscar actualización',command=self.check_update,bg=FIELD,fg=INK,font=(FONT,-12),pady=7,state='disabled');self.update_button.pack(side='right')
        self.calibration_label=tk.Label(versions.body,text='Calibraciones · sin sincronizar',font=(FONT,-12),bg=PANEL,fg=MUTED,wraplength=580,justify='left');self.calibration_label.pack(anchor='w',pady=(8,0))
        self.update_label=tk.Label(versions.body,text='Actualizaciones · sin comprobar',font=(FONT,-12),bg=PANEL,fg=MUTED,wraplength=580,justify='left');self.update_label.pack(anchor='w',pady=(5,0))
        self.account_row=tk.Frame(versions.body,bg=PANEL);self.account_row.pack(fill='x',pady=(12,0))
        self.panel_button=LauncherButton(self.account_row,text='Abrir panel de cuenta',command=self.open_account,bg=FIELD,fg=TEXT,font=(FONT,-12),pady=7);self.panel_button.pack(side='left')
        self.logout_button=LauncherButton(self.account_row,text='Cerrar sesión',command=self.logout,bg=PANEL,fg=MUTED,font=(FONT,-12),pady=7);self.logout_button.pack(side='right')
        privacy=tk.Frame(self.dashboard_page,bg=BG);self.privacy=privacy;privacy.pack(fill='x',padx=32,pady=(14,16))
        self.consent=ConsentSwitch(privacy,text='Ayudar a mejorar las calibraciones',variable=self.share,command=self.change_consent,state='disabled',font=(FONT,-12));self.consent.pack(anchor='w')
        tk.Label(privacy,text='Opcional · solo mediciones. Sin capturas, chats ni nombres.',font=(FONT,-11),bg=BG,fg=MUTED,wraplength=540,justify='left').pack(anchor='w',pady=(3,0))
        self.game.trace_add('write',lambda *args:self.game_changed())
        self.game_changed();self.show_login();root.protocol('WM_DELETE_WINDOW',self.close);root.after(100,self.poll)
        if self.demo:
            root.title('DragonLab · '+('Automático' if self.training_mode else 'Manual')+' · PRUEBA · Launcher '+LAUNCHER_VERSION)
            self.login_area.pack_forget();self.login_button.config(text='Entrar a la prueba  →');self.status.config(text='Prueba local. No necesitas correo ni contraseña.')
            self.sync_controls()
            if '--check' not in sys.argv:root.after(150,self.enter_demo)
            return
        try:self.client=CloudClient(BASE/'cloud-desktop.json')
        except CloudError:self.status.config(text='Servidor pendiente de configuración. Consulta la guía de activación.')
        self.sync_controls();self.refresh_versions()
        if self.client and self.client.session and '--check' not in sys.argv:self.run(self.client.require_access,self.show_account)
    def resize_content(self,event):
        if event.widget is not self.viewport:return
        width=max(1,min(920,event.width))
        if getattr(self,'content_width',None)!=width:
            self.content_width=width;self.viewport.itemconfigure(self.content_item,width=width)
            for label,padding in ((self.login_status,70),(self.license_title,100),(self.license_detail,100),(self.game_note,100),(self.dashboard_status,220),(self.shortcut_hint,220),(self.recommended_text,260)):
                label.configure(wraplength=max(180,width-padding))
        self.viewport.coords(self.content_item,max(0,(event.width-width)/2),0)
        self.schedule_scroll()
    def schedule_scroll(self,event=None):
        if not self.closed and self.scroll_job is None:self.scroll_job=self.root.after_idle(self.layout_scroll)
    def layout_scroll(self):
        self.scroll_job=None
        if self.closed:return
        width=self.viewport.winfo_width();height=self.content.winfo_reqheight();viewport_height=self.viewport.winfo_height()
        self.viewport.configure(scrollregion=(0,0,width,height))
        if height>viewport_height+1:
            if not self.scrollbar.winfo_manager():self.scrollbar.pack(side='right',fill='y')
        else:
            self.viewport.yview_moveto(0)
            if self.scrollbar.winfo_manager():self.scrollbar.pack_forget()
    def scroll_wheel(self,event):
        if self.scrollbar.winfo_manager() and not isinstance(event.widget,RoundedChoice):self.viewport.yview_scroll(-int(event.delta/120),'units')
    def fit_window(self,width=None,height=None):
        # Kept for callers from older integrations; user geometry is authoritative.
        self.schedule_scroll()
    def sync_controls(self):
        enabled=self.authenticated and self.access_active and not self.busy
        self.login_button.config(state='normal' if not self.busy and (self.demo or self.client) else 'disabled')
        for control in (self.play_button,self.settings_button,self.catalog_button):control.config(state='normal' if enabled else 'disabled')
        self.game_choice.config(state='readonly' if self.authenticated and not self.busy else 'disabled')
        self.logout_button.config(state='normal' if self.authenticated and not self.busy else 'disabled')
        self.update_button.config(state='normal' if self.authenticated and not self.demo and not self.busy else 'disabled')
        self.consent.config(state='normal' if self.authenticated and self.client and not self.busy else 'disabled')
        self.panel_button.config(state='normal' if not self.busy and self.client and getattr(self.client,'config',{}).get('panelUrl','').startswith('https://') else 'disabled')
        self.mascot.set_state('loading' if self.busy else 'ready')
    def show_login(self):
        self.authenticated=False;self.access_active=False;self.dashboard_page.pack_forget();self.footer.pack_forget();self.login_page.pack(fill='both',expand=True)
        self.status=self.login_status;self.viewport.yview_moveto(0);self.sync_controls();self.schedule_scroll()
    def show_dashboard(self,account):
        self.authenticated=True;self.access_active=bool(account.get('active'));self.login_page.pack_forget();self.dashboard_page.pack(fill='both',expand=True)
        self.footer.pack(side='bottom',fill='x',padx=22,pady=(8,10),before=self.viewport_shell)
        self.status=self.dashboard_status;self.viewport.yview_moveto(0);self.sync_controls();self.schedule_scroll()
    def open_details(self):
        if not self.authenticated:return
        self.details_open=not self.details_open
        if self.details_open:
            options={'fill':'x','padx':26,'pady':(12,0)}
            if self.privacy.winfo_manager():options['before']=self.privacy
            self.versions_panel.pack(**options)
        else:self.versions_panel.pack_forget()
        self.account_button.config(text='Ocultar detalles' if self.details_open else 'Cuenta y versión');self.schedule_scroll()
    def open_catalog(self):
        if not self.authenticated or not self.access_active or self.busy:return
        try:
            from catalog_ui import open_catalog
            open_catalog(self.get_engine().app,game_id=GAMES[self.game.get()]['id']);self.refresh_recommendations()
        except Exception:self.status.config(text='No se pudo abrir el catálogo. Vuelve a intentarlo.');self.mascot.set_state('error')
    def open_performance(self):
        try:
            from performance_ui import open_performance
            open_performance(self.root,app_provider=lambda:self.engine.app if self.engine else None)
        except Exception:self.guide('Rendimiento',[('Sin datos todavía','Abre la guía para ver la actividad de captura y cálculo. Puedes consultar esta ventana sin abrir el juego.')])
    def refresh_recommendations(self):
        names=[]
        if self.engine:
            try:
                from mobile_catalog import recommendations
                names=[str(item['name']) for item in recommendations(self.engine.app,GAMES[self.game.get()]['id'])[:3]]
            except (ImportError,AttributeError,KeyError,TypeError):pass
        self.recommended_text.config(text=' · '.join(names) if names else 'Consulta cada carro, sus balas y lo que queda por aprender.')
    def open_support(self):
        self.guide('Soporte de DragonLab',[
            ('Antes de informar un problema','Consulta Cómo usarlo y Rendimiento. Si la guía está pendiente, revisa el juego, la partida y la modalidad seleccionada.'),
            ('Comparte solo lo necesario','Describe qué ocurrió y qué esperabas. Evita incluir contraseñas, chats, nombres o datos de tu cuenta.')],link=('Abrir incidencias en GitHub','https://github.com/'+REPO+'/issues'))
    def enter_demo(self):
        if not self.demo or self.closed:return
        self.show_dashboard({'active':True});self.license_title.config(text='ACCESO LOCAL · LISTO')
        self.headline.config(text='Tu sesión de práctica.' if self.training_mode else 'Todo listo para jugar.')
        self.license_detail.config(text='Dos cuentas, una sesión de entrenamiento.' if self.training_mode else 'Fuerza y trayectoria, justo donde las necesitas.')
        self.account_row.pack_forget()
        self.privacy.pack_forget();self.consent.config(state='disabled');self.share.set(False)
        self.update_button.config(state='disabled');self.update_label.config(text='Prueba local · actualizaciones Cloud desactivadas')
        self.program_label.config(text='Motor integrado · v'+PROGRAM_VERSION)
        self.calibration_label.config(text='Calibraciones · se utilizan las del programa local')
        self.status.config(text='Preparado para entrenar' if self.training_mode else 'Preparado para jugar')
        self.sync_controls();self.schedule_scroll()
        if '--auto-game' in sys.argv and '--check' not in sys.argv:
            sys.argv.remove('--auto-game');self.root.after(100,self.play)
    def refresh_versions(self):
        directory=self.client.directory if self.client else BASE
        version=installed_version(directory)
        self.program_label.config(text='Programa instalado · v'+version if version else 'Motor integrado · v'+PROGRAM_VERSION)
        self.calibration_label.config(text='Calibraciones · '+calibration_revision(directory/'published-profiles.json'))
    def run(self,work,done):
        if self.busy or self.closed:return
        self.busy=True;self.sync_controls()
        def thread():
            try:self.events.put((work(),None,done))
            except Exception as e:self.events.put((None,str(e),done))
        threading.Thread(target=thread,daemon=True).start()
    def poll(self):
        if self.closed:return
        while not self.events.empty():self.finish(*self.events.get_nowait())
        if self.engine and not self.engine.window.winfo_exists():
            self.engine=None;self.sync_controls();self.play_button.config(text=self.start_caption())
            self.status.config(text='La guía se detuvo. Pulsa Jugar para volver a conectarte.')
        if self.engine and not self.busy:
            from product_status import capture_status
            app=self.engine.app;worker=getattr(app,'worker',None)
            if worker and worker.is_alive() or getattr(app,'training_session',None):
                label,message=capture_status(app)
                button='Detener automático' if self.training_mode else 'Pausar guía'
                if self.play_button.cget('text')!=button:self.play_button.config(text=button)
                status=label+' · '+message
                if self.status.cget('text')!=status:self.status.config(text=status)
                self.mascot.set_state('error' if label.startswith(('Revisar','Sin potencia')) else 'loading' if label in ('Calculando','Identificando jugadores','Deteniendo') else 'active' if label in ('Guía activa','Entrenando','Aplicando tiro') else 'ready')
                if not self.training_mode:
                    target=getattr(app,'target_key','Ctrl');fire=getattr(app,'fire_key','Q')
                    hint=f'{target} · cambiar objetivo'+(f'     {fire} · aplicar fuerza' if getattr(app,'auto_shot_enabled',False) else '')
                    if self.shortcut_hint.cget('text')!=hint:self.shortcut_hint.config(text=hint)
        self.root.after(100,self.poll)
    def finish(self,value,error,done):
        self.busy=False
        if error:
            if self.authenticated and self.client and not self.client.session:
                self.client.account=None;self.show_login()
            self.status.config(text=error);self.share.set(bool(self.client and self.client.account and self.client.account.get('share_measurements')))
            if self.update_label.cget('text')=='Actualizaciones · comprobando…':self.update_label.config(text='Actualizaciones · no se pudo comprobar')
        else:done(value)
        if self.closed:return
        account=self.client.account if self.client else None
        if account:self.access_active=bool(account.get('active'))
        self.sync_controls();self.refresh_versions()
        if error:self.mascot.set_state('error')
    def login(self):
        if self.demo:self.enter_demo();return
        if not self.client or self.busy:return
        email=self.email.get().strip();password=self.password.get()
        if not email or not password:self.status.config(text='Escribe tu correo y contraseña.');return
        self.password.set('');self.status.config(text='Comprobando tu cuenta…');self.run(lambda:self.client.login(email,password),self.show_account)
    def show_account(self,account):
        self.show_dashboard(account)
        seconds=max(0,int(account.get('remaining_seconds',0)));days=seconds//86400;end=account.get('expires_at')
        remaining=f'{days} días completos disponibles' if days else f'{seconds//3600} h {(seconds%3600)//60} min disponibles'
        user=(self.client.session or {}).get('user',{}).get('email') or self.email.get() or 'Tu cuenta'
        self.license_title.config(text='Acceso de administrador' if account.get('role')=='admin' else user)
        try:expires=datetime.fromisoformat(end.replace('Z','+00:00')).astimezone().strftime('%d/%m/%Y %H:%M') if end else 'sin fecha asignada'
        except (ValueError,TypeError):expires='por comprobar'
        self.license_detail.config(text='Panel de administración disponible.' if account.get('role')=='admin' else remaining+' · vence '+expires)
        if not account.get('active'):self.license_detail.config(text='Acceso vencido o suspendido. Contacta al administrador.')
        self.share.set(bool(account.get('share_measurements')))
        self.status.config(text='Acceso activo · listo para jugar' if account.get('active') else 'Tu acceso no está activo')
        self.schedule_scroll()
        if account.get('active') and '--auto-game' in sys.argv:
            sys.argv.remove('--auto-game');self.root.after(100,self.play)
    def change_consent(self):
        if self.demo:return
        if not self.client or not self.authenticated or self.busy:return
        enabled=self.share.get();self.run(lambda:(self.client.consent(enabled),self.client.account)[1],self.show_account)
    def logout(self):
        if self.busy:return
        self.stop_engine()
        if self.demo:
            self.show_login();self.status.config(text='Prueba cerrada. Pulsa Entrar para volver.');return
        if not self.client or self.busy:return
        def done(value):
            self.client.account=None;self.password.set('');self.share.set(False);self.show_login();self.status.config(text='Sesión cerrada. Puedes volver a entrar.')
        self.run(self.client.logout,done)
    def open_account(self):
        if self.demo:
            messagebox.showinfo('Versión de prueba','Esta es una prueba local sin cuenta ni licencia del servidor.',parent=self.root);return
        url=self.client.config.get('panelUrl','') if self.client else ''
        if url.startswith('https://'):webbrowser.open(url)
        else:messagebox.showinfo('Tu cuenta','El panel todavía no está configurado.',parent=self.root)
    def guide(self,title,steps,link=None):
        if self.closed:return
        if self.dialog and self.dialog.winfo_exists():self.dialog.lift();return
        win=tk.Toplevel(self.root);self.dialog=win;win.withdraw();win.title('DragonLab · '+title);win.configure(bg=BG);win.resizable(True,True);win.minsize(460,360);win.transient(self.root)
        heading=tk.Frame(win,bg=BG);heading.pack(fill='x',padx=24,pady=(20,14))
        label=tk.Label(heading,text=title,font=(FONT,-23,'bold'),fg=INK,bg=BG);label.pack(side='left')
        def close():
            try:win.grab_release();win.destroy()
            except tk.TclError:pass
            self.dialog=None
        card=RoundedPanel(win,PANEL,radius=26,padding=20);card.pack(fill='both',expand=True,padx=22,pady=(0,16))
        for step_title,detail in steps:
            tk.Label(card.body,text=step_title,font=(FONT,-15,'bold'),fg=ACCENT,bg=PANEL).pack(anchor='w',pady=(8,4))
            tk.Label(card.body,text=detail,font=(FONT,-14),fg=MUTED,bg=PANEL,wraplength=470,justify='left').pack(anchor='w',pady=(0,12))
        if link:LauncherButton(card.body,text=link[0],command=lambda:webbrowser.open(link[1]),bg=FIELD,fg=TEXT,font=(FONT,-13),pady=10).pack(anchor='w',pady=(0,10))
        confirm=LauncherButton(win,text='Entendido',command=close,bg=FIELD,fg=TEXT,activebackground=LINE,activeforeground=ACCENT,pady=10);confirm.pack(fill='x',padx=44,pady=(0,22))
        win.protocol('WM_DELETE_WINDOW',close);win.bind('<Escape>',lambda e:close());win.update_idletasks()
        width=560;height=heading.winfo_reqheight()+34+card.body.winfo_reqheight()+40+16+confirm.winfo_reqheight()+22;x=self.root.winfo_x()+(self.root.winfo_width()-width)//2;y=self.root.winfo_y()+40
        x,y,width,height=place_in_work_area(x,y,width,height,monitor_work_area(self.root))
        win.geometry(f'{width}x{height}{x:+d}{y:+d}');style_window(win);win.deiconify();win.grab_set()
    def help(self):
        if self.training_mode:
            self.guide('Entrenamiento independiente',[
                ('Prepara las cuentas','Deja las dos sesiones de prueba en Avatar Off. Pulsa Iniciar entrenamiento para activar el modo automático.'),
                ('Comprueba el panel','El panel muestra turnos, tiros y guías guardadas. Las modalidades sin una trayectoria comprobada pueden quedar pendientes.'),
                ('Volver al manual','Detén el entrenamiento y cierra esta ventana. Abre DragonLab Manual para jugar con la guía.')]);return
        self.guide('Juega con tu guía',[
            ('Abre tu partida','Elige el juego y pulsa Abrir juego. La guía de fuerza y las trayectorias aparecen al detectar la partida.'),
            ('Apunta y elige objetivo','Ajusta el ángulo en el juego. Ctrl cambia el objetivo y Q aplica la fuerza indicada, si habilitaste ese atajo en Ajustes.'),
            ('Comprueba el estado','Verde identifica la guía. Los avisos distinguen terreno bloqueado, rango aprendido y modalidades pendientes. Una guía aproximada necesita más mediciones.'),
            ('Personaliza y pausa','Ajustes reúne líneas, marca de fuerza y atajos. Pausar guía detiene la lectura; el juego permanece abierto. Cerrar DragonLab guarda los datos locales.')])
    def calibration_help(self):
        self.guide('Cada carro tiene su ritmo.',[
            ('Carro + modalidad','Tiro 1, tiro 2 y SS usan perfiles distintos. Un ajuste de Armor no valida Nak, Trico o Kalsiddon.'),
            ('Listo, Aprendiendo o Bloqueado','Revisa el estado en el juego. El viento, terreno y clima pueden cambiar la trayectoria; una guía aproximada necesita más mediciones.'),
            ('Tu decides si compartes','En el acceso real puedes compartir mediciones para mejorar los perfiles. Es opcional. Esta prueba local no envía datos al servidor.')])
    def check_update(self):
        if self.demo:return
        if not self.authenticated or self.busy:return
        self.update_label.config(text='Actualizaciones · comprobando…')
        def done(manifest):
            self.manifest=manifest;version=installed_version(self.client.directory) if self.client else None
            self.update_label.config(text='Actualizado · v'+manifest['version'] if version==manifest['version'] else 'Disponible · v'+manifest['version']+' · se instalará al iniciar')
            self.status.config(text='Comprobación de actualizaciones terminada.')
        self.run(fetch_manifest,done)
    def game_changed(self):
        if self.game.get() not in GAMES:self.game.set('DragonBound');return
        if self.engine and self.engine.app.clone_id!=GAMES[self.game.get()]['id']:self.stop_engine()
        self.game_note.config(text='Armor medido: 1 (0–18), 2 (0–22), SS (2–24 de viento).\nOtros carros: aprendizaje con tus tiros manuales.' if self.game.get()=='GunBound World' else 'DragonBound · entrenamiento experimental de dos cuentas.' if self.training_mode else 'DragonBound · fuerza, trayectorias y objetivo en la partida.')
        if not self.engine:self.play_button.config(text=self.start_caption())
        self.refresh_recommendations();self.schedule_scroll()
    def start_caption(self):return 'Iniciar entrenamiento' if self.training_mode else 'Abrir juego'
    def engine_directory(self):
        from state_storage import engine_directory
        return engine_directory(BASE,self.client.directory if self.client else None)
    def stop_engine(self):
        if self.engine:self.engine.stop();self.engine=None
        self.opening_until=0
        self.mascot.set_state('ready')
    def get_engine(self):
        if not self.engine:self.engine=EngineHost(self.root,self.engine_directory(),None if self.demo else self.client)
        self.engine.app.training_enabled=self.training_mode
        self.engine.prepare(GAMES[self.game.get()]['id'])
        self.refresh_recommendations()
        return self.engine
    def open_settings(self):
        if not self.authenticated or self.busy:return
        if not self.demo and (not self.client or not self.client.account or not self.client.account.get('active')):return
        try:self.get_engine().settings()
        except Exception:self.status.config(text='No se pudieron abrir los ajustes. Vuelve a intentarlo.')
    def start_engine(self):
        if time.monotonic()<self.opening_until:return
        self.busy=True;self.sync_controls();self.status.config(text='Conectando el juego…');self.root.update_idletasks()
        try:
            ok=self.get_engine().start(GAMES[self.game.get()]['id'])
            if ok:self.opening_until=time.monotonic()+2
            if ok and self.training_mode:
                self.training_instances=2 if '--train-two' in sys.argv else 1
                if '--train' not in sys.argv:self.training_instances=2
                for flag in ('--train','--train-two'):
                    if flag in sys.argv:sys.argv.remove(flag)
                self.root.after(1500,self.start_training)
            self.status.config(text='Abriendo el juego. La guía espera una partida.' if ok else 'No se pudo abrir el juego. Revisa Chrome o Edge y vuelve a intentar.')
        except Exception:
            self.stop_engine();self.status.config(text='No se pudo iniciar la captura. Vuelve a intentarlo.')
        finally:self.busy=False;self.sync_controls()
        self.mascot.set_state('ready' if self.engine else 'error')
    def start_training(self):
        if self.closed or not self.authenticated or not self.engine or not getattr(self,'training_mode',False):return
        from game_profiles import get_profile
        profile=get_profile(self.engine.app.clone_id)
        if not profile or not profile['capabilities']['autonomous_training']:
            self.status.config(text='El entrenamiento de este juego aún no está disponible. Usa la guía manual.');return
        try:
            from training_ui import open_training,start_training
            instances=getattr(self,'training_instances',1);self.engine.app.training_instances=instances
            if instances==2:
                from training_browsers import ready_slots,open_second_browser
                try:ready_slots(self.engine.app.book.path.parent)
                except (OSError,ValueError,TypeError,KeyError):
                    attempts=getattr(self,'training_browser_attempts',0)
                    if attempts>=30:raise ValueError('No se conectaron las dos ventanas. Abre Aprendizaje y comprueba sus cuentas antes de empezar.')
                    self.training_browser_attempts=attempts+1
                    if not getattr(self,'training_second_requested',False):
                        open_second_browser(self.engine.app.book.path.parent);self.training_second_requested=True
                    self.status.config(text='Preparando las dos ventanas de entrenamiento…')
                    self.root.after(1000,self.start_training);return
            self.training_browser_attempts=0;self.training_second_requested=False
            open_training(self.engine.app);start_training(self.engine.app,instances=instances)
        except (ValueError,RuntimeError,OSError) as error:self.status.config(text=str(error))
    def toggle_game(self):
        if self.busy or time.monotonic()<self.opening_until:return
        worker=getattr(self.engine.app,'worker',None) if self.engine else None
        session=getattr(self.engine.app,'training_session',None) if self.engine else None
        if worker and worker.is_alive() or session and session.running:
            self.stop_engine();self.play_button.config(text=self.start_caption())
            self.status.config(text='Guía pausada. El juego sigue abierto.')
        else:self.play()
    def play(self):
        if not self.authenticated or self.busy:return
        if self.demo:self.start_engine();return
        if not self.client or not self.client.account or not self.client.account.get('active'):return
        if self.engine and getattr(self.engine.app,'last_live',0):
            self.run(self.client.require_access,lambda account:self.start_engine());return
        self.status.config(text='Comprobando acceso y actualización…')
        def update():
            # Access is mandatory. Release availability is an optional service.
            account=self.client.require_access()
            try:manifest=fetch_manifest(self.client.config.get('githubRepo',REPO))
            except CloudError:return account,None,'Actualizaciones · sin conexión; se usará el motor integrado'
            if tuple(map(int,manifest['version'].split('.'))) <= tuple(map(int,PROGRAM_VERSION.split('.'))):return account,None,None
            target=self.client.directory/('DragonLab-Cloud-'+manifest['version']+'.exe')
            if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest()!=manifest['sha256']:download_verified(manifest['url'],target,manifest['sha256'],REPO)
            atomic_write(self.client.directory/'cloud-desktop.json',json.dumps(self.client.config).encode())
            atomic_write(self.client.directory/'installed-release.json',json.dumps({'version':manifest['version'],'sha256':manifest['sha256']}).encode())
            return account,target,None
        def done(result):
            account,target,notice=result
            self.access_active=bool(account.get('active'))
            if not self.access_active:self.show_account(account);return
            if notice:self.update_label.config(text=notice)
            if target:
                try:subprocess.Popen([str(target),'--handoff','--auto-game','--clone='+GAMES[self.game.get()]['id']]+(['--trainer'] if self.training_mode else []),cwd=target.parent)
                except OSError:self.status.config(text='No se pudo aplicar la actualización. Vuelve a intentarlo.');return
                self.close();return
            self.start_engine()
        self.run(update,done)
    def close(self):
        self.closed=True;self.stop_engine()
        for job in self.root.tk.splitlist(self.root.tk.call('after','info')):self.root.after_cancel(job)
        self.root.destroy()

def demo_launch_requested(argv,executable,frozen):
    # Windows launchers can normalize a path's case before starting the app.
    return '--demo' in argv or bool(frozen and pathlib.PureWindowsPath(executable).stem.casefold() in ('dragonlab-prueba','dragonlab-manual','dragonlab-automatico'))

def requested_training_mode(argv,executable,frozen):
    name=pathlib.PureWindowsPath(executable).stem.casefold() if frozen else ''
    if name=='dragonlab-manual':return False
    return name=='dragonlab-automatico' or any(flag in argv for flag in ('--trainer','--train','--train-two'))

def main():
    if '--native-check' in sys.argv:
        from native_checks import run
        run(sys.argv[sys.argv.index('--native-check')+1]);return
    if '--connection-check' in sys.argv:
        from training_diagnostics import connection_check
        connection_check(pathlib.Path(sys.argv[sys.argv.index('--connection-check')+1]));return
    import time
    instance=SingleInstance('DragonLab.Launcher') if '--check' not in sys.argv else None
    if instance and not instance.primary and '--handoff' in sys.argv:
        for attempt in range(60):
            instance.close();time.sleep(.05);instance=SingleInstance('DragonLab.Launcher')
            if instance.primary:break
    if instance and not instance.primary:restore_launcher();instance.close();return
    enable_high_dpi()
    root=tk.Tk();root.withdraw();app=Launcher(root,demo=demo_launch_requested(sys.argv,sys.executable,getattr(sys,'frozen',False)))
    if '--check' in sys.argv:
        if '--engine-check' in sys.argv and app.demo:app.get_engine()
        root.withdraw();root.after(600,app.close)
    else:root.update_idletasks();style_window(root);root.deiconify()
    root.mainloop()
    if instance:instance.close()

if __name__=='__main__':main()
