// Geometry is explanatory; counts and intervention coordinates are evidence-bound.
export const ADULT_LAYERS=[104,32,16,1];
export function adultPositions(){
 return ADULT_LAYERS.map((n,l)=>Array.from({length:n},(_,j)=>{
  const cols=[8,4,4,1][l],rows=n/cols;
  return [[-5.8,-1.8,2.1,5.8][l],
   ((rows-1)/2-Math.floor(j/cols))*[.27,.36,.46,1][l],
   (j%cols-(cols-1)/2)*[.46,.6,.54,1][l]];
 }));
}
// Sparse context edges illustrate connectivity; all nodes and the highlighted
// unmasked route are retained. No measured activation is inferred here.
export function adultContextEdges(mask){
 const edges=[];
 for(let l=0;l<3;l++)for(let i=0;i<ADULT_LAYERS[l];i+=l===2?1:4){
  const j=(i*7+3)%ADULT_LAYERS[l+1];
  if(l!==1||!mask[j][i])edges.push([l,i,j]);
 }
 return edges;
}
// Every reduced frame uses this cue-fixed phase, including a direct seek into
// the middle of the cue. It must match the cue-fixed render cache key.
export const stagePose=(p,reduced)=>reduced?{...p,progress:.5,settle:1}:p;
export const GATED_NODES={
 input:[-6,0,0],norm:[-4.65,0,0],gate:[-2.65,1.45,-.45],silu:[-.7,1.45,-.45],
 up:[-2.65,-1.15,.55],product:[1.25,0,0],down:[3.35,0,0],add:[5.35,0,0],output:[6.25,0,0],
 bypassA:[-6,-2.2,.3],bypassB:[5.35,-2.2,.3]
};
export const GATED_WIDTHS={input:.13,norm:.13,gate:.44,silu:.44,up:.44,product:.44,down:.13,add:.13,output:.13,bypassA:.13,bypassB:.13};
export const GATED_PATHS=[
 {nodes:['input','norm'],kind:'signal',step:0},
 {nodes:['norm','gate','silu','product'],kind:'signal',step:1},
 {nodes:['norm','up','product'],kind:'signal',step:2},
 {nodes:['product','down','add','output'],kind:'signal',step:3},
 {nodes:['input','bypassA','bypassB','add'],kind:'residual',step:4}
];
export const TRANSFORMER_BLOCKS=Array.from({length:24},(_,i)=>({index:i,position:[-5.25+(i%8)*1.5,2.1-Math.floor(i/8)*2.1,(i%8)*.08]}));
export function sceneGeometry(scene,cue=0){
 if(['network','article'].includes(scene))return 'adult-network';
 if(scene==='matrix'||scene==='edit'&&cue===0)return 'adult-matrix';
 if(['neuron','edit'].includes(scene))return 'adult-computation';
 if(['lm-matrix','lm-candidate'].includes(scene))return 'lm-down-projection';
 if(scene==='transformer')return cue===0?'transformer-24':cue===1?'transformer-block':cue===2?'gated-mlp':'lm-down-projection';
 if(scene==='gated')return 'gated-mlp';
 if(scene==='branches')return 'editor-branches';
 return null;
}
// Camera distance fits the actual 3D bounding box, including its depth. Width is
// intentionally 78% of the available canvas unless vertical fit is limiting.
export function fitDistance(width,height,depth,aspect,fov=37,fill=.78){
 const tan=Math.tan(fov*Math.PI/360);
 return Math.max(width/(2*tan*aspect*fill),height/(2*tan*.76))+depth/2+.15;
}
// Fit real camera-oriented vertices. At each distance, intersect the permissible
// camera-centre intervals, rather than padding a rotated world AABB by its depth.
export function fitVertices(vertices,aspect,fov=37,fillX=.8,fillY=.84){
 const sy=Math.tan(fov*Math.PI/360)*fillY,sx=Math.tan(fov*Math.PI/360)*aspect*fillX;
 const limits=d=>{
  let left=-Infinity,right=Infinity,bottom=-Infinity,top=Infinity;
  for(const [x,y,z] of vertices){
   const depth=d-z;
   if(depth<.2)return null;
   left=Math.max(left,x-depth*sx);right=Math.min(right,x+depth*sx);
   bottom=Math.max(bottom,y-depth*sy);top=Math.min(top,y+depth*sy);
  }
  return left<=right&&bottom<=top?{x:(left+right)/2,y:(bottom+top)/2}:null;
 };
 let lo=Math.max(...vertices.map(p=>p[2]))+.2,hi=lo+1;
 while(!limits(hi))hi=lo+(hi-lo)*2;
 for(let i=0;i<48;i++){const mid=(lo+hi)/2;if(limits(mid))hi=mid;else lo=mid;}
 return {distance:hi,...limits(hi)};
}
export function signalPhase(p,reduced=false){
 const sequence=p.chapter.scene==='network'?Math.min(2,Math.max(0,p.cueIndex-1)):0;
 return {layer:sequence,u:reduced?1:p.progress};
}
