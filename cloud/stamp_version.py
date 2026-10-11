import os,re,pathlib
version=os.environ['CLOUD_VERSION']
if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('Version must be numeric x.y.z')
pathlib.Path('app_version.py').write_text(f"LAUNCHER_VERSION = '{version}'\nPROGRAM_VERSION = '{version}'\n",encoding='utf-8')
