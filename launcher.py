"""Native launcher: explicit license, installed versions and verified updates."""
import json,pathlib,subprocess,sys,threading,queue,urllib.request,webbrowser,tkinter as tk,re,hashlib
from tkinter import messagebox
from datetime import datetime
from rounded_widgets import RoundedButton,RoundedPanel
from rounded_controls import RoundedEntry,RoundedSwitch
from cloud_client import CloudClient,CloudError,download_verified
from local_storage import atomic_write
from app_version import LAUNCHER_VERSION
BASE=pathlib.Path(sys.executable).parent if getattr(sys,'frozen',False) else pathlib.Path(__file__).parent
BG='#0e171b';PANEL='#19282d';INK='#edf4f1';MUTED='#9bb1b4';ACCENT='#72dfba';REPO='leo10m2010/DragonLab'

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
    def __init__(self,root):
        self.root=root;root.title('DragonLab · Launcher '+LAUNCHER_VERSION);root.geometry('760x710');root.configure(bg=BG);root.resizable(False,False)
        self.busy=False;self.client=None;self.closed=False;self.events=queue.Queue();self.manifest=None
        self.email=tk.StringVar();self.password=tk.StringVar();self.share=tk.BooleanVar()
        header=tk.Frame(root,bg=BG);header.pack(fill='x',padx=30,pady=(24,18))
        tk.Label(header,text='◉',font=('Bahnschrift',28),bg=BG,fg=ACCENT).pack(side='left',padx=(0,12))
        tk.Label(header,text='DragonLab',font=('Bahnschrift',24,'bold'),bg=BG,fg=INK).pack(side='left')
        tk.Label(header,text='Launcher v'+LAUNCHER_VERSION,font=('Bahnschrift',10),bg=BG,fg=MUTED).pack(side='right')
        panel=RoundedPanel(root,PANEL,radius=30,padding=22);panel.pack(fill='x',padx=26)
        body=panel.body
        tk.Label(body,text='Tu próxima partida empieza aquí.',font=('Bahnschrift',21),bg=PANEL,fg=INK).pack(anchor='w',pady=(4,6))
        self.license_title=tk.Label(body,text='Conecta tu cuenta',font=('Bahnschrift',12,'bold'),bg=PANEL,fg=ACCENT);self.license_title.pack(anchor='w')
        self.license_detail=tk.Label(body,text='Tu acceso y tiempo restante aparecerán aquí.',font=('Bahnschrift',10),bg=PANEL,fg=MUTED,wraplength=640,justify='left');self.license_detail.pack(anchor='w',pady=(4,14))
        self.login_area=tk.Frame(body,bg=PANEL);self.login_area.pack(fill='x')
        for col,(title,var,secret) in enumerate([('Correo',self.email,False),('Contraseña',self.password,True)]):
            cell=tk.Frame(self.login_area,bg=PANEL);cell.grid(row=0,column=col,sticky='ew',padx=(0,12));self.login_area.columnconfigure(col,weight=1)
            tk.Label(cell,text=title,font=('Bahnschrift',10),bg=PANEL,fg=MUTED).pack(anchor='w',pady=(0,6))
            entry=RoundedEntry(cell,textvariable=var,show='●' if secret else '',font=('Bahnschrift',11));entry.pack(fill='x');entry.entry.bind('<Return>',lambda e:self.login())
        self.login_button=RoundedButton(self.login_area,text='Entrar',command=self.login,bg=ACCENT,fg=BG,activebackground='#94efd1',activeforeground=BG,pady=10)
        self.login_button.grid(row=0,column=2,sticky='s',pady=(0,2))
        self.account_row=tk.Frame(body,bg=PANEL)
        RoundedButton(self.account_row,text='Mi cuenta',command=self.open_account,bg=PANEL,fg=INK,pady=5).pack(side='left')
        RoundedButton(self.account_row,text='Cerrar sesión',command=self.logout,bg=PANEL,fg=MUTED,pady=5).pack(side='right')
        self.play_button=RoundedButton(root,text='Iniciar DragonLab  ↗',command=self.play,bg=ACCENT,fg=BG,activebackground='#94efd1',activeforeground=BG,font=('Bahnschrift',18,'bold'),pady=18,state='disabled')
        self.play_button.pack(fill='x',padx=54,pady=(20,12))
        self.status=tk.Label(root,text='Inicia sesión para comprobar tu acceso.',wraplength=680,justify='center',bg=BG,fg=MUTED,font=('Bahnschrift',10));self.status.pack(fill='x',padx=32,pady=(0,12))
        versions=RoundedPanel(root,PANEL,radius=24,padding=14);versions.pack(fill='x',padx=26)
        row=tk.Frame(versions.body,bg=PANEL);row.pack(fill='x')
        self.program_label=tk.Label(row,text='Programa · por instalar',font=('Bahnschrift',11,'bold'),bg=PANEL,fg=INK);self.program_label.pack(side='left')
        self.update_button=RoundedButton(row,text='Buscar actualización',command=self.check_update,bg='#263b42',fg=INK,pady=5);self.update_button.pack(side='right')
        self.calibration_label=tk.Label(versions.body,text='Calibraciones · sin sincronizar',font=('Bahnschrift',10),bg=PANEL,fg=MUTED);self.calibration_label.pack(anchor='w',pady=(6,0))
        self.update_label=tk.Label(versions.body,text='Actualizaciones · sin comprobar',font=('Bahnschrift',10),bg=PANEL,fg=MUTED);self.update_label.pack(anchor='w',pady=(4,0))
        privacy=tk.Frame(root,bg=BG);privacy.pack(fill='x',padx=34,pady=(16,0))
        self.consent=ConsentSwitch(privacy,text='Ayudar a mejorar las calibraciones',variable=self.share,command=self.change_consent,state='disabled');self.consent.pack(anchor='w')
        tk.Label(privacy,text='Opcional. Solo mediciones de tiros; sin capturas, chats ni nombres.',font=('Bahnschrift',9),bg=BG,fg=MUTED).pack(anchor='w',pady=(3,0))
        foot=tk.Frame(root,bg=BG);foot.pack(side='bottom',fill='x',padx=30,pady=18)
        RoundedButton(foot,text='Cómo usarlo',command=self.help,bg=BG,fg=MUTED,pady=5).pack(side='left')
        RoundedButton(foot,text='Carros y calibraciones',command=self.calibration_help,bg=BG,fg=MUTED,pady=5).pack(side='left',padx=10)
        RoundedButton(foot,text='Mi cuenta ↗',command=self.open_account,bg=BG,fg=MUTED,pady=5).pack(side='right')
        root.protocol('WM_DELETE_WINDOW',self.close)
        try:self.client=CloudClient(BASE/'cloud-desktop.json')
        except CloudError:
            self.status.config(text='Servidor pendiente de configuración. Consulta la guía de activación.');self.license_detail.config(text='Configura el servidor antes de distribuir el launcher.');self.login_button.config(state='disabled');self.consent.config(state='disabled')
        self.refresh_versions();root.after(50,self.poll)
        if self.client and self.client.session and '--check' not in sys.argv:self.run(self.client.require_access,self.show_account)
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
        self.root.after(100,self.poll)
    def finish(self,value,error,done):
        self.busy=False;self.login_button.config(state='normal' if self.client else 'disabled');self.update_button.config(state='normal')
        if error:
            self.status.config(text=error);self.share.set(bool(self.client and self.client.account and self.client.account.get('share_measurements')))
            if self.update_label.cget('text')=='Actualizaciones · comprobando…':self.update_label.config(text='Actualizaciones · no se pudo comprobar')
        else:done(value)
        account=self.client.account if self.client else None
        self.play_button.config(state='normal' if account and account.get('active') else 'disabled');self.consent.config(state='normal' if account else 'disabled');self.refresh_versions()
    def login(self):
        if not self.client or self.busy:return
        email=self.email.get().strip();password=self.password.get()
        if not email or not password:self.status.config(text='Escribe tu correo y contraseña.');return
        self.password.set('');self.status.config(text='Comprobando tu cuenta…');self.run(lambda:self.client.login(email,password),self.show_account)
    def show_account(self,account):
        seconds=max(0,int(account.get('remaining_seconds',0)));days=seconds//86400;end=account.get('expires_at')
        remaining=f'{days} días completos disponibles' if days else f'{seconds//3600} h {(seconds%3600)//60} min disponibles'
        user=(self.client.session or {}).get('user',{}).get('email') or self.email.get() or 'Tu cuenta'
        self.license_title.config(text='Acceso de administrador' if account.get('role')=='admin' else user)
        try:expires=datetime.fromisoformat(end.replace('Z','+00:00')).astimezone().strftime('%d/%m/%Y %H:%M') if end else 'sin fecha asignada'
        except (ValueError,TypeError):expires='por comprobar'
        self.license_detail.config(text='Panel de administración disponible.' if account.get('role')=='admin' else remaining+' · vence '+expires)
        if not account.get('active'):self.license_detail.config(text='Acceso vencido o suspendido. Contacta al administrador.')
        self.login_area.pack_forget();self.account_row.pack(fill='x');self.share.set(bool(account.get('share_measurements')))
        self.status.config(text='Tu acceso está comprobado.' if account.get('active') else 'No tienes un acceso activo.')
    def change_consent(self):
        if not self.client or self.busy:return
        enabled=self.share.get();self.run(lambda:(self.client.consent(enabled),self.client.account)[1],self.show_account)
    def logout(self):
        if not self.client or self.busy:return
        def done(value):
            self.client.account=None;self.account_row.pack_forget();self.login_area.pack(fill='x');self.license_title.config(text='Conecta tu cuenta');self.license_detail.config(text='Tu acceso y tiempo restante aparecerán aquí.');self.share.set(False);self.status.config(text='Sesión cerrada.')
        self.run(self.client.logout,done)
    def open_account(self):
        url=self.client.config.get('panelUrl','') if self.client else ''
        if url.startswith('https://'):webbrowser.open(url)
        else:messagebox.showinfo('Tu cuenta','El panel todavía no está configurado.',parent=self.root)
    def help(self):messagebox.showinfo('Cómo usar DragonLab','1. Entra con tu cuenta.\n2. Pulsa Iniciar DragonLab.\n3. Abre el juego desde DragonLab.\n\nCtrl cambia el objetivo. Q aplica un tiro en tu turno.\nLos atajos se pueden cambiar en Ajustes.',parent=self.root)
    def calibration_help(self):messagebox.showinfo('Carros y calibraciones','DragonLab distingue carro, tiro 1, tiro 2 y SS.\nEn el juego verás Listo, Aprendiendo o Bloqueado.\n\nCompartir mediciones es opcional. Una revisión compartida no garantiza que todos los carros estén completamente calibrados.',parent=self.root)
    def check_update(self):
        if self.busy:return
        self.update_label.config(text='Actualizaciones · comprobando…')
        def done(manifest):
            self.manifest=manifest;version=installed_version(self.client.directory) if self.client else None
            self.update_label.config(text='Actualizado · v'+manifest['version'] if version==manifest['version'] else 'Disponible · v'+manifest['version']+' · se instalará al iniciar')
            self.status.config(text='Comprobación de actualizaciones terminada.')
        self.run(fetch_manifest,done)
    def play(self):
        if not self.client or self.busy:return
        self.status.config(text='Comprobando acceso y preparando el programa…')
        def update():
            self.client.require_access();manifest=fetch_manifest(self.client.config.get('githubRepo',REPO));version=manifest['version'];target=self.client.directory/('DragonLab-Cloud-'+version+'.exe')
            if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest()!=manifest['sha256']:download_verified(manifest['url'],target,manifest['sha256'],REPO)
            atomic_write(self.client.directory/'cloud-desktop.json',json.dumps(self.client.config).encode())
            subprocess.Popen([str(target),'--minimized'],cwd=self.client.directory)
            atomic_write(self.client.directory/'installed-release.json',json.dumps({'version':version,'sha256':manifest['sha256']}).encode())
            return self.client.account
        def done(account):self.show_account(account);self.status.config(text='DragonLab abierto. Las actualizaciones se comprueban al iniciar.');self.update_label.config(text='Versión comprobada al iniciar')
        self.run(update,done)
    def close(self):self.closed=True;self.root.destroy()

if __name__=='__main__':
    root=tk.Tk();app=Launcher(root)
    if '--check' in sys.argv:root.withdraw();root.after(600,app.close)
    root.mainloop()
