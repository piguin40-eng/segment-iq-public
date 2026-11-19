"""Short, local, unreviewed dictation. Audio is temporary; it never enters RAG."""
import threading
from pathlib import Path

MAX_AUDIO_BYTES=20*1024*1024
MAX_AUDIO_SECONDS=120
FORMATS={'webm':'matroska','ogg':'ogg','opus':'ogg','wav':'wav','mp3':'mp3',
         'mp4':'mov','m4a':'mov','flac':'flac'}

class DictationError(ValueError):pass
class DictationBusy(RuntimeError):pass

def decode_short_audio(path,extension):
    import av
    import numpy as np
    pieces=[];samples=0;limit=16000*MAX_AUDIO_SECONDS
    try:
        # Force an audio/container demuxer, so a renamed playlist cannot fetch URLs.
        with av.open(str(path),format=FORMATS[extension]) as container:
            if not container.streams.audio:raise DictationError('El archivo no contiene una pista de audio.')
            resampler=av.AudioResampler(format='fltp',layout='mono',rate=16000)
            def collect(frames):
                nonlocal samples
                for frame in frames:
                    value=frame.to_ndarray().reshape(-1);samples+=len(value)
                    if samples>limit:raise DictationError('El dictado admite hasta 2 minutos. Divide la indicación en varias notas.')
                    pieces.append(value)
            for frame in container.decode(audio=0):collect(resampler.resample(frame))
            collect(resampler.resample(None))
    except DictationError:raise
    except Exception as error:raise DictationError('No se pudo leer el audio. Prueba una grabación WAV, WebM, M4A o MP3.') from error
    if samples<1600:raise DictationError('La grabación es demasiado corta. Mantén el micrófono activo mientras hablas.')
    audio=np.concatenate(pieces)
    if not np.isfinite(audio).all() or float(np.max(np.abs(audio)))<1e-5:
        raise DictationError('No se oye voz en la grabación. Comprueba el micrófono y vuelve a intentarlo.')
    return audio

class Dictation:
    def __init__(self,settings):
        self.settings=settings;self.model=None;self.lock=threading.Lock()

    def transcribe(self,path,extension):
        if not self.lock.acquire(blocking=False):
            raise DictationBusy('Se está transcribiendo otra nota de voz. Espera unos segundos y pulsa Reintentar.')
        try:
            audio=decode_short_audio(path,extension)
            if self.model is None:
                from faster_whisper import WhisperModel
                self.model=WhisperModel(self.settings.whisper_model,device='cpu',compute_type='int8',
                    cpu_threads=2,download_root=str(self.settings.data/'models/whisper'))
            segments,_=self.model.transcribe(audio,language='es',vad_filter=True,
                condition_on_previous_text=False,beam_size=5,
                initial_prompt='Vocabulario dental: Blender, primaria, supra, barra, chimenea, interfase, retenciones, milímetros.')
            text=' '.join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
            if not text:raise DictationError('No se ha detectado una indicación hablada. Prueba de nuevo, más cerca del micrófono.')
            return {'text':text,'language':'es','seconds':round(len(audio)/16000,2),
                    'engine':'faster-whisper local','review_required':True}
        finally:self.lock.release()
