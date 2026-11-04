import {mkdir,cp,readFile,writeFile} from 'node:fs/promises';
await mkdir('public/source',{recursive:true});
for(const dir of ['docs','configs','prompts','data']) await cp('../'+dir,'public/source/'+dir,{recursive:true});
await cp('../assets/art','public/art',{recursive:true});
const m=JSON.parse(await readFile('../data/manifest.json','utf8'));
await writeFile('public/source/manifest-identity.txt',m.manifest_sha256+'\n');
for(const [from,to] of [['../report/report.pdf','public/report/report.pdf'],['../presentation/presentation.pdf','public/presentation/presentation.pdf'],['../presentation/weight-editing-offline.zip','public/presentation/weight-editing-offline.zip']]){
 try{await mkdir(to.slice(0,to.lastIndexOf('/')),{recursive:true});await cp(from,to);}catch(e){if(e.code!=='ENOENT')throw e;}
}
