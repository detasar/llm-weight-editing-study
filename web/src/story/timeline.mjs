import {chapters,DURATION} from './chapters.mjs';
export {DURATION};
export const clampTime=t=>Math.max(0,Math.min(DURATION,Number.isFinite(t)?t:0));
export const ease=t=>{t=Math.max(0,Math.min(1,t));return t*t*(3-2*t)};
export function poseAt(t){t=clampTime(t);const chapter=chapters.findLast(ch=>ch.start<=t);const local=Math.min(t-chapter.start,chapter.duration);const cueIndex=Math.min(chapter.cues.length-1,Math.floor(local/20));const cue=chapter.cues[cueIndex];return {t,chapter,cue,cueIndex,local,progress:Math.min(1,(t-cue.start)/20),settle:ease((t-cue.start)/3)};}
export class PresentationClock{
 constructor(t=0){this.time=clampTime(t);this.playing=false;this.last=null;}
 tick(ms){if(!Number.isFinite(ms))return this.time;if(this.last!==null&&this.playing)this.time=clampTime(this.time+Math.max(0,ms-this.last)/1000);this.last=ms;if(this.time===DURATION)this.playing=false;return this.time;}
 seek(t){this.time=clampTime(t);this.last=null;return this.time;}
 play(){if(this.time===DURATION)this.seek(0);this.playing=true;this.last=null;}
 pause(){this.playing=false;this.last=null;}
 replay(){this.seek(0);this.play();}
}
export const formatTime=t=>`${Math.floor(t/60).toString().padStart(2,'0')}:${Math.floor(t%60).toString().padStart(2,'0')}`;
export const escapeHTML=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const safeJSON=value=>JSON.stringify(value).replace(/</g,'\\u003c').replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029');
