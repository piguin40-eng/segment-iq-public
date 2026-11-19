const $ = id => document.getElementById(id);
const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const json = data => ({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
let busy = 0, refreshing = false, asking=false, state = {cases:[],jobs:[],feedback:[]}, historyFilter = null;
const openFiles = new Map();
const versionFiles = new Map();
let versionEpoch=0,redesignBusy=false;
const labels = {queued:'En cola',indexing:'Indexando',running:'En curso',ready:'Consultable',partial:'Índice parcial',registered:'Registrado',failed:'Revisar error',needs_review:'Necesita revisión',done:'Completado',unchanged:'Sin cambios nuevos',interrupted:'Interrumpido',needs_profile:'Listo para iniciar',preparing:'Midiendo el diseño',ready_to_generate:'Listo para generar',generating:'Generando',review_pending:'Pendiente de revisión',changes_requested:'Cambios solicitados',approved:'Aprobado',rejected:'Rechazado',correction:'Corrección'};
function tag(value){return '<span class="tag '+esc(value)+'">'+esc(labels[value]||value)+'</span>'}
function jobDetail(job){
  let detail=job.detail||'';
  if(job.status==='failed'&&detail.startsWith('Command ['))detail='La ejecución se detuvo. El motivo y las etapas están en sus archivos de diagnóstico.';
  if(['failed','interrupted'].includes(job.status)&&state.jobs.some(j=>j.kind===job.kind&&j.target===job.target&&j.created>job.created))detail='Intento anterior; este trabajo tiene una versión posterior. '+detail;
  return detail;
}
function notice(message){$('notice').hidden=!message;$('notice').textContent=message}
function dictationPending(){return window.segmentVoice?.some(v=>v.isBusy)||false}
function cancelDictation(){window.segmentVoice?.filter(v=>v.isBusy).forEach(v=>v.cancel())}
function login(){cancelDictation();if(!$('loginDialog').open)$('loginDialog').showModal()}
async function request(path,options={}){
  try{return await fetch(path,options)}
  catch{throw Error('No se puede conectar con SEGMENT IQ. Comprueba que el ordenador del laboratorio está encendido y abre su acceso directo. Si se está recuperando el servicio, vuelve a intentarlo en un minuto.')}
}
async function api(path,options={}){
  const r=await request(path,options);
  if(r.status===401){login();throw Error('Inicia sesión')}
  if(!r.ok){let b=await r.json();throw Error(typeof b.detail==='string'?b.detail:JSON.stringify(b.detail))}
  return r.json();
}
function go(tab){
  window.segmentVoice?.filter(v=>v.isBusy&&!$(tab).contains(v.target)).forEach(v=>v.cancel());
  document.querySelectorAll('nav button,.tab').forEach(x=>x.classList.remove('active'));
  const button=document.querySelector('nav [data-tab="'+tab+'"]');
  button.classList.add('active');$(tab).classList.add('active');$('title').textContent=button.querySelector('span').textContent;
  refresh();
}
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>go(b.dataset.tab));
document.querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>go(b.dataset.go));
$('loginDialog').addEventListener('cancel',e=>e.preventDefault());
$('loginForm').onsubmit=async e=>{
  e.preventDefault();$('loginSubmit').disabled=true;$('loginError').textContent='';
  try{const r=await request('/login',json({username:$('username').value,password:$('password').value}));if(!r.ok)throw Error(r.status===429?'Demasiados intentos. Espera un minuto.':'Usuario o contraseña incorrectos');$('password').value='';$('loginDialog').close();await refresh()}
  catch(x){$('loginError').textContent=x.message}
  finally{$('loginSubmit').disabled=false}
};
$('logout').onclick=async()=>{try{await api('/api/logout',{method:'POST'});login()}catch(x){notice(x.message)}};
function sourcesView(rows){
  $('citations').innerHTML=rows.map(r=>'<div class="card"><h3>['+r.citation+'] '+esc(r.name)+'</h3><small>'+esc(r.kind)+(r.start!=null?' · '+Math.floor(r.start/60)+':'+String(Math.floor(r.start%60)).padStart(2,'0'):'')+'</small><p>'+esc(r.text)+'</p><div class="actions">'+(r.source_id?'<a href="/api/source/'+encodeURIComponent(r.source_id)+'" target="_blank" rel="noopener">Abrir fuente</a>':'')+(r.source_kind==='video'?'<button class="secondary" data-video="'+esc(r.source_id)+'" data-time="'+(r.start||0)+'">Ver este momento</button>':'')+'</div>'+(r.frame?'<img loading="lazy" alt="Captura de la fuente" src="/api/frame/'+encodeURIComponent(r.source_id)+'/'+encodeURIComponent(r.frame.replace(/\\/g,'/').split('/').pop())+'">':'')+'</div>').join('')||'<p class="muted">No se encontraron fuentes. Añade material a la biblioteca.</p>';
  document.querySelectorAll('[data-video]').forEach(b=>b.onclick=()=>{$('video').src='/api/source/'+b.dataset.video+'#t='+b.dataset.time;$('videoDialog').showModal()});
}
$('closeVideo').onclick=()=>{$('video').pause();$('videoDialog').close()};
$('videoDialog').addEventListener('close',()=>$('video').pause());
$('askForm').onsubmit=async e=>{
  e.preventDefault();if(asking)return;if(dictationPending()){notice('Termina el dictado y revisa el texto antes de consultar.');return}asking=true;$('ask').disabled=true;notice('Consultando la biblioteca y el modelo local…');
  try{const r=await api('/api/chat',json({question:$('question').value}));$('answer').hidden=false;$('answerText').textContent=r.answer;sourcesView(r.citations);notice(r.embedding_warning?'La búsqueda semántica requiere revisión; se han usado las fuentes disponibles.':'')}
  catch(x){notice(x.message)}finally{asking=false;$('ask').disabled=dictationPending()}
};
$('searchOnly').onclick=async()=>{try{sourcesView(await api('/api/search?q='+encodeURIComponent($('question').value)));notice('')}catch(x){notice(x.message)}};

