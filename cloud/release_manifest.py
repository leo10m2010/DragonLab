import hashlib,json,os,pathlib,re,zipfile
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from cloud_client import validate_public_key
version=os.environ['CLOUD_VERSION'];repo=os.environ['CLOUD_REPOSITORY']
if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('Version must be numeric x.y.z')
url=os.environ.get('SUPABASE_URL','');key=os.environ.get('SUPABASE_PUBLIC_KEY','');panel=os.environ.get('PANEL_URL','')
if not re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co',url) or not key or not panel.startswith('https://'):raise ValueError('Configure public Supabase URL/key and panel URL in repository Variables first')
validate_public_key(key)
root=pathlib.Path('cloud-dist');asset='DragonLab-Cloud.exe';digest=hashlib.sha256((root/asset).read_bytes()).hexdigest()
(root/'dragonlab-release.json').write_text(json.dumps({'schema':1,'version':version,'asset':asset,'url':f'https://github.com/{repo}/releases/download/cloud-v{version}/{asset}','sha256':digest},indent=2))
(root/'cloud-desktop.json').write_text(json.dumps({'supabaseUrl':url,'publicKey':key,'githubRepo':repo,'panelUrl':panel},indent=2))
with zipfile.ZipFile(root/'DragonLab-Launcher.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in ['DragonLab-Launcher.exe','cloud-desktop.json']:z.write(root/name,name)
