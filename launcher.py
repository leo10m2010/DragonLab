"""Windows launcher: account, remaining time, consent and GitHub Releases updates."""
import json,pathlib,subprocess,sys,threading,urllib.request,webbrowser,tkinter as tk
from tkinter import messagebox
from datetime import datetime
from rounded_widgets import RoundedButton,RoundedPanel
from cloud_client import CloudClient,CloudError,download_verified
BASE=pathlib.Path(sys.executable).parent if getattr(sys,'frozen',False) else pathlib.Path(__file__).parent
BG='#f3f1e9';INK='#193b2d'
class Launcher:
    def __init__(self,root):
        self.root=root;root.title('DragonLab · Launcher');root.geometry('440x610');root.configure(bg=BG);root.resizable(False,False);self.busy=False;self.client=None
        tk.Label(root,text='↗  DragonLab',font=('Bahnschrift',25),bg=BG,fg=INK).pack(pady=(30,8))
        tk.Label(root,text='TU PARTIDA. TU GUÍA.',font=('Bahnschrift',10),bg=BG,fg='#68805d').pack()
        panel=RoundedPanel(root,'#fffdf7',radius=28,padding=22);panel.pack(fill='both',expand=True,padx=24,pady=24);self.body=panel.body
        self.email=tk.StringVar();self.password=tk.StringVar();self.share=tk.BooleanVar()
        tk.Label(self.body,text='Tu cuenta',font=('Bahnschrift',22),bg='#fffdf7',fg=INK).pack(anchor='w',pady=(5,20))
        for title,var,secret in [('Correo',self.email,False),('Contraseña',self.password,True)]:
            tk.Label(self.body,text=title,bg='#fffdf7',fg=INK,font=('Bahnschrift',10)).pack(anchor='w')
            tk.Entry(self.body,textvariable=var,show='●' if secret else '',font=('Bahnschrift',12),relief='flat',bg='#edf0e4',fg=INK).pack(fill='x',ipady=10,pady=(6,14))
        self.login_button=RoundedButton(self.body,text='Entrar',command=self.login,bg=INK,fg='#faffef');self.login_button.pack(fill='x',pady=6)
        self.status=tk.Label(self.body,text='Inicia sesión para comprobar tu acceso.',wraplength=325,justify='left',bg='#fffdf7',fg='#59715c',font=('Bahnschrift',11));self.status.pack(anchor='w',pady=14)
        self.consent=tk.Checkbutton(self.body,text='Compartir mediciones para mejorar',variable=self.share,command=self.change_consent,bg='#fffdf7',fg=INK,activebackground='#fffdf7',wraplength=320,justify='left',state='disabled');self.consent.pack(anchor='w')
        tk.Label(self.body,text='Solo datos de los tiros. Sin capturas, chats ni nombres. Puedes desactivarlo en tu cuenta.',wraplength=315,justify='left',bg='#fffdf7',fg='#697b65',font=('Bahnschrift',9)).pack(anchor='w',pady=(2,15))
        self.play_button=RoundedButton(self.body,text='Abrir DragonLab ↗',command=self.play,bg=INK,fg='#faffef',state='disabled');self.play_button.pack(fill='x')
        RoundedButton(root,text='Mi cuenta',command=self.open_account,bg=BG,fg=INK,pady=4).pack(pady=(0,12))
        try:self.client=CloudClient(BASE/'cloud-desktop.json')
        except CloudError as e:self.status.config(text=str(e));self.login_button.config(state='disabled')
        if self.client and self.client.session:self.run(lambda:self.client.require_access(),self.show_account)
    def run(self,work,done):
        if self.busy:return
        self.busy=True;self.login_button.config(state='disabled');self.play_button.config(state='disabled')
        def thread():
            try:value=work();error=None
            except Exception as e:value=None;error=str(e)
            self.root.after(0,lambda:self.finish(value,error,done))
        threading.Thread(target=thread,daemon=True).start()
    def finish(self,value,error,done):
        self.busy=False;self.login_button.config(state='normal')
        if error:self.status.config(text=error)
        else:done(value)
        self.play_button.config(state='normal' if self.client and self.client.account and self.client.account.get('active') else 'disabled')
    def login(self):
        email=self.email.get().strip();password=self.password.get()
        self.run(lambda:self.client.login(email,password),self.show_account);self.password.set('')
    def show_account(self,account):
        seconds=int(account.get('remaining_seconds',0));days=seconds//86400;end=account.get('expires_at')
        remaining=f'{days} días completos disponibles' if days else f'{seconds//3600} h {(seconds%3600)//60} min disponibles'
        text='Administrador · acceso de gestión' if account['role']=='admin' else remaining+'\nVence: '+(datetime.fromisoformat(end.replace('Z','+00:00')).astimezone().strftime('%d/%m/%Y %H:%M') if end else 'sin acceso asignado')
        if not account.get('active'):text='Acceso vencido o suspendido. Contacta al administrador.'
        self.status.config(text=text);self.share.set(account['share_measurements']);self.consent.config(state='normal')
    def change_consent(self):self.run(lambda:(self.client.consent(self.share.get()),self.client.account)[1],self.show_account)
    def open_account(self):
        if self.client:
            url=self.client.config.get('panelUrl','')
            if url.startswith('https://'):webbrowser.open(url)
            else:messagebox.showinfo('Tu cuenta','Falta configurar panelUrl en cloud-desktop.json.')
    def play(self):
        self.status.config(text='Comprobando acceso y actualizaciones…')
        def update():
            self.client.require_access();repo=self.client.config.get('githubRepo','leo10m2010/DragonLab')
            if repo!='leo10m2010/DragonLab':raise CloudError('Repositorio no autorizado en esta versión del launcher.')
            req=urllib.request.Request('https://api.github.com/repos/'+repo+'/releases/latest',headers={'User-Agent':'DragonLabLauncher','Accept':'application/vnd.github+json'})
            try:
                with urllib.request.urlopen(req,timeout=15) as response:release=json.load(response)
            except Exception:raise CloudError('No hay una versión Cloud publicada o no se pudo comprobar GitHub.')
            asset=next((a for a in release['assets'] if a['name']=='dragonlab-release.json'),None)
            if not asset:raise CloudError('La versión publicada todavía no incluye el paquete Cloud.')
            if not asset['browser_download_url'].startswith('https://github.com/'+repo+'/releases/download/'):raise CloudError('Manifest de actualización inválido.')
            with urllib.request.urlopen(asset['browser_download_url'],timeout=15) as response:manifest=json.load(response)
            if manifest.get('schema')!=1 or manifest.get('asset')!='DragonLab-Cloud.exe':raise CloudError('Versión Cloud no compatible.')
            import re,hashlib
            version=manifest.get('version','')
            if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise CloudError('Versión de actualización inválida.')
            target=self.client.directory/('DragonLab-Cloud-'+version+'.exe')
            if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest()!=manifest['sha256']:
                download_verified(manifest['url'],target,manifest['sha256'],repo)
            (self.client.directory/'cloud-desktop.json').write_text(json.dumps(self.client.config),encoding='utf-8')
            subprocess.Popen([str(target),'--minimized'],cwd=self.client.directory)
            return self.client.account
        self.run(update,self.show_account)
if __name__=='__main__':
    root=tk.Tk();app=Launcher(root)
    if '--check' in sys.argv:root.withdraw();root.after(600,root.destroy)
    root.mainloop()