const extensions='.mp4,.mkv,.mov,.avi,.webm,.wav,.mp3,.m4a,.flac,.ogg,.txt,.md,.srt,.vtt,.json,.py,.pdf,.png,.jpg,.jpeg,.stl,.blend,.blend1';
function size(bytes){return bytes>=1024**3?(bytes/1024**3).toFixed(2)+' GB':bytes>=1024**2?(bytes/1024**2).toFixed(1)+' MB':Math.ceil(bytes/1024)+' KB'}
class FileQueue{
  constructor(input,drop,list,{single=false,max=100,onChange=()=>{}}={}){
    this.input=$(input);this.drop=$(drop);this.list=$(list);this.files=[];this.single=single;this.max=max;this.onChange=onChange;this.locked=false;
    this.input.accept=single?'.stl':extensions;
    this.input.onchange=()=>{this.add(this.input.files);this.input.value=''};
    this.drop.addEventListener('dragover',e=>{e.preventDefault();if(!this.isLocked())this.drop.classList.add('dragging')});
    this.drop.addEventListener('dragleave',()=>this.drop.classList.remove('dragging'));
    this.drop.addEventListener('drop',e=>{e.preventDefault();this.drop.classList.remove('dragging');if(!this.isLocked())this.add(e.dataTransfer.files)});
  }
  isLocked(){return this.locked||this.input.form?.dataset.busy==='true'}
  add(files){
    if(this.isLocked())return;
    const incoming=Array.from(files),errors=[];
    if(this.single&&incoming.length>1){notice('Para crear un caso, elige un solo STL sin segmentar.');return}
    for(const file of incoming){
      const ext='.'+file.name.split('.').pop().toLowerCase();
      if(!(this.single?['.stl']:extensions.split(',')).includes(ext)){errors.push(file.name+': formato no admitido');continue}
      if(file.size>8*1024**3){errors.push(file.name+': supera 8 GB; usa la carpeta de entrada');continue}
      if(this.files.some(r=>r.file.name===file.name&&r.file.size===file.size&&r.file.lastModified===file.lastModified))continue;
      if(this.single)this.files=[];
      if(this.files.length>=this.max){errors.push('Máximo '+this.max+' archivos por envío');break}
      this.files.push({file,status:'pending',progress:0,id:null,error:''});
    }
    if(errors.length)notice(errors.join('. '));
    this.render();this.onChange();
  }
  clear(){this.files=[];this.input.value='';this.render();this.onChange()}
  render(){
    this.drop.classList.toggle('busy',this.isLocked());this.input.disabled=this.isLocked();
    this.list.innerHTML=this.files.map((r,i)=>{
      const status=r.status==='done'?(r.duplicate?'Ya estaba guardado · se reutiliza':'Guardado · indexación en cola'):r.status==='error'?r.error:r.status==='uploading'?(r.progress<100?'Subiendo '+r.progress+' %':'Guardando en el laboratorio…'):'Listo para subir';
      return '<li class="file-'+r.status+'"><div class="fileinfo"><div class="filename">'+esc(r.file.name)+'</div><small>'+size(r.file.size)+' · '+esc(status)+'</small>'+(r.status==='uploading'?'<progress max="100" value="'+r.progress+'" aria-label="Progreso de '+esc(r.file.name)+'"></progress>':'')+'</div><button type="button" class="removefile" data-remove="'+i+'" aria-label="Quitar '+esc(r.file.name)+'" '+(this.isLocked()?'disabled':'')+'>×</button></li>';
    }).join('');
    this.list.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{if(!this.isLocked()){this.files.splice(Number(b.dataset.remove),1);this.render();this.onChange()}});
  }
  async upload(){
    this.locked=true;this.render();let errors=0;
    try{
      for(const row of this.files){
        if(row.id)continue;
        row.status='uploading';row.progress=0;this.render();
        try{const result=await this.send(row);row.id=result.id;row.duplicate=!result.new;row.status='done'}
        catch(x){row.status='error';row.error=x.message;errors++}
        this.render();
      }
    }finally{this.locked=false;this.render();this.onChange()}
    if(errors)throw Error('No se han subido todos los archivos. Los correctos están guardados; vuelve a pulsar para reintentar los que fallaron.');
    return this.files.map(r=>r.id);
  }
  send(row){
    return new Promise((resolve,reject)=>{
      const xhr=new XMLHttpRequest();xhr.open('POST','/api/upload');xhr.responseType='json';
      xhr.upload.onprogress=e=>{if(e.lengthComputable){row.progress=Math.round(e.loaded/e.total*100);this.render()}};
      xhr.onerror=()=>reject(Error('Conexión interrumpida. Puedes reintentar.'));
      xhr.onabort=()=>reject(Error('Subida cancelada.'));
      xhr.onload=()=>{
        if(xhr.status===401){login();reject(Error('Inicia sesión y vuelve a intentarlo.'));return}
        if(xhr.status<200||xhr.status>=300){reject(Error(typeof xhr.response?.detail==='string'?xhr.response.detail:'No se pudo guardar el archivo.'));return}
        resolve(xhr.response);
      };
      const form=new FormData();form.append('file',row.file);xhr.send(form);
    });
  }
}
const learning=new FileQueue('learningFiles','learningDrop','learningQueue',{onChange:()=>{$('uploadButton').disabled=learning.isLocked()||!learning.files.some(f=>!f.id)}});
const caseUpload=new FileQueue('caseFile','caseDrop','caseQueue',{single:true,onChange:()=>{
  if(caseUpload.files.length){$('caseSource').value='';if(!$('caseName').value)$('caseName').value=caseUpload.files[0].file.name.replace(/\.stl$/i,'').slice(0,120)}
}});
const attachments=new FileQueue('feedbackFiles','feedbackDrop','feedbackQueue',{max:20});
document.addEventListener('dragover',e=>{if(Array.from(e.dataTransfer?.types||[]).includes('Files'))e.preventDefault()});
document.addEventListener('drop',e=>{if(Array.from(e.dataTransfer?.types||[]).includes('Files'))e.preventDefault()});
$('caseSource').onchange=()=>{if($('caseSource').value)caseUpload.clear()};

