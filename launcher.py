"""Native launcher: explicit license, installed versions and verified updates."""
import json,pathlib,subprocess,sys,threading,queue,urllib.request,webbrowser,tkinter as tk,re,hashlib,time
from tkinter import messagebox
from datetime import datetime
from rounded_widgets import RoundedButton,RoundedPanel
from rounded_controls import RoundedEntry,RoundedSwitch,RoundedChoice
from cloud_client import CloudClient,CloudError,download_verified
from local_storage import atomic_write
from app_version import LAUNCHER_VERSION,PROGRAM_VERSION,DEMO_ALLOWED
from engine_host import EngineHost
from game_catalog import GAMES
from desktop_shell import style_window,drag_handle,SingleInstance,restore_launcher
BASE=pathlib.Path(sys.executable).parent if getattr(sys,'frozen',False) else pathlib.Path(__file__).parent
BG='#0b121c';PANEL='#152232';INK='#f1f6fc';MUTED='#b1c0d2';ACCENT='#54d7ee';REPO='leo10m2010/DragonLab'

class LauncherButton(RoundedButton):
    def __init__(self,master,**options):
        defaults={'disabledbackground':'#26384c','disabledforeground':'#a8b9cf','focuscolor':ACCENT}
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
        self.root=root;root.title('DragonLab · Launcher '+LAUNCHER_VERSION);root.geometry('760x710');root.configure(bg=BG);root.resizable(False,False)
        self.busy=False;self.client=None;self.closed=False;self.events=queue.Queue();self.manifest=None;self.demo=demo;self.engine=None;self.dialog=None;self.opening_until=0
        self.email=tk.StringVar();self.password=tk.StringVar();self.share=tk.BooleanVar();self.game=tk.StringVar(value='DragonBound')
        requested=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--clone=')),None)
        if requested:self.game.set(next((name for name,g in GAMES.items() if g['id']==requested),'DragonBound'))
        header=tk.Frame(root,bg=BG);header.pack(fill='x',padx=30,pady=(24,18))
        mark=tk.Label(header,text='◉',font=('Bahnschrift',28),bg=BG,fg=ACCENT);mark.pack(side='left',padx=(0,12))
        brand=tk.Label(header,text='DragonLab',font=('Bahnschrift',24,'bold'),bg=BG,fg=INK);brand.pack(side='left')
        LauncherButton(header,text='×',command=self.close,bg=BG,fg=MUTED,activebackground='#532c3c',activeforeground=INK,padx=10,pady=4,font=('Bahnschrift',17)).pack(side='right')
        LauncherButton(header,text='−',command=root.iconify,bg=BG,fg=MUTED,activebackground=PANEL,activeforeground=INK,padx=10,pady=4,font=('Bahnschrift',17)).pack(side='right',padx=(12,4))
        tk.Label(header,text='v'+LAUNCHER_VERSION,font=('Bahnschrift',10),bg=BG,fg=MUTED).pack(side='right')
        for handle in (header,mark,brand):drag_handle(handle,root)
        self.login_page=tk.Frame(root,bg=BG)
        self.dashboard_page=tk.Frame(root,bg=BG)
        self.authenticated=False
        login_panel=RoundedPanel(self.login_page,PANEL,radius=30,padding=28);login_panel.pack(fill='x',padx=26,pady=(8,0))
        form=login_panel.body
        tk.Label(form,text='Bienvenido de nuevo.',font=('Bahnschrift',23),bg=PANEL,fg=INK).pack(anchor='w',pady=(4,8))
        tk.Label(form,text='Inicia sesión para acceder a DragonLab.',font=('Bahnschrift',11),bg=PANEL,fg=MUTED).pack(anchor='w',pady=(0,22))
        self.login_area=tk.Frame(form,bg=PANEL);self.login_area.pack(fill='x')
        for title,var,secret in [('Correo',self.email,False),('Contraseña',self.password,True)]:
            tk.Label(self.login_area,text=title,font=('Bahnschrift',10),bg=PANEL,fg=MUTED).pack(anchor='w',pady=(0,6))
            entry=RoundedEntry(self.login_area,textvariable=var,show='●' if secret else '',font=('Bahnschrift',12),bg='#24374e',fg=INK,insertbackground=INK,selectbackground=ACCENT,selectforeground=BG);entry.pack(fill='x',pady=(0,16));entry.entry.bind('<Return>',lambda e:self.login())
        self.login_button=LauncherButton(form,text='Iniciar sesión  →',command=self.login,bg=ACCENT,fg=BG,activebackground='#89e9f8',activeforeground=BG,font=('Bahnschrift',13,'bold'),pady=14)
        self.login_button.pack(fill='x',pady=(4,6))
        self.login_status=tk.Label(self.login_page,text='Tu cuenta es personal. Entra con tu correo y contraseña.',wraplength=440,justify='center',bg=BG,fg=MUTED,font=('Bahnschrift',10));self.login_status.pack(fill='x',padx=34,pady=20)
        panel=RoundedPanel(self.dashboard_page,PANEL,radius=30,padding=22);panel.pack(fill='x',padx=26)
        body=panel.body
        self.headline=tk.Label(body,text='Tu próxima partida.',font=('Bahnschrift',25),bg=PANEL,fg=INK);self.headline.pack(anchor='w',pady=(4,10))
        self.license_title=tk.Label(body,font=('Bahnschrift',12,'bold'),bg=PANEL,fg=ACCENT);self.license_title.pack(anchor='w')
        self.license_detail=tk.Label(body,font=('Bahnschrift',10),bg=PANEL,fg=MUTED,wraplength=640,justify='left');self.license_detail.pack(anchor='w',pady=(4,14))
        self.account_row=tk.Frame(body,bg=PANEL);self.account_row.pack(fill='x')
        self.account_button=LauncherButton(self.account_row,text='Mi cuenta',command=self.open_account,bg=PANEL,fg=INK,pady=5);self.account_button.pack(side='left')
        LauncherButton(self.account_row,text='Cerrar sesión',command=self.logout,bg=PANEL,fg=MUTED,pady=5).pack(side='right')
        selection=tk.Frame(self.dashboard_page,bg=BG);selection.pack(fill='x',padx=54,pady=(20,0))
        tk.Label(selection,text='JUEGO',font=('Bahnschrift',10,'bold'),bg=BG,fg=MUTED).pack(anchor='w',pady=(0,6))
        self.game_choice=RoundedChoice(selection,textvariable=self.game,values=list(GAMES),width=26,font=('Bahnschrift',13));self.game_choice.pack(fill='x')
        self.game_note=tk.Label(selection,bg=BG,fg=MUTED,font=('Bahnschrift',10),wraplength=620,justify='left');self.game_note.pack(anchor='w',pady=(8,0))
        self.game.trace_add('write',lambda *args:self.game_changed())
        self.play_button=LauncherButton(self.dashboard_page,text='Jugar  →',command=self.toggle_game,bg=ACCENT,fg=BG,activebackground='#89e9f8',activeforeground=BG,font=('Bahnschrift',18,'bold'),pady=18,state='disabled')
        self.play_button.pack(fill='x',padx=54,pady=(20,12))
        self.dashboard_status=tk.Label(self.dashboard_page,wraplength=680,justify='center',bg=BG,fg=MUTED,font=('Bahnschrift',10));self.dashboard_status.pack(fill='x',padx=32,pady=(0,12))
        versions=RoundedPanel(self.dashboard_page,PANEL,radius=24,padding=14);self.versions_panel=versions
        row=tk.Frame(versions.body,bg=PANEL);row.pack(fill='x')
        self.program_label=tk.Label(row,text='Programa · por instalar',font=('Bahnschrift',11,'bold'),bg=PANEL,fg=INK);self.program_label.pack(side='left')
        self.update_button=LauncherButton(row,text='Buscar actualización',command=self.check_update,bg='#263b54',fg=INK,pady=5,state='disabled');self.update_button.pack(side='right')
        self.calibration_label=tk.Label(versions.body,text='Calibraciones · sin sincronizar',font=('Bahnschrift',10),bg=PANEL,fg=MUTED);self.calibration_label.pack(anchor='w',pady=(6,0))
        self.update_label=tk.Label(versions.body,text='Actualizaciones · sin comprobar',font=('Bahnschrift',10),bg=PANEL,fg=MUTED);self.update_label.pack(anchor='w',pady=(4,0))
        privacy=tk.Frame(self.dashboard_page,bg=BG);self.privacy=privacy;privacy.pack(fill='x',padx=34,pady=(16,0))
        self.consent=ConsentSwitch(privacy,text='Ayudar a mejorar las calibraciones',variable=self.share,command=self.change_consent,state='disabled');self.consent.pack(anchor='w')
        tk.Label(privacy,text='Opcional. Solo mediciones de tiros; sin capturas, chats ni nombres.',font=('Bahnschrift',9),bg=BG,fg=MUTED).pack(anchor='w',pady=(3,0))
        foot=tk.Frame(self.dashboard_page,bg=BG);foot.pack(side='bottom',fill='x',padx=30,pady=18)
        LauncherButton(foot,text='Cómo usarlo',command=self.help,bg=BG,fg=MUTED,pady=5).pack(side='left')
        LauncherButton(foot,text='Ajustes',command=self.open_settings,bg=BG,fg=MUTED,pady=5).pack(side='right')
        self.game_changed();self.show_login()
        root.protocol('WM_DELETE_WINDOW',self.close)
        root.after(50,self.poll)
        if self.demo:
            root.title('DragonLab · PRUEBA · Launcher '+LAUNCHER_VERSION)
            self.login_area.pack_forget();self.login_button.config(text='Entrar a la prueba  →')
            self.status.config(text='Prueba local. No necesitas correo ni contraseña.')
            if '--check' not in sys.argv:root.after(150,self.enter_demo)
            return
        try:self.client=CloudClient(BASE/'cloud-desktop.json')
        except CloudError:
            self.status.config(text='Servidor pendiente de configuración. Consulta la guía de activación.');self.login_button.config(state='disabled');self.consent.config(state='disabled')
        self.refresh_versions()
        if self.client and self.client.session and '--check' not in sys.argv:self.run(self.client.require_access,self.show_account)
    def show_login(self):
        self.authenticated=False;self.dashboard_page.pack_forget();self.login_page.pack(fill='both',expand=True)
        self.status=self.login_status;self.root.geometry('520x570')
        self.play_button.config(state='disabled');self.update_button.config(state='disabled');self.consent.config(state='disabled')
        self.root.after_idle(lambda:style_window(self.root) if not self.closed else None)
    def show_dashboard(self,account):
        self.authenticated=True;self.login_page.pack_forget();self.dashboard_page.pack(fill='both',expand=True)
        self.status=self.dashboard_status;self.root.geometry('760x690')
        self.play_button.config(state='normal' if account.get('active') else 'disabled')
        self.update_button.config(state='normal');self.consent.config(state='normal')
        self.root.after_idle(lambda:style_window(self.root) if not self.closed else None)
    def enter_demo(self):
        if not self.demo or self.closed:return
        self.show_dashboard({'active':True});self.license_title.config(text='VERSIÓN DE PRUEBA · acceso automático')
        self.headline.config(text='Elige tu juego.')
        self.license_detail.config(text='La guía aparece dentro del juego al empezar una partida.')
        self.root.geometry('760x630');self.account_button.pack_forget()
        self.privacy.pack_forget();self.consent.config(state='disabled');self.share.set(False)
        self.update_button.config(state='disabled');self.update_button.pack_forget();self.update_label.config(text='Prueba local · actualizaciones Cloud desactivadas')
        self.program_label.config(text='Motor integrado · v'+PROGRAM_VERSION)
        self.calibration_label.config(text='Calibraciones · se utilizan las del programa local')
        self.status.config(text='El juego y la captura se preparan con un solo clic.')
        self.play_button.config(state='normal')
        if '--auto-game' in sys.argv and '--check' not in sys.argv:
            sys.argv.remove('--auto-game');self.root.after(100,self.play)
    def refresh_versions(self):
        directory=self.client.directory if self.client else BASE
        version=installed_version(directory)
        self.program_label.config(text='Programa · v'+version if version else 'Programa · por instalar')
        self.calibration_label.config(text='Calibraciones · '+calibration_revision(directory/'published-profiles.json'))
    def run(self,work,done):
        if self.busy or self.closed:return
        self.busy=True;self.login_button.config(state='disabled');self.play_button.config(state='disabled');self.update_button.config(state='disabled');self.consent.config(state='disabled')
        def thread():
            try:self.events.put((work(),None,done))
            except Exception as e:self.events.put((None,str(e),done))
        threading.Thread(target=thread,daemon=True).start()
    def poll(self):
        if self.closed:return
        while not self.events.empty():self.finish(*self.events.get_nowait())
        if self.engine and not self.engine.window.winfo_exists():
            self.engine=None;self.play_button.config(state='normal' if self.authenticated else 'disabled')
            self.status.config(text='La guía se detuvo. Pulsa Jugar para volver a conectarte.')
        if self.engine and not self.busy:
            from product_status import capture_status
            app=self.engine.app;worker=getattr(app,'worker',None)
            if worker and worker.is_alive():
                label,message=capture_status(app)
                self.play_button.config(text=label+' · Pausar')
                self.status.config(text=message)
        self.root.after(100,self.poll)
    def finish(self,value,error,done):
        self.busy=False;self.login_button.config(state='normal' if self.client else 'disabled');self.update_button.config(state='normal' if self.authenticated else 'disabled')
        if error:
            if self.authenticated and self.client and not self.client.session:
                self.client.account=None;self.show_login()
            self.status.config(text=error);self.share.set(bool(self.client and self.client.account and self.client.account.get('share_measurements')))
            if self.update_label.cget('text')=='Actualizaciones · comprobando…':self.update_label.config(text='Actualizaciones · no se pudo comprobar')
        else:done(value)
        if self.closed:return
        account=self.client.account if self.client else None
        self.play_button.config(state='normal' if self.authenticated and account and account.get('active') else 'disabled');self.consent.config(state='normal' if self.authenticated and account else 'disabled');self.refresh_versions()
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
        self.status.config(text='Tu acceso está comprobado.' if account.get('active') else 'No tienes un acceso activo.')
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
    def guide(self,title,steps):
        if self.closed:return
        if self.dialog and self.dialog.winfo_exists():self.dialog.lift();return
        win=tk.Toplevel(self.root);self.dialog=win;win.withdraw();win.configure(bg=BG);win.resizable(False,False);win.transient(self.root)
        heading=tk.Frame(win,bg=BG);heading.pack(fill='x',padx=24,pady=(20,14))
        label=tk.Label(heading,text=title,font=('Bahnschrift',21),fg=INK,bg=BG);label.pack(side='left');drag_handle(heading,win);drag_handle(label,win)
        def close():win.grab_release();win.destroy();self.dialog=None
        LauncherButton(heading,text='×',command=close,bg=BG,fg=MUTED,pady=5).pack(side='right')
        card=RoundedPanel(win,PANEL,radius=26,padding=20);card.pack(fill='both',expand=True,padx=22,pady=(0,16))
        for step_title,detail in steps:
            tk.Label(card.body,text=step_title,font=('Bahnschrift',12,'bold'),fg=ACCENT,bg=PANEL).pack(anchor='w',pady=(8,4))
            tk.Label(card.body,text=detail,font=('Bahnschrift',11),fg=MUTED,bg=PANEL,wraplength=470,justify='left').pack(anchor='w',pady=(0,12))
        confirm=LauncherButton(win,text='Entendido',command=close,bg=ACCENT,fg=BG,activebackground='#89e9f8',activeforeground=BG,pady=10);confirm.pack(fill='x',padx=44,pady=(0,22))
        win.protocol('WM_DELETE_WINDOW',close);win.bind('<Escape>',lambda e:close());win.update_idletasks()
        width=550;height=heading.winfo_reqheight()+34+card.body.winfo_reqheight()+40+16+confirm.winfo_reqheight()+22;x=self.root.winfo_x()+(self.root.winfo_width()-width)//2;y=max(0,self.root.winfo_y()+40)
        y=min(y,max(0,win.winfo_screenheight()-height-40))
        win.geometry(f'{width}x{height}{max(0,x):+d}{y:+d}');style_window(win);win.deiconify();win.grab_set()
    def help(self):
        self.guide('Una partida, en un paso.',[
            ('01 · Elige un juego y pulsa Jugar','Esta es la única pantalla principal. La captura trabaja internamente; no se abre otro panel de DragonLab.'),
            ('02 · Entra al juego y empieza una partida','Usa tu cuenta del juego. La guía se muestra dentro de la partida cuando hay datos suficientes. GunBound World es experimental y necesita validar sus propias calibraciones.'),
            ('Colores y calibración','Verde: salida medida. Naranja: aproximado o terreno bloqueado. Pendiente: aún no hay perfil válido para ese carro, tiro o viento. El nombre del carro y el tiro aparecen sobre la barra.'),
            ('03 · Elige y comprueba tu tiro','Ctrl cambia de objetivo. Q solicita un tiro en tu turno. Estos son los atajos iniciales; puedes cambiarlos en Ajustes del auxiliar. Comprueba el objetivo y la guía antes de usarlo.'),
            ('Ajustes y salida','Ajustes cambia los controles y la apariencia de la guía. Cerrar DragonLab detiene la captura; el navegador queda abierto. Q aplica un tiro con controles de Windows. Requiere tu turno, fuerza válida y juego en primer plano; prueba primero un tiro normal sin ítems.')])
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
        self.game_note.config(text='Armor medido: 1 (0–18), 2 (0–22), SS (2–24 de viento).\nOtros carros: aprendizaje con tus tiros manuales.' if self.game.get()=='GunBound World' else 'DragonBound · guía y controles automáticos dentro de la partida.')
    def engine_directory(self):
        if self.client:return self.client.directory
        for directory in (BASE/'DragonLab',BASE.parent/'DragonLab',BASE.parent.parent/'DragonLab'):
            if (directory/'calibraciones.json').is_file():return directory
        return BASE/'datos'
    def stop_engine(self):
        if self.engine:self.engine.stop();self.engine=None
        self.opening_until=0
    def get_engine(self):
        if not self.engine:self.engine=EngineHost(self.root,self.engine_directory(),None if self.demo else self.client)
        return self.engine
    def open_settings(self):
        if not self.authenticated or self.busy:return
        if not self.demo and (not self.client or not self.client.account or not self.client.account.get('active')):return
        try:self.get_engine().settings()
        except Exception:self.status.config(text='No se pudieron abrir los ajustes. Vuelve a intentarlo.')
    def start_engine(self):
        if time.monotonic()<self.opening_until:return
        self.busy=True;self.play_button.config(state='disabled');self.status.config(text='Conectando el juego…');self.root.update_idletasks()
        try:
            ok=self.get_engine().start(GAMES[self.game.get()]['id'])
            if ok:self.opening_until=time.monotonic()+2
            if ok and '--train' in sys.argv:
                sys.argv.remove('--train');self.root.after(1500,self.start_training)
            self.status.config(text='Abriendo el juego. La guía espera una partida.' if ok else 'No se pudo abrir el juego. Revisa Chrome o Edge y vuelve a intentar.')
        except Exception:
            self.stop_engine();self.status.config(text='No se pudo iniciar la captura. Vuelve a intentarlo.')
        finally:self.busy=False;self.play_button.config(state='normal')
    def start_training(self):
        if self.closed or not self.authenticated or not self.engine:return
        try:
            from training_ui import open_training,start_training
            open_training(self.engine.app);start_training(self.engine.app)
        except (ValueError,RuntimeError):self.status.config(text='Abre Ajustes para iniciar el entrenamiento en DragonBound.')
    def toggle_game(self):
        if self.busy or time.monotonic()<self.opening_until:return
        worker=getattr(self.engine.app,'worker',None) if self.engine else None
        if worker and worker.is_alive():
            self.stop_engine();self.play_button.config(text='Jugar →')
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
            account=self.client.require_access();manifest=fetch_manifest(self.client.config.get('githubRepo',REPO))
            if tuple(map(int,manifest['version'].split('.'))) <= tuple(map(int,PROGRAM_VERSION.split('.'))):return account,None
            target=self.client.directory/('DragonLab-Cloud-'+manifest['version']+'.exe')
            if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest()!=manifest['sha256']:download_verified(manifest['url'],target,manifest['sha256'],REPO)
            atomic_write(self.client.directory/'cloud-desktop.json',json.dumps(self.client.config).encode())
            atomic_write(self.client.directory/'installed-release.json',json.dumps({'version':manifest['version'],'sha256':manifest['sha256']}).encode())
            return account,target
        def done(result):
            account,target=result
            if target:
                try:subprocess.Popen([str(target),'--handoff','--auto-game','--clone='+GAMES[self.game.get()]['id']],cwd=target.parent)
                except OSError:self.status.config(text='No se pudo aplicar la actualización. Vuelve a intentarlo.');return
                self.close();return
            self.start_engine()
        self.run(update,done)
    def close(self):
        self.closed=True;self.stop_engine()
        for job in self.root.tk.splitlist(self.root.tk.call('after','info')):self.root.after_cancel(job)
        self.root.destroy()

def main():
    import time
    instance=SingleInstance('DragonLab.Launcher') if '--check' not in sys.argv else None
    if instance and not instance.primary and '--handoff' in sys.argv:
        for attempt in range(60):
            instance.close();time.sleep(.05);instance=SingleInstance('DragonLab.Launcher')
            if instance.primary:break
    if instance and not instance.primary:restore_launcher();instance.close();return
    root=tk.Tk();root.withdraw();app=Launcher(root,demo='--demo' in sys.argv or (getattr(sys,'frozen',False) and pathlib.Path(sys.executable).stem=='DragonLab-Prueba'))
    if '--check' in sys.argv:
        if '--engine-check' in sys.argv and app.demo:app.get_engine()
        root.withdraw();root.after(600,app.close)
    else:root.update_idletasks();style_window(root);root.deiconify()
    root.mainloop()
    if instance:instance.close()

if __name__=='__main__':main()
