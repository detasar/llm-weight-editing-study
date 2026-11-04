import {build} from 'vite';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {packHTML,imageMime} from './src/story/packaging.mjs';
const web=fileURLToPath(new URL('.',import.meta.url));
const assetNames=['weight-space-hero.png','reference-article-title.png'];
const assets=await Promise.all(assetNames.map(async name=>{
 const bytes=await readFile(path.join(web,'public/story-assets',name));
 return {name,bytes,mime:imageMime(bytes),url:`data:${imageMime(bytes)};base64,${bytes.toString('base64')}`};
}));
// Signature-based URLs are correct even when the source filename has a different suffix.
const storyImages={name:'story-image-signatures',enforce:'pre',load(id){
 const asset=assets.find(a=>id===path.join(web,'public/story-assets',a.name)+'?inline');
 if(asset)return `export default ${JSON.stringify(asset.url)};`;
}};
// All imported assets and fonts are inlined by Vite library mode; no public-directory copy.
const result=await build({plugins:[storyImages],root:web,configFile:false,publicDir:false,logLevel:'warn',build:{write:false,target:'es2022',minify:true,cssCodeSplit:false,sourcemap:false,assetsInlineLimit:Infinity,lib:{entry:path.join(web,'src/story/main.mjs'),name:'ResearchStory',formats:['iife'],fileName:()=> 'story.js'},rollupOptions:{output:{inlineDynamicImports:true}}}});
const outputs=(Array.isArray(result)?result:[result]).flatMap(r=>r.output);
const js=outputs.filter(o=>o.type==='chunk');
if(js.length!==1||js[0].imports.length||js[0].dynamicImports.length)throw Error('Offline story must have exactly one import-free classic bundle');
const css=outputs.filter(o=>o.type==='asset'&&o.fileName.endsWith('.css')).map(o=>String(o.source)).join('\n');
const leftovers=outputs.filter(o=>o.type==='asset'&&!o.fileName.endsWith('.css'));
if(leftovers.length)throw Error(`Non-inlined assets: ${leftovers.map(o=>o.fileName).join(', ')}`);
if(!css.includes('data:font/woff2')&&!css.includes('data:application/font-woff2'))throw Error('Fonts were not bundled');
for(const asset of assets)if(!js[0].code.includes(asset.url))throw Error(`Missing signature-correct inline image: ${asset.name}`);
const html=packHTML(await readFile(path.join(web,'story.html'),'utf8'),js[0].code,css);
if(/<script[^>]+(?:src=|type="module")|<link[^>]+(?:href=)/i.test(html))throw Error('External runtime dependency in offline HTML');
const destination=path.resolve(web,'../artifacts/bbva-research/START_PRESENTATION.html');
await mkdir(path.dirname(destination),{recursive:true});
await writeFile(destination,html);
console.log(JSON.stringify({status:'built',file:'artifacts/bbva-research/START_PRESENTATION.html',bytes:Buffer.byteLength(html),sha256:createHash('sha256').update(html).digest('hex'),duration:2700,chapters:33}));
