import manifest from '../../data/manifest.json';
import graph from '../../data/adult_graph.json';
import predictions from '../../data/adult_predictions.json';
export const M:any=manifest, G:any=graph, P:any=predictions;
export const LM:any=M.lm.versions[M.lm.main_version];
export const methods=['baseline','Sol','Astra','joint'];
export const colors:Record<string,string>={baseline:'#778b99',Sol:'#c27b21',Astra:'#168a9b',joint:'#16665f',clean:'#536477',random:'#70796d',grid:'#8c7765'};
export const pct=(v:number|undefined,d=3)=>v===undefined?'NA':(v*100).toFixed(d)+'%';
export const num=(v:number|undefined,d=3)=>v===undefined?'NA':v.toLocaleString('en-US',{maximumFractionDigits:d});
export const esc=(s:unknown)=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
// Match native Adult float32 assignment from the immutable origin for inspection.
// Selected endpoints use the exported executed scalar values directly.
export function adultChanges(method:string,index?:number):any[]{
 const group=M.adult.candidates[method];
 if(index===undefined||index===group?.selected_index)return G.variants[method]?.changes??[];
 const patch=group?.candidates.find((c:any)=>c.index===index)?.patch;const changes:any[]=[];
 const add=(row:number,column:number,value:number)=>{const before=G.root['fc2.weight'][row][column],after=Math.fround(value);if(before!==after)changes.push({row,column,before,after});};
 for(const op of patch?.ops??[]){if(op.kind==='sparse')for(const [r,c,d] of op.entries)add(r,c,G.root['fc2.weight'][r][c]+d);else for(const c of op.columns)for(let r=0;r<16;r++)add(r,c,G.root['fc2.weight'][r][c]*op.factor);}
 return changes;
}
