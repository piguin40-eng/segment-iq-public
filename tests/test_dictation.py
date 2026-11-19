import io,wave
from pathlib import Path
import numpy as np
import pytest
from test_core import client
from dental_lab import dictation as speech

def wav(seconds=1,silence=False):
    audio=np.zeros(int(16000*seconds),dtype='<i2') if silence else (5000*np.sin(np.arange(int(16000*seconds))*.15)).astype('<i2')
    stream=io.BytesIO()
    with wave.open(stream,'wb') as output:
        output.setnchannels(1);output.setsampwidth(2);output.setframerate(16000);output.writeframes(audio.tobytes())
    return stream.getvalue()

def test_dictation_is_private_temporary_and_does_not_save_a_correction(client,monkeypatch):
    c,app=client;seen=[]
    def transcribe(path,extension):
        assert extension=='webm' and path.read_bytes()==b'audio';seen.append(path)
        return {'text':'Más altura de la barra.','review_required':True}
    monkeypatch.setattr(app.state.dictation,'transcribe',transcribe)
    assert c.post('/api/dictation',content=b'audio',headers={'Authorization':'bad'}).status_code==401
    assert c.post('/api/dictation',content=b'audio',headers={'Origin':'https://otro.test'}).status_code==403
    result=c.post('/api/dictation?format=webm',content=b'audio')
    assert result.status_code==200 and result.json()['review_required']
    assert all(not path.exists() for path in seen)
    assert not list(app.state.settings.data.glob('dictation-*'))
    assert c.get('/api/feedback').json()==[]
    assert c.get('/api/sources').json()==[] and c.get('/api/jobs').json()==[]

def test_audio_limits_and_invalid_inputs(client,monkeypatch):
    c,app=client
    monkeypatch.setattr('dental_lab.server.MAX_AUDIO_BYTES',5)
    assert c.post('/api/dictation?format=blend',content=b'x').status_code==400
    assert c.post('/api/dictation',content=b'').status_code==400
    assert c.post('/api/dictation',content=b'123456').status_code==413
    assert c.post('/api/dictation',content=iter([b'123',b'456'])).status_code==413
    assert not list(app.state.settings.data.glob('dictation-*'))

@pytest.mark.parametrize('error,status',[(speech.DictationError('No hay voz'),422),(speech.DictationBusy('Ocupado'),429),(RuntimeError('Modelo falló'),503)])
def test_errors_clean_the_temporary_audio(client,monkeypatch,error,status):
    c,app=client
    def fail(*args):raise error
    monkeypatch.setattr(app.state.dictation,'transcribe',fail)
    assert c.post('/api/dictation',content=b'audio').status_code==status
    assert not list(app.state.settings.data.glob('dictation-*'))

def test_decoder_rejects_silence_invalid_and_long_audio(tmp_path,monkeypatch):
    path=tmp_path/'voice.wav';path.write_bytes(wav(silence=True))
    with pytest.raises(speech.DictationError,match='No se oye voz'):speech.decode_short_audio(path,'wav')
    path.write_bytes(b'not audio')
    with pytest.raises(speech.DictationError,match='No se pudo leer'):speech.decode_short_audio(path,'wav')
    path.write_bytes(wav())
    decoded=speech.decode_short_audio(path,'wav')
    assert len(decoded)==16000 and np.isfinite(decoded).all()
    monkeypatch.setattr(speech,'MAX_AUDIO_SECONDS',.5)
    with pytest.raises(speech.DictationError,match='hasta 2 minutos'):speech.decode_short_audio(path,'wav')

def test_transcription_lock_releases_after_decode_failure(tmp_path):
    from dental_lab.config import Settings
    service=speech.Dictation(Settings(data=tmp_path,password='test-only'))
    service.lock.acquire()
    with pytest.raises(speech.DictationBusy):service.transcribe(tmp_path/'missing.wav','wav')
    service.lock.release()
    with pytest.raises(speech.DictationError):service.transcribe(tmp_path/'missing.wav','wav')
    assert not service.lock.locked()
