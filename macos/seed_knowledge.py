"""Index the shipped method in this Mac's private library, with no patient files."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dental_lab.config import load
from dental_lab.store import Store
from dental_lab.rag import Rag
from dental_lab.ingest import Ingest
s=load();db=Store(s.data);ingest=Ingest(s,db,Rag(s,db))
for path in sorted((s.app/'openclaw/skills').rglob('*.md')):
    source,new=ingest.register(path,name='Protocolo incluido · '+str(path.relative_to(s.app/'openclaw/skills')))
    if new or source['status']!='ready':ingest.process(source['id'])
print('Skills y procedimiento indexados en el RAG de este Mac.')
