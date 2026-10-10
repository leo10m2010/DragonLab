"""Small HTTPS account client; public config only. Tokens stay protected on Windows."""
import base64,ctypes,hashlib,json,os,pathlib,re,time,urllib.request,urllib.error

class CloudError(Exception):pass
def validate_public_key(key):
    if not key or 'YOUR-' in key or key.startswith('sb_secret_'):raise CloudError('Se requiere una clave pública, nunca service_role.')
    if key.startswith('sb_publishable_'):return
    try:
        payload=key.split('.')[1];role=json.loads(base64.urlsafe_b64decode(payload+'='*((4-len(payload)%4)%4))).get('role')
    except (ValueError,IndexError):raise CloudError('Clave pública no válida.') from None
    if role!='anon':raise CloudError('Se requiere la clave pública anon, nunca service_role.')
class Blob(ctypes.Structure):_fields_=[('size',ctypes.c_ulong),('data',ctypes.POINTER(ctypes.c_byte))]
def protect(data,decrypt=False):
    if os.name!='nt':raise CloudError('El almacenamiento de sesión requiere Windows.')
    buf=ctypes.create_string_buffer(data);inp=Blob(len(data),ctypes.cast(buf,ctypes.POINTER(ctypes.c_byte)));out=Blob()
    method=ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not method(ctypes.byref(inp),None,None,None,None,1,ctypes.byref(out)):raise CloudError('No se pudo proteger la sesión.')
    try:return ctypes.string_at(out.data,out.size)
    finally:ctypes.windll.kernel32.LocalFree(out.data)

class CloudClient:
    def __init__(self,config_path):
        try:self.config=json.loads(pathlib.Path(config_path).read_text(encoding='utf-8'))
        except (OSError,ValueError):raise CloudError('Falta cloud-desktop.json. Consulta la guía de instalación.')
        self.url=self.config.get('supabaseUrl','').rstrip('/');self.key=self.config.get('publicKey','')
        if not re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co',self.url) or not self.key or 'YOUR-' in self.key:raise CloudError('El servidor todavía no está configurado.')
        validate_public_key(self.key)
        self.directory=pathlib.Path(os.environ.get('LOCALAPPDATA',str(pathlib.Path.home())))/'DragonLabCloud'/hashlib.sha256(self.url.encode()).hexdigest()[:12]
        self.directory.mkdir(parents=True,exist_ok=True);self.path=self.directory/'session.bin';self.session=None;self.account=None
        try:self.session=json.loads(protect(self.path.read_bytes(),True))
        except (OSError,ValueError,CloudError):pass
    def save(self):
        temp=self.path.with_suffix('.tmp');temp.write_bytes(protect(json.dumps(self.session).encode()));temp.replace(self.path)
    def request(self,path,data=None,method='POST',auth=True):
        if auth and not self.session:raise CloudError('Inicia sesión en el launcher.')
        headers={'apikey':self.key,'Content-Type':'application/json'}
        if auth:headers['Authorization']='Bearer '+self.session['access_token']
        req=urllib.request.Request(self.url+path,data=json.dumps(data).encode() if data is not None else None,headers=headers,method=method)
        try:
            with urllib.request.urlopen(req,timeout=12) as response:return json.load(response)
        except urllib.error.HTTPError as error:
            try:value=json.loads(error.read());message=value.get('msg') or value.get('message') or value.get('error_description') or 'Operación rechazada.'
            except (ValueError,TypeError):message='Operación rechazada.'
            raise CloudError(message) from None
        except (urllib.error.URLError,TimeoutError,OSError):raise CloudError('No se pudo conectar con el servidor.') from None
    def login(self,email,password):
        self.session=self.request('/auth/v1/token?grant_type=password',{'email':email,'password':password},auth=False);self.save();return self.status()
    def refresh(self):
        if not self.session:raise CloudError('Inicia sesión en el launcher.')
        self.session=self.request('/auth/v1/token?grant_type=refresh_token',{'refresh_token':self.session['refresh_token']},auth=False);self.save()
    def status(self):
        try:self.session=json.loads(protect(self.path.read_bytes(),True))
        except (OSError,ValueError,CloudError):pass
        if not self.session:raise CloudError('Inicia sesión en el launcher.')
        if self.session.get('expires_at',0)<time.time()+60:self.refresh()
        self.account=self.rpc('my_account');return self.account
    def require_access(self):
        account=self.status()
        if not account or not account.get('active'):raise CloudError('Tu acceso venció o está suspendido. Contacta al administrador.')
        return account
    def rpc(self,name,args=None):return self.request('/functions/v1/dragonlab-api',{'action':name,'args':args or {}})
    def logout(self):
        try:self.request('/auth/v1/logout',{})
        finally:self.session=None;self.path.unlink(missing_ok=True)
    def consent(self,enabled):self.rpc('set_measurement_consent',{'enabled':bool(enabled),'erase_existing':False});self.status()
    def send_new_measurements(self,book,excluded_ids=None):
        # Consent and expiry are also checked by the server on every batch.
        if not self.account or not self.account.get('share_measurements'):return 0
        sent_path=self.directory/('sent-'+self.account['user_id']+'.json')
        try:sent=set(json.loads(sent_path.read_text()))
        except (OSError,ValueError):sent=set()
        batch=[]
        for key,record in book.records.items():
            clone,mobile,shot=key.split(':')
            for sample in record.get('samples',[]):
                if sample.get('source')!='native-shot-start' or not sample.get('sample_id'):continue
                digest=hashlib.sha256((key+':'+sample['sample_id']).encode()).hexdigest()
                if excluded_ids and digest in excluded_ids:continue
                if digest in sent:continue
                item={k:sample[k] for k in ('power','vx','vy','ax','ay','wind','wind_angle')};item.update(sample_key=digest,clone=clone,mobile=mobile,shot=int(shot),source='native-shot-start');batch.append(item)
                if len(batch)>=50:break
            if len(batch)>=50:break
        if not batch:return 0
        count=self.rpc('ingest_measurements',{'batch':batch});sent.update(x['sample_key'] for x in batch)
        temp=sent_path.with_suffix('.tmp');temp.write_text(json.dumps(sorted(sent)[-100000:]));temp.replace(sent_path);return count

def download_verified(url,destination,expected,repo,opener=urllib.request.urlopen):
    if not re.fullmatch(r'[0-9a-f]{64}',expected):raise CloudError('La actualización no tiene una comprobación válida.')
    if not url.startswith('https://github.com/'+repo+'/releases/download/'):raise CloudError('La descarga no pertenece al repositorio configurado.')
    destination=pathlib.Path(destination);temporary=destination.with_suffix('.download');digest=hashlib.sha256();size=0
    try:
        with opener(urllib.request.Request(url,headers={'User-Agent':'DragonLabLauncher'}),timeout=30) as response,temporary.open('wb') as file:
            while True:
                block=response.read(1024*1024)
                if not block:break
                size+=len(block)
                if size>150*1024*1024:raise CloudError('Actualización demasiado grande.')
                digest.update(block);file.write(block)
        if digest.hexdigest()!=expected:raise CloudError('La descarga no coincide con la versión publicada.')
        temporary.replace(destination)
    finally:temporary.unlink(missing_ok=True)
