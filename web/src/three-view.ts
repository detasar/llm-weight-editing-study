import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {G,LM,adultChanges} from './data';

// Geometry explains topology only. No mesh intensity encodes an unrecorded activation.
export function mountThree(host:HTMLElement,kind:string,method:string,candidate:number,motion:()=>boolean,scalar=0):(()=>void)|null{
 let renderer:T.WebGLRenderer;
 try{renderer=new T.WebGLRenderer({antialias:true,alpha:false});}catch{return null;}
 renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor('#071626');renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.35;
 host.append(renderer.domElement);renderer.domElement.setAttribute('aria-label','Interactive schematic geometry. Drag to orbit; scroll to zoom. Exact topology labels are in the adjacent label band; operations are in the inspector.');renderer.domElement.setAttribute('role','img');
 const scene=new T.Scene(),camera=new T.PerspectiveCamera(35,1,.1,100);camera.position.set(3,3,18);camera.lookAt(0,0,0);
 const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=false;controls.minDistance=3;controls.maxDistance=60;controls.maxPolarAngle=Math.PI*.8;controls.saveState();
 const group=new T.Group();scene.add(group);scene.add(new T.AmbientLight('#98c8df',1.8));
 const key=new T.DirectionalLight('#d6f8ff',4);key.position.set(3,7,8);scene.add(key);const rim=new T.PointLight('#50d9e6',55,30);rim.position.set(-5,1,-3);scene.add(rim);
 const mat=(color:string)=>new T.MeshStandardMaterial({color,emissive:color,emissiveIntensity:.3,roughness:.32,metalness:.25});
 const cyan=mat('#50d9e6'),amber=mat('#f5b35b'),instanceMat=new T.MeshStandardMaterial({color:'#ffffff',emissive:'#0e3037',emissiveIntensity:.35,roughness:.3,metalness:.25});
 const segments=(pairs:T.Vector3[][],color:string,opacity:number)=>{if(!pairs.length)return;const geo=new T.BufferGeometry().setFromPoints(pairs.flat());group.add(new T.LineSegments(geo,new T.LineBasicMaterial({color,transparent:true,opacity})));};
 const reveal:T.Object3D[]=[];let focus=new T.Vector3();
 if(['network','mask','scalar'].includes(kind)){
  const ns:number[]=G.architecture.layers,changes=adultChanges(method,candidate),chosen=changes[scalar%Math.max(changes.length,1)];
  const point=(l:number,i:number)=>{const cols=[8,4,4,1][l],rows=Math.ceil(ns[l]/cols);return new T.Vector3(-8.7+l*5.8,(rows-1)/2*.2-Math.floor(i/cols)*.2,((i%cols)-(cols-1)/2)*.4);};
  ns.forEach((n,l)=>{
   const nodes=new T.InstancedMesh(new T.SphereGeometry(l===0?.055:.1,16,12),instanceMat,n),matrix=new T.Matrix4();
   for(let i=0;i<n;i++){matrix.makeTranslation(...point(l,i).toArray());nodes.setMatrixAt(i,matrix);const active=chosen&&((l===1&&i===chosen.column)||(l===2&&i===chosen.row));nodes.setColorAt(i,new T.Color(active?'#f5b35b':'#50d9e6'));}
   nodes.instanceMatrix.needsUpdate=true;group.add(nodes);reveal.push(nodes);
   const plane=new T.Mesh(new T.PlaneGeometry(3.7,3.2),new T.MeshBasicMaterial({color:'#50d9e6',transparent:true,opacity:.035,side:T.DoubleSide,depthWrite:false}));plane.rotation.y=Math.PI/2;plane.position.set(-8.7+l*5.8,0,0);group.add(plane);
  });
  const intact:T.Vector3[][]=[],changed:T.Vector3[][]=[],masked:T.Vector3[][]=[];
  for(let l=0;l<3;l++)for(let r=0;r<ns[l+1];r++)for(let c=0;c<ns[l];c++){
   if(l===0&&c%8!==r%8)continue;
   const pair=[point(l,c),point(l+1,r)];if(l===1&&G.permanent_mask[r][c]){if(kind==='mask')masked.push(pair);continue;}
   if(l===1&&changes.some((v:any)=>v.row===r&&v.column===c))changed.push(pair);else intact.push(pair);
  }
  segments(intact,'#50d9e6',.075);segments(masked,'#e58982',.18);segments(changed,'#f5b35b',.85);
  if(chosen){const a=point(1,chosen.column),b=point(2,chosen.row);segments([[a,b]],'#ffffff',1);focus.copy(a).add(b).multiplyScalar(.5);
   const halo=new T.Mesh(new T.SphereGeometry(.21,20,12),new T.MeshBasicMaterial({color:'#f5b35b',transparent:true,opacity:.22,depthWrite:false}));halo.position.copy(b);group.add(halo);}
 }else{
  const c=LM.candidates[method]?.candidates.find((v:any)=>v.index===candidate),ops=c?.patch.ops??[],touched=ops.map((o:any)=>Number(o.tensor.match(/layers\.(\d+)/)?.[1]));
  const boxes=new T.InstancedMesh(new T.BoxGeometry(.7,.6,.6),instanceMat,24),matrix=new T.Matrix4();const pts:T.Vector3[]=[];
  for(let i=0;i<24;i++){const p=new T.Vector3(-5+(i%8)*1.35,1.8-Math.floor(i/8)*1.25,-Math.floor(i/8)*.7);pts.push(p);matrix.makeTranslation(...p.toArray());boxes.setMatrixAt(i,matrix);boxes.setColorAt(i,new T.Color(touched.includes(i)?'#f5b35b':'#237884'));if(touched.includes(i))focus.copy(p);}
  group.add(boxes);reveal.push(boxes);segments(pts.slice(1).map((p,i)=>[pts[i],p]),'#50d9e6',.35);
  if(kind!=='blocks'){
   // Two spatial branches join at the intermediate channel plane.
   const branch=new T.Mesh(new T.BoxGeometry(1,.3,.6),cyan);branch.position.set(-4,-2,1);group.add(branch);
   const gate=branch.clone();gate.position.set(-2,-1.8,2);group.add(gate);const up=branch.clone();up.position.set(-2,-2.3,0);group.add(up);
   const down=new T.Mesh(new T.BoxGeometry(.5,1.2,2.4),amber);down.position.set(4.5,-2.1,1);group.add(down);
   segments([[branch.position,gate.position],[branch.position,up.position],[gate.position,new T.Vector3(1,-2,1)],[up.position,new T.Vector3(1,-2,1)],[new T.Vector3(1,-2,1),down.position]],'#50d9e6',.6);
   const bars=new T.InstancedMesh(new T.BoxGeometry(.055,.95,.08),instanceMat,64);
   for(let i=0;i<64;i++){matrix.makeTranslation(-.3+(i%32)*.12,-2.1,Math.floor(i/32)*.9+.5);bars.setMatrixAt(i,matrix);const selected=ops.some((o:any)=>(o.columns??[]).some((n:number)=>Math.floor(n/128)===i)||(o.entries??[]).some((e:number[])=>Math.floor(e[1]/128)===i));bars.setColorAt(i,new T.Color(selected?'#f5b35b':'#237884'));}group.add(bars);reveal.push(bars);
  }
 }
 const labels=document.createElement('div');labels.className='topology-labels';labels.setAttribute('aria-label','Exact architecture labels');
 if(['network','mask','scalar'].includes(kind))labels.innerHTML=G.architecture.layers.map((n:number,i:number)=>`<span>${n} ${['inputs','ReLU','ReLU','sigmoid'][i]}</span>`).join('');
 else {const ops=LM.candidates[method]?.candidates.find((v:any)=>v.index===candidate)?.patch.ops??[];const touched=ops.map((o:any)=>Number(o.tensor.match(/layers\.(\d+)/)?.[1]));labels.innerHTML=`<div class="block-labels">${Array.from({length:24},(_,i)=>`<span data-block="${i}" ${touched.includes(i)?'class="touched"':''}>${i}</span>`).join('')}</div><p>24 blocks · amber = touched${kind==='blocks'?'':' · h: 2048 → SiLU(gate) ⊙ up: 8192 → down_proj: 2048 · 128 channels / bin'}</p>`;}
 host.after(labels);
 const tools=document.createElement('div');tools.className='orbit-tools';tools.innerHTML='<button type="button" data-focus>Focus patch</button><button type="button" data-home>Reset view</button><span>Drag to orbit · scroll to zoom · schematic flow</span>';host.after(tools);
 const home=()=>{controls.reset();};tools.querySelector('[data-home]')!.addEventListener('click',home);tools.querySelector('[data-focus]')!.addEventListener('click',()=>{controls.target.copy(focus);camera.position.copy(focus).add(new T.Vector3(3,2,10));controls.update();});
 const size=()=>{if(!host.clientHeight)return;renderer.setSize(host.clientWidth,host.clientHeight,false);camera.aspect=host.clientWidth/host.clientHeight;camera.updateProjectionMatrix();
  // Fit projected spatial bounds to the available aspect ratio; no stretched canvas.
  const bounds=new T.Box3().setFromObject(group),center=bounds.getCenter(new T.Vector3()),direction=new T.Vector3(.18,.16,1).normalize();camera.position.copy(center).add(direction);camera.lookAt(center);const inverse=camera.quaternion.clone().invert(),tan=Math.tan(T.MathUtils.degToRad(camera.fov/2));let distance=3;
  for(const x of [bounds.min.x,bounds.max.x])for(const y of [bounds.min.y,bounds.max.y])for(const z of [bounds.min.z,bounds.max.z]){const v=new T.Vector3(x,y,z).sub(center).applyQuaternion(inverse);distance=Math.max(distance,Math.abs(v.y)/tan+v.z,Math.abs(v.x)/(tan*camera.aspect)+v.z);}
  camera.position.copy(center).addScaledVector(direction,distance*1.12);controls.target.copy(center);controls.update();controls.saveState();};const resize=new ResizeObserver(size);resize.observe(host);size();
 let frame=0,clock=0,last=0;const animate=(t:number)=>{frame=requestAnimationFrame(animate);if(motion()){clock+=last?Math.min(t-last,40):0;group.rotation.y=Math.sin(clock/6000)*.035;reveal.forEach((o,i)=>o.visible=clock>i*180);}else{group.rotation.y=0;reveal.forEach(o=>o.visible=true);}last=t;renderer.render(scene,camera);};frame=requestAnimationFrame(animate);
 return ()=>{cancelAnimationFrame(frame);resize.disconnect();controls.dispose();tools.remove();labels.remove();const geometries=new Set<T.BufferGeometry>(),materials=new Set<T.Material>();scene.traverse(o=>{if(o instanceof T.Mesh||o instanceof T.Line){geometries.add(o.geometry);(Array.isArray(o.material)?o.material:[o.material]).forEach(m=>materials.add(m));}});geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());renderer.dispose();renderer.domElement.remove();};
}
