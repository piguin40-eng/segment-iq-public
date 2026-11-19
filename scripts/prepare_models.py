from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dental_lab.config import load
from dental_lab.store import Store
from dental_lab.rag import Rag
import httpx
s=load()
with httpx.Client(timeout=900) as client:
    with client.stream('POST',s.ollama_url+'/api/pull',json={'model':s.model,'stream':True}) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:continue
            result=json.loads(line)
            if result.get('error'):raise RuntimeError(result['error'])
rag=Rag(s,Store(s.data));assert len(rag.vectors(['Barra dental'])[0])==384
from faster_whisper import WhisperModel
WhisperModel(s.whisper_model,device='cpu',compute_type='int8',cpu_threads=4,download_root=str(s.data/'models/whisper'))
print('Modelos preparados: lenguaje/vision, embeddings y transcripcion.')
