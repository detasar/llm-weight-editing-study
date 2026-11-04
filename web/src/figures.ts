import {M,G,P,LM,colors,pct,num,esc,adultChanges} from './data';
const text=(x:number,y:number,s:string,extra='')=>`<text x="${x}" y="${y}" ${extra}>${esc(s)}</text>`;
const svg=(s:string,label:string)=>`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 500" role="img" aria-label="${esc(label)}"><title>${esc(label)}</title>${s}</svg>`;
export function forest(reference='baseline'){
 const ms=reference==='baseline'?['Sol','Astra','joint','clean','random','grid']:['Sol','Astra','joint'];
 const cs=ms.map(k=>M.adult.contrasts[k+'_minus_'+reference]);
 const lower=Math.min(-.3,...cs.map(c=>100*c.difference_95ci[0])),upper=Math.max(.7,...cs.map(c=>100*c.difference_95ci[1]));const step=[.1,.2,.25,.5,1,2,5].find(v=>v>=(upper-lower)/5)??5;const lo=Math.floor(lower/step)*step,hi=Math.ceil(upper/step)*step;
 const x=(v:number)=>185+(v-lo)/(hi-lo)*630;
 let s=`<line x1="${x(0)}" y1="35" x2="${x(0)}" y2="420" stroke="currentColor" stroke-dasharray="4 5" opacity=".4"/>`;
 for(let v=lo;v<=hi+step/10;v+=step){s+=`<line x1="${x(v)}" y1="40" x2="${x(v)}" y2="420" stroke="currentColor" opacity=".09"/>`+text(x(v),450,v.toFixed(2),'text-anchor="middle"');}
 cs.forEach((c,i)=>{let y=70+i*(ms.length>3?62:120);const [a,b]=c.difference_95ci.map((v:number)=>x(v*100));s+=`<g data-reveal="${i}" style="--reveal-order:${i}">`+text(12,y+7,ms[i])+`<g stroke="${colors[ms[i]]}" fill="${colors[ms[i]]}"><path d="M${a} ${y}H${b} M${a} ${y-8}V${y+8} M${b} ${y-8}V${y+8}" stroke-width="3"/><circle cx="${x(c.difference*100)}" cy="${y}" r="6"/></g>`+text(855,y+7,(c.difference*100).toFixed(3))+'</g>';});
 const pair=M.adult.contrasts.joint_minus_Sol; if(reference==='baseline')s+=text(500,25,`Joint − Sol: ${(pair.difference*100).toFixed(3)} pp [${pair.difference_95ci.map((v:number)=>(v*100).toFixed(3)).join(', ')}]`,'text-anchor="middle"');
 return svg(s+text(500,490,`Δ balanced accuracy vs ${reference} · percentage points · paired 95% CI`,'text-anchor="middle"'),`Paired balanced accuracy differences against ${reference}. `+cs.map((c,i)=>`${ms[i]} ${(c.difference*100).toFixed(3)} pp, 95% CI ${c.difference_95ci.map((v:number)=>(v*100).toFixed(3)).join(' to ')}`).join('; '));
}
export function network(method='Sol',lesion=false,candidate?:number){
 const layers:number[]=G.architecture.layers;const pos=(l:number,i:number)=>[70+l*285,40+(i+.5)/layers[l]*390];let s='';
 for(let l=0;l<3;l++)for(let r=0;r<layers[l+1];r++)for(let c=0;c<layers[l];c++){
  if(l===0&&c%8!==r%8)continue;
  const a=pos(l,c),b=pos(l+1,r),mask=l===1&&G.permanent_mask[r][c],changed=l===1&&adultChanges(method,candidate).some((v:any)=>v.row===r&&v.column===c);
  if(mask&&!lesion)continue;
  s+=`<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="${mask?'#a65151':changed?'#f5b35b':'#50d9e6'}" opacity="${mask?'.12':changed?'.95':'.1'}" stroke-width="${changed?2:1}" ${mask?'stroke-dasharray="3 5"':''}/>`;
 }
 layers.forEach((n,l)=>{for(let i=0;i<n;i++){let [x,y]=pos(l,i);s+=`<circle cx="${x}" cy="${y}" r="${l===0?1.7:3.6}" fill="#50d9e6"/>`;}s+=text(70+l*285,475,`${n} ${['inputs','ReLU','ReLU','sigmoid'][l]}`,'text-anchor="middle"');});
 return svg(s,'Adult actual 104 to 32 to 16 to 1 architecture; all nodes; sampled first-layer edges; full surviving fc2 edges. Amber denotes real selected patch support.');
}
export function trajectory(method='Sol',lm=false,active?:number){
 const group=(lm?LM.candidates:M.adult.candidates)[method];const cs=group?.candidates??[];const metric=lm?'acc_norm':'balanced_accuracy';const vals=cs.map((c:any)=>c.metrics[metric]*100);const lo=Math.min(...vals)-.25,hi=Math.max(...vals)+.25;const x=(i:number)=>120+i/Math.max(...cs.map((c:any)=>c.index),1)*760,y=(v:number)=>390-(v-lo)/(hi-lo)*320;let s='';
 for(let i=0;i<4;i++){let v=lo+(hi-lo)*i/3;s+=text(85,y(v)+7,v.toFixed(2),'text-anchor="end"')+`<path d="M100 ${y(v)}H910" stroke="currentColor" opacity=".13"/>`;}
 const b=cs.find((c:any)=>c.index===0);if(b)s+=`<path d="M100 ${y(b.metrics[metric]*100)}H910" stroke="currentColor" stroke-dasharray="6 5" opacity=".5"/>`;
 cs.forEach((c:any)=>{const selected=c.index===group.selected_index;s+=`<circle data-candidate="${c.index}" tabindex="0" role="button" aria-label="Candidate ${c.index}, development ${pct(c.metrics[metric])}${selected?', selected':''}" cx="${x(c.index)}" cy="${y(c.metrics[metric]*100)}" r="${active===c.index?12:8}" fill="${colors[method]}" stroke="currentColor" stroke-width="${selected?3:0}"/>`+text(x(c.index),425,String(c.index),'text-anchor="middle"');});
 s+=text(500,475,`DEV ${lm?'acc_norm':'balanced accuracy'} (%) · candidate index · outline = frozen selection`,'text-anchor="middle"');
 if(lm&&method==='joint')s+=text(500,30,'Attempt 1 INVALID · no score · valid indices 0 / 2 / 3 / 4 / 5','text-anchor="middle"');
 return svg(s,`${method} real measured development candidates only. No interpolation. Selected candidate ${group?.selected_index}.`);
}
export function probabilities(method='Sol'){
 const a=P.methods.baseline,b=P.methods[method];
 const flipped:number[]=a.probabilities.map((p:number,i:number)=>(p>=.5)!==(b.probabilities[i]>=.5)?i:-1).filter((i:number)=>i>=0);
 const values=flipped.flatMap(i=>[a.probabilities[i],b.probabilities[i]]);
 const low=Math.min(.5,...values),high=Math.max(.5,...values),pad=Math.max(.005,(high-low)*.08),lo=Math.max(0,low-pad),hi=Math.min(1,high+pad);
 const x=(p:number)=>110+(p-lo)/(hi-lo)*570,y=(p:number)=>400-(p-lo)/(hi-lo)*340;
 let s=`<defs><clipPath id="decision-zoom"><rect x="110" y="60" width="570" height="340"/></clipPath></defs>`;
 s+=`<rect x="110" y="60" width="${x(.5)-110}" height="${y(.5)-60}" fill="#c27b21" opacity=".09"/><rect x="${x(.5)}" y="${y(.5)}" width="${680-x(.5)}" height="${400-y(.5)}" fill="#168a9b" opacity=".09"/>`;
 for(let i=0;i<5;i++){const v=lo+(hi-lo)*i/4;s+=`<path d="M${x(v)} 60V400 M110 ${y(v)}H680" stroke="currentColor" opacity=".12"/>`+text(x(v),430,v.toFixed(3),'text-anchor="middle"')+text(96,y(v)+6,v.toFixed(3),'text-anchor="end"');}
 s+=`<path d="M${x(.5)} 60V400 M110 ${y(.5)}H680" stroke="currentColor" stroke-dasharray="5 5"/>`;
 s+=text(395,18,'Decision boundary: 0.500 on both axes','text-anchor="middle"')+text(665,85,'1 → 1','text-anchor="end"')+text(125,386,'0 → 0')+text(120,43,'0 → 1 decisions')+text(670,461,'1 → 0 decisions','text-anchor="end"');
 let points='',inset='';let shown=0;
 for(let i=0;i<a.probabilities.length;i++){const p=a.probabilities[i],q=b.probabilities[i],flip=(p>=.5)!==(q>=.5);if(!flip&&i%37)continue;const color=a.labels[i]?'#bf7b21':'#168a9b';
  inset+=`<circle cx="${760+p*205}" cy="${280-q*205}" r="${flip?1.8:.8}" fill="${color}" opacity="${flip?.8:.25}"/>`;
  if(p<lo||p>hi||q<lo||q>hi)continue;shown++;points+=`<circle data-flip="${flip}" cx="${x(p)}" cy="${y(q)}" r="${flip?3.8:2}" fill="${color}" opacity="${flip?.85:.3}"><title>Anonymous ordinal ${i}; class ${a.labels[i]}; baseline ${p}; ${method} ${q}</title></circle>`;
 }
 s+=`<g clip-path="url(#decision-zoom)">${points}</g>`+text(862,40,'Full range','text-anchor="middle"')+`<rect x="760" y="75" width="205" height="205" fill="none" stroke="currentColor" opacity=".5"/><path d="M862.5 75V280 M760 177.5H965" stroke="currentColor" stroke-dasharray="3 4" opacity=".4"/>`+inset+text(760,306,'0')+text(862,306,'0.5','text-anchor="middle"')+text(965,306,'1','text-anchor="end"')+text(748,85,'1','text-anchor="end"')+text(748,282,'0','text-anchor="end"');
 s+=`<circle cx="748" cy="347" r="6" fill="#bf7b21"/><circle cx="748" cy="381" r="6" fill="#168a9b"/>`+text(765,354,'Class 1 · amber')+text(765,388,'Class 0 · cyan')+text(740,425,`${flipped.length} flips in zoom`)+text(395,491,'Baseline probability → · edited probability ↑','text-anchor="middle"');
 const c=M.adult.contrasts[method+'_minus_baseline'].paired_counts;
 return svg(s,`Frozen FINAL selected endpoint · ${method}: decision-boundary zoom [${lo}, ${hi}], all ${flipped.length} flipped rows included; ${shown} rows in zoom. ${c.rescues} rescues and ${c.regressions} regressions. Upper left: 0 to 1; lower right: 1 to 0. Full-range inset. Class 1 amber, class 0 cyan.`);
}
export function flow(joint=false){return svg(`<g fill="none" stroke="#50d9e6" stroke-width="3"><path d="M130 250L400 100 M130 250L400 400"/>${joint?'<path d="M550 100L800 250 M550 400L800 250" stroke-dasharray="8 6"/>':''}</g>`+text(20,235,'Same origin')+text(400,90,'Sol · independent')+text(400,410,'Astra · independent')+(joint?text(720,230,'Joint search')+text(660,280,'development history only'):'')+text(380,490,'Each patch is applied to the immutable origin.'),'Independent source searches share an origin; joint search receives development history, never serially accumulated solo weights.');}
export function lmDiagram(method='Sol',candidate=0,stack=false){
 const c=LM.candidates[method]?.candidates.find((v:any)=>v.index===candidate);const ops=c?.patch.ops??[];const touched=ops.map((o:any)=>Number(o.tensor.match(/layers\.(\d+)/)?.[1]));let s='';
 for(let i=0;i<24;i++){const x=30+(i%12)*79,y=45+Math.floor(i/12)*65;s+=`<rect x="${x}" y="${y}" width="63" height="42" fill="${touched.includes(i)?'#f5b35b':'#50d9e6'}" opacity="${touched.includes(i)?1:.18}"/>`+text(x+31,y+28,String(i),'text-anchor="middle"');}
 s+=text(500,205,'24 transformer blocks · schematic topology, actual intervention indices','text-anchor="middle"');
 if(!stack){s+=text(45,275,'h · 2048')+text(350,260,'SiLU(gate) ⊙ up')+text(400,300,'8192 channels')+text(750,275,'down_proj → 2048')+'<path d="M160 270H330 M590 270H730" stroke="#50d9e6" stroke-width="3"/>';
  for(let i=0;i<64;i++){let selected=ops.some((o:any)=>(o.columns??[]).some((n:number)=>Math.floor(n/128)===i));s+=`<rect x="${70+i*13.5}" y="340" width="10" height="85" fill="${selected?'#f5b35b':'#50d9e6'}" opacity="${selected?1:.2}"/>`;}
  s+=text(500,470,'down_proj columns · 128 channels per displayed bin · exact ops below','text-anchor="middle"');}
 return svg(s,`SmolLM2 schematic 24 blocks, gated MLP 2048 to 8192 to 2048. ${method} candidate ${candidate}: ${ops.length?ops.map((o:any)=>o.tensor+' '+o.kind).join('; '):'no intervention'}.`);
}
export function lmEndpoints(){let s='';for(const [i,task] of ['arc_easy','piqa'].entries()){let b=LM.tasks[task].baseline;let x=70+i*490;s+=text(x,55,task==='arc_easy'?'ARC-Easy':'PIQA')+text(x,165,pct(b.metrics.acc_norm,6),'class="big-number"')+text(x,225,`acc_norm · ${b.paired_minus_baseline.acc_norm.condition_correct} / ${b.n}`)+text(x,300,`Raw acc ${pct(b.metrics.acc,6)}`)+text(x,350,`${b.paired_minus_baseline.acc.condition_correct} / ${b.n} correct`);}s+=text(500,405,'1 executed state · frozen v2','text-anchor="middle"');for(const [i,label] of ['baseline','Sol','Astra','joint'].entries()){const x=140+i*240;s+=`<path d="M500 415V430H${x}V447" stroke="currentColor" opacity=".35" fill="none"/>`+text(x,480,label,'text-anchor="middle"');}return svg(s,'Completed v2 final endpoints: '+['arc_easy','piqa'].map(t=>`${t} acc_norm ${pct(LM.tasks[t].baseline.metrics.acc_norm,6)}, raw acc ${pct(LM.tasks[t].baseline.metrics.acc,6)}`).join('; '));}
export function metricsTable(){return `<table><caption>Adult final · ${num(M.adult.methods.baseline.n)} paired examples</caption><thead><tr><th>State</th><th>BA ↑</th><th>Accuracy ↑</th><th>AUC ↑</th><th>Log-loss ↓</th><th>Brier ↓</th></tr></thead><tbody>${['baseline','Sol','Astra','joint','clean','random','grid'].map(k=>{const a=M.adult.methods[k].metrics;return `<tr><th>${k}</th><td>${pct(a.balanced_accuracy)}</td><td>${pct(a.accuracy)}</td><td>${num(a.roc_auc,6)}</td><td>${num(a.logloss,6)}</td><td>${num(a.brier,6)}</td></tr>`;}).join('')}</tbody></table>`;}
export function workTable(){return `<table><caption>Recorded target work · native units kept separate</caption><thead><tr><th>Phase</th><th>Examples</th><th>Forwards</th><th>Seconds</th><th>Editor calls</th></tr></thead><tbody>${['Sol','Astra','joint'].map(k=>{let c=LM.candidates[k],w=c.target_work;return `<tr><th>LM v2 DEV ${k}</th><td>${num(w.examples)}</td><td>${num(w.forwards)}</td><td>${num(w.wall_seconds)}</td><td>${num(c.editor_calls.recorded)}</td></tr>`}).join('')}<tr><th>LM v2 FINAL · unique state</th><td>${num(LM.assessment_work.examples)}</td><td>${num(LM.assessment_work.forwards)}</td><td>${num(LM.assessment_work.wall_seconds)}</td><td>0</td></tr><tr><th>Adult controls · CPU batches</th><td>${num(M.adult.controls.work.examples)}</td><td>${num(M.adult.controls.work.forwards)}</td><td>${num(M.adult.controls.work.elapsed_seconds,6)}</td><td>${num(M.adult.controls.work.editor_calls)}</td></tr></tbody></table><p>LM forwards are per-choice requests; Adult forwards are batched calls. One LM final state feeds four method labels; it is one observation, not four replications.</p>`;}
export function lmIntervention(method='Sol',candidate=0){
 const c=LM.candidates[method]?.candidates.find((v:any)=>v.index===candidate),ops=c?.patch.ops??[];
 const blocks=[...new Set(ops.map((o:any)=>Number(o.tensor.match(/layers\.(\d+)/)?.[1])))];
 let s=text(260,36,blocks.length?`Block ${blocks.join(', ')} · down_proj`:'Unchanged origin','text-anchor="middle"');
 s+=text(260,76,`${num(c?.stats.count)} changed scalars`,'text-anchor="middle"')+text(260,110,`L2 ${num(c?.stats.norm,8)}`,'text-anchor="middle"');
 const columns=ops.flatMap((o:any)=>o.columns??(o.entries??[]).map((e:number[])=>e[1]));
 for(let i=0;i<64;i++){const selected=columns.some((j:number)=>Math.floor(j/128)===i),x=40+(i%8)*56,y=140+Math.floor(i/8)*44;
  s+=`<rect x="${x}" y="${y}" width="48" height="36" fill="${selected?'#c27b21':'#168a9b'}" opacity="${selected?1:.18}"><title>Columns ${i*128}–${i*128+127}${selected?'; actual operation support present':''}</title></rect>`;}
 s+=text(260,535,'8192 channels · 128 / tile','text-anchor="middle"')+text(260,575,'Exact operations below','text-anchor="middle"');
 return svg(s,`${method} DEV candidate ${candidate}. Actual down_proj operation support binned into 128 channels per tile. ${num(c?.stats.count)} actual changed scalars; norm ${num(c?.stats.norm,8)}.`).replace('0 0 1000 500','0 0 520 600');
}

