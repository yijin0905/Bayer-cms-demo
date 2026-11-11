// Music nodes share the existing canvas, but never change caption/voice state.
const musicFiles = new Map();
let musicPlayer = null, musicPreviewId = null;
let musicConnectionStart = null, musicSequence = 0;
function ensureMusicState() {
  if (!Array.isArray(state.musicNodes)) {
    state.musicNodes = [];
    state.musicAssignments = {};
    // Preserve an explicitly added legacy full-length track on migration.
    if (state.audio.musicAdded || state.audio.musicEnabled) {
      state.musicNodes.push({id:'music-legacy', title:state.audio.music, source:'upload', volume:Number(state.audio.volume ?? 38), ready:false});
      state.scenes.forEach(s => state.musicAssignments[s.id] = 'music-legacy');
      state.positions['music-legacy'] = {x:250,y:520};
    }
  }
  state.musicNodes.forEach(m=>{if(m.source!=='upload'){m.source='upload';m.ready=false;}delete m.prompt;});
  state.musicAssignments ??= {};
  for (const [sceneId, musicId] of Object.entries(state.musicAssignments)) {
    if (!state.scenes.some(s => s.id === sceneId) || !state.musicNodes.some(m => m.id === musicId)) delete state.musicAssignments[sceneId];
  }
  state.audio.musicAdded = state.musicNodes.length > 0;
  state.audio.musicEnabled = Object.keys(state.musicAssignments).length > 0;
  state.audio.music = state.musicNodes.find(m => Object.values(state.musicAssignments).includes(m.id))?.title || '';
}
function selectedMusic() { return state.musicNodes.find(m => m.id === state.selectedMusicId); }
function selectMusic(id) {
  state.selectedMusicId=id; state.selectedType='music'; state.sidebarOpen=true;
  state.mobileProps=window.innerWidth<=760; persist(); render();
}
function stopMusicPreview() {
  if (musicPlayer) { musicPlayer.pause(); musicPlayer=null; }
  musicPreviewId=null;
}
function addMusicNode() {
  ensureMusicState();
  const id=`music-${Date.now()}-${++musicSequence}`;
  state.musicNodes.push({id,title:`新配乐 ${state.musicNodes.length+1}`,source:'upload',volume:38,ready:false});
  state.positions[id]={x:250+(state.musicNodes.length-1)%3*260,y:520+Math.floor((state.musicNodes.length-1)/3)*190};
  state.addMenuOpen=false; invalidateAudioCheck('music'); selectMusic(id);
  toast('已添加独立音乐节点；连接分镜后才会加入轨道','success');
}
addMusicTrack = addMusicNode;
function assignMusic(sceneId,musicId) {
  if (!state.scenes.some(s=>s.id===sceneId) || (musicId && !state.musicNodes.some(m=>m.id===musicId))) return;
  if (musicId) state.musicAssignments[sceneId]=musicId;
  else delete state.musicAssignments[sceneId];
  stopMusicPreview(); invalidateAudioCheck('music'); persist(); render();
}
function musicVolume(m) {
  return `<div class="volume-row"><label class="tiny" for="volume-${m.id}-${state.step}">音量</label><input aria-label="${esc(m.title)}音量" type="range" min="0" max="100" value="${m.volume}" data-music-volume="${m.id}"><b>${m.volume}%</b></div>`;
}
function musicCanvasNode(m) {
  const pos=state.positions[m.id]||{x:250,y:520};
  const count=Object.values(state.musicAssignments).filter(id=>id===m.id).length;
  return `<div class="node music-node ${state.selectedType==='music'&&state.selectedMusicId===m.id?'selected':''}" data-node="${m.id}" data-node-kind="music" style="left:${pos.x}px;top:${pos.y}px"><div class="node-head"><b>♫ ${esc(m.title)}</b><button class="text-link" data-action="music-select" data-id="${m.id}">编辑</button></div><div class="node-copy">手动上传音频</div><div class="music-node-status">${m.ready&&musicFiles.has(m.id)?'✓ 已就绪':'待上传音频'} · 已关联 ${count} 个分镜</div>${musicVolume(m)}<button class="btn btn-soft btn-sm" data-action="music-preview" data-id="${m.id}" ${m.ready&&musicFiles.has(m.id)?'':'disabled'}>${musicPreviewId===m.id?'Ⅱ 停止':'▶ 试听'}</button><span class="node-port out music-port" data-music-port="${m.id}" title="点击这里，再点击分镜连接点"></span></div>`;
}
function musicProperties() {
  const m=selectedMusic(); if(!m)return '<div class="prop-form">请选择音乐节点</div>';
  return `<div class="prop-header"><div><div class="prop-kind">独立音乐节点</div><div class="prop-title">配乐设置</div></div><button class="prop-close" data-action="close-prop">×</button></div><div class="prop-form"><div class="field"><label>配乐名称</label><input class="input" data-music-field="title" value="${esc(m.title)}"></div><div class="field"><label>选择本地音频</label><input type="file" accept="audio/*,.mp3,.wav,.m4a,.ogg,.flac,.aac" data-music-upload="${m.id}"></div><p class="prop-hint">${esc(m.filename||'音频仅在当前浏览器使用，不会上传服务器。')}${m.filename&&!musicFiles.has(m.id)?' · 刷新后请重新选择原音频':''}</p>${musicVolume(m)}<button class="btn btn-soft btn-sm" data-action="music-preview" data-id="${m.id}" ${m.ready&&musicFiles.has(m.id)?'':'disabled'}>${musicPreviewId===m.id?'Ⅱ 停止试听':'▶ 试听配乐'}</button><section class="prop-section"><b class="tiny">应用范围 · 手动关联</b><p class="prop-hint">也可点击音乐节点绿色连接点，再点击分镜连接点。每个分镜只使用一条配乐，重新关联会替换。</p>${state.scenes.map(s=>`<label class="music-scene-choice"><input type="checkbox" data-music-assignment="${s.id}" data-music-id="${m.id}" ${state.musicAssignments[s.id]===m.id?'checked':''}>${esc(s.title)}<span>${s.duration}s</span></label>`).join('')}</section><button class="btn btn-quiet btn-sm danger-action" data-action="music-delete" data-id="${m.id}">删除音乐节点及关联</button></div>`;
}
function musicTimeline() {
  ensureMusicState(); let elapsed=0;
  return `<section class="music-timeline card"><div class="sound-card-head"><div><div class="section-title">♫ 分段配乐轨道</div><p class="tiny muted">绿色片段跟随分镜顺序与时长；未关联分镜保持无配乐。</p></div><button class="btn btn-soft btn-sm" data-action="music-add">＋ 音乐节点</button></div><div class="music-segments" style="grid-template-columns:${state.scenes.map(s=>`${Number(s.duration)}fr`).join(' ')}">${state.scenes.map(s=>{const start=elapsed;elapsed+=Number(s.duration);const m=state.musicNodes.find(m=>m.id===state.musicAssignments[s.id]);return `<button class="music-segment ${m?'':'empty'}" data-action="${m?'music-edit-canvas':'music-scene-canvas'}" data-id="${m?.id||s.id}"><b>${esc(s.title)}</b><span>${m?esc(m.title):'无配乐'}</span><small>${timeLabel(start)}–${timeLabel(elapsed)}${m?` · ${m.volume}%${m.ready&&musicFiles.has(m.id)?'':' · 待上传'}`:''}</small></button>`}).join('')}</div>${state.musicNodes.length?'':'<p class="tiny muted">尚无音乐节点。可在画布左侧点击 ♫ 创建。</p>'}</section>`;
}
const originalProperties=properties;
properties=function(){return state.selectedType==='music'?musicProperties():originalProperties();};
const originalCanvas=canvas;
canvas=function(){return originalCanvas().replace(/手动添加全片配乐/g,'添加独立音乐节点').replace('♫ 配乐需手动添加','♫ 点击音乐绿色端点，再点击分镜端点关联').replace('拖动分镜可同步移动字幕与配音','拖动分镜可同步移动字幕与配音').replace('</svg>','</svg>'+state.musicNodes.map(musicCanvasNode).join(''));};
const originalConnections=buildConnections;
buildConnections=function(){let paths=originalConnections();for(const s of state.scenes){const id=state.musicAssignments?.[s.id];if(!id)continue;const a=state.positions[id]||{x:250,y:520},b=scenePosition(s);paths+=`<path class="music-link" d="M ${a.x+230} ${a.y+85} C ${a.x+290} ${a.y+85}, ${b.x-60} ${b.y+91}, ${b.x} ${b.y+91}"/>`;}return paths;};
const originalSoundWorkspace=soundWorkspace;
soundWorkspace=function(){return state.step===6?'':originalSoundWorkspace().replace(/<button class="track-key[^\"]*" data-action="[^"]*" data-track="music">[\s\S]*?<div class="music-lane">[\s\S]*?<\/div>/,'').replace(/<section class="sound-edit-card music-edit[^\"]*">[\s\S]*?<\/section>/,'')+musicTimeline();};
const originalReviewTools=reviewTools;
reviewTools=function(){return originalReviewTools().replace('配乐覆盖全片','配乐按分镜关联')+musicTimeline();};
const originalQaRows=qaRows;
qaRows=function(){return originalQaRows().replace(/配乐覆盖全片/g,'配乐按分镜关联').replace(/全片配乐轨道/g,'关联配乐节点');};
const originalResetProjectState=resetProjectState;
resetProjectState=function(progress){stopMusicPreview();musicFiles.forEach(url=>URL.revokeObjectURL(url));musicFiles.clear();originalResetProjectState(progress);state.musicNodes=[];state.musicAssignments={};state.selectedMusicId=null;};
const originalRender=render;
render=function(){ensureMusicState();originalRender();};
function handleMusicConnection(target) {
  const musicId=target.closest('[data-music-port]')?.dataset.musicPort;
  const sceneId=target.closest('[data-port]')?.dataset.id;
  if(musicId){musicConnectionStart=musicId;connectStart=null;toast('已选择配乐，请点击目标分镜的连接点');return true;}
  if(musicConnectionStart&&sceneId){if(state.scenes.some(s=>s.id===sceneId)){assignMusic(sceneId,musicConnectionStart);musicConnectionStart=null;connectStart=null;suppressPortClick=false;toast('已关联配乐，原配乐自动替换','success');}else toast('配乐只能连接分镜','warning');return true;}
  return false;
}
document.addEventListener('pointerdown',e=>{if(e.target.closest('[data-music-port]')||(musicConnectionStart&&e.target.closest('[data-port]'))){e.stopImmediatePropagation();return;}if(e.target.closest('.music-node input,.music-node button'))e.stopImmediatePropagation();},true);
document.addEventListener('pointerup',e=>{if(musicConnectionStart&&e.target.closest('[data-port]'))e.stopImmediatePropagation();},true);
document.addEventListener('click',async e=>{
  if(handleMusicConnection(e.target)){e.stopImmediatePropagation();return;}
  const button=e.target.closest('[data-action]');const action=button?.dataset.action;
  if(!action&&e.target.closest('.music-node')){e.stopImmediatePropagation();if(!dragMoved)selectMusic(e.target.closest('.music-node').dataset.node);return;}
  if(action==='add-music'||action==='add-music-track'||action==='music-add'){e.stopImmediatePropagation();if(state.step!==5){state.step=5;state.maxStep=Math.max(5,state.maxStep);}addMusicNode();return;}
  if(action==='sync-audio'){
    e.stopImmediatePropagation();ensureMusicState();
    const badVoice=state.scenes.find(s=>s.voiceEnabled&&(!s.narration?.trim()||!s.voiceGenerated||s.narration.trim().length>Number(s.duration)*8));
    const badMusic=state.musicNodes.find(m=>Object.values(state.musicAssignments).includes(m.id)&&(!m.ready||!musicFiles.has(m.id)));
    state.audio.syncStatus=badVoice||badMusic?'attention':'ok';state.audio.syncTarget=badVoice?.id||state.scenes.find(s=>state.musicAssignments[s.id]===badMusic?.id)?.id||state.scenes[0]?.id;state.qaConfirmed=false;state.audio.declarationConfirmed=false;state.exportDone=false;persist();render();toast(badVoice?'请生成或调整字幕配音':badMusic?'关联配乐尚未就绪，请重新选择音频':'音画同步检查通过；未关联分镜保持无配乐',badVoice||badMusic?'warning':'success');return;
  }
  if(!action?.startsWith('music-'))return;
  e.stopImmediatePropagation();const id=button.dataset.id;const m=selectedMusic();
  if(action==='music-select')selectMusic(id);
  if(action==='music-edit-canvas'){state.step=5;selectMusic(id);}
  if(action==='music-scene-canvas'){state.step=5;selectScene(id);}
  if(action==='music-delete'){stopMusicPreview();const url=musicFiles.get(id);if(url)URL.revokeObjectURL(url);musicFiles.delete(id);state.musicNodes=state.musicNodes.filter(m=>m.id!==id);delete state.positions[id];state.selectedType='scene';musicConnectionStart=null;invalidateAudioCheck('music');render();}
  if(action==='music-preview')await previewMusic(state.musicNodes.find(m=>m.id===id));
},true);
app.addEventListener('input',e=>{
  const t=e.target;
  if(t.dataset.musicVolume){const m=state.musicNodes.find(m=>m.id===t.dataset.musicVolume);if(!m)return;m.volume=clamp(t.value,0,100);document.querySelectorAll(`[data-music-volume="${m.id}"]`).forEach(input=>{input.value=m.volume;input.parentElement.querySelector('b').textContent=`${m.volume}%`;});if(musicPreviewId===m.id&&musicPlayer)musicPlayer.volume=m.volume/100;invalidateAudioCheck('music');scheduleSave();}
  if(t.dataset.musicField){const m=selectedMusic();if(!m)return;m.title=t.value;invalidateAudioCheck('music');scheduleSave();}
});
app.addEventListener('change',e=>{
  const t=e.target;
  if(t.dataset.musicAssignment){assignMusic(t.dataset.musicAssignment,t.checked?t.dataset.musicId:null);return;}
  if(t.dataset.musicVolume||t.dataset.musicField){render();return;}
  if(t.dataset.musicUpload){const m=state.musicNodes.find(m=>m.id===t.dataset.musicUpload),file=t.files?.[0];if(!m||!file)return;if(!file.type.startsWith('audio/')&&!/\.(mp3|wav|m4a|ogg|flac|aac)$/i.test(file.name)){toast('请选择音频文件','warning');return;}stopMusicPreview();const old=musicFiles.get(m.id);if(old)URL.revokeObjectURL(old);musicFiles.set(m.id,URL.createObjectURL(file));m.filename=file.name;m.title=file.name;m.source='upload';m.ready=true;invalidateAudioCheck('music');render();toast('音频已载入，可试听并关联分镜','success');}
});
async function previewMusic(m) {
  if(!m?.ready||!musicFiles.has(m.id))return;
  if(musicPreviewId===m.id){stopMusicPreview();render();return;}
  stopMusicPreview();musicPreviewId=m.id;
  try {
    musicPlayer=new Audio(musicFiles.get(m.id));musicPlayer.volume=m.volume/100;
    musicPlayer.onended=()=>{stopMusicPreview();render();};
    await musicPlayer.play();
    render();
  } catch(error){stopMusicPreview();render();toast(error.message||'无法播放该音频，请更换文件','warning');}
}
window.addEventListener('keydown',e=>{if(e.key==='Escape')musicConnectionStart=null;});
window.addEventListener('pagehide',stopMusicPreview);
render();