async function formAction(form,action){
  const controls=Array.from(form.querySelectorAll('button,input,select,textarea'));
  const previous=controls.map(x=>x.disabled);form.dataset.busy='true';controls.forEach(x=>x.disabled=true);busy++;
  try{await action()}catch(x){notice(x.message)}
  finally{busy--;delete form.dataset.busy;controls.forEach((x,i)=>x.disabled=previous[i]);[learning,caseUpload,attachments].forEach(q=>q.render());learning.onChange();revisionOptions()}
}
$('uploadForm').onsubmit=async e=>{
  e.preventDefault();await formAction(e.currentTarget,async()=>{
    await learning.upload();$('uploadProgress').textContent='Archivos guardados. El progreso de indexación aparece abajo.';notice('Material incorporado a la biblioteca.');await refresh();
  });
};
$('caseForm').onsubmit=async e=>{
  e.preventDefault();await formAction(e.currentTarget,async()=>{
    let source=$('caseSource').value;
    if(caseUpload.files.length)source=(await caseUpload.upload())[0];
    if(!source)throw Error('Arrastra un STL o elige uno de la biblioteca.');
    const result=await api('/api/cases',json({name:$('caseName').value.trim(),source_id:source}));
    caseUpload.clear();$('caseName').value='';$('caseSource').value='';$('existingSource').open=false;
    notice('Caso creado. La medición y segmentación se han puesto en cola automáticamente.');await refresh();
    await openConstruction(result.job_id);
  });
};
function revisionOptions(){
  const specific=$('feedbackCase').value!=='general',approved=$('feedbackStatus').value==='approved';
  $('saveFeedback').textContent=approved?'Guardar aprobación':$('feedbackStatus').value==='rejected'?'Guardar rechazo':'Guardar corrección';
  updateRedesignButton();
  $('revisionHint').textContent=specific?(approved?'La aprobación se asocia a la última generación terminada.':'Guarda la observación o usa el botón rojo de abajo para aplicarla y rediseñar el trabajo.'):'El criterio general queda disponible para futuras consultas.';
}
$('feedbackCase').onchange=()=>{historyFilter=$('feedbackCase').value;if(historyFilter!=='general')$('redesignCase').value=historyFilter;revisionOptions();renderFeedback();renderVersions()};
$('feedbackStatus').onchange=revisionOptions;
$('allFeedback').onclick=()=>{historyFilter=null;renderFeedback()};
$('feedbackForm').onsubmit=async e=>{
  e.preventDefault();if(dictationPending()){notice('Termina el dictado y revisa el texto antes de guardar.');return}const requestPlan=false;
  await formAction(e.currentTarget,async()=>{
    const ids=await attachments.upload();
    const result=await api('/api/feedback',json({case_id:$('feedbackCase').value,author:$('author').value.trim(),text:$('feedbackText').value,status:$('feedbackStatus').value,attachment_ids:ids,request_generation:requestPlan}));
    $('feedbackText').value='';attachments.clear();historyFilter=$('feedbackCase').value;
    notice(result.job_id?'Corrección guardada. Nueva segmentación en cola; verás los ajustes aplicados y pendientes junto a sus resultados.':'Revisión guardada en la memoria del laboratorio.');
    await refresh();
  });
};

