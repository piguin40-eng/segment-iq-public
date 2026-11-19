"""Check the exact staged payload, not ignored working files, before publication."""
import subprocess,sys,re
from pathlib import Path
names=subprocess.check_output(['git','diff','--cached','--name-only','-z']).decode().split('\0')
forbidden={'.stl','.blend','.blend1','.mp4','.avi','.mov','.mkv','.wav','.mp3','.sqlite','.sqlite3','.db','.zip'}
errors=[]
for name in filter(None,names):
    path=Path(name)
    if path.suffix.lower() in forbidden or any(x in path.parts for x in ['data','runtime','models','.venv','.local']) or path.name in ['config.local.json','ACCESO_LAB.txt','.env']:errors.append(name+': archivo privado o generado');continue
    content=subprocess.check_output(['git','show',':'+name])
    if len(content)>5*1024*1024:errors.append(name+': tamaño inesperado')
    if re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{35,})',content):errors.append(name+': posible credencial')
    if re.search(rb'(?i)(?:\\\\|//)[A-Za-z0-9_-]+[/\\](?:Produccion|patients|pacientes)[/\\_]',content):errors.append(name+': ruta de datos privados')
if errors:print('\n'.join(errors));sys.exit(1)
print('PASS: payload preparado sin formatos de casos, rutas del paciente o credenciales detectadas.')
