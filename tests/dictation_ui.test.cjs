const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../dental_lab/static/dictation.js'),'utf8');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
class Element{
  constructor(){this.value='';this.maxLength=10000;this.form={dataset:{}};this.nodes=new Map();this.classList={add(){},toggle(){}};this.events=[]}
  querySelector(key){if(!this.nodes.has(key))this.nodes.set(key,new Element());return this.nodes.get(key)}
  setAttribute(){} removeAttribute(){} pause(){} dispatchEvent(event){this.events.push(event.type)}
}
function environment(secure=true){
  const tracks=[];let permissions=0;
  class Recorder{
    static isTypeSupported(){return true}
    constructor(stream){this.stream=stream;this.state='inactive';this.mimeType='audio/webm'}
    start(){this.state='recording'}
    stop(){this.state='inactive';queueMicrotask(()=>{this.ondataavailable?.({data:new Blob(['spoken'])});this.onstop?.()})}
  }
  const window={isSecureContext:secure,MediaRecorder:Recorder,addEventListener(){}};
  const navigator={mediaDevices:{getUserMedia:async()=>{permissions++;const track={stops:0,stop(){this.stops++}};tracks.push(track);return {getTracks:()=>[track]}}}};
  const context={window,navigator,MediaRecorder:Recorder,Event,Blob,AbortController,URL:{createObjectURL:()=> 'blob:owned',revokeObjectURL(){}},Date,setTimeout:()=>1,clearTimeout(){},setInterval:()=>2,clearInterval(){}};
  vm.runInNewContext(code,context);
  return {tracks,navigator,get permissions(){return permissions},create(api){const target=new Element(),root=new Element();return {target,voice:new window.SegmentVoiceInput({root,target,label:'Dictar',api})}}};
}
async function main(){
  { // A delayed permission grant cannot leave the microphone on after cancellation.
    const e=environment();let grant;const track={stops:0,stop(){this.stops++}};
    e.navigator.mediaDevices.getUserMedia=()=>new Promise(resolve=>grant=resolve);
    const {voice}=e.create(()=>assert.fail('must not upload'));
    const opening=voice.start();voice.cancel();grant({getTracks:()=>[track]});await opening;
    assert.equal(track.stops,1);assert.equal(voice.isBusy,false);
  }
  { // Stop the real track, then append to the current draft, never its stale snapshot.
    const e=environment();let resolve,calls=0;
    const {voice,target}=e.create(()=>{calls++;return new Promise(r=>resolve=r)});
    target.value='Texto inicial';await voice.start();voice.stop();await tick();
    assert.equal(e.tracks[0].stops,1);assert.equal(voice.phase,'transcribing');
    target.value='Texto editado mientras transcribe';resolve({text:'Más altura.'});await tick();
    assert.equal(target.value,'Texto editado mientras transcribe\nMás altura.');
    assert.deepEqual(target.events,['input']);assert.equal(calls,1);assert.equal(voice.isBusy,false);
  }
  { // A response arriving after cancellation cannot alter the draft.
    const e=environment();let resolve;const {voice,target}=e.create(()=>new Promise(r=>resolve=r));
    await voice.start();voice.stop();await tick();voice.cancel();resolve({text:'Obsoleto'});await tick();
    assert.equal(target.value,'');assert.equal(target.events.length,0);
  }
  { // Keep the complete transcript if the field would overflow.
    const e=environment();const {voice,target}=e.create(async()=>({text:'Una corrección larga'}));
    target.maxLength=5;target.value='Antes';await voice.start();voice.stop();await tick();
    assert.equal(target.value,'Antes');assert.equal(voice.result.value,'Una corrección larga');
  }
  { // Plain HTTP never asks for a microphone; an audio note still works.
    const e=environment(false);const {voice,target}=e.create(async()=>({text:'Nota local'}));
    await voice.start();assert.equal(e.permissions,0);assert.match(voice.message,/HTTPS/);
    const blob=new Blob(['voice']);blob.name='nota.wav';voice.fromFile(blob);await tick();
    assert.equal(target.value,'Nota local');
  }
  { // Failed requests can retry the same blob without another recording.
    const e=environment();let calls=0;
    const {voice,target}=e.create(async()=>{if(++calls===1)throw Error('Servidor ocupado');return {text:'Reintentada'}});
    await voice.start();voice.stop();await tick();assert.equal(voice.retry.hidden,false);
    voice.retry.onclick();await tick();assert.equal(e.permissions,1);assert.equal(target.value,'Reintentada');
  }
  { // An old stop callback must not close a newly started microphone.
    const e=environment();const {voice}=e.create(async()=>({text:'x'}));
    await voice.start();voice.cancel();await voice.start();await tick();
    assert.equal(e.tracks[1].stops,0);voice.cancel();assert.equal(e.tracks[1].stops,1);
  }
  console.log('PASS: 7 dictation UI scenarios; cancellation, tracks, drafts, limits, HTTP and retry.');
}
main().catch(error=>{console.error(error);process.exitCode=1});