function updateRedesignButton(){
  const id=$('redesignCase').value;
  const active=state.jobs.find(j=>j.target===id&&j.kind==='segment'&&['queued','running'].includes(j.status));
  const drafted=$('feedbackText').value.trim()||attachments.files.length;
  const approved=$('feedbackStatus').value==='approved'&&drafted;
  $('redesignFeedback').disabled=!id||Boolean(active)||redesignBusy||Boolean(approved)||dictationPending();
  $('redesignFeedback').textContent=redesignBusy?'Guardando y preparando el rediseño…':active?'Rediseño en curso…':'Aplicar correcciones y rediseñar este trabajo';
  $('redesignHint').textContent=!id?'Elige el trabajo al que aplicar las correcciones. No hace falta volver a subir el STL.':active?'Puedes seguir guardando observaciones mientras termina esta versión.':approved?'Guarda la aprobación o cambia el tipo a corrección para pedir un rediseño.':'Se ejecutará Blender con el historial de este trabajo y los criterios generales. Los cambios que no pueda interpretar se señalarán como pendientes.';
}
$('feedbackText').addEventListener('input',updateRedesignButton);
$('redesignCase').onchange=()=>{updateRedesignButton();renderVersions()};
$('redesignFeedback').onclick=async()=>{
  if(dictationPending()){notice('Termina el dictado y revisa la corrección antes de rediseñar.');return}
  const id=$('redesignCase').value;
  if(!id||redesignBusy)return;
  const text=$('feedbackText').value.trim();
  if(text||attachments.files.length){
    if(!$('author').reportValidity())return;
    if(!text){notice('Escribe qué debemos corregir con los adjuntos antes de rediseñar.');$('feedbackText').focus();return}
    if(!$('feedbackText').reportValidity())return;
    if($('feedbackStatus').value==='approved'){notice('Selecciona corrección o rechazo para rediseñar.');return}
    if($('feedbackCase').value!=='general'&&$('feedbackCase').value!==id){notice('La corrección escrita pertenece a otro caso. Selecciona ese mismo trabajo para rediseñarlo.');return}
  }
  redesignBusy=true;$('redesignCase').disabled=true;updateRedesignButton();
  try{
    await formAction($('feedbackForm'),async()=>{
      let result;
      if(text){
        const ids=await attachments.upload();
        result=await api('/api/feedback',json({case_id:id,author:$('author').value.trim(),text,status:$('feedbackStatus').value,attachment_ids:ids,request_generation:true}));
        $('feedbackText').value='';attachments.clear();
        $('feedbackCase').value=id;historyFilter=id;
      }else{
        result=await api('/api/cases/'+encodeURIComponent(id)+'/redesign',{method:'POST'});
      }
      $('redesignProgress').hidden=false;
      $('redesignProgress').textContent='Rediseño solicitado. Verás el avance y la nueva propuesta en las versiones de este trabajo.';
      notice('Rediseño en cola para '+(state.cases.find(c=>c.id===id)?.name||'el trabajo seleccionado')+'. Las versiones anteriores se conservan.');
      await refresh();await renderVersions();
      await openConstruction(result.job_id);
    });
  }finally{redesignBusy=false;$('redesignCase').disabled=false;updateRedesignButton()}
};
async function loadVersion(job){
  const key=job.id+':'+job.status;
  if(versionFiles.has(key))return versionFiles.get(key);
  const files=await api('/api/jobs/'+job.id+'/files');
  let measures=null;
  const report=files.find(f=>f.name==='Perfil_automatico.medidas.json');
  if(report)measures=await api('/api/jobs/'+job.id+'/file/'+report.path.split('/').map(encodeURIComponent).join('/'));
  const value={files,measures};versionFiles.set(key,value);return value;
}
async function renderVersions(){
  const id=$('redesignCase').value,epoch=++versionEpoch;
  $('versionSection').hidden=!id;
  if(!id){$('versionList').innerHTML='';$('redesignProgress').hidden=true;return}
  try{
    const jobs=await api('/api/cases/'+encodeURIComponent(id)+'/versions');
    const previews=jobs.filter(j=>['done','needs_review'].includes(j.status)).slice(0,2);
    await Promise.all(previews.map(loadVersion));
    if(epoch!==versionEpoch||$('redesignCase').value!==id)return;
    const active=jobs.find(j=>['queued','running'].includes(j.status));
    $('redesignProgress').hidden=!active;
    $('redesignProgress').textContent=active?(active.detail||'Rediseño en cola'):'';
    $('versionTitle').textContent='Versiones de '+(state.cases.find(c=>c.id===id)?.name||'este trabajo');
    $('versionList').innerHTML=jobs.map((j,i)=>{
      const loaded=versionFiles.get(j.id+':'+j.status),m=loaded?.measures;
      const applied=m?.corrections_applied?.flatMap(r=>r.changes||[])||[];
      const pending=m?.corrections_pending?.length||0;
      return '<article class="versioncard"><div class="cardtop"><h3>Versión '+(jobs.length-i)+'</h3>'+tag(j.status)+'</div><small>'+new Date(j.created*1000).toLocaleString('es-ES')+'</small><p>'+esc(j.detail||'Preparación en cola')+'</p>'+(loaded?'<div>'+fileLinks(j.id,loaded.files)+'</div>':'<button class="secondary" data-construction="'+j.id+'">Ver construcción</button><button type="button" class="secondary" data-version-open="'+j.id+'">Ver archivos de esta versión</button>')+(applied.length?'<p class="versionchanges"><b>Ajustes aplicados</b><br>'+applied.map(esc).join('<br>')+'</p>':'')+(pending?'<p class="versionpending">'+pending+' indicaciones pendientes de interpretar. Consulta el informe; no se dan por aplicadas.</p>':'')+'</article>';
    }).join('')||'<p class="muted">Este trabajo todavía no tiene versiones.</p>';
    $('versionList').querySelectorAll('[data-version-open]').forEach(button=>button.onclick=async()=>{
      button.disabled=true;
      try{const job=jobs.find(j=>j.id===button.dataset.versionOpen);await loadVersion(job);await renderVersions()}catch(x){notice(x.message);button.disabled=false}
    });
  }catch(x){if(epoch===versionEpoch)$('versionList').textContent='No se pudieron cargar las versiones: '+x.message}
}

