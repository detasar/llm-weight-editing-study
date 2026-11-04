#!/usr/bin/env python3
"""Build a vector, selectable-text reader report from frozen evidence, offline.

Single prose source, hash-bound measurements, shared vector diagrams and offline math.
Only the named PDF and HTML are published; intermediates are ephemeral.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import re
import shutil
import subprocess
import tempfile
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/bbva-research'
TEX = shutil.which('xelatex') or str(Path('/Library') / 'TeX/texbin/xelatex')
REPO = 'https://github.com/detasar/llm-weight-editing-study'
COLORS = {'navy': '#172b42', 'teal': '#167c80', 'amber': '#bc7c20',
          'rose': '#b45166', 'gray': '#d9ddde', 'paper': '#fcfaf5'}
METHODS = ['baseline', 'Sol', 'Astra', 'joint', 'clean', 'random', 'grid']
METRICS = ['balanced_accuracy', 'accuracy', 'roc_auc', 'logloss', 'brier']
MAIN = ['Sol_minus_baseline', 'Astra_minus_baseline',
        'joint_minus_baseline', 'joint_minus_Sol']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def evidence():
    m = json.loads((ROOT / 'data/manifest.json').read_text())
    payload = {k: v for k, v in m.items() if k != 'manifest_sha256'}
    if digest(payload) != m['manifest_sha256']:
        raise ValueError('Manifest self binding differs')
    for name, expected in m['files'].items():
        if sha(ROOT / 'data' / name) != expected:
            raise ValueError('Frozen input differs: ' + name)
    for name, expected in m['prompts'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('Frozen prompt differs: ' + name)
    if digest(m['summary']) != m['summary_sha256']:
        raise ValueError('Summary binding differs')
    g = json.loads((ROOT / 'data/adult_graph.json').read_text())
    p = json.loads((ROOT / 'data/adult_predictions.json').read_text())['methods']
    return m, g, p


def selected(m, name):
    r = m['adult']['candidates'][name]
    return next(c for c in r['candidates'] if c['index'] == r['selected_index'])


def endpoints(p):
    b, s = p['baseline'], p['Sol']
    if b['paired_ids'] != s['paired_ids'] or b['labels'] != s['labels']:
        raise ValueError('Unpaired illustration')
    found = {}
    for ordinal, (y, pb, ps) in enumerate(zip(b['labels'], b['probabilities'], s['probabilities']), 1):
        before, after = (pb >= .5) == y, (ps >= .5) == y
        kind = 'Rescue' if not before and after else 'Regression' if before and not after else None
        if kind and kind not in found:
            found[kind] = (ordinal, y, pb, ps)
    return found


def tex_escape(s):
    return str(s).replace('&', r'\&').replace('_', r'\_').replace('%', r'\%')


class Graphic:
    """Exact vector primitives emitted to both TikZ and self-contained SVG."""
    def __init__(self, height=220):
        self.w, self.h = 440, height
        self.t = [r'\begin{tikzpicture}[x=1pt,y=-1pt,>=Latex]',
                  f'\\path[use as bounding box] (0,0) rectangle (440,{height});']
        self.s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 {height}" role="img"><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/></marker></defs>']
    def rect(self,x,y,w,h,color='gray',stroke=None):
        self.t.append(f'\\filldraw[fill={color},draw={stroke or color},line width=.6pt] ({x},{y}) rectangle ({x+w},{y+h});')
        self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{COLORS[color]}" stroke="{COLORS[stroke or color]}"/>')
    def line(self,x,y,xx,yy,color='navy',dash=False,arrow=False):
        self.t.append(f'\\draw[draw={color},line width=1pt{",dotted" if dash else ""}{",-{Latex[length=6pt,width=5pt]}" if arrow else ""}] ({x},{y}) -- ({xx},{yy});')
        self.s.append(f'<line x1="{x}" y1="{y}" x2="{xx}" y2="{yy}" stroke="{COLORS[color]}" stroke-width="1"'+(' stroke-dasharray="2 3"' if dash else '')+(' marker-end="url(#arrow)"' if arrow else '')+'/>')
    def arrow(self,x,y,xx,yy,color='navy',dash=False):
        self.line(x,y,xx,yy,color,dash,arrow=True)
    def join(self,x,y):
        self.t.append(f'\\draw[fill=paper,draw=amber,line width=1pt] ({x},{y}) circle (9pt);')
        self.s.append(f'<circle cx="{x}" cy="{y}" r="9" fill="{COLORS["paper"]}" stroke="{COLORS["amber"]}"/>')
        self.text(x,y,'+',14,'navy','middle')
    def text(self,x,y,text,size=10.5,color='navy',anchor='start'):
        size = max(10.5, size)
        anc = {'start':'west','middle':'center','end':'east'}[anchor]
        self.t.append(f'\\node[anchor={anc},text={color},inner sep=0pt,font=\\sffamily\\fontsize{{{size}}}{{{size+2}}}\\selectfont] at ({x},{y}) {{{tex_escape(text)}}};')
        self.s.append(f'<text x="{x}" y="{y+size*.33}" text-anchor="{anchor}" font-family="Arial,sans-serif" font-size="{size}" fill="{COLORS[color]}">{html.escape(str(text))}</text>')
    def dot(self,x,y,color='teal',r=3):
        self.t.append(f'\\fill[{color}] ({x},{y}) circle ({r}pt);')
        self.s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{COLORS[color]}"/>')
    def box(self,x,y,w,h,label,color='teal'):
        self.rect(x,y,w,h,'paper',color)
        self.text(x+w/2,y+h/2,label,11,color,'middle')
    def finish(self):
        return '\n'.join(self.t+[r'\end{tikzpicture}']), ''.join(self.s+['</svg>'])


def graphics(m,g):
    result = {}
    q=Graphic(170)
    for x,y,w,label in [(5,15,100,'Frozen origin'),(155,15,120,'Structured patch'),(315,15,115,'Validate + cast'),
                         (315,115,115,'Dev score'),(155,115,120,'Select + freeze'),(5,115,100,'Final panel')]:
        q.box(x,y,w,38,label)
    for x,y,xx,yy in [(105,34,155,34),(275,34,315,34),(372,53,372,115),(315,134,275,134),(155,134,105,134)]:q.arrow(x,y,xx,yy)
    q.line(340,115,340,80,'teal',True)
    q.line(340,80,215,80,'teal',True)
    q.arrow(215,80,215,53,'teal',True)
    q.text(325,96,'Development feedback',9,'teal','end')
    result['intervention']=q.finish()
    q=Graphic(153)
    q.box(5,52,90,36,'Origin')
    for y,n in [(5,'Sol search'),(106,'Astra search')]:
        q.box(140,y,105,34,n);q.arrow(95,70,140,y+17)
        q.arrow(245,y+17,300,70,'teal')
    q.box(300,52,135,36,'Joint full patch')
    q.arrow(95,70,300,70,'amber',True)
    q.text(210,59,'root weights',9,'amber','middle')
    q.text(269,17,'history',9,'teal')
    q.text(269,129,'history',9,'teal')
    q.text(220,150,'Select on development; freeze before final assessment',9,'navy','middle')
    result['cooperation']=q.finish()
    q=Graphic(145)
    for x,label,sub in [(4,'104 inputs','encoded x'),(122,'32 units','ReLU + bias'),(240,'16 units','ReLU + bias'),(358,'1 output','sigmoid + bias')]:
        q.box(x,20,78,55,label);q.text(x+39,100,sub,9,'navy','middle')
        if x<350:q.arrow(x+78,48,x+118,48)
    q.text(220,133,'float32 forward pass; threshold p >= 0.5',10,'teal','middle')
    result['adultnet']=q.finish()
    q=Graphic(230)
    for r,row in enumerate(g['permanent_mask']):
        for c,masked in enumerate(row):
            q.rect(35+c*12,35+r*10,10,8,'gray' if masked else 'teal',
                   'amber' if (r,c) in {(v['row'],v['column']) for v in g['variants']['Sol']['changes']} else None)
    for c in [0,4,8,12,16,20,24,28,31]:q.text(40+c*12,22,str(c),9,'navy','middle')
    for r in [0,4,8,12,15]:q.text(23,39+r*10,str(r),9,'navy','end')
    q.text(225,216,'columns 0--31; rows 0--15',10,'navy','middle')
    result['mask']=q.finish()
    q=Graphic(126)
    q.text(0,9,'01 / ADULT: SPARSE INTERVENTION',10,'teal')
    for r,row in enumerate(g['permanent_mask']):
        for c,masked in enumerate(row):
            q.rect(c*5.1,24+r*4.3,4,3.2,'gray' if masked else 'teal',
                   'amber' if (r,c) in {(v['row'],v['column']) for v in g['variants']['Sol']['changes']} else None)
    q.text(0,108,'Actual mask / 16 selected edits',9)
    d=m['adult']['contrasts']['Sol_minus_baseline']['difference']*100
    q.text(192,36,f'{d:+.4f} pp',23,'teal')
    q.text(192,60,'Adult balanced accuracy',10)
    q.text(192,82,'02 / INTACT LANGUAGE MODEL',10,'amber')
    q.text(192,105,'Candidate zero selected',15,'navy')
    result['opening']=q.finish()
    q=Graphic(250)
    xmin,xmax=-.16,.72
    fx=lambda x:150+(x-xmin)/(xmax-xmin)*275
    for tick in [-.1,0,.1,.2,.3,.4,.5,.6,.7]:
        xx=fx(tick);q.line(xx,20,xx,193,'gray');q.text(xx,212,f'{tick:.1f}',9,'navy','middle')
    q.line(fx(0),20,fx(0),193,'navy',True)
    for i,n in enumerate(MAIN):
        d=m['adult']['contrasts'][n];y=40+i*43
        q.text(3,y,n.replace('_minus_',' - '),10)
        lo,hi=[100*x for x in d['difference_95ci']]
        q.line(fx(lo),y,fx(hi),y,'teal');q.line(fx(lo),y-4,fx(lo),y+4,'teal');q.line(fx(hi),y-4,fx(hi),y+4,'teal');q.dot(fx(100*d['difference']),y)
    q.text(290,240,'Delta balanced accuracy (pp)',10,'navy','middle')
    result['forest']=q.finish()
    q=Graphic(185)
    for i,n in enumerate(['Sol','joint','Astra']):
        c=m['adult']['contrasts'][n+'_minus_baseline']['paired_counts']['by_class'];y=20+i*48
        q.text(0,y+11,n,11)
        for yy,count,col in [(y,c['1']['rescues'],'teal'),(y+17,c['0']['regressions'],'rose')]:
            q.rect(65,yy,count*2.5,11,col);q.text(74+count*2.5,yy+5,str(count),10,col)
    q.text(65,173,'Positive rescues / negative regressions (raw counts)',10)
    result['counts']=q.finish()
    q=Graphic(319)
    q.box(170,5,100,30,'Residual r')
    q.box(170,57,100,30,'Norm: x')
    q.arrow(220,35,220,57)
    q.line(170,20,15,20,'amber');q.line(15,20,15,303,'amber')
    q.box(35,105,130,32,'gate: 8,192');q.box(280,105,130,32,'up: 8,192')
    q.arrow(195,87,100,105);q.arrow(245,87,345,105)
    q.box(35,157,130,32,'SiLU(gate)');q.arrow(100,137,100,157)
    q.box(170,207,100,30,'Multiply')
    q.arrow(100,189,190,207);q.line(345,137,345,182);q.arrow(345,182,250,207)
    q.box(135,253,170,30,'down: 2,048');q.arrow(220,237,220,253)
    q.arrow(220,283,220,294);q.arrow(15,303,211,303,'amber')
    q.join(220,303);q.arrow(229,303,400,303)
    q.text(26,247,'Residual bypass r',9,'amber')
    q.text(281,229,'h: 8,192',10,'teal')
    q.text(325,289,'r + y',10,'navy')
    result['gated']=q.finish()
    q=Graphic(180)
    q.rect(40,35,62,90,'teal');q.rect(144,35,256,90,'gray')
    q.text(40,13,'W down: 2,048 rows x 8,192 columns',11)
    q.text(71,148,'32 selected',10,'teal','middle')
    q.text(272,148,'8,160 unchanged',10,'navy','middle')
    q.text(71,79,'x 0.5',11,'paper','middle')
    for x in [115,127]:q.line(x,70,x+7,90,'navy')
    q.text(220,173,'Separated bundles / widths not proportional',9,'navy','middle')
    result['columns']=q.finish()
    q=Graphic(250)
    for k,(name,col) in enumerate([('Sol','teal'),('Astra','amber'),('joint','rose')]):
        top=12+k*77
        q.text(2,top+23,name,10,col)
        ty=lambda v:top+49-(v-.735)/.02*40
        for tick in [.735,.745,.755]:
            yy=ty(tick);q.line(105,yy,427,yy,'gray');q.text(98,yy,f'{tick:.3f}',9,'navy','end')
        records={c['index']:c for c in m['lm']['versions']['v2']['candidates'][name]['candidates']}
        prev=None
        for i in range(6):
            x=110+i*62
            q.text(x,top+64,str(i),9,'navy','middle')
            if i not in records:prev=None;continue
            y=ty(records[i]['metrics']['acc_norm'])
            if prev:q.line(*prev,x,y,col)
            q.dot(x,y,col,3);prev=(x,y)
    q.text(268,246,'Candidate index / shared score scale',9,'navy','middle')
    result['trajectory']=q.finish()
    q=Graphic(160)
    for i,n in enumerate(['baseline','Sol','Astra','joint']):
        x=5+i*112;q.box(x,8,100,35,n);q.arrow(x+50,43,220,92)
    q.box(100,92,240,40,'One executed state: candidate 0')
    q.text(220,151,'Same weights + requests + scorer + runtime',10,'teal','middle')
    result['identity']=q.finish()
    return result


PREAMBLE = r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=23mm,top=24mm,bottom=23mm,headheight=15pt]{geometry}
\usepackage{fontspec,amsmath,amssymb,booktabs,microtype,tikz,fancyhdr,xcolor,graphicx,seqsplit}
\usetikzlibrary{arrows.meta,calc}
\usepackage[colorlinks=true,urlcolor=teal,linkcolor=teal,breaklinks=true]{hyperref}
\setmainfont{texgyrepagella}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,ItalicFont=*-italic,BoldItalicFont=*-bolditalic]
\setsansfont{texgyreheros}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold]
\newfontfamily\tablefont{texgyreheroscn}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold]
\setmonofont{texgyrecursor}[Extension=.otf,UprightFont=*-regular]
\definecolor{navy}{HTML}{172B42}\definecolor{teal}{HTML}{167C80}
\definecolor{amber}{HTML}{BC7C20}\definecolor{rose}{HTML}{B45166}
\definecolor{gray}{HTML}{D9DDDE}\definecolor{paper}{HTML}{FCFAF5}
\pagecolor{paper}\color{navy}
\setlength{\emergencystretch}{4em}\setlength{\parindent}{0pt}\setlength{\parskip}{8pt}
\AtBeginDocument{\fontsize{11}{15.3}\selectfont}
\pagestyle{fancy}\fancyhf{}
\fancyhead[L]{\sffamily\fontsize{9}{11}\selectfont Editing neural networks with language models}
\fancyhead[R]{\sffamily\fontsize{9}{11}\selectfont BBVA AI Innovation}
\fancyfoot[L]{\sffamily\fontsize{9}{11}\selectfont Davut Emre Taşar · 4 November 2026}
\fancyfoot[R]{\sffamily\small\thepage}\renewcommand{\headrulewidth}{.3pt}
\newcommand{\Page}[2]{\clearpage{\sffamily\small\color{teal}#1\par}\vspace{8pt}{\raggedright\sffamily\bfseries\fontsize{26}{30}\selectfont #2\par}\vspace{12pt}}
\newcommand{\Caption}[1]{{\sffamily\fontsize{10.5}{13}\selectfont #1\par}\vspace{6pt}}
\hypersetup{pdftitle={Editing Neural Networks with Language Models},pdfauthor={Davut Emre Taşar},pdfsubject={BBVA AI Innovation · Research report}}
\begin{document}
'''
AUTHOR = 'Davut Emre Taşar'
TITLE = 'Editing Neural Networks with Language Models'
SOURCE = ROOT / 'report/research-source.tex'
ASSETS = ROOT / 'web/public/story-assets'


def run(argv, cwd=None, input=None):
    r = subprocess.run(argv, cwd=cwd, input=input, capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise RuntimeError(f'{Path(argv[0]).name} exit {r.returncode}\n'+r.stdout[-5000:]+r.stderr[-1000:])
    return r.stdout


def public_scan(value):
    for token in ['/Users/', '/home/', '/private/tmp/', '/tmp/slm-', 'PRIVATE_NARRATOR',
                  'sk-proj-', 'OPENROUTER_API_KEY']:
        if token in value:
            raise ValueError('Private marker in public output: '+token)


def table(headers, rows):
    spec = 'l' + 'r'*(len(headers)-1)
    tex = (r'\begin{center}{\tablefont\fontsize{10.5}{14}\selectfont\setlength{\tabcolsep}{4pt}'
           r'\renewcommand{\arraystretch}{1.16}\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}'+spec+r'}\toprule'+'\n'+
           ' & '.join(map(tex_escape, headers))+r'\\\midrule'+'\n'+
           '\n'.join(' & '.join(map(tex_escape, row))+r'\\' for row in rows)+
           r'\bottomrule\end{tabular*}}\end{center}')
    h = '<table><thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'
    h += ''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)
    return tex, h+'</tbody></table>'


def bindings(m, g, p):
    a, v = m['adult'], m['lm']['versions']['v2']
    config = json.loads((ROOT/'configs/defaults.json').read_text())
    sol = a['contrasts']['Sol_minus_baseline']
    values = {'sol_pp':f"{100*sol['difference']:.4f}",
              'sol_ci':' to '.join(f'{100*x:.4f}' for x in sol['difference_95ci']),
              'acc_pp':f'{100*(65-102)/16281:.4f}',
              'sol_model':config['editors']['Sol'], 'astra_model':config['editors']['Astra'],
              'reasoning':config['reasoning'],
              'manifest':m['manifest_sha256']}
    for name in ['Sol','Astra','joint']:
        values[name.lower()+'_index'] = str(a['candidates'][name]['selected_index'])
        values[name.lower()+'_dev'] = f"{selected(m,name)['metrics']['balanced_accuracy']:.9f}"
    c = next(x for x in g['variants']['Sol']['changes'] if x['column']==15)
    values.update(before=repr(c['before']), after=repr(c['after']))
    lm = next(c for c in v['candidates']['Astra']['candidates'] if c['index']==1)
    values['lm_norm'] = repr(lm['stats']['norm'])
    values['lm_relative'] = f"{next(iter(lm['stats']['relative_norms'].values())):.9f}"
    t = {}
    t['main'] = table(['Condition','Balanced accuracy (%)','Accuracy (%)','Correct / 16,281'],
        [[n]+[f"{100*a['methods'][n]['metrics'][k]:.6f}" for k in METRICS[:2]]+
         [str(sum((q>=.5)==y for q,y in zip(p[n]['probabilities'],p[n]['labels'])))]
         for n in METHODS[:4]])
    t['quality'] = table(['State','BA','Accuracy','ROC-AUC','Log-loss','Brier'],
        [[n]+[f"{a['methods'][n]['metrics'][k]:.6f}" for k in METRICS] for n in METHODS])
    t['intervals'] = table(['Contrast','ΔBA (pp)','95% low','95% high'],
        [[n.replace('_minus_',' − '),f"{100*a['contrasts'][n]['difference']:+.4f}"]+
         [f'{100*x:+.4f}' for x in a['contrasts'][n]['difference_95ci']] for n in MAIN])
    t['cases'] = table(['Change','Anonymous ordinal','Truth','Baseline p','Sol p'],
        [[k,i,y,f'{pb:.9f}',f'{ps:.9f}'] for k,(i,y,pb,ps) in endpoints(p).items()])
    se=a['slots']['Sol']['patch']['ops'][0]['entries']
    je=a['slots']['joint']['patch']['ops'][0]['entries']
    ae=a['slots']['Astra']['patch']['ops'][0]['entries']
    if not len(se)==len(je)==len(ae)==16 or not all(
        s[:2]==j[:2]==z[:2] and Decimal(str(j[2]))==Decimal('.93')*Decimal(str(s[2]))
        for s,j,z in zip(se,je,ae)):
        raise ValueError('Frozen selected-patch relationship changed')
    t['patch'] = table(['Row, column (zero-based)','Sol Δ','Astra Δ','Joint Δ'],
        [[f'({s[0]}, {s[1]})',s[2],z[2],j[2]] for s,j,z in zip(se,je,ae)])
    t['patchstats'] = table(['Executed statistic','Sol','Astra','Joint'],
        [['Changed scalars']+[g['variants'][n]['stats']['count'] for n in METHODS[1:4]],
         ['Delta L2']+[f"{g['variants'][n]['stats']['norm']:.9f}" for n in METHODS[1:4]],
         ['Relative L2']+[f"{g['variants'][n]['stats']['relative_norm']:.9f}" for n in METHODS[1:4]]])
    series={n:{c['index']:c for c in v['candidates'][n]['candidates']} for n in METHODS[1:4]}
    t['lmtrajectory'] = table(['Candidate','Sol acc_norm','Astra acc_norm','Joint acc_norm'],
        [[i]+[f"{series[n][i]['metrics']['acc_norm']:.7f}" if i in series[n] else 'invalid / unscored'
              for n in series] for i in range(6)])
    rows=[]
    for task, states in v['tasks'].items():
        r=states['baseline']; n=r['n']
        rows.append([task,n]+[
            f"{r['paired_minus_baseline'][key]['condition_correct']}/{n} = {100*r['metrics'][key]:.6f}%"
            for key in ['acc_norm','acc']])
    t['lmfinal']=table(['Task','n','Character-normalized','Raw likelihood'],rows)
    adultrows=[]
    for n in METHODS[1:4]:
        r=a['candidates'][n]
        adultrows += [[n,c['index'],f"{c['metrics']['balanced_accuracy']:.9f}",f"{c['stats']['norm']:.6f}",
                       'selected' if c['index']==r['selected_index'] else ''] for c in r['candidates']]
    t['adulthistory']=table(['Editor','Index','Dev BA','Delta L2','Selection'],adultrows)
    return values,t


def extra_graphics(m,g):
    figs=graphics(m,g)
    q=Graphic(260)
    # Dot plot uses explicit truncated percentage axis: values, not area, carry the comparison.
    for k,(metric,label) in enumerate([('balanced_accuracy','Balanced accuracy'),('accuracy','Ordinary accuracy')]):
        left=100+k*175
        q.text(left+67,12,label,12,'teal','middle')
        for tick in [78,80,82,84]:
            x=left+(tick-78)*21
            q.line(x,35,x,200,'gray');q.text(x,220,str(tick),11,'navy','middle')
        for i,n in enumerate(METHODS[:4]):
            y=52+i*43
            if k==0:q.text(2,y,n,12)
            val=100*m['adult']['methods'][n]['metrics'][metric]
            q.dot(left+(val-78)*21,y,'amber' if n=='joint' else 'teal',4)
            q.text(left+(val-78)*21,y+17,f'{val:.3f}',10.5,'navy','middle')
    q.text(270,249,'Test score (%) · linear axes begin at 78%',11,'navy','middle')
    figs['mainresult']=q.finish()
    q=Graphic(125)
    for i,(a,b) in enumerate([('Question','Can a small edit help?'),('Targets','Census classifier / base LM'),('Compare','Baseline / Sol / Astra / joint'),('Measure','Frozen decisions and likelihoods')]):
        y=14+i*28;q.text(0,y,a,12,'teal');q.text(90,y,b,12)
        if i<3:q.arrow(45,y+8,45,y+22,'amber')
    figs['readermap']=q.finish()
    q=Graphic(120)
    for i in range(24):
        x=6+(i%12)*36;y=10+(i//12)*48
        q.rect(x,y,29,28,'paper','amber' if i==23 else 'teal');q.text(x+14.5,y+14,str(i),10.5,'navy','middle')
    q.text(220,113,'24 decoder blocks · zero-based indices · focus on block 23',11,'navy','middle')
    figs['blocks']=q.finish()
    return figs


def expanded():
    m,g,p=evidence()
    values,tables=bindings(m,g,p)
    source=SOURCE.read_text()
    for k,v in values.items():source=source.replace('@'+k+'@',v)
    if re.search(r'@[a-z_]+@',source):raise ValueError('Unbound prose token')
    return source,tables,extra_graphics(m,g),m


def image_uri(name):
    return 'data:image/png;base64,'+base64.b64encode((ASSETS/name).read_bytes()).decode()


def render(source,tables,figs,mode):
    replacements={};number={'table':0,'figure':0}
    def block(match):
        kind,key,caption=match.groups();typ='table' if kind=='Data' else 'figure'
        number[typ]+=1;cap=f'{typ.title()} {number[typ]}. '+caption
        if kind=='Data': content=tables[key][0 if mode=='tex' else 1]
        elif kind=='Graphic': content=figs[key][0 if mode=='tex' else 1]
        else:content=(r'\includegraphics[width=\linewidth]{'+key+'}' if mode=='tex' else '<img alt="'+html.escape(caption)+'" src="'+image_uri(key)+'">')
        if mode=='tex':
            return r'\begin{samepage}'+ '\n'+r'\begin{center}'+content+r'\end{center}'+ '\n'+r'\Caption{'+cap+'}'+r'\end{samepage}'+'\n'
        marker=f'RESEARCHBLOCK{len(replacements)}END'
        # Captions pass through the same offline math/text renderer as body prose.
        caphtml=run(['pandoc','-f','latex','-t','html5','--mathml'],input=cap).strip()
        replacements[marker]='<figure class="'+typ+'">'+content+'<figcaption>'+caphtml+'</figcaption></figure>'
        return '\n\n'+marker+'\n\n'
    source=re.sub(r'\\(Data|Graphic|Image)\{([^{}]+)\}\{([^\n]+)\}',block,source)
    if mode=='tex':return source
    source=re.sub(r'\\Page\{([^{}]*)\}\{([^{}]*)\}',lambda x:r'\section{'+x[2]+'}\n'+x[1]+'\n',source)
    body=run(['pandoc','-f','latex','-t','html5','--mathml'],input=source)
    for marker,value in replacements.items():body=body.replace('<p>'+marker+'</p>',value)
    if 'RESEARCHBLOCK' in body:raise ValueError('HTML block conversion failed')
    return body


def cover_tex():
    return r'''\thispagestyle{empty}
\begin{tikzpicture}[remember picture,overlay]
\fill[navy] (current page.south west) rectangle (current page.north east);
\node[anchor=south east,inner sep=0] at (current page.south east) {\includegraphics[width=\paperwidth]{weight-space-hero.png}};
\fill[navy,opacity=.92] (current page.north west) rectangle ($(current page.north east)+(0,-123mm)$);
\node[anchor=north west,text=white,text width=166mm,align=left,inner sep=0] at ($(current page.north west)+(23mm,-24mm)$) {
{\sffamily\fontsize{12}{16}\selectfont BBVA AI Innovation\par}\vspace{13mm}
{\sffamily\bfseries\fontsize{36}{41}\selectfont Editing Neural Networks\\with Language Models\par}\vspace{7mm}
{\sffamily\fontsize{16}{21}\selectfont Independent edits, cooperative search\\and what the measurements reveal\par}\vspace{12mm}
{\sffamily\fontsize{15}{20}\selectfont Davut Emre Taşar\par}
{\sffamily\fontsize{11}{15}\selectfont 4 November 2026 · Research report\par}};
\node[anchor=south west,text=white,text width=160mm,inner sep=0] at ($(current page.south west)+(23mm,12mm)$) {\sffamily\fontsize{10.5}{13}\selectfont Conceptual glass artwork · not a measurement of activations};
\end{tikzpicture}\null
'''


def companion(body,m):
    cover='<header class="cover"><div><p>BBVA AI Innovation · 4 November 2026</p><h1>'+TITLE+'</h1><p class="subtitle">Independent edits, cooperative search and what the measurements reveal</p><p>'+AUTHOR+'</p></div><img alt="Conceptual fine-glass neural structure; not measured activations" src="'+image_uri('weight-space-hero.png')+'"><figcaption>Conceptual glass artwork · not a measurement of activations</figcaption></header>'
    receipt={'manifest_sha256':m['manifest_sha256'],'summary_sha256':m['summary_sha256'],
             'prose_sha256':sha(SOURCE),'adult_metrics':{n:r['metrics'] for n,r in m['adult']['methods'].items()},
             'adult_contrasts':m['adult']['contrasts'],'lm_version':'v2',
             'lm_tasks':m['lm']['versions']['v2']['tasks']}
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="author" content="Davut Emre Taşar"><title>Editing Neural Networks with Language Models</title><style>
*{box-sizing:border-box}body{margin:0;background:#fcfaf5;color:#172b42;font:18px/1.65 Georgia,serif}main{max-width:860px;margin:auto;padding:36px}h1,h2,h3{font-family:Arial,sans-serif;line-height:1.15}h2{font-size:34px;border-top:1px solid #167c80;padding-top:32px;margin-top:90px}h3{font-size:22px}a{color:#167c80;overflow-wrap:anywhere}figure{margin:32px 0}figure img,svg{width:100%;height:auto}figcaption{font:15px/1.5 Arial,sans-serif;margin-top:12px}figcaption p{margin:0}table{width:100%;border-collapse:collapse;font:15px/1.6 Arial,sans-serif}td,th{text-align:right;padding:8px 5px;border-bottom:1px solid #d9ddde}td:first-child,th:first-child{text-align:left}pre{white-space:pre-wrap;font-size:15px}math{font-size:1.08em}.cover{background:#172b42;color:#fff;position:relative;max-width:1100px;margin:auto}.cover div{padding:55px 50px 28px;position:relative;z-index:1}.cover h1{font-size:58px;max-width:850px;margin:35px 0}.cover .subtitle{font-size:24px;max-width:650px}.cover img{width:100%;display:block}.cover figcaption{padding:14px 50px;margin:0}@media(max-width:600px){main{padding:22px}table{font-size:12px}.cover h1{font-size:38px}.cover div{padding:32px 22px}}@media print{h2{break-before:page}figure{break-inside:avoid}}
</style></head><body>'''+cover+'<main><p><a href="RESEARCH_REPORT.pdf">Download the research report PDF</a></p>'+body+'</main><script type="application/json" id="frozen-research-data">'+json.dumps(receipt,sort_keys=True).replace('<',r'\u003c')+'</script></body></html>'


def build():
    for tool in [TEX,'pandoc','pdftotext','pdfinfo']:
        if not shutil.which(tool):raise RuntimeError('Required local tool unavailable: '+tool)
    source,tables,figs,m=expanded()
    tex=PREAMBLE+cover_tex()+render(source,tables,figs,'tex')+r'\end{document}'
    output=companion(render(source,tables,figs,'html'),m)
    public_scan(tex);public_scan(output)
    with tempfile.TemporaryDirectory(prefix='research-report-') as tmp:
        td=Path(tmp)
        for name in ['weight-space-hero.png','reference-article-title.png']:
            shutil.copyfile(ASSETS/name,td/name)
        (td/'research.tex').write_text(tex)
        for _ in range(2):run([TEX,'-no-shell-escape','-interaction=nonstopmode','-halt-on-error','research.tex'],td)
        log=(td/'research.log').read_text()
        problems=[line for line in log.splitlines() if any(x in line for x in ['Overfull','Missing character:','undefined references'])]
        if problems:raise RuntimeError('TeX layout/font issue: '+'\n'.join(problems))
        text=run(['pdftotext',str(td/'research.pdf'),'-']);public_scan(text)
        if AUTHOR not in text:raise ValueError('PDF author extraction failed')
        pages=int(re.search(r'Pages:\s+(\d+)',run(['pdfinfo',str(td/'research.pdf')]))[1])
        if not 22<=pages<=26:raise ValueError(f'Expected 22–26 substantive pages; got {pages}')
        OUT.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(td/'research.pdf',OUT/'RESEARCH_REPORT.pdf')
    (OUT/'RESEARCH_REPORT.html').write_text(output)
    evidence()
    print(json.dumps({'status':'BUILT','pages':pages,'manifest_sha256':m['manifest_sha256'],
                      'prose_sha256':sha(SOURCE),'pdf_sha256':sha(OUT/'RESEARCH_REPORT.pdf'),
                      'artifacts':['artifacts/bbva-research/RESEARCH_REPORT.pdf','artifacts/bbva-research/RESEARCH_REPORT.html']}))


if __name__=='__main__':build()
