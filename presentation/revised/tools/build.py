from pathlib import Path
import base64,json
R=Path(__file__).resolve().parents[1]
def datauri(name,mime):return 'data:'+mime+';base64,'+base64.b64encode((R/'assets'/name).read_bytes()).decode()
assets={'paper':datauri('source-title.jpg','image/jpeg'),'landscape':datauri('weight-space-art.webp','image/webp'),'logo':datauri('openai-logomark.svg','image/svg+xml')}
scenes=json.loads((R/'data/scenes.json').read_text()); ev=json.loads((R/'data/evidence.json').read_text())
np=R/'data/narration-tr.json'; notes=json.loads(np.read_text()) if np.exists() else ['Türkçe anlatım metni hazırlanıyor.']*len(scenes)
pp=R/'data/prompts.json'; prompts=json.loads(pp.read_text()) if pp.exists() else {}
data='window.ASSETS='+json.dumps(assets)+';window.SCENES='+json.dumps(scenes,ensure_ascii=False)+';window.EVIDENCE='+json.dumps(ev,ensure_ascii=False)+';window.NARRATION='+json.dumps(notes,ensure_ascii=False)+';window.PROMPTS='+json.dumps(prompts,ensure_ascii=False)+';'
html=(R/'src/shell.html').read_text()
for key,value in {'STYLE':(R/'src/style.css').read_text(),'THREE':(R/'vendor/three.r169.local.js').read_text(),'DATA':data,'DIAGRAMS':(R/'src/diagrams.js').read_text(),'FIELD':(R/'src/field.js').read_text(),'APP':(R/'src/app.js').read_text()}.items():html=html.replace('/*'+key+'*/',value)
(R/'START_PRESENTATION.html').write_text(html)
print('built',len(html),'bytes')
