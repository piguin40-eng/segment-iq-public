"""Native service/RAG/voice checks. Only synthetic content; no account tokens."""
import json,os,subprocess,sys,time
from pathlib import Path

app=Path(__file__).resolve().parents[1];sys.path.insert(0,str(app))
from dental_lab.config import load
from macos.install_local import wait_health

root=Path(os.environ['SEGMENT_IQ_INSTALL_ROOT']).resolve()
os.environ['DENTAL_LAB_DATA']=str(root/'data')
s=load()
installation=json.loads((root/'INSTALLATION.json').read_text())
env={**os.environ,'OLLAMA_HOST':'127.0.0.1:11435','OLLAMA_MODELS':str(s.data/'models/ollama')}
processes=[]
try:
    for command in ([installation['ollama'],'serve'],[sys.executable,'-m','dental_lab.service','--serve-only',
                    '--data',str(s.data),'--host','127.0.0.1','--port','8765']):
        processes.append(subprocess.Popen(command,cwd=app,env=env))
    assert wait_health('http://127.0.0.1:8765/health')['service']=='SEGMENT IQ'
    assert wait_health('http://127.0.0.1:11435/api/version')['version']
    import httpx
    with httpx.Client(base_url='http://127.0.0.1:8765') as client:
        assert client.get('/api/cases').status_code==401
        assert client.get('/api/cases',headers={'Authorization':'Bearer '+s.password}).status_code==200
    subprocess.run([sys.executable,str(app/'scripts/prepare_models.py')],check=True,env=env)
    subprocess.run([sys.executable,str(app/'macos/seed_knowledge.py')],check=True,env=env)
    from dental_lab.store import Store
    from dental_lab.rag import Rag
    from faster_whisper import WhisperModel
    import numpy as np
    db=Store(s.data);rag=Rag(s,db)
    assert rag.search('barra continua centrada conexiones')
    assert not rag.last_embedding_error,rag.last_embedding_error
    model=WhisperModel(s.whisper_model,device='cpu',compute_type='int8',download_root=str(s.data/'models/whisper'))
    segments,_=model.transcribe(np.zeros(16000,dtype=np.float32),language='es')
    list(segments)
    # Prove model inference through the local Ollama service, without clinical claims.
    with httpx.Client(timeout=600) as client:
        response=client.post(s.ollama_url+'/api/generate',json={'model':s.model,'prompt':'Responde solo OK',
           'stream':False,'options':{'num_predict':8,'num_ctx':1024}})
        response.raise_for_status();assert response.json().get('response')
    report={'platform':sys.platform,'architecture':__import__('platform').machine(),
      'local_api':True,'authentication':True,'ollama_inference':True,'semantic_rag':True,
      'whisper_inference':True,'codex_account_tested':False,'b4d_tested':False}
    (s.data/'native-services-validation.json').write_text(json.dumps(report,indent=2))
    print('MAC_LOCAL_SERVICES_PASS (Codex account and B4D not tested)')
finally:
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=30)
            except subprocess.TimeoutExpired:process.kill();process.wait()