function correctCase(id){
  if(dictationPending()){notice('Termina o cancela el dictado antes de cambiar de trabajo.');return}
  if($('feedbackForm').dataset.busy==='true'){notice('Espera a que termine de guardarse la revisión actual.');return}
  if(($('feedbackText').value.trim()||attachments.files.length)&&$('feedbackCase').value!==id){
    notice('Tienes una corrección sin guardar de otro ámbito. Guárdala o vacía el borrador antes de cambiar de caso.');go('criterio');return;
  }
  $('feedbackCase').value=id;$('redesignCase').value=id;$('feedbackStatus').value='correction';historyFilter=id;renderVersions();revisionOptions();renderFeedback();go('criterio');$('feedbackText').focus();
}
function renderFeedback(){
  const cases=state.cases,rows=historyFilter?state.feedback.filter(f=>f.case_id===historyFilter):state.feedback;
  $('historyTitle').textContent=historyFilter?'Historial · '+(historyFilter==='general'?'Criterio general':cases.find(c=>c.id===historyFilter)?.name||'Caso'):'Historial del laboratorio';
  $('allFeedback').hidden=historyFilter===null;
  $('feedbackList').innerHTML=rows.map(f=>'<div class="card feedbackcard"><h3>'+esc(f.author)+' '+tag(f.status)+'</h3><small>'+esc(f.case_id==='general'?'Ámbito general':cases.find(c=>c.id===f.case_id)?.name||f.case_id)+' · '+new Date(f.created*1000).toLocaleString('es-ES')+'</small><p>'+esc(f.text)+'</p>'+(f.attachments?.length?'<div class="attachments">'+f.attachments.map(a=>'<a class="attachment" href="/api/source/'+encodeURIComponent(a.id)+'" target="_blank" rel="noopener">'+esc(a.name)+'</a>').join('')+'</div>':'')+(f.plan_id?'<div class="actions"><button class="secondary" data-review-result="'+esc(f.plan_id)+'">Ver revisión · '+esc(labels[state.jobs.find(j=>j.id===f.plan_id)?.status]||'Resultados')+'</button></div>':'')+'</div>').join('')||'<p class="muted">Aquí aparecerán las correcciones, referencias y decisiones de este ámbito.</p>';
  $('feedbackList').querySelectorAll('[data-review-result]').forEach(b=>b.onclick=async()=>{await showFiles(b.dataset.reviewResult);go('casos');$('job-'+b.dataset.reviewResult)?.scrollIntoView({behavior:'smooth',block:'center'})});
}
function fileLinks(id,files){
  if(!files.length)return 'Preparando los primeros archivos…';
  const url=f=>'/api/jobs/'+encodeURIComponent(id)+'/file/'+f.path.split('/').map(encodeURIComponent).join('/');
  const link=(f,label)=>'<a href="'+url(f)+'">'+esc(label||f.name)+'</a>';
  const previews=files.filter(f=>f.display_group==='preview').map(f=>'<p><b>'+esc(f.proposal_label)+'</b></p><img class="resultpreview" alt="'+esc(f.proposal_label)+'" loading="lazy" src="'+url(f)+'">').join('');
  const principal=files.filter(f=>f.display_group==='principal');
  const stages=files.filter(f=>f.display_group==='stage');
  const technical=files.filter(f=>f.display_group==='technical');
  return '<button class="secondary" data-construction="'+esc(id)+'">Ver construcción por etapas</button>'+previews+'<div class="resultdownloads">'+principal.map(f=>link(f,/^Primaria.*\.stl$/i.test(f.name)?'Primaria · STL':/^Supra.*\.stl$/i.test(f.name)?'Supra · STL':/\.blend$/i.test(f.name)?'Escena de Blender':/\.zip$/i.test(f.name)?'Descargar propuesta para revisar':f.name)).join('')+'</div>'+(stages.length?'<details><summary>Ver las etapas del diseño</summary><div class="resultfiles">'+stages.map(f=>link(f)).join('')+'</div></details>':'')+(technical.length?'<details><summary>Otros intentos, mediciones y registro</summary><div class="resultfiles">'+technical.map(f=>link(f,f.path)).join('')+'</div></details>':'');
}
async function showFiles(id){
  try{const files=await api('/api/jobs/'+id+'/files');openFiles.set(id,files);if($('files-'+id)){$('files-'+id).innerHTML=fileLinks(id,files);$('job-'+id)?.classList.add('with-results')}}catch(x){notice(x.message)}
}
async function action(button,path,message){
  button.disabled=true;busy++;
  try{const result=await api(path,{method:'POST'});notice(message);await refresh();if(result.job_id&&/\/(generate|redesign)$/.test(path))await openConstruction(result.job_id)}catch(x){notice(x.message)}finally{button.disabled=false;busy--}
}
async function refresh(){
  if(refreshing)return;refreshing=true;
  try{
    const [status,sources,cases,jobs,feedback]=await Promise.all(['/api/status','/api/sources','/api/cases','/api/jobs','/api/feedback'].map(x=>api(x)));
    state={cases,jobs,feedback};
    $('model').textContent=status.agent_harness==='codex'?(status.codex_installed?'Agente Codex · Blender local':'Agente Codex · instalación pendiente'):(status.llm_ready?'Modelo local disponible':'Modelo local pendiente');$('chunkCount').textContent=status.chunks;$('inbox').textContent=status.inbox;
    const workflow=status.lab_workflow;
    if($('barWorkflow')){$('barWorkflow').hidden=!workflow;$('barWorkflowStatus').textContent=!workflow?'':!workflow.available?'Protocolo pendiente de reparar: '+workflow.error:status.agent_harness==='codex'?'Consulta obligatoria en cada planificación y revisión · versión '+workflow.version+'. El agente debe explicar cada paso y señalar lo pendiente.':'Referencia instalada · versión '+workflow.version+'. Activa el agente Codex para aplicarla y revisarla por etapas; el motor fijo solo conserva la referencia.';}
    $('sources').innerHTML=sources.map(s=>'<div class="item"><div class="description"><b>'+esc(s.name)+'</b><small>'+esc(s.kind)+' · '+esc(s.detail)+'</small></div>'+tag(s.status)+'<button class="secondary" data-index="'+s.id+'">Reindexar</button></div>').join('')||'<p class="muted">La biblioteca está lista para recibir material.</p>';
    let selected=$('caseSource').value;
    $('caseSource').innerHTML='<option value="">Selecciona un STL…</option>'+sources.filter(x=>x.kind==='geometry'&&x.name.toLowerCase().endsWith('.stl')).map(s=>'<option value="'+s.id+'">'+esc(s.name)+'</option>').join('');$('caseSource').value=selected;
    selected=$('feedbackCase').value;
    $('feedbackCase').innerHTML='<option value="general">Criterio general del laboratorio</option>'+cases.map(c=>'<option value="'+c.id+'">'+esc(c.name)+'</option>').join('');$('feedbackCase').value=selected;
    selected=$('redesignCase').value;
    $('redesignCase').innerHTML='<option value="">Elige un trabajo…</option>'+cases.map(c=>'<option value="'+c.id+'">'+esc(c.name)+'</option>').join('');
    $('redesignCase').value=selected;
    const detailsOpen=new Set(Array.from($('cases').querySelectorAll('details[open]')).map(d=>d.dataset.settings));
    $('cases').innerHTML=cases.map(c=>{
      const caseJobs=jobs.filter(j=>j.target===c.id),versions=caseJobs.filter(j=>j.kind==='segment'),reviews=feedback.filter(f=>f.case_id===c.id);
      const working=caseJobs.some(j=>j.kind==='plan'&&['queued','running'].includes(j.status)),generating=caseJobs.some(j=>j.kind==='segment'&&['queued','running'].includes(j.status));
      const latest=caseJobs.find(j=>j.kind==='segment'&&j.status!=='unchanged')||caseJobs.find(j=>j.kind==='plan');
      return '<div class="card casecard" id="case-'+c.id+'"><div class="cardtop"><h3>'+esc(c.name)+'</h3>'+tag(c.status)+'</div><p class="casecounts">'+versions.length+' ejecuciones de geometría · '+reviews.length+' revisiones del equipo</p><div class="actions"><button data-correct="'+c.id+'">Corregir / Iterar</button><button class="secondary" data-generate="'+c.id+'" '+(generating?'disabled':'')+'>'+(generating?'Segmentación en curso…':versions.length?'Generar otra versión':'Empezar segmentación')+'</button>'+(latest?'<button class="secondary" data-construction="'+latest.id+'">Ver construcción</button><button class="secondary" data-case-result="'+latest.id+'">Ver resultados</button>':'')+'</div><p class="muted">'+(generating?esc(versions[0]?.detail||'Preparación automática en cola'):c.status==='failed'?'El intento se ha detenido. El diagnóstico y las etapas realizadas están disponibles en los resultados.':'Propuesta para revisar en el laboratorio. Cada versión conserva el original, sus etapas y las correcciones utilizadas.')+'</p><details data-settings="'+c.id+'" '+(detailsOpen.has(c.id)?'open':'')+'><summary>Consultar el patrón y las referencias</summary><p class="muted">El análisis adicional consulta la biblioteca y guarda sus fuentes. La generación empieza automáticamente al crear el caso.</p><button class="secondary" data-plan="'+c.id+'" '+(working||generating?'disabled':'')+'>'+(working?'Análisis en curso…':'Analizar con el agente')+'</button></details></div>';
    }).join('')||'<p class="muted">Empieza subiendo el STL de vuestro primer caso.</p>';
    $('jobs').innerHTML=jobs.map(j=>'<div class="item '+(openFiles.has(j.id)?'with-results':'')+'" id="job-'+j.id+'"><div class="description"><b>'+(j.kind==='index'?'Indexación':j.kind==='plan'?'Revisión del agente':'Segmentación')+' · '+esc(cases.find(c=>c.id===j.target)?.name||j.id.slice(0,8))+'</b><small>'+esc(jobDetail(j))+'</small><div id="files-'+j.id+'">'+(openFiles.has(j.id)?fileLinks(j.id,openFiles.get(j.id)):'')+'</div></div>'+tag(j.status)+(j.kind!=='index'?'<button class="secondary" data-files="'+j.id+'">Archivos</button>':'')+'</div>').join('')||'<p class="muted">No hay trabajos en la cola.</p>';
    renderFeedback();revisionOptions();renderVersions();
    document.querySelectorAll('[data-index]').forEach(b=>b.onclick=()=>action(b,'/api/sources/'+b.dataset.index+'/reindex','Indexación en cola.'));
    document.querySelectorAll('[data-plan]').forEach(b=>b.onclick=()=>action(b,'/api/cases/'+b.dataset.plan+'/plan','Revisión en cola con el historial actual del caso.'));
    document.querySelectorAll('[data-generate]').forEach(b=>b.onclick=()=>action(b,'/api/cases/'+b.dataset.generate+'/generate','Generación con Blender en cola.'));
    document.querySelectorAll('[data-correct]').forEach(b=>b.onclick=()=>correctCase(b.dataset.correct));
    document.querySelectorAll('[data-files]').forEach(b=>b.onclick=()=>showFiles(b.dataset.files));
    document.querySelectorAll('[data-case-result]').forEach(b=>b.onclick=async()=>{await showFiles(b.dataset.caseResult);$('job-'+b.dataset.caseResult)?.scrollIntoView({behavior:'smooth',block:'center'})});

  }catch(x){if(x.message!=='Inicia sesión')notice(x.message)}
  finally{refreshing=false}
}

