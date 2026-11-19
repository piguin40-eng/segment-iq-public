/* Local dictation: explicit recording, editable text, no automatic submission. */
(() => {
  let active=null;
  const MAX_BYTES=20*1024*1024,MAX_SECONDS=120;
  const formats=['webm','ogg','opus','wav','mp3','mp4','m4a','flac'];
  const micIcon='<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="2" width="8" height="13" rx="4" fill="currentColor"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8" fill="none" stroke="currentColor" stroke-width="2"/></svg>';
  function appendText(target,text){
    const value=target.value.trimEnd(),combined=value+(value?'\n':'')+text.trim();
    if(target.maxLength>0&&combined.length>target.maxLength)return false;
    target.value=combined;target.dispatchEvent(new Event('input',{bubbles:true}));return true;
  }
  class VoiceInput {
    constructor({root,target,label,api,onChange=()=>{}}){
      this.root=root;this.target=target;this.label=label;this.api=api;this.onChange=onChange;
      this.phase='idle';this.session=0;this.blob=null;this.url=null;this.message='Español · hasta 2 minutos · revisa el texto antes de enviarlo.';
      root.classList.add('voiceinput');
      root.innerHTML='<div class="voiceactions"><button type="button" class="voicemic">'+micIcon+'<span></span></button><button type="button" class="secondary voicefile">Transcribir audio</button><button type="button" class="secondary voiceretry" hidden>Reintentar transcripción</button><button type="button" class="secondary voicecancel" hidden>Cancelar dictado</button><span class="voicetimer"></span></div><input type="file" class="voiceupload" accept=".webm,.ogg,.opus,.wav,.mp3,.mp4,.m4a,.flac" hidden><p class="voicestatus muted" role="status" aria-live="polite"></p><audio class="voiceaudio" controls hidden></audio><textarea class="voiceresult" aria-label="Transcripción que supera el espacio disponible" readonly hidden></textarea>';
      const find=s=>root.querySelector(s);
      this.button=find('.voicemic');this.status=find('.voicestatus');this.file=find('.voiceupload');this.fileButton=find('.voicefile');this.retry=find('.voiceretry');this.cancelButton=find('.voicecancel');this.player=find('.voiceaudio');this.result=find('.voiceresult');this.timer=find('.voicetimer');
      this.button.onclick=()=>this.phase==='recording'?this.stop():this.start();
      this.fileButton.onclick=()=>this.file.click();
      this.file.onchange=()=>{const file=this.file.files[0];this.file.value='';if(file)this.fromFile(file)};
      this.cancelButton.onclick=()=>this.cancel();
      this.retry.onclick=()=>{if(this.claim()){const token=++this.session;this.transcribe(this.blob,this.extension,token)}};
      if(!window.isSecureContext)this.message='En este acceso HTTP de red el navegador no permite el micrófono. Usa HTTPS o Transcribir audio. En el ordenador del servidor puedes abrir localhost:8765.';
      this.render();
    }
    get isBusy(){return ['permission','recording','transcribing'].includes(this.phase)}
    claim(){
      if(this.target.disabled||this.target.form?.dataset.busy==='true')return false;
      if(active&&active!==this){this.message='Termina el dictado que ya está abierto antes de iniciar otro.';this.render();return false}
      active=this;return true;
    }
    set(phase,message){this.phase=phase;this.message=message;if(!this.isBusy&&active===this)active=null;this.render();this.onChange(this)}
    render(){
      this.root.classList.toggle('recording',this.phase==='recording');
      this.button.querySelector('span').textContent=this.phase==='recording'?'Detener y transcribir':this.phase==='permission'?'Esperando permiso…':this.phase==='transcribing'?'Transcribiendo…':this.label;
      this.button.disabled=['permission','transcribing'].includes(this.phase);
      this.button.setAttribute('aria-pressed',String(this.phase==='recording'));
      this.status.textContent=this.message;this.fileButton.disabled=this.isBusy;
      this.cancelButton.hidden=!this.isBusy;this.retry.hidden=!(this.phase==='error'&&this.blob);
    }
    releaseMedia(){
      clearInterval(this.ticker);clearTimeout(this.limit);
      if(this.stream){for(const track of this.stream.getTracks()){track.onended=null;track.stop()}this.stream=null}
      this.timer.textContent='';
    }
    clearAudio(){
      this.player.pause();this.player.removeAttribute('src');this.player.hidden=true;
      if(this.url)URL.revokeObjectURL(this.url);
      this.url=null;this.blob=null;this.result.hidden=true;this.result.value='';
    }
    showAudio(blob){
      if(this.url)URL.revokeObjectURL(this.url);
      this.url=URL.createObjectURL(blob);this.player.src=this.url;this.player.hidden=false;
    }
    cancel(){
      ++this.session;this.abort?.abort();
      if(this.recorder?.state==='recording')this.recorder.stop();
      this.releaseMedia();this.clearAudio();this.set('idle','Dictado cancelado. El texto que ya tenías se conserva.');
    }
    async start(){
      if(this.isBusy||!this.claim())return;
      this.clearAudio();
      if(!window.isSecureContext||!navigator.mediaDevices?.getUserMedia){
        this.set('error',!window.isSecureContext?'El micrófono necesita HTTPS en otros ordenadores. En este servidor usa localhost:8765; también puedes pulsar Transcribir audio.':'Este navegador no ofrece acceso al micrófono. Abre SEGMENT IQ en Chrome o Edge, o usa Transcribir audio.');return;
      }
      if(!window.MediaRecorder){this.set('error','Este navegador no permite grabar audio. Puedes usar Transcribir audio.');return}
      const token=++this.session;
      this.set('permission','Permite el micrófono cuando lo solicite el navegador. Solo se graba mientras aparece Grabando.');
      try{
        const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true},video:false});
        if(token!==this.session){stream.getTracks().forEach(track=>track.stop());return}
        this.stream=stream;
        const mime=['audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus','audio/mp4'].find(x=>MediaRecorder.isTypeSupported(x));
        const recorder=new MediaRecorder(stream,mime?{mimeType:mime,audioBitsPerSecond:64000}:{});
        this.recorder=recorder;const chunks=[];let bytes=0;
        recorder.ondataavailable=e=>{if(token===this.session&&e.data.size){chunks.push(e.data);bytes+=e.data.size;if(bytes>MAX_BYTES){this.cancel();this.set('error','La grabación superó 20 MB. Graba una nota más corta.')}}};
        recorder.onerror=()=>{if(token===this.session){this.cancel();this.set('error','El micrófono dejó de responder. Comprueba la conexión y vuelve a dictar.')}};
        recorder.onstop=()=>{
          if(token!==this.session)return;this.releaseMedia();
          const type=recorder.mimeType||mime||'audio/webm';
          const extension=type.includes('mp4')?'mp4':type.includes('ogg')?'ogg':'webm';
          const blob=new Blob(chunks,{type});this.showAudio(blob);this.transcribe(blob,extension,token);
        };
        for(const track of stream.getTracks())track.onended=()=>{if(token===this.session)this.stop()};
        recorder.start(1000);this.started=Date.now();
        this.set('recording','Grabando tu indicación. Pulsa Detener y transcribir cuando termines.');
        this.ticker=setInterval(()=>{const n=Math.floor((Date.now()-this.started)/1000);this.timer.textContent=Math.floor(n/60)+':'+String(n%60).padStart(2,'0')+' / 2:00'},500);
        this.limit=setTimeout(()=>this.stop(),MAX_SECONDS*1000);
      }catch(error){
        if(token!==this.session)return;this.releaseMedia();
        const message={NotAllowedError:'El navegador no ha permitido el micrófono. Permítelo desde el icono de permisos de esta página o usa Transcribir audio.',NotFoundError:'No se ha encontrado un micrófono conectado.',NotReadableError:'No se puede abrir el micrófono. Comprueba que otra aplicación no lo esté usando.'}[error.name]||'No se pudo iniciar la grabación. Puedes usar Transcribir audio.';
        this.set('error',message);
      }
    }
    stop(){
      if(this.recorder?.state!=='recording')return;
      this.recorder.stop();this.releaseMedia();
    }
    fromFile(file){
      if(this.isBusy||!this.claim())return;
      this.clearAudio();
      const extension=file.name.split('.').pop().toLowerCase();
      if(!formats.includes(extension)){this.set('error','Elige un audio WAV, WebM, OGG, M4A, MP3 o FLAC.');return}
      if(file.size>MAX_BYTES){this.set('error','La nota de voz supera 20 MB.');return}
      this.showAudio(file);this.transcribe(file,extension,++this.session);
    }
    async transcribe(blob,extension,token){
      if(!blob?.size){this.set('error','La grabación está vacía. Vuelve a dictar la indicación.');return}
      this.blob=blob;this.extension=extension;const controller=new AbortController();this.abort=controller;
      const timer=setTimeout(()=>controller.abort(),180000);
      this.set('transcribing','Transcribiendo en el ordenador del laboratorio… El texto aparecerá aquí para que lo revises.');
      try{
        const result=await this.api('/api/dictation?format='+encodeURIComponent(extension),{method:'POST',body:blob,headers:{'Content-Type':blob.type||'application/octet-stream'},signal:controller.signal});
        if(token!==this.session)return;
        if(typeof result.text!=='string'||!result.text.trim())throw Error('No se recibió texto. Prueba otra vez.');
        if(appendText(this.target,result.text))this.set('ready','Transcripción añadida. Revisa piezas, medidas y palabras antes de guardar o rediseñar.');
        else {this.result.value=result.text;this.result.hidden=false;this.set('ready','El texto supera el espacio disponible. La transcripción completa aparece debajo para copiarla; no se ha borrado tu texto.');}
      }catch(error){if(token===this.session)this.set('error',controller.signal.aborted?'La transcripción está tardando demasiado. Puedes reintentar sin volver a grabar.':error.message)}
      finally{clearTimeout(timer)}
    }
  }
  window.SegmentVoiceInput=VoiceInput;
  window.addEventListener('pagehide',()=>active?.cancel());
})();
