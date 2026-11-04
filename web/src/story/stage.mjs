import * as T from 'three';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {UnrealBloomPass} from 'three/addons/postprocessing/UnrealBloomPass.js';
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js';
import E from './evidence.json' with {type:'json'};
import {adultPositions,adultContextEdges,stagePose,GATED_NODES,GATED_WIDTHS,GATED_PATHS,TRANSFORMER_BLOCKS,sceneGeometry,fitDistance,fitVertices,signalPhase} from './geometry.mjs';
const cyan='#78dbe0',amber='#f5bf67',violet='#b3a2df',dark='#263239';
const v=a=>new T.Vector3(...a);
const ease=t=>{t=Math.max(0,Math.min(1,t));return t*t*(3-2*t)};
function wire(points,color=cyan,opacity=.5,dashed=false){
 const g=new T.BufferGeometry().setFromPoints(points.map(p=>Array.isArray(p)?v(p):p));
 const m=dashed?new T.LineDashedMaterial({color,transparent:true,opacity,dashSize:.13,gapSize:.11,depthWrite:false}):new T.LineBasicMaterial({color,transparent:true,opacity,depthWrite:false});
 const o=new T.Line(g,m);if(dashed)o.computeLineDistances();return o;
}
// Teaser density hierarchy: almost transparent glass fill, antialiased thin rims,
// bright packets only on the active path. DOM annotations are after the bloom pass.
function sheet(w,h,color=cyan){
 const g=new T.Group();
 g.add(new T.Mesh(new T.PlaneGeometry(w,h),new T.MeshBasicMaterial({color,transparent:true,opacity:.022,side:T.DoubleSide,depthWrite:false})));
 g.add(wire([[-w/2,-h/2,0],[w/2,-h/2,0],[w/2,h/2,0],[-w/2,h/2,0],[-w/2,-h/2,0]],color,.65));return g;
}
function points(positions,color=cyan,size=.065){
 const g=new T.BufferGeometry().setFromPoints(positions);
 return new T.Points(g,new T.ShaderMaterial({uniforms:{color:{value:new T.Color(color)},size:{value:size}},transparent:true,depthWrite:false,blending:T.AdditiveBlending,
 vertexShader:`uniform float size;void main(){vec4 p=modelViewMatrix*vec4(position,1.);gl_Position=projectionMatrix*p;gl_PointSize=clamp(size*650./-p.z,2.,12.);}`,
 fragmentShader:`uniform vec3 color;void main(){float r=length(gl_PointCoord-.5)*2.;if(r>1.)discard;float ring=(r-.64)*7.;float rim=exp(-ring*ring);float core=exp(-r*r*24.);gl_FragColor=vec4(color*(1.1+core*1.3),max(rim*.95,core));}`}));
}
export class GlassStage{
 constructor(canvas,overlay){
  this.overlay=overlay;this.renderer=new T.WebGLRenderer({canvas,antialias:true,alpha:false,powerPreference:'low-power'});
  this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));this.renderer.setClearColor(0x000000,1);this.renderer.outputColorSpace=T.SRGBColorSpace;
  this.scene=new T.Scene();this.camera=new T.PerspectiveCamera(37,1,.1,120);
  this.composer=new EffectComposer(this.renderer);this.composer.addPass(new RenderPass(this.scene,this.camera));
  this.composer.addPass(new UnrealBloomPass(new T.Vector2(800,400),.5,.22,.86));this.composer.addPass(new OutputPass());
  this.groups={};this.anchors={};this.paths=[];this.makeNetwork();this.makeMatrices();this.makeMechanism();this.makeTransformer();this.makeGated();this.makeBranches();
  this.packet=points([new T.Vector3()],amber,.11);this.scene.add(this.packet);this.trail=wire([[0,0,0],[0,0,0]],amber,1);this.trail.frustumCulled=false;this.scene.add(this.trail);
  canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();this.onFailure?.();});this.size=[0,0];
 }
 group(name){const g=new T.Group();this.groups[name]=g;this.scene.add(g);this.anchors[name]=[];return g;}
 label(name,text,position,color='',offset=22,screen=null){this.anchors[name].push({text,position:v(position),color,offset,screen});}
 captureVertices(group){
  group.updateWorldMatrix(true,true);const inverse=group.matrixWorld.clone().invert(),vertices=[];
  group.traverse(o=>{const attr=o.geometry?.attributes.position;if(!attr)return;
   const matrix=new T.Matrix4().multiplyMatrices(inverse,o.matrixWorld);
   for(let i=0;i<attr.count;i++)vertices.push(new T.Vector3().fromBufferAttribute(attr,i).applyMatrix4(matrix));
  });
  group.userData.fitVertices=vertices;
 }
 makeNetwork(){
  const name='adult-network',g=this.group(name);this.nodes=adultPositions().map(layer=>layer.map(v));
  const positions=[];
  for(const [l,i,j] of adultContextEdges(E.mask))positions.push(...this.nodes[l][i],...this.nodes[l+1][j]);
  const geo=new T.BufferGeometry();geo.setAttribute('position',new T.Float32BufferAttribute(positions,3));
  g.add(new T.LineSegments(geo,new T.LineBasicMaterial({color:cyan,transparent:true,opacity:.055,depthWrite:false})));
  this.networkPoints=[];
  this.nodes.forEach((layer,i)=>{
   const dots=points(layer,i===3?amber:cyan,.13);this.networkPoints.push(dots);g.add(dots);
   const x=layer[0].x,halfY=[1.8,1.4,.85,.35][i],halfZ=[1.8,1.05,1,.35][i];
   g.add(wire([[x,-halfY,-halfZ],[x,halfY,-halfZ],[x,halfY,halfZ],[x,-halfY,halfZ],[x,-halfY,-halfZ]],cyan,.38));
   this.label(name,['104 inputs','32 · Σ → ReLU','16 · Σ → ReLU','1 · sigmoid → p'][i],[x,-halfY,0],'',0,[[.13,.92],[.38,.92],[.63,.92],[.86,.92]][i]);
  });
  // One real topological route is distinguished from the context connectivity.
  this.networkRoute=[this.nodes[0][52],this.nodes[1][15],this.nodes[2][0],this.nodes[3][0]];
  this.networkEdges=[];for(let i=0;i<3;i++){const edge=wire(this.networkRoute.slice(i,i+2),i===1?amber:cyan,.6);this.networkEdges.push(edge);g.add(edge);}
  this.captureVertices(g);
 }
 makeMatrices(){
  const adult=this.group('adult-matrix');this.adultCells=[];
  const shader=new T.ShaderMaterial({transparent:true,depthWrite:false,side:T.DoubleSide,
   vertexShader:`attribute vec3 tint;varying vec3 c;varying vec2 uv0;void main(){uv0=uv;c=tint;gl_Position=projectionMatrix*modelViewMatrix*instanceMatrix*vec4(position,1.);}`,
   fragmentShader:`varying vec3 c;varying vec2 uv0;void main(){vec2 q=min(uv0,1.-uv0);float d=min(q.x,q.y);float rim=1.-smoothstep(.008,.008+fwidth(d),d);gl_FragColor=vec4(c*(.55+rim*.7),.018+rim*.72);}`});
  const geometry=new T.PlaneGeometry(.265,.25);geometry.setAttribute('tint',new T.InstancedBufferAttribute(new Float32Array(512*3),3));
  this.adultMesh=new T.InstancedMesh(geometry,shader,512);const obj=new T.Object3D();
  for(let r=0;r<16;r++)for(let c=0;c<32;c++){obj.position.set((c-15.5)*.33,(7.5-r)*.33,0);obj.updateMatrix();this.adultMesh.setMatrixAt(r*32+c,obj.matrix);}
  adult.add(this.adultMesh);adult.rotation.y=-.13;
  this.label('adult-matrix','32 incoming activations',[0,-3.05,0]);this.label('adult-matrix','16 rows',[-6,0,0],'',0);
  const lm=this.group('lm-down-projection');this.lmColumns=[];
  // The first 32 columns are explicit; the rest are sampled context. No scalar values.
  for(let c=0;c<64;c++){const x=c<32?-5+c*.085:-1.7+(c-32)*.22;const o=sheet(c<32?.045:.11,4.1);o.position.set(x,0,(c%4)*.035);lm.add(o);this.lmColumns.push(o);}
  lm.rotation.y=-.14;this.label('lm-down-projection','Columns 0…31',[-3.68,-2.55,0],amber);
  this.label('lm-down-projection','Remaining 8,160 · sampled',[1.9,-2.55,0]);
 }
 makeMechanism(){
  const name='adult-computation',g=this.group(name);
  this.mechanismNodes=[[-5.2,1.1,0],[-5.2,0,0],[-5.2,-1.1,0],[-2.7,0,.2],[-.6,0,0],[1.5,0,0],[4.4,0,0]];
  this.mechanismNodes.slice(0,3).forEach(p=>g.add(wire([p,this.mechanismNodes[3]],cyan,.55)));
  g.add(points(this.mechanismNodes.map(v),cyan,.09));g.add(wire(this.mechanismNodes.slice(3),amber,.8));
  const gate=sheet(1.35,1.7);gate.position.set(-.6,0,0);g.add(gate);
  this.label(name,'w × input',[-4,1.5,0],amber);this.label(name,'Σ + bias',[-2.7,-.7,.2]);this.label(name,'ReLU',[-.6,-1,0]);this.label(name,'logit → sigmoid',[3,-.7,0]);
 }
 makeTransformer(){
  const name='transformer-24',g=this.group(name);
  this.blocks=TRANSFORMER_BLOCKS.map(({index,position})=>{
   const block=new T.Group();for(let j=0;j<3;j++){const o=sheet(.95,1.25,index===23?amber:cyan);o.position.z=(j-1)*.16;o.rotation.y=-.18;block.add(o);}
   block.position.copy(v(position));g.add(block);this.label(name,String(index),[position[0],position[1]-.85,position[2]],index===23?amber:'',5);return block;
  });
  const block=this.group('transformer-block');
  const pieces=[['Attention',-4.7],['RMSNorm',-1.7],['Gated MLP',1.6],['Residual +',4.8]];
  pieces.forEach(([text,x],i)=>{const o=sheet(2.1,2.8,i===2?amber:cyan);o.position.set(x,0,i*.2);o.rotation.y=-.18;block.add(o);this.label('transformer-block',text,[x,-1.7,i*.2]);});
  block.add(wire([[-5,0,0],[5,0,.6]],cyan,.55));
 }
 makeGated(){
  const name='gated-mlp',g=this.group(name);this.gatedPaths=[];this.gatedCurves=[];
  for(const path of GATED_PATHS){
   const color=path.kind==='residual'?violet:cyan,bundle=new T.Group(),curves=[];
   // Representational channels show expansion, never scalar coefficients.
   for(let j=0;j<13;j++){
    const lane=(j-6)/6;
    const curve=new T.CatmullRomCurve3(path.nodes.map(key=>{
     const p=v(GATED_NODES[key]),width=GATED_WIDTHS[key];
     p.y+=lane*width;p.z+=Math.sin(j*2.4)*width*.6;return p;
    }),false,'centripetal');
    curves.push(curve);bundle.add(wire(curve.getPoints(64),color,j===6?.9:.38,path.kind==='residual'));
   }
   g.add(bundle);this.gatedPaths.push(bundle);this.gatedCurves.push(curves);
  }
  for(const [key,w,h] of [['norm',.65,.7],['gate',1.1,1.3],['up',1.1,1.3],['silu',.7,1.3],['product',.65,1.3],['down',.85,1.15],['add',.5,.7]]){
   const slab=new T.Group(),color=key==='product'?amber:key==='add'?violet:cyan;
   for(const z of [-.3,0,.3]){const face=sheet(w,h,color);face.position.z=z;slab.add(face);}
   for(const y of [-h/2,h/2])for(const x of [-w/2,w/2])slab.add(wire([[x,y,-.3],[x,y,.3]],color,.4));
   for(let j=0;j<11;j++){
    const y=(j-5)/5*GATED_WIDTHS[key],z=Math.sin(j*2.4)*.19;
    slab.add(wire([[-w/2,y,z],[w/2,y,z]],color,.5));
   }
   slab.position.copy(v(GATED_NODES[key]));g.add(slab);
  }
  this.captureVertices(g);
  this.gatedPackets=points(Array.from({length:39},()=>new T.Vector3()),amber,.15);g.add(this.gatedPackets);
  const labels={input:'x · 2048',norm:'RMSNorm',gate:'gate · 8192',silu:'SiLU(g)',up:'up · 8192',product:'⊙ multiply',down:'down · 2048',add:'+ residual'};
  const callouts={input:[.08,.22],norm:[.23,.66],gate:[.32,.1],silu:[.49,.1],up:[.37,.72],product:[.61,.72],down:[.75,.22],add:[.9,.68]};
  for(const [key,text] of Object.entries(labels)){
   this.label(name,text,GATED_NODES[key],key==='product'?amber:key==='add'?violet:'',0,callouts[key]);
  }
  this.label(name,'Residual x · bypass',[-.5,-2.2,.3],violet,0,[.51,.94]);
  // Compress the explanatory branch spacing, preserving channel topology and
  // depth, so the wide mechanism fits beside readable screen-space callouts.
  g.scale.y=.62;
 }
 makeBranches(){
  const name='editor-branches',g=this.group(name);
  this.branchCenters=[[-5,0,0],[-1.2,1.5,0],[-1.2,-1.5,.2],[4.5,0,0]];
  this.branchCenters.forEach((center,i)=>{
   const b=new T.Group();for(let l=0;l<3;l++){const node=[];for(let j=0;j<4;j++)node.push(new T.Vector3(-.75+l*.75,(j-1.5)*.24,l*.08));b.add(points(node,i===3?amber:cyan,.05));if(l)for(let j=0;j<4;j++)b.add(wire([[-.75+(l-1)*.75,(j-1.5)*.24,(l-1)*.08],[-.75+l*.75,(j-1.5)*.24,l*.08]],cyan,.35));}
   const glass=sheet(2.1,1.4,i===3?amber:cyan);glass.position.z=-.1;b.add(glass);b.position.copy(v(center));g.add(b);this.label(name,['Common origin','Sol · isolated','Astra · isolated','Joint · fresh stage'][i],[center[0],center[1]-.95,center[2]],i===3?amber:'',10);
  });
  for(let i=1;i<=3;i++)g.add(wire([this.branchCenters[0],[-3,0,-.2],this.branchCenters[i]],cyan,i===3?.18:.6));
  this.feedback=[];for(let i=1;i<=2;i++){const o=wire([this.branchCenters[i],[1.5,this.branchCenters[i][1],.3],this.branchCenters[3]],amber,.8,true);g.add(o);this.feedback.push(o);}
 }
 fit(group,p,reduced){
  group.updateWorldMatrix(true,true);const box=group.userData.fitBounds?group.userData.fitBounds.clone().applyMatrix4(group.matrixWorld):new T.Box3().setFromObject(group);
  const name=Object.keys(this.groups).find(key=>this.groups[key]===group);
  for(const label of this.anchors[name])if(!label.screen)box.expandByPoint(group.localToWorld(label.position.clone()));
  const center=box.getCenter(new T.Vector3());
  // View the y/z node planes obliquely; fit their projected bounds rather than
  // assuming all explanatory geometry lies in a flat x/y plane.
  const spatial=['adult-network','gated-mlp','transformer-block'].includes(name);
  const cue=Math.min(3,p.cueIndex),turn=reduced?1:ease(p.progress*3);
  const angles=[.78,.66,.54,.46],from=angles[Math.max(0,cue-1)];
  const oblique=name==='adult-network'?from+(angles[cue]-from)*turn:name==='gated-mlp'?.32+.04*Math.sin((cue-1+turn)*.8):.36;
  const direction=new T.Vector3(spatial?oblique:0,name==='gated-mlp'?.06:spatial?.16:.01,1).normalize();
  this.camera.position.copy(center.clone().add(direction));this.camera.lookAt(center);
  if(group.userData.fitVertices){
   const rotation=this.camera.quaternion.clone(),inverse=rotation.clone().invert();
   const vertices=group.userData.fitVertices.map(point=>group.localToWorld(point.clone()).sub(center).applyQuaternion(inverse).toArray());
   const fitted=fitVertices(vertices,this.camera.aspect);
   const offset=new T.Vector3(fitted.x,fitted.y,0).applyQuaternion(rotation);
   center.add(offset);
   this.camera.position.copy(center.clone().addScaledVector(direction,fitted.distance));
   this.camera.lookAt(center);this.camera.updateMatrixWorld();return;
  }
  const inverse=this.camera.quaternion.clone().invert(),projected=new T.Box3();
  for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z])projected.expandByPoint(new T.Vector3(x,y,z).sub(center).applyQuaternion(inverse));
  const size=projected.getSize(new T.Vector3()),distance=fitDistance(size.x,size.y,size.z,this.camera.aspect);
  const focus=name==='adult-network'?[-.45,-.18,.18,.45][Math.min(3,p.cueIndex)]:0;
  center.x+=focus*(reduced?1:ease(p.progress*4));
  this.camera.position.copy(center.clone().addScaledVector(direction,distance));this.camera.lookAt(center);this.camera.updateMatrixWorld();
 }
 animatePacket(route,u,reduced){
  const progress=Math.min(.999999,Math.max(0,u))*(route.length-1),i=Math.floor(progress),t=progress-i;
  const a=Array.isArray(route[i])?v(route[i]):route[i],b=Array.isArray(route[i+1])?v(route[i+1]):route[i+1];
  const tip=a.clone().lerp(b,reduced?1:t),tail=a.clone().lerp(b,reduced?0:Math.max(0,t-.2));
  this.packet.position.copy(tip);this.packet.visible=!reduced;this.trail.visible=true;
  const pos=this.trail.geometry.getAttribute('position');pos.setXYZ(0,tail.x,tail.y,tail.z);pos.setXYZ(1,tip.x,tip.y,tip.z);pos.needsUpdate=true;
 }
 render(p,reduced){
  p=stagePose(p,reduced);
  const canvas=this.renderer.domElement,{scene}=p.chapter,k=p.cueIndex,name=sceneGeometry(scene,k),group=this.groups[name];
  // Restore visibility and the scene's layout before measuring a previously hidden canvas.
  canvas.hidden=!group||scene==='article'&&k<2;this.overlay.hidden=canvas.hidden;
  if(canvas.hidden){this.frameKey='';return;}
  const arithmetic=name==='adult-computation';canvas.classList.toggle('mechanism',arithmetic);this.overlay.classList.toggle('mechanism',arithmetic);
  const w=canvas.clientWidth,h=canvas.clientHeight;if(!w||!h){this.frameKey='';return;}
  const key=`${reduced?`${p.chapter.index}:${p.cueIndex}`:p.t}:${reduced}:${w}:${h}`;if(key===this.frameKey)return;this.frameKey=key;
  if(w!==this.size[0]||h!==this.size[1]){this.size=[w,h];this.renderer.setSize(w,h,false);this.composer.setSize(w,h);this.camera.aspect=w/h;this.camera.updateProjectionMatrix();}
  Object.values(this.groups).forEach(g=>g.visible=g===group);this.packet.visible=false;this.trail.visible=false;
  this.fit(group,p,reduced);
  if(name==='adult-computation'){
   // Deterministic camera settlement follows the explained sum, rectifier and output.
   const centers=scene==='edit'?[-.4,-3.4,-2.7,2.6]:[-.4,-2.7,-.6,2.6,-.4];
   const focus=centers[Math.min(k,centers.length-1)],previous=centers[Math.max(0,k-1)];
   const settle=reduced?1:ease(p.progress*5),wide=this.camera.position.z;
   const close=fitDistance(7,3,.4,this.camera.aspect),overview=i=>i===0||scene==='neuron'&&i===4;
   const from=overview(Math.max(0,k-1))?wide:close,to=overview(k)?wide:close;
   const x=previous+(focus-previous)*settle;
   this.camera.position.set(x,.15,from+(to-from)*settle);this.camera.lookAt(x,0,0);this.camera.updateMatrixWorld();
  }
  if(name==='transformer-24'){
   // The overview ends by traveling to the last block, which opens in the next cue.
   const approach=reduced?0:ease((p.progress-.65)/.35),target=this.blocks[23].position;
   const wide=this.camera.position.clone(),close=target.clone().add(new T.Vector3(0,.15,4.3));
   this.camera.position.lerpVectors(wide,close,approach);this.camera.lookAt(target.clone().multiplyScalar(approach));this.camera.updateMatrixWorld();
  }
  if(name==='adult-network'){
   const {layer,u}=signalPhase(p,reduced);const route=k===0?[this.nodes[0][48],this.nodes[0][52]]:this.networkRoute.slice(layer,layer+2);
   this.networkPoints?.forEach((o,i)=>o.material.uniforms.color.value.set(i===(k===0?0:layer+1)?amber:cyan));
   this.networkEdges.forEach((edge,i)=>{const active=k>0&&i===layer;edge.material.opacity=active?1:.24;edge.material.color.set(active?amber:cyan);});this.animatePacket(route,u,reduced);
  }
  if(name==='adult-matrix'){
   const tint=this.adultMesh.geometry.getAttribute('tint');
   for(let r=0;r<16;r++)for(let c=0;c<32;c++){
    const changed=E.changes.some(d=>d.row===r&&d.column===c),edited=scene==='edit'||p.chapter.index===10&&k>0;
    tint.setXYZ(r*32+c,...new T.Color(E.mask[r][c]?dark:edited&&changed?amber:cyan).toArray());
   }tint.needsUpdate=true;
  }
  if(name==='adult-computation')this.animatePacket([this.mechanismNodes[scene==='edit'?1:Math.min(2,k)],...this.mechanismNodes.slice(3)],p.progress,reduced);
  if(name==='lm-down-projection'){
   this.lmColumns.forEach((o,c)=>o.traverse(n=>{if(n.material){n.material.color?.set(c<32&&k>0?amber:cyan);}}));
  }
  if(name==='gated-mlp'){
   const active=scene==='transformer'?[1,2,3]:[[0],[1,2],[1,2],[3],[3,4]][Math.min(4,k)];
   this.gatedPaths.forEach((o,i)=>o.children.forEach((line,j)=>{line.material.opacity=active.includes(i)?(j===6?1:.7):.2;}));
   const attr=this.gatedPackets.geometry.getAttribute('position');
   for(let i=0;i<attr.count;i++){
    const path=active[Math.floor(i/13)%active.length],curve=this.gatedCurves[path][i%13];
    const u=reduced?.65:((p.progress*2+Math.floor(i/(13*active.length))/3)%1);
    const point=curve.getPoint(u);attr.setXYZ(i,point.x,point.y,point.z);
   }
   attr.needsUpdate=true;this.gatedPackets.geometry.computeBoundingSphere();
  }
  if(name==='transformer-24'){
   const idx=Math.min(23,Math.floor(p.progress*24));this.animatePacket([this.blocks[idx].position.clone().add(new T.Vector3(0,-.6,.4)),this.blocks[idx].position.clone().add(new T.Vector3(0,.6,.4))],(p.progress*24)%1,reduced);
  }
  if(name==='editor-branches'){
   const history=k>=2||p.chapter.index===14&&k>=1;this.feedback.forEach(o=>o.visible=history);
   const route=!history?[this.branchCenters[0],this.branchCenters[k+1]]:[this.branchCenters[k%2+1],[1.5,0,.3],this.branchCenters[3]];this.animatePacket(route,p.progress,reduced);
  }
  this.composer.render();this.annotate(name,group);
 }
 annotate(name,group){
  const labels=this.anchors[name];if(this.labelKey!==name){
   this.overlay.replaceChildren(...labels.map(()=>document.createElement('span')));
   this.leaders=document.createElementNS('http://www.w3.org/2000/svg','svg');this.leaders.classList.add('anchor-leaders');
   this.leaders.setAttribute('viewBox','0 0 1000 1000');this.leaders.setAttribute('preserveAspectRatio','none');
   labels.forEach(()=>this.leaders.append(document.createElementNS('http://www.w3.org/2000/svg','line')));
   this.overlay.append(this.leaders);this.labelKey=name;
  }
  labels.forEach((label,i)=>{
   const pt=group.localToWorld(label.position.clone()).project(this.camera),el=this.overlay.children[i];
   const x=pt.x*.5+.5,y=-pt.y*.5+.5,[lx,ly]=label.screen||[x,y];
   el.hidden=pt.x<-.98||pt.x>.98||pt.y<-.98||pt.y>.98||pt.z>1;
   el.textContent=label.text;el.style.left=`${lx*100}%`;el.style.top=`${ly*100}%`;el.style.color=label.color;el.style.marginTop=`${label.offset}px`;
   const line=this.leaders.children[i];line.style.display=label.screen&&!el.hidden?'':'none';
   for(const [key,value] of Object.entries({x1:x*1000,y1:y*1000,x2:lx*1000,y2:(ly+(ly<y?.025:-.025))*1000}))line.setAttribute(key,value);
   line.style.stroke=label.color||cyan;
  });
 }
 dispose(){this.composer.dispose();this.scene.traverse(o=>{o.geometry?.dispose();o.material?.dispose();});this.renderer.dispose();}
}
