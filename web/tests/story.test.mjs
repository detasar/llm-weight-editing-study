import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {chapters,CUES,DURATION} from '../src/story/chapters.mjs';
import {PresentationClock,poseAt,escapeHTML,safeJSON} from '../src/story/timeline.mjs';
import {packHTML,imageMime,normalizeImageURL} from '../src/story/packaging.mjs';
import {illustration} from '../src/story/math.mjs';
import {figure,evidenceText,I} from '../src/story/figures.mjs';
import * as T from 'three';
import {GlassStage} from '../src/story/stage.mjs';
import {adultPositions,adultContextEdges,TRANSFORMER_BLOCKS,GATED_NODES,GATED_WIDTHS,GATED_PATHS,sceneGeometry,fitDistance,signalPhase} from '../src/story/geometry.mjs';
const web=new URL('../',import.meta.url),repo=new URL('../../',import.meta.url);
const json=url=>JSON.parse(readFileSync(url,'utf8'));
const E=json(new URL('src/story/evidence.json',web));
const M=json(new URL('data/manifest.json',repo));
const G=json(new URL('data/adult_graph.json',repo));

test('hidden canvas restores drawing and current anchors across scene, fallback and clock transitions',()=>{
 for(const reduced of [false,true]){
  let flat=false,renders=0,anchors=null;
  const classes=()=>({toggle(){}});
  const canvas={hidden:false,classList:classes(),get clientWidth(){return this.hidden||flat?0:1200;},get clientHeight(){return this.hidden||flat?0:600;}};
  const group={},stage=Object.assign(Object.create(GlassStage.prototype),{
   renderer:{domElement:canvas,setSize(w,h){assert.equal(w,1200);assert.equal(h,600);}},
   composer:{setSize(){},render(){renders++;}},camera:{updateProjectionMatrix(){}},
   overlay:{hidden:false,classList:classes()},size:[0,0],groups:{'adult-network':group},
   packet:{},trail:{},networkEdges:[],nodes:[[]],networkRoute:[0,1,2,3],
   fit(g){assert.equal(g,group);},animatePacket(){},annotate(name,g){anchors={name,g};}
  });
  const chapter=scene=>chapters.find(c=>c.scene===scene);
  const network=chapter('network'),article=chapter('article'),table=chapter('adult-results');
  const draw=t=>stage.render(poseAt(t),reduced);
  const visible=(t,changed=true)=>{const before=renders;draw(t);assert.equal(canvas.hidden,false);assert.equal(stage.overlay.hidden,false);assert.deepEqual(stage.size,[1200,600]);if(changed)assert.ok(renders>before);assert.deepEqual(anchors,{name:'adult-network',g:group});};
  draw(0);assert.equal(canvas.hidden,true);visible(network.start);
  draw(table.start);assert.equal(canvas.hidden,true);visible(network.start);
  draw(article.start);assert.equal(canvas.hidden,true);visible(article.cues[2].start);
  flat=true;draw(network.start);assert.equal(canvas.clientWidth,0);
  flat=false;visible(network.start);
  const clock=new PresentationClock();clock.seek(network.start);clock.play();clock.tick(0);clock.tick(1000);visible(clock.time,false);
  clock.pause();draw(clock.time);clock.seek(table.start);draw(clock.time);clock.seek(network.start);visible(clock.time);
  clock.play();clock.tick(2000);clock.tick(3000);visible(clock.time,false);
  clock.replay();draw(clock.time);assert.equal(canvas.hidden,true);clock.seek(network.start);visible(clock.time);
 }
});

test('paper theme binds inherited text to its own ink with readable result-page contrast',()=>{
 const css=readFileSync(new URL('src/story/style.css',web),'utf8');
 const rules=selector=>[...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].filter(m=>m[1].trim()===selector).map(m=>m[2]).join(';');
 assert.match(rules('#presentation'),/(?:^|;)\s*color\s*:\s*var\(--ink\)\s*(?:;|$)/);
 const paper=rules('#presentation.paper');
 const hex=name=>{const match=paper.match(new RegExp(`${name}:#([0-9a-f]{6})`,'i'));assert.ok(match);return match[1];};
 const luminance=hex=>{const rgb=hex.match(/../g).map(c=>parseInt(c,16)/255).map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4);return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722;};
 const background=luminance(hex('--bg'));
 for(const ink of ['--ink','--muted'])assert.ok((background+.05)/(luminance(hex(ink))+.05)>=4.5,ink);
});