// Exact row/column coordinates: every cell corresponds to one stored fc2 scalar.
export function fc2Matrix(method='Sol',candidate?:number,mask=false,scalar=0){
 const changes=adultChanges(method,candidate),chosen=changes[scalar%Math.max(changes.length,1)];
 const count=G.permanent_mask.flat().filter(Boolean).length;
 let s=text(70,28,mask?`Permanent fc2 mask · ${count} masked zeros / ${512-count} eligible`:`fc2 patch · ${changes.length} executed scalar changes`);
 for(let r=0;r<16;r++)for(let c=0;c<32;c++){
  const removed=!!G.permanent_mask[r][c],change=changes.find((v:any)=>v.row===r&&v.column===c),active=chosen?.row===r&&chosen?.column===c;
  s+=`<rect data-row="${r}" data-column="${c}" data-masked="${removed}" data-changed="${!!change}" x="${70+c*19}" y="${65+r*22}" width="17" height="19" fill="${removed?'#de8c87':change&&!mask?'#f5b35b':'#50d9e6'}" opacity="${removed||(!mask&&!!change)?1:.24}" ${active&&!mask?'stroke="white" stroke-width="3"':''}><title>fc2[${r}, ${c}] · ${removed?'masked zero':change?`${change.before} → ${change.after}`:'eligible, unchanged'}</title></rect>`;
 }
 for(let c=0;c<32;c+=4)s+=text(78+c*19,52,String(c),'text-anchor="middle"');
 for(let r=0;r<16;r+=3)s+=text(54,80+r*22,String(r),'text-anchor="end"');
 s+=text(365,455,'Column 0–31 → · row 0–15 ↓','text-anchor="middle"');
 if(mask)s+=`<rect data-mask-legend="masked" x="710" y="130" width="18" height="18" fill="#de8c87"/><rect data-mask-legend="eligible" x="710" y="175" width="18" height="18" fill="#50d9e6" opacity=".24"/>`+text(740,145,`Pink: ${count} masked`)+text(740,190,`Teal: ${512-count} eligible`)+text(725,260,'16 × 32 entries')+text(725,305,'Mask never reopens');
 else if(chosen)s+=text(720,115,`fc2[${chosen.row}, ${chosen.column}]`)+text(720,165,'Before · float32')+text(720,202,chosen.before.toPrecision(10))+text(720,267,'After · float32')+text(720,304,chosen.after.toPrecision(10))+text(720,370,'Amber = changed')+text(720,408,'Outline = inspected');
 else s+=text(720,180,'No changed scalars');
 return svg(s,mask?`Adult exact 16 by 32 permanent mask: ${count} masked zeros, ${512-count} eligible entries.`:`Adult ${method} candidate ${candidate}: ${changes.length} changed fc2 scalars, exact float32 before and after.`);
}
