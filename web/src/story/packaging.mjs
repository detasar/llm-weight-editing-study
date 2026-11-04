export function packHTML(template,javascript,css){
 const safeScript=javascript.replace(/<\/script/gi,'<\\/script');
 const safeStyle=css.replace(/<\/style/gi,'<\\/style');
 const scriptPattern=/<script\s+type="module"\s+src="\.\/src\/story\/main\.mjs"><\/script>/;
 if(!scriptPattern.test(template))throw Error('Missing story entry point');
 return template.replace('</head>',()=>`<style>${safeStyle}</style></head>`).replace(scriptPattern,()=>`<script>${safeScript}</script>`);
}
// File extensions are not authoritative: the supplied article-title .png is JPEG.
export function imageMime(bytes){
 if(bytes[0]===0xff&&bytes[1]===0xd8&&bytes[2]===0xff)return 'image/jpeg';
 if([137,80,78,71,13,10,26,10].every((n,i)=>bytes[i]===n))return 'image/png';
 throw Error('Unsupported story image signature');
}
export function normalizeImageURL(url){
 if(!url.startsWith('data:'))return url;
 const comma=url.indexOf(','),raw=atob(url.slice(comma+1,comma+1+16));
 const mime=imageMime(Uint8Array.from(raw,c=>c.charCodeAt(0)));
 return `data:${mime};base64,${url.slice(comma+1)}`;
}
