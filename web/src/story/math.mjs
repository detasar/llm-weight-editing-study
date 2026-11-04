// Selectively retained accepted float64 synthetic illustration; never a heldout feature row.
export const clamp=(x,a=0,b=1)=>Math.min(b,Math.max(a,x));
export const smooth=x=>{x=clamp(x);return x*x*(3-2*x)};
export const mix=(a,b,t)=>a+(b-a)*t;
export function syntheticInput(){return Array.from({length:104},(_,i)=>((i*17+11)%31-15)/30-.2)}
export function affine(w,b,x){if(w.length!==b.length||w.some(r=>r.length!==x.length))throw Error('Invalid affine dimensions');return w.map((r,i)=>r.reduce((s,v,j)=>s+v*x[j],b[i]))}
export function forward(root,x=syntheticInput(),changes=[]){
 if(x.length!==104||x.some(v=>!Number.isFinite(v)))throw Error('Invalid input');
 const w2=root['fc2.weight'].map(r=>r.slice());
 for(const c of changes){if(w2[c.row][c.column]!==c.before)throw Error('Patch origin mismatch');w2[c.row][c.column]=c.after}
 const z1=affine(root['fc1.weight'],root['fc1.bias'],x),h1=z1.map(v=>Math.max(0,v));
 const z2=affine(w2,root['fc2.bias'],h1),h2=z2.map(v=>Math.max(0,v));
 const logit=affine(root['fc3.weight'],root['fc3.bias'],h2)[0],p=1/(1+Math.exp(-logit));
 if([...z1,...h1,...z2,...h2,logit,p].some(v=>!Number.isFinite(v)))throw Error('Nonfinite illustration');
 return {x,z1,h1,z2,h2,logit,p};
}
export function illustration(e){const before=forward(e.root),after=forward(e.root,syntheticInput(),e.changes),deltaZ=Array(16).fill(0);for(const c of e.changes)deltaZ[c.row]+=before.h1[c.column]*(c.after-c.before);const focus=e.changes.find(c=>before.h1[c.column]!==0);
 if(!focus)throw Error('No nonzero edited contribution in fixed fixture');
 const neuron=before.z1.findIndex(v=>v>0),negative=before.z1.findIndex(v=>v<0);
 const terms=before.x.slice(0,3).map((x,j)=>({x,w:e.root['fc1.weight'][neuron][j],value:x*e.root['fc1.weight'][neuron][j]}));
 const remainder=before.x.slice(3).reduce((sum,x,j)=>sum+x*e.root['fc1.weight'][neuron][j+3],0);
 return {before,after,deltaZ,focus,computation:{neuron,negative,terms,remainder,bias:e.root['fc1.bias'][neuron]}}}