test('one continuous 2700-second composition, 33 substantive chapters, cues every 20 seconds',()=>{
 assert.equal(DURATION,2700);assert.equal(chapters.length,33);assert.equal(CUES.length,135);
 let end=0;for(const ch of chapters){assert.equal(ch.start,end);assert.ok(ch.cues.length>=4);const labels=new Set();for(const cue of ch.cues){assert.equal(cue.start,end);assert.equal(cue.end-cue.start,20);assert.ok(cue.narration.length>65);labels.add(cue.label);end=cue.end;}assert.equal(labels.size,ch.cues.length);assert.equal(ch.duration,ch.cues.length*20);}assert.equal(end,DURATION);
});
test('exact seeking semantics on both sides of every chapter and cue boundary',()=>{
 for(const ch of chapters){assert.equal(poseAt(ch.start).chapter.index,ch.index);if(ch.index)assert.equal(poseAt(ch.start-1e-6).chapter.index,ch.index-1);for(const cue of ch.cues){assert.equal(poseAt(cue.start).cue,cue);assert.equal(poseAt(cue.end-1e-6).cue,cue);}}
 assert.equal(poseAt(-100).t,0);assert.equal(poseAt(Infinity).t,0);assert.equal(poseAt(NaN).t,0);assert.equal(poseAt(9999).t,2700);assert.equal(poseAt(2700).chapter.index,32);assert.equal(poseAt(2700).cueIndex,3);
});
test('clock starts paused, pause/resume excludes paused time, seek and replay reset elapsed origin',()=>{
 const c=new PresentationClock();c.tick(100);c.tick(1100);assert.equal(c.time,0);c.play();c.tick(1200);c.tick(2200);assert.equal(c.time,1);c.pause();c.tick(10000);assert.equal(c.time,1);c.play();c.tick(11000);c.tick(11500);assert.equal(c.time,1.5);c.seek(2699);c.tick(12000);c.tick(15000);assert.equal(c.time,2700);assert.equal(c.playing,false);c.play();assert.equal(c.time,0);c.tick(20000);c.tick(20250);assert.equal(c.time,.25);c.replay();assert.equal(c.time,0);assert.equal(c.playing,true);c.seek(-1);assert.equal(c.time,0);
});
test('linear playback and arbitrary seek yield the same semantic pose including final frame',()=>{
 const c=new PresentationClock();c.play();c.tick(0);for(let t=0;t<=2700;t+=.5){c.tick(t*1000);assert.deepEqual(poseAt(c.time),poseAt(t));}
 assert.equal(c.playing,false);
});
test('frozen scientific inputs remain hash-identical and selective evidence binds manifest, graph and patches',()=>{
 for(const [name,hash] of Object.entries(E.hashes)){const bytes=readFileSync(new URL('data/'+name,repo));assert.equal(createHash('sha256').update(bytes).digest('hex'),hash,name);}
 assert.deepEqual(E.root,G.root);assert.deepEqual(E.mask,G.permanent_mask);assert.deepEqual(E.changes,G.variants.Sol.changes);
 for(const n of ['baseline','Sol','Astra','joint','clean','random','grid'])assert.deepEqual(E.adult.methods[n],M.adult.methods[n]);
 assert.deepEqual(E.adult.contrasts,M.adult.contrasts);
 assert.equal(E.mask.flat().filter(Boolean).length,256);assert.equal(E.changes.length,16);assert.ok(E.changes.every(c=>!E.mask[c.row][c.column]));
 assert.equal(E.adult.soloBudget,10);assert.equal(E.adult.jointBudget,5);
});
test('real-weight synthetic multiplication uses nonzero column 15 and propagates all actual deltas',()=>{
 const v=illustration(E),c=E.changes.find(c=>c.column===15);assert.ok(v.before.h1[15]>0);assert.equal(c.before,E.root['fc2.weight'][0][15]);assert.ok(Math.abs((v.after.z2[0]-v.before.z2[0])-v.deltaZ[0])<1e-12);assert.notEqual(v.after.p,v.before.p);assert.ok(Number.isFinite(c.after*v.before.h1[15]));
});
test('actual paired decisions bind saved probabilities and preserve the 0.5 rule',()=>{
 const predictions=json(new URL('data/adult_predictions.json',repo));
 // Structure is independently addressed below rather than recreating feature activations.
 assert.ok(predictions);for(const item of Object.values(E.cases)){assert.ok(item.before<.5);assert.ok(item.after>=.5);assert.ok([53,76].includes(item.order));}
 for(const item of Object.values(E.cases)){assert.equal(predictions.methods.baseline.probabilities[item.order],item.before);assert.equal(predictions.methods.Sol.probabilities[item.order],item.after);assert.equal(predictions.methods.baseline.labels[item.order],item.truth);}
 const counts=E.adult.contrasts.Sol_minus_baseline.paired_counts;assert.equal(counts.by_class['1'].n,3846);assert.equal(counts.by_class['0'].n,12435);assert.equal(counts.rescues,65);assert.equal(counts.regressions,102);assert.ok(Math.abs((65/3846-102/12435)/2-E.adult.contrasts.Sol_minus_baseline.difference)<1e-14);
});
test('LM v2 exact scored indices, candidate geometry, no-op identities, and final numerators',()=>{
 const v2=M.lm.versions.v2;assert.equal(M.lm.main_version,'v2');assert.equal(E.lm.scene.scalar_samples,null);
 assert.equal(E.lm.candidate.stats.count,65536);assert.equal(E.lm.candidate.stats.norm,13.910684498150486);
 assert.deepEqual(E.lm.candidate,v2.candidates.Astra.candidates.find(c=>c.index===1));
 const op=E.lm.candidate.patch.ops[0];assert.equal(op.tensor,'model.layers.23.mlp.down_proj.weight');assert.equal(op.factor,.5);assert.equal(op.kind,'scale_columns');assert.deepEqual(op.columns,Array.from({length:32},(_,i)=>i));
 assert.ok(chapters.find(c=>c.scene==='lm-candidate').caption.includes('Astra candidate 1'));
 assert.deepEqual(E.lm.trajectories.joint.map(x=>x.index),[0,2,3,4,5]);
 for(const name of ['Sol','Astra','joint'])assert.deepEqual(E.lm.trajectories[name],v2.candidates[name].candidates.map(c=>({index:c.index,score:c.metrics.acc_norm})));
 for(const name of ['Sol','Astra'])assert.deepEqual(E.lm.trajectories[name].map(x=>x.index),[0,1,2,3,4,5]);
 assert.equal(new Set(Object.values(E.lm.frozen).map(v=>v.executed_weight_sha256)).size,1);
 for(const frozen of Object.values(E.lm.frozen))assert.deepEqual(frozen.patch.ops,[]);
 for(const [task,n,norm,raw] of [['arc_easy',512,376,396],['piqa',256,201,205]])for(const method of ['baseline','Sol','Astra','joint']){const v=E.lm.tasks[task][method];assert.deepEqual(v,v2.tasks[task][method]);assert.equal(v.n,n);assert.equal(v.metrics.acc_norm,norm/n);assert.equal(v.metrics.acc,raw/n);}
});
test('every cue renders a substantive 2D explanation and glass overlay deterministically',()=>{
 for(const cue of CUES)for(const fallback of [false,true]){const p=poseAt(cue.start+5);const html=figure(p,fallback);assert.ok(html.length>100);assert.ok(!/NaN|undefined|Infinity/.test(html),p.chapter.title);assert.equal(html,figure(p,fallback));}
});
test('offline packager neutralizes closing tags, retains literal dollar strings, and uses a classic script',()=>{
 const t=readFileSync(new URL('story.html',web),'utf8');const out=packHTML(t,'console.log("</script><img src=x>","$&")','p::after{content:"</style>"}');assert.ok(!out.includes('type="module"'));assert.ok(!out.includes('src="./src/story'));assert.ok(out.includes('<\\/script>'));assert.ok(out.includes('<\\/style>'));assert.ok(out.includes('"$&"'));assert.equal(escapeHTML('<x a="&">'), '&lt;x a=&quot;&amp;&quot;&gt;');assert.ok(!safeJSON({x:'</script>\u2028'}).includes('<'));assert.throws(()=>packHTML('', '', ''));
});
test('asset sources, installed fonts and IIFE packaging are explicit and available without runtime network',()=>{
 for(const name of ['weight-space-hero.png','reference-article-title.png']){const b=readFileSync(new URL('public/story-assets/'+name,web));assert.equal(imageMime(b),name.startsWith('reference')?'image/jpeg':'image/png');const source=`data:image/png;base64,${b.toString('base64')}`;const actual=normalizeImageURL(source);assert.ok(actual.startsWith(`data:${imageMime(b)};base64,`));assert.deepEqual(Buffer.from(actual.split(',')[1],'base64'),b);}
 const source=readFileSync(new URL('src/story/main.mjs',web),'utf8');assert.ok(!/\bfetch\s*\(|import\s*\(/.test(source));assert.ok(source.includes('weight-space-hero.png?inline'));assert.ok(source.includes('reference-article-title.png?inline'));
 const css=readFileSync(new URL('src/story/style.css',web),'utf8');for(const match of css.matchAll(/url\('([^']+)'\)/g))assert.ok(existsSync(new URL(match[1],new URL('src/story/style.css',web))));
 const build=readFileSync(new URL('build-story.mjs',web),'utf8');assert.ok(build.includes("formats:['iife']"));assert.ok(build.includes('inlineDynamicImports:true'));assert.ok(build.includes('assetsInlineLimit:Infinity'));
});

test('scene geometry separates Adult tensors, LM tensors, transformer, product and history paths',()=>{
 assert.deepEqual(adultPositions().map(a=>a.length),[104,32,16,1]);
 const input=adultPositions()[0];assert.equal(new Set(input.map(p=>p[1])).size,13);assert.equal(new Set(input.map(p=>p[2])).size,8);
 for(const layer of adultPositions())assert.equal(new Set(layer.map(p=>p.join(','))).size,layer.length);
 assert.equal(TRANSFORMER_BLOCKS.length,24);assert.deepEqual(TRANSFORMER_BLOCKS.map(b=>b.index),Array.from({length:24},(_,i)=>i));
 assert.equal(new Set(TRANSFORMER_BLOCKS.map(b=>b.position.join(','))).size,24);
 const incoming=GATED_PATHS.filter(p=>p.nodes.at(-1)==='product');assert.equal(incoming.length,2);
 assert.ok(incoming.some(p=>p.nodes.includes('silu')));assert.ok(incoming.some(p=>p.nodes.includes('up')));
 const bypass=GATED_PATHS.find(p=>p.kind==='residual');assert.deepEqual(bypass.nodes,['input','bypassA','bypassB','add']);assert.ok(!bypass.nodes.includes('product'));
 for(const p of GATED_PATHS)for(const key of p.nodes)assert.ok(GATED_NODES[key]);
 assert.equal(sceneGeometry('matrix'),'adult-matrix');assert.equal(sceneGeometry('lm-candidate'),'lm-down-projection');
 assert.equal(sceneGeometry('transformer',0),'transformer-24');assert.equal(sceneGeometry('transformer',2),'gated-mlp');
 assert.equal(sceneGeometry('gated'),'gated-mlp');assert.equal(sceneGeometry('branches'),'editor-branches');
});
test('WebGL owns each diagram; fallback alone supplies the separate 2D drawing',()=>{
 for(const scene of ['network','matrix','transformer','gated','lm-matrix','lm-candidate','branches']){
  const ch=chapters.find(c=>c.scene===scene),p=poseAt(ch.start+25);
  assert.ok(!figure(p,false).includes('<svg'),scene);assert.ok(figure(p,true).includes('<svg'),scene);
 }
 const ch=chapters.find(c=>c.title==='Follow the forward pass');
 const a=poseAt(ch.start+41),b=poseAt(ch.start+49);
 assert.equal(signalPhase(a).layer,1);assert.notEqual(signalPhase(a).u,signalPhase(b).u);
 assert.deepEqual(signalPhase(a,true),signalPhase(b,true));
 for(const aspect of [1257*.9/(740*.54),1920*.9/(1000*.54)]){
  const d=fitDistance(12.8,4.35,1.4,aspect),tan=Math.tan(37*Math.PI/360),near=d-.7;
  assert.ok(12.8/(2*near*tan*aspect)<=.78);assert.ok(4.35/(2*near*tan)<=.76);
 }
});
test('signature validation rejects unsupported bytes and credits bind exact hero/title bytes',()=>{
 assert.throws(()=>imageMime(Buffer.from('not an image')));
 const credits=json(new URL('public/story-assets/credits.json',web));assert.ok(!('gated-flow-concept.png' in credits));
 for(const name of ['weight-space-hero.png','reference-article-title.png'])assert.equal(createHash('sha256').update(readFileSync(new URL('public/story-assets/'+name,web))).digest('hex'),credits[name].sha256);
 const build=readFileSync(new URL('build-story.mjs',web),'utf8');assert.ok(build.includes('../artifacts/bbva-research/START_PRESENTATION.html'));
});


test('reduced render is identical after playback, direct seek and a forced redraw within a cue',()=>{
 // Exercise the actual stage/cache/material/camera path using Three geometry,
 // with only the browser surface and GPU submission replaced.
 const make=()=>{
  const stage=Object.assign(Object.create(GlassStage.prototype),{
   scene:new T.Scene(),groups:{},anchors:{},size:[0,0],
   camera:new T.PerspectiveCamera(37,2,.1,120),
   renderer:{domElement:{clientWidth:1200,clientHeight:600,classList:{toggle(){}}},setSize(){}},
   composer:{setSize(){},render(){}},overlay:{classList:{toggle(){}}},
   packet:new T.Object3D(),trail:new T.Line(new T.BufferGeometry().setFromPoints([new T.Vector3(),new T.Vector3()])),
   annotate(){}
  });
  stage.makeTransformer();stage.makeNetwork();stage.makeGated();return stage;
 };
 const snapshot=s=>({
  camera:[...s.camera.position.toArray(),...s.camera.quaternion.toArray()],
  paths:s.gatedPaths.map(g=>g.children.map(o=>o.material.opacity)),
  packets:Array.from(s.gatedPackets.geometry.attributes.position.array),
  network:s.networkPoints.map(o=>o.material.uniforms.color.value.toArray()),
  edges:s.networkEdges.map(o=>[o.material.opacity,...o.material.color.toArray()]),
  tip:s.packet.position.toArray(),trail:Array.from(s.trail.geometry.attributes.position.array),
  visible:Object.values(s.groups).map(g=>g.visible)
 });
 const transformer=chapters.find(c=>c.scene==='transformer'),gated=chapters.find(c=>c.scene==='gated'),network=chapters.find(c=>c.scene==='network');
 for(const cue of [transformer.cues[0],transformer.cues[2],...gated.cues,...network.cues]){
  const playback=make(),seek=make(),t=cue.start+17;
  playback.render(poseAt(cue.start),true);playback.render(poseAt(t),true);
  seek.render(poseAt(t),true);
  assert.deepEqual(snapshot(playback),snapshot(seek),`${cue.label}: playback versus seek`);
  playback.frameKey='';playback.render(poseAt(t),true);
  assert.deepEqual(snapshot(playback),snapshot(seek),`${cue.label}: redraw`);
 }
});

test('real projected Adult and gated vertices fill the stage without clipping or label collisions',()=>{
 const stage=Object.assign(Object.create(GlassStage.prototype),{
  scene:new T.Scene(),groups:{},anchors:{},camera:new T.PerspectiveCamera(37,1,.1,120)
 });
 stage.makeNetwork();stage.makeGated();
 // Actual canvas dimensions at the two review viewports, plus the wider rail layout.
 for(const [viewport,width,height] of [[1274,1146,408],[1920,1728,550]]){
  stage.camera.aspect=width/height;stage.camera.updateProjectionMatrix();
  for(const [scene,name] of [['network','adult-network'],['gated','gated-mlp']]){
   const group=stage.groups[name],chapter=chapters.find(c=>c.scene===scene);
   for(const cue of chapter.cues)for(const progress of [0,.15,.5,1])for(const reduced of [false,true]){
    stage.fit(group,{...poseAt(cue.start),progress},reduced);
    const projected=group.userData.fitVertices.map(p=>group.localToWorld(p.clone()).project(stage.camera));
    const xs=projected.map(p=>p.x),ys=projected.map(p=>p.y);
    const fill=(Math.max(...xs)-Math.min(...xs))/2;
    assert.ok(fill>=.7&&fill<=.85,`${name}: width ${fill}`);
    assert.ok(projected.every(p=>Math.abs(p.x)<=.85&&Math.abs(p.y)<=.85&&p.z>-1&&p.z<1),`${name}: clipped`);
    // Conservative text boxes: 0.75em per character and 1.4em line height.
    // This checks explicit callout spacing; the coordinator checks actual font rendering.
    const font=Math.min(23,Math.max(14,viewport*.013));
    const boxes=stage.anchors[name].map(a=>({x:a.screen[0]*width,y:a.screen[1]*height,w:a.text.length*font*.75,h:font*1.4}));
    boxes.forEach((a,i)=>{
     assert.ok(a.x-a.w/2>=0&&a.x+a.w/2<=width&&a.y-a.h/2>=0&&a.y+a.h/2<=height);
     for(const b of boxes.slice(i+1))assert.ok(Math.abs(a.x-b.x)>(a.w+b.w)/2+8||Math.abs(a.y-b.y)>(a.h+b.h)/2+4,`${name}: labels overlap`);
    });
   }
  }
 }
});

test('point rim shader squares by multiplication with a finite luminous core across the sprite',()=>{
 const stage=Object.assign(Object.create(GlassStage.prototype),{scene:new T.Scene(),groups:{},anchors:{}});
 stage.makeNetwork();
 const shader=stage.networkPoints[0].material.fragmentShader;
 assert.match(shader,/float ring=\(r-\.64\)\*7\.;float rim=exp\(-ring\*ring\)/);
 assert.ok(!shader.includes('pow('));
 // CPU range check only; no claim of GPU driver execution.
 for(let i=0;i<=1000;i++){
  const r=i/1000,ring=(r-.64)*7,rim=Math.exp(-ring*ring),core=Math.exp(-r*r*24),alpha=Math.max(rim*.95,core);
  assert.ok(Number.isFinite(alpha)&&alpha>=0&&alpha<=1);
  if(i===0)assert.equal(alpha,1);
 }
});

test('Adult layers occupy separate depth planes and context never invents a masked edge',()=>{
 const layers=adultPositions();
 layers.forEach((layer,i)=>{
  assert.equal(new Set(layer.map(p=>p[0])).size,1);
  if(i<3){assert.ok(new Set(layer.map(p=>p[1])).size>1);assert.ok(new Set(layer.map(p=>p[2])).size>1);}
  if(i)assert.ok(layer[0][0]-layers[i-1][0][0]>3);
 });
 const edges=adultContextEdges(E.mask);
 assert.ok(edges.length<100);assert.ok(edges.length>0);
 for(const [l,i,j] of edges){assert.ok(layers[l][i]);assert.ok(layers[l+1][j]);if(l===1)assert.equal(E.mask[j][i],false);}
 assert.equal(E.mask[0][15],false,'highlighted route uses an eligible connection');
 assert.ok(GATED_WIDTHS.gate>GATED_WIDTHS.norm);assert.ok(GATED_WIDTHS.product>GATED_WIDTHS.down);
 assert.notEqual(GATED_NODES.gate[2],GATED_NODES.up[2]);
});

test('main metrics are rounded while evidence retains exact saved and synthetic values',()=>{
 const ch=chapters.find(c=>c.scene==='adult-results'),html=figure(poseAt(ch.cues.at(-1).start),false);
 assert.ok(html.includes((100*E.adult.methods.baseline.metrics.balanced_accuracy).toFixed(2)+'%'));
 assert.ok(!html.includes((100*E.adult.methods.baseline.metrics.balanced_accuracy).toFixed(6)+'%'));
 const exact=evidenceText();assert.ok(exact.includes(String(E.cases.rescue.before)));assert.ok(exact.includes(String(E.adult.methods.baseline.metrics.balanced_accuracy)));assert.ok(exact.includes(String(I.before.p)));
});
