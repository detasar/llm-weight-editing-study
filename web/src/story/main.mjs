import './style.css';
import hero from '../../public/story-assets/weight-space-hero.png?inline';
import articleSource from '../../public/story-assets/reference-article-title.png?inline';
import {normalizeImageURL} from './packaging.mjs';
const article=normalizeImageURL(articleSource);
import {chapters,DURATION,CUES} from './chapters.mjs';
import {PresentationClock,poseAt,formatTime,escapeHTML} from './timeline.mjs';
import {figure,evidenceText} from './figures.mjs';
import {GlassStage} from './stage.mjs';
const $=s=>document.querySelector(s),clock=new PresentationClock();
const panel=$('#presentation'),slider=$('#seek'),toggle=$('#toggle'),select=$('#chapters');
$('#hero').src=hero;$('#evidence-content').innerHTML=evidenceText();
select.innerHTML=chapters.map(ch=>`<option value="${ch.index}">${String(ch.index+1).padStart(2,'0')} · ${escapeHTML(ch.title)}</option>`).join('');
let reduced=matchMedia('(prefers-reduced-motion: reduce)').matches,flat=false,stage=null,lastCue='',started=false;
$('#reduced').checked=reduced;
function fallback(reason){flat=true;$('#flat').checked=true;document.body.classList.add('fallback');$('#anchors').hidden=true;$('#mode').textContent=reason||'Intentional 2D view';lastCue='';}
try{stage=new GlassStage($('#glass'),$('#anchors'));stage.onFailure=()=>fallback('Graphics context lost · 2D explanation');}catch{fallback('2D explanation · WebGL unavailable');}
function renderAt(t){
 const p=poseAt(t),ch=p.chapter,key=`${ch.index}:${p.cueIndex}:${flat}`;
 if(lastCue!==key){
  lastCue=key;panel.classList.toggle('paper',['adult-results','controls','intervals','lm-results','metrics','counts','trajectory'].includes(ch.scene));
  panel.classList.toggle('hero-scene',ch.scene==='hero');$('#hero').hidden=ch.scene!=='hero';
  $('h1').textContent=ch.title;$('.cue-heading').textContent=p.cue.label;
  $('#chapter-position').textContent=`${String(ch.index+1).padStart(2,'0')} / 33`;
  $('#figure').innerHTML=figure(p,flat).replaceAll('__ARTICLE__',article);
  $('#subtitles').textContent=p.cue.narration;$('#caption').textContent=ch.caption;
  $('#cue-dots').innerHTML=ch.cues.map((_,i)=>`<span class="${i===p.cueIndex?'active':''}"></span>`).join('');
  select.value=String(ch.index);
 }
 if(!flat&&stage){try{stage.render(p,reduced);}catch{fallback('2D explanation · graphics fallback');renderAt(t);return;}}
 slider.value=String(p.t);slider.setAttribute('aria-valuetext',`${formatTime(p.t)} of 45 minutes`);$('#time').textContent=`${formatTime(p.t)} / 45:00`;
 toggle.textContent=clock.playing?'Pause':p.t===DURATION?'Replay presentation':started?'Resume':'Start presentation';
 toggle.setAttribute('aria-label',toggle.textContent);
 document.body.classList.toggle('reduced',reduced);
 return p;
}
function seek(t){clock.seek(t);renderAt(clock.time);}
toggle.addEventListener('click',()=>{started=true;clock.playing?clock.pause():clock.play();renderAt(clock.time);});
$('#replay').addEventListener('click',()=>{started=true;clock.replay();renderAt(0);});
slider.addEventListener('input',()=>seek(Number(slider.value)));
select.addEventListener('change',()=>seek(chapters[Number(select.value)].start));
$('#subtitles-on').addEventListener('change',e=>{$('#subtitles').hidden=!e.target.checked;});
$('#reduced').addEventListener('change',e=>{reduced=e.target.checked;renderAt(clock.time);});
$('#flat').addEventListener('change',e=>{if(e.target.checked)fallback();else if(stage){flat=false;document.body.classList.remove('fallback');stage.frameKey='';$('#mode').textContent='Glass / wire';lastCue='';}else fallback('2D explanation · WebGL unavailable');renderAt(clock.time);});
$('#evidence-button').addEventListener('click',()=>{$('#evidence-dialog').showModal();});
$('#close-evidence').addEventListener('click',()=>$('#evidence-dialog').close());
$('#fullscreen').addEventListener('click',async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch{$('#error').textContent='Fullscreen unavailable; presentation remains playable.';}});
document.addEventListener('keydown',e=>{if(e.target.closest('button,input,select,dialog'))return;if(e.code==='Space'){e.preventDefault();toggle.click();}if(e.code==='ArrowRight'){e.preventDefault();seek(clock.time+20);}if(e.code==='ArrowLeft'){e.preventDefault();seek(clock.time-20);}if(e.code==='Home'){e.preventDefault();seek(0);}if(e.code==='End'){e.preventDefault();seek(DURATION);}});
// Absolute-time rendering is shared by playback, seeking, replay and coordinator inspection.
window.renderAt=t=>{clock.seek(t);return renderAt(clock.time);};window.DURATION=DURATION;window.CHAPTERS=chapters;window.CUES=CUES;
window.presentation={clock,poseAt,renderAt:window.renderAt};
if(!flat)$('#mode').textContent='Glass / wire';
renderAt(0);window.READY=true;
function loop(ms){clock.tick(ms);renderAt(clock.time);requestAnimationFrame(loop);}requestAnimationFrame(loop);
