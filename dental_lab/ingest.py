import hashlib,json,time,uuid,re,shutil,threading
from pathlib import Path
import numpy as np

VIDEO={'.mp4','.mkv','.mov','.avi','.webm'}
AUDIO={'.wav','.mp3','.m4a','.flac','.ogg'}
TEXT={'.txt','.md','.srt','.vtt','.json','.py'}
ALLOWED=VIDEO|AUDIO|TEXT|{'.pdf','.png','.jpg','.jpeg','.stl','.blend','.blend1'}

def sha(path):
    with open(path,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

class Ingest:
    def __init__(self,s,db,rag):self.s=s;self.db=db;self.rag=rag;self.whisper=None;self.ocr=None

    def register(self,path,name=None):
        path=Path(path);suffix=path.suffix.lower()
        if suffix not in ALLOWED:raise ValueError('Formato no admitido')
        hash=sha(path);old=self.db.one('SELECT * FROM sources WHERE sha256=?',(hash,))
        if old:return old,False
        id=uuid.uuid4().hex;dest=self.s.data/'originals'/(id+suffix);shutil.copy2(path,dest)
        kind='video' if suffix in VIDEO else 'audio' if suffix in AUDIO else 'geometry' if suffix in {'.stl','.blend','.blend1'} else 'document'
        self.db.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?)',(id,name or path.name,str(dest),hash,kind,'queued','',time.time()))
        return self.db.one('SELECT * FROM sources WHERE id=?',(id,)),True

    def ocr_text(self,image):
        if self.ocr is None:
            from rapidocr import RapidOCR
            self.ocr=RapidOCR()
        result=self.ocr(image)
        return '\n'.join(result.txts or [])

    def process(self,id):
        source=self.db.one('SELECT * FROM sources WHERE id=?',(id,));path=Path(source['path']);suffix=path.suffix.lower();chunks=[];notes=[]
        self.db.execute('UPDATE sources SET status=?,detail=? WHERE id=?',('indexing','Procesando contenido',id))
        try:
            if suffix in VIDEO|AUDIO:
                import av
                with av.open(str(path)) as container:has_audio=bool(container.streams.audio)
                if has_audio:
                    if self.whisper is None:
                        from faster_whisper import WhisperModel
                        self.whisper=WhisperModel(self.s.whisper_model,device='cpu',compute_type='int8',cpu_threads=4,download_root=str(self.s.data/'models/whisper'))
                    segments,info=self.whisper.transcribe(str(path),language='es',vad_filter=True,initial_prompt='Blender, primaria, supra, barra, cement gap, remallado, Skin, Shrinkwrap, conos, retenciones, implantes.')
                    for seg in segments:
                        if seg.text.strip():chunks.append({'text':seg.text.strip(),'start':seg.start,'end':seg.end,'kind':'transcripcion_no_revisada'})
                else:notes.append('Sin pista de audio; indexacion visual')
                if suffix in VIDEO:chunks.extend(self.frames(path,id,notes))
            elif suffix=='.pdf':
                from pypdf import PdfReader
                for i,page in enumerate(PdfReader(path).pages):
                    text=page.extract_text() or ''
                    chunks.extend(self.text_chunks(text,f'documento_pagina_{i+1}'))
                if not chunks:notes.append('PDF sin texto extraible: requiere OCR o capturas')
            elif suffix in TEXT:chunks.extend(self.text_chunks(path.read_text(encoding='utf-8-sig',errors='replace'),'documento_no_revisado'))
            elif suffix in {'.png','.jpg','.jpeg'}:
                from PIL import Image
                text=self.ocr_text(np.array(Image.open(path).convert('RGB')))
                if text:chunks.append({'text':text,'kind':'ocr_no_revisado'})
                if self.s.vision:
                    try:chunks.append({'text':self.rag.describe_frame(path),'kind':'inferencia_visual_no_revisada'})
                    except Exception as e:notes.append('Descripcion visual pendiente: '+str(e)[:200])
            elif source['kind']=='geometry':
                from .learning_geometry import measure_geometry
                chunks.extend(measure_geometry(self.s,source,self.s.data/'derived'/id))
                notes.append('Geometría de referencia medida. Escenas y mallas sirven para comparar; la construcción parte del STL original del caso.')
            else:notes.append('Formato sin extracción disponible')
            if suffix in VIDEO:
                # Re-indexing machine transcript/OCR must not erase reviewed lab learning.
                reviewed=self.db.rows("SELECT text,start,end,frame,kind FROM chunks WHERE source_id=? AND kind='sintesis_video_contrastada' ORDER BY id",(id,))
                chunks.extend(reviewed)
                if reviewed:notes.append(f'{len(reviewed)} síntesis contrastadas conservadas')
            self.rag.enrich(chunks);self.db.add_chunks(id,chunks)
            if self.rag.last_embedding_error:notes.append('Indice semantico pendiente: '+self.rag.last_embedding_error[:200])
            status='ready' if chunks and not any('pendiente' in n or 'limite' in n for n in notes) else 'partial' if chunks else 'registered' if source['kind']=='geometry' else 'needs_review'
            detail=f'{len(chunks)} fragmentos. '+' | '.join(notes)
            self.db.execute('UPDATE sources SET status=?,detail=? WHERE id=?',(status,detail,id))
            folder=self.s.data/'derived'/id;folder.mkdir(exist_ok=True)
            (folder/'index.json').write_text(json.dumps({'source_sha256':source['sha256'],'chunks':[{k:v for k,v in c.items() if k!='vector'} for c in chunks],'notes':notes},ensure_ascii=False,indent=2),encoding='utf-8')
            return detail
        except Exception as e:
            self.db.execute('UPDATE sources SET status=?,detail=? WHERE id=?',('failed',str(e),id));raise

    @staticmethod
    def text_chunks(text,kind):
        return [{'text':text[i:i+1400],'kind':kind} for i in range(0,len(text),1100) if text[i:i+1400].strip()]

    def frames(self,path,id,notes):
        import av
        from PIL import Image
        dest=self.s.data/'derived'/id;dest.mkdir(exist_ok=True);chunks=[];next_time=0;previous=None;count=0;vision_failed=False
        with av.open(str(path)) as container:
            if not container.streams.video:return chunks
            for frame in container.decode(video=0):
                t=float(frame.time or 0)
                if t<next_time:continue
                next_time=t+self.s.frame_seconds
                if count>=self.s.max_frames:notes.append(f'limite visual {self.s.max_frames} capturas alcanzado en {t:.1f}s; transcripcion completa conservada');break
                image=frame.to_image();tiny=np.asarray(image.resize((32,32)).convert('L'),dtype=float)
                if previous is not None and np.abs(tiny-previous).mean()<2:continue
                previous=tiny;count+=1;image.thumbnail((1280,960));file=dest/f'frame_{count:05d}.jpg';image.save(file,quality=85)
                text=self.ocr_text(np.array(image.convert('RGB')))
                frame_key=str(file.relative_to(self.s.data)).replace('\\','/')
                if text:chunks.append({'text':text,'start':t,'end':t,'frame':frame_key,'kind':'ocr_no_revisado'})
                if self.s.vision and not vision_failed:
                    try:chunks.append({'text':self.rag.describe_frame(file),'start':t,'end':t,'frame':frame_key,'kind':'inferencia_visual_no_revisada'})
                    except Exception as e:notes.append('Descripcion visual pendiente: '+str(e)[:200]);vision_failed=True
            notes.append(f'{count} capturas muestreadas, intervalo minimo {self.s.frame_seconds}s; no captura cada movimiento')
        return chunks