let construction={id:null,caseId:null,frames:[],index:0,live:true,playing:false,epoch:0,polling:false,mode:'auto',data:null};
function constructionSelectFrames(){
  const p=construction.data,windowFrames=p?.window_frames||[];
  construction.windowMode=construction.mode==='window'||(construction.mode==='auto'&&windowFrames.length>0);
  construction.frames=construction.windowMode?windowFrames:(p?.frames||[]);
  construction.index=construction.live?Math.max(0,construction.frames.length-1):Math.min(construction.index,Math.max(0,construction.frames.length-1));
  for(const [id,selected] of [['constructionWindow',construction.windowMode],['constructionGeometry',!construction.windowMode]]){
    $(id).className=selected?'':'secondary';$(id).setAttribute('aria-pressed',String(selected));
  }
  $('constructionFrame').alt=construction.windowMode?'Ventana real de Blender después de una operación del trabajo':'Geometría real de la etapa seleccionada';
  $('constructionHelp').textContent=construction.windowMode?'La ventana del Blender que ejecuta este trabajo, capturada después de operaciones reales. Durante un cálculo largo se mantiene la última imagen. El agente trabaja con código: no simula movimientos de ratón.':'Vistas de la geometría al completar cada etapa. Puedes repetirlas como una secuencia; no es una grabación del cursor.';
  if(construction.windowMode&&!windowFrames.length)$('constructionEmpty').textContent=['done','failed','interrupted','unchanged','needs_review'].includes(p?.status)?'Esta versión no guardó la ventana de Blender. Puedes ver sus vistas por etapas; las nuevas generaciones la capturan.':'La ventana aparecerá al comenzar la construcción en Blender. La preparación del STL se realiza antes.';
  if(construction.windowMode&&p?.window_capture_error)$('constructionHelp').textContent+=' Una captura no se pudo guardar; las etapas y el diagnóstico siguen disponibles.';
}
function constructionDraw(){
  const frame=construction.frames[construction.index];
  $('constructionFrame').hidden=!frame;$('constructionEmpty').hidden=Boolean(frame);
  if(frame){
    const url='/api/jobs/'+encodeURIComponent(construction.id)+'/file/'+frame.path.split('/').map(encodeURIComponent).join('/');
    if($('constructionFrame').getAttribute('src')!==url)$('constructionFrame').src=url;
    $('constructionCaption').textContent='Paso '+frame.step+' · '+frame.label+(construction.windowMode&&frame.created?' · '+new Date(frame.created*1000).toLocaleTimeString('es-ES'):'');
  }else $('constructionCaption').textContent='';
  $('constructionSeek').max=Math.max(0,construction.frames.length-1);$('constructionSeek').value=construction.index;
  $('constructionSeek').disabled=!frame;$('constructionPlay').disabled=construction.frames.length<2;
  $('constructionPlay').textContent=construction.playing?'Pausar':'Reproducir';
  $('constructionLive').textContent=construction.live?'Siguiendo en directo':'Seguir en directo';
  $('constructionLive').setAttribute('aria-pressed',String(construction.live));
}
async function pollConstruction(){
  if(!construction.id||construction.polling||!$('constructionDialog').open)return;
  const id=construction.id,epoch=construction.epoch;construction.polling=true;
  try{
    const p=await api('/api/jobs/'+encodeURIComponent(id)+'/progress');
    if(epoch!==construction.epoch)return;
    construction.caseId=p.case_id;construction.data=p;
    const agent=p.agent||{};
    $('constructionAgent').hidden=!agent.provider;
    $('agentSummary').textContent=agent.provider?agent.provider+' · intento '+(agent.attempt||0)+' de '+agent.max_attempts+' · '+(agent.detail||'Preparando el caso'):'';
    $('agentEvents').innerHTML=(agent.events||[]).slice(-5).map(e=>'<li>'+esc(e.text)+'</li>').join('');
    $('constructionTitle').textContent=state.cases.find(c=>c.id===p.case_id)?.name||'Así se está construyendo';
    $('constructionEngine').textContent=p.engine+(p.b4d?.status==='PASS'?' · Herramienta B4D ejecutada y comprobada':'');
    const stopped=['failed','interrupted','needs_review'].includes(p.status);
    $('constructionStatus').className=['failed','interrupted'].includes(p.status)?'processerror':['done','unchanged'].includes(p.status)?'processdone':'processrunning';
    $('constructionStatus').textContent=(labels[p.status]||p.status)+' · '+(p.detail||'Esperando turno');
    if(stopped&&p.error&&!p.error.startsWith('Command ')&&!p.detail?.includes(p.error))$('constructionStatus').textContent+=' · '+p.error;
    $('constructionEmpty').textContent=p.status==='needs_review'?'Borrador generado; consulta las piezas y los ajustes pendientes en los archivos.':stopped?'La ejecución se detuvo antes de guardar una vista. Abre el diagnóstico.':p.status==='done'?'Esta versión anterior no guardó una secuencia. La próxima generación sí la mostrará.':'Preparando la primera vista. Las etapas aparecerán aquí al completarse.';
    constructionSelectFrames();
    $('constructionStages').innerHTML=p.stages.map(stage=>'<li class="stage-'+esc(stage.status)+'"><button data-process-step="'+stage.step+'" '+(![...p.frames,...(p.window_frames||[])].some(f=>f.step===stage.step)?'disabled':'')+'><span>'+stage.step+'</span><div>'+esc(stage.label)+'<small>'+esc({done:'Terminada',running:'En curso',failed:'Error en este paso',pending:'Pendiente',skipped:'No necesaria en este diseño'}[stage.status]||stage.status)+(stage.seconds?' · '+Math.round(stage.seconds)+' s':'')+'</small></div></button></li>').join('');
    const applied=p.corrections_applied.flatMap(row=>row.changes||[]),pending=p.corrections_pending;
    const measured=p.measured_sections;
    let summary=measured?.anterior_height_median_mm!=null?'<p>Altura medida: anterior <b>'+Number(measured.anterior_height_median_mm).toFixed(2)+' mm</b> · posterior <b>'+Number(measured.posterior_height_median_mm).toFixed(2)+' mm</b>.</p>':'';
    const attempts=p.local_safety?.attempts||[];
    const comparison=p.redesign_comparison;
    if(comparison){
      const delta=Number(comparison.bar_top_change_mm||0);
      if(delta)summary+='<p><b>Cambio frente a la versión anterior:</b> altura nominal de barra '+(delta>0?'+':'')+delta.toFixed(2)+' mm.</p>';
      else if(comparison.geometry_parameters_changed)summary+='<p><b>Cambios de forma frente a la versión anterior.</b> El TOP nominal no cambia; las rebajas locales se detallan abajo.</p>';
      if(comparison.mesh_volumes){const m=comparison.mesh_volumes;summary+='<p>Volumen de metal: '+Number(m.primaria.before_mm3).toFixed(1)+' → '+Number(m.primaria.after_mm3).toFixed(1)+' mm³. Supra: '+Number(m.supra.before_mm3).toFixed(1)+' → '+Number(m.supra.after_mm3).toFixed(1)+' mm³.</p>'}
      if(!comparison.geometry_parameters_changed&&!comparison.engine_changed)summary+='<p class="versionpending">'+(comparison.previous_approval==='draft_needs_review'?'Borrador reconstruido para completar su revisión; no se acredita un cambio de forma nuevo.':'Sin cambios geométricos interpretados. Se ha conservado la versión anterior; no se genera otra idéntica.')+'</p>';
    }
    const shape=p.shape_refinement||{},roof=p.local_safety?.roof_refinement;
    if(p.extraction){const test=p.extraction;summary+='<p class="versionpending"><b>Ensayo de extracción:</b> '+(test.status==='COLLISION_DETECTED'?'interferencias detectadas; revisar la inserción.':'sin interferencias en las '+Number(test.sample_count)+' posiciones ensayadas.')+' Dirección provisional; el recorrido continuo sigue pendiente de comprobar.</p>'}
    if(p.walls){const w=p.walls;summary+='<p class="versionpending"><b>Paredes y extremos:</b> '+Number(w.measured_wall_count)+' medidas en la normal de la cavidad.'+(w.minimum_sampled_wall_mm!=null?' Mínimo muestreado: <b>'+Number(w.minimum_sampled_wall_mm).toFixed(3)+' mm</b>.':' Sin medidas válidas suficientes.')+(w.thin_wall_count?' Hay paredes por debajo del mínimo exigido.':'')+(w.missing_cavity_count?' Hay direcciones sin cavidad de supra que requieren revisión.':'')+' Muestreo de superficie; el mínimo global sigue pendiente de comprobar.</p>'}
    if(shape.trace?.median_total_width_reduction_mm>0)summary+='<p>Afinado del trazado: reducción mediana total de <b>'+Number(shape.trace.median_total_width_reduction_mm).toFixed(2)+' mm</b>, limitada alrededor de las conexiones.</p>';
    if(p.shape_construction?.cervical_bevel_width_mm)summary+='<p>Bisel cervical construido con un ancho propuesto de <b>'+Number(p.shape_construction.cervical_bevel_width_mm).toFixed(2)+' mm</b>. Revisar su terminación tras el remallado.</p>';
    if(roof)summary+='<p>Cresta entre conexiones reducida <b>'+Number(roof.interimplant_peak_reduction_mm||0).toFixed(2)+' mm</b> en el perfil del separador, además del redondeo local. Las conexiones se han protegido de nuevo.</p>';
    if(p.bar_centering?.all_bilateral)summary+='<p>Barra a ambos lados de las conexiones. Desfase máximo del centro en las secciones medidas: <b>'+Number(p.bar_centering.max_center_offset_mm).toFixed(3)+' mm</b>.</p>';
    if(p.retentions?.rejected?.length)summary+='<p>Se excluyeron los surcos de retención que perforaban o separaban metal. Los grupos de surcos seguros se mantienen; el informe de retenciones detalla las zonas.</p>';
    if(measured?.minimum_sampled_occlusal_mm!=null)summary+='<p>Espesor mínimo de supra en las secciones medidas: <b>'+Number(measured.minimum_sampled_occlusal_mm).toFixed(3)+' mm</b>.'+(measured.measurement_method==='separating_surface_normal'?' Medido perpendicularmente a la separación.':'')+' El espesor global de paredes y márgenes sigue pendiente de revisión.</p>';
    if(attempts.length>1)summary+='<p>Corrección local de zona fina: mínimo oclusal muestreado de <b>'+Number(attempts[0].minimum_sampled_mm).toFixed(3)+' mm</b> a <b>'+Number(attempts.at(-1).minimum_sampled_mm).toFixed(3)+' mm</b>.'+(p.local_safety.unresolved?' La corrección requiere revisión.':'')+'</p>';
    $('constructionCorrections').innerHTML=(applied.length||summary?'<div class="versionchanges"><b>'+(p.status==='done'?'Ajustes incorporados a esta versión':'Ajustes preparados para esta versión')+'</b>'+summary+'<ul>'+applied.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul></div>':'')+(pending.length?'<div class="versionpending"><b>Correcciones que siguen pendientes</b><ul>'+pending.map(x=>'<li>'+esc(x.text)+'<br><small>'+esc(x.reason)+'</small></li>').join('')+'</ul></div>':'');
    constructionDraw();
  }catch(error){if(epoch===construction.epoch)$('constructionStatus').textContent=error.message}
  finally{construction.polling=false}
}
async function openConstruction(id){
  construction={id,caseId:null,frames:[],index:0,live:true,playing:false,epoch:construction.epoch+1,polling:false,mode:'auto',data:null};
  $('constructionStages').innerHTML='';$('constructionCorrections').innerHTML='';$('constructionAgent').hidden=true;$('constructionStatus').textContent='Cargando el proceso…';
  $('constructionEmpty').textContent='Cargando las vistas del trabajo…';constructionSelectFrames();constructionDraw();
  if(!$('constructionDialog').open)$('constructionDialog').showModal();
  await pollConstruction();
}
$('closeConstruction').onclick=()=>$('constructionDialog').close();
$('constructionDialog').addEventListener('close',()=>{construction.playing=false;construction.id=null;construction.epoch++;$('constructionDialog').classList.remove('expanded');$('constructionFullscreen').textContent='Pantalla completa';if(document.fullscreenElement)document.exitFullscreen().catch(()=>{})});
for(const [id,mode] of [['constructionWindow','window'],['constructionGeometry','geometry']])$(id).onclick=()=>{construction.mode=mode;construction.playing=false;construction.index=0;constructionSelectFrames();constructionDraw()};
$('constructionFullscreen').onclick=()=>{const expanded=$('constructionDialog').classList.toggle('expanded');$('constructionFullscreen').textContent=expanded?'Reducir visor':'Pantalla completa'};
$('constructionPlay').onclick=()=>{construction.live=false;construction.playing=!construction.playing;if(construction.playing&&construction.index===construction.frames.length-1)construction.index=0;constructionDraw()};
$('constructionSeek').oninput=()=>{construction.live=false;construction.playing=false;construction.index=Number($('constructionSeek').value);constructionDraw()};
$('constructionLive').onclick=()=>{construction.live=true;construction.playing=false;construction.index=Math.max(0,construction.frames.length-1);constructionDraw();pollConstruction()};
$('constructionStages').onclick=e=>{const button=e.target.closest('[data-process-step]');if(!button)return;const step=Number(button.dataset.processStep);if(!construction.frames.some(f=>f.step===step)){construction.mode=construction.windowMode?'geometry':'window';constructionSelectFrames()}const index=construction.frames.findIndex(f=>f.step===step);if(index>=0){construction.index=index;construction.live=false;construction.playing=false;constructionDraw()}};
$('constructionCorrect').onclick=()=>{const id=construction.caseId;if(id){$('constructionDialog').close();correctCase(id)}};
$('constructionFiles').onclick=async()=>{const id=construction.id;$('constructionDialog').close();go('casos');await showFiles(id);$('job-'+id)?.scrollIntoView({behavior:'smooth',block:'center'})};
document.addEventListener('click',e=>{const button=e.target.closest('[data-construction]');if(button)openConstruction(button.dataset.construction)});
setInterval(()=>{if(construction.playing&&$('constructionDialog').open){if(construction.index<construction.frames.length-1)construction.index++;else construction.playing=false;constructionDraw()}},1800);
setInterval(()=>{if(!$('loginDialog').open)pollConstruction()},2000);

let voiceContextLocks=null;
function voiceChanged(){
  const pending=dictationPending();
  const ids=['feedbackCase','feedbackStatus','redesignCase'];
  if(pending&&!voiceContextLocks){voiceContextLocks=ids.map(id=>[$(id),$(id).disabled]);voiceContextLocks.forEach(([el])=>el.disabled=true)}
  if(!pending&&voiceContextLocks){voiceContextLocks.forEach(([el,disabled])=>el.disabled=disabled);voiceContextLocks=null}
  $('saveFeedback').disabled=pending||$('feedbackForm').dataset.busy==='true';
  $('ask').disabled=pending||asking;$('searchOnly').disabled=pending;
  updateRedesignButton();
}
window.segmentVoice=[
  new window.SegmentVoiceInput({root:$('feedbackVoice'),target:$('feedbackText'),label:'Dictar corrección',api,onChange:voiceChanged}),
  new window.SegmentVoiceInput({root:$('questionVoice'),target:$('question'),label:'Dictar indicación',api,onChange:voiceChanged})
];
refresh();
setInterval(()=>{if(!busy&&!$('loginDialog').open&&!document.activeElement.matches('input,select,textarea'))refresh()},12000);
