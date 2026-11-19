import argparse,json,os,shutil
from pathlib import Path
from .config import load,set_login
from .store import Store
from .rag import Rag
from .ingest import Ingest

def main():
    import sys
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    server=sub.add_parser('serve');server.add_argument('--host',default='127.0.0.1');server.add_argument('--port',type=int,default=8765)
    index=sub.add_parser('index');index.add_argument('path');index.add_argument('--queue',action='store_true')
    search=sub.add_parser('search');search.add_argument('question')
    ask=sub.add_parser('ask');ask.add_argument('question')
    sub.add_parser('status');sub.add_parser('backup')
    login=sub.add_parser('set-login');login.add_argument('--username',required=True)
    a=p.parse_args();s=load()
    if a.command=='set-login':
        from getpass import getpass
        password=getpass('Nueva contraseña: ')
        if password!=getpass('Repite la contraseña: '):p.error('Las contraseñas no coinciden')
        set_login(s.data,a.username,password)
        print('Acceso guardado. Reinicia SEGMENT IQ para aplicarlo. La clave API se conserva.');return
    if a.command=='serve':
        import uvicorn
        from .server import create_app
        uvicorn.run(create_app(s),host=a.host,port=a.port);return
    db=Store(s.data);rag=Rag(s,db);ingest=Ingest(s,db,rag)
    if a.command=='index':
        source,new=ingest.register(a.path)
        print(json.dumps({'source_id':source['id'],'new':new,'result':db.job('index',source['id']) if a.queue else ingest.process(source['id'])},ensure_ascii=False))
    elif a.command=='search':print(json.dumps(rag.search(a.question),ensure_ascii=False,indent=2))
    elif a.command=='ask':print(json.dumps(rag.chat(a.question),ensure_ascii=False,indent=2))
    elif a.command=='status':print(json.dumps({'sources':db.one('SELECT count(*) n FROM sources'),'jobs':db.rows('SELECT status,count(*) n FROM jobs GROUP BY status'),'data':str(s.data)},ensure_ascii=False,indent=2))
    elif a.command=='backup':
        import sqlite3,time
        target=s.data.parent/'backups'/time.strftime('%Y%m%d_%H%M%S');target.mkdir(parents=True)
        with sqlite3.connect(db.path) as source,sqlite3.connect(target/'knowledge.sqlite3') as dest:source.backup(dest)
        for name in ['originals','derived','profiles','cases','runs']:shutil.copytree(s.data/name,target/name)
        print(target)

if __name__=='__main__':main()
