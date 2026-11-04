"""Focused editorial and frozen-binding checks; the connector runs PDF build separately."""
import importlib.util
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('research_report',ROOT/'scripts/build_research_report.py')
report=importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class Figures(HTMLParser):
    def __init__(self):
        super().__init__(); self.figures=[]; self.current=None; self.depth=0
    def handle_starttag(self,tag,attrs):
        if tag=='figure': self.current=[]
        if self.current is not None and tag in ['table','svg','img','figcaption']:
            self.current.append(tag)
    def handle_endtag(self,tag):
        if tag=='figure': self.figures.append(self.current); self.current=None


class ResearchReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source,cls.tables,cls.figs,cls.manifest=report.expanded()
        cls.html=report.companion(report.render(cls.source,cls.tables,cls.figs,'html'),cls.manifest)

    def test_identity_and_definitions_precede_results(self):
        self.assertIn('Davut Emre Taşar',self.html)
        self.assertIn('BBVA AI Innovation',self.html)
        self.assertIn('pdfauthor={Davut Emre Taşar}',report.PREAMBLE)
        for definition in ['What the Adult classifier predicts','Weights persist; activations respond',
                           'Four conditions, one starting point','Two meanings of a correct classifier']:
            self.assertLess(self.source.index(definition),self.source.index('The improvement is metric-specific'))
        self.assertLess(self.source.index('An intact compact language model'),self.source.index('Four names, one exact weight state'))
        self.assertNotIn('Davut Emre (detasar)',self.html)

    def test_every_measurement_visual_has_immediate_caption(self):
        p=Figures();p.feed(self.html)
        self.assertGreater(len(p.figures),20)
        for tags in p.figures:
            self.assertEqual(tags[-1],'figcaption')
            self.assertEqual(tags.count('figcaption'),1)
            self.assertIn(tags[0],['table','svg','img'])
        self.assertEqual(len(p.figures),len(re.findall(r'\\(?:Graphic|Image|Data)\{',self.source)))

    def test_exact_numeric_bindings_and_denominators(self):
        m=self.manifest
        receipt=json.loads(re.search(r'id="frozen-research-data">(.*?)</script>',self.html,re.S)[1])
        self.assertEqual(receipt['adult_contrasts'],m['adult']['contrasts'])
        self.assertEqual(receipt['lm_tasks'],m['lm']['versions']['v2']['tasks'])
        for n in report.METHODS:
            for metric in report.METRICS:
                value=m['adult']['methods'][n]['metrics'][metric]
                self.assertIn(f'{value:.6f}',self.tables['quality'][1])
        for value in ['376/512','396/512','201/256','205/256']:
            self.assertIn(value,self.tables['lmfinal'][1])
        self.assertIn('2,048-row feedback panel',self.source)
        self.assertIn('6,513',self.source)
        self.assertIn('256-row diagnostic panel',self.source)
        self.assertEqual(m['adult']['contrasts']['Sol_minus_baseline']['paired_counts']['rescues'],65)
        self.assertEqual(m['adult']['contrasts']['Sol_minus_baseline']['paired_counts']['regressions'],102)
        self.assertIn('invalid / unscored',self.tables['lmtrajectory'][1])

    def test_tampered_frozen_input_fails_closed(self):
        original=report.sha
        with patch.object(report,'sha',side_effect=lambda p:'0'*64 if p.name=='adult_graph.json' else original(p)):
            with self.assertRaisesRegex(ValueError,'Frozen input differs'):
                report.evidence()

    def test_standalone_offline_render_and_private_exclusion(self):
        self.assertIn('<math',self.html)
        self.assertIn('data:image/png;base64,',self.html)
        self.assertNotRegex(self.html,r'(?:src|href)="https?://[^\"]+\.(?:js|css|png|woff)')
        self.assertNotIn('RESEARCHBLOCK',self.html)
        self.assertNotIn('PRIVATE_NARRATOR',self.html)
        self.assertNotRegex(self.html,r'\bfetch\s*\(|XMLHttpRequest|<script[^>]+src=')
        report.public_scan(self.html)
        # No public build path discovers or opens private narration, even indirectly.
        code=(ROOT/'scripts/build_research_report.py').read_text()
        self.assertNotIn('rglob(',code)
        self.assertNotIn('urllib',code)
        self.assertNotIn('requests.',code)
        self.assertNotIn('imagegen',code)
        self.assertNotIn('readable-report-worktree',code)

    def test_pdf_generation_contract_and_artwork(self):
        self.assertEqual(report.OUT,ROOT/'artifacts/bbva-research')
        self.assertIn('weight-space-hero.png',report.cover_tex())
        credits=json.loads((report.ASSETS/'credits.json').read_text())
        for name in ['weight-space-hero.png','reference-article-title.png']:
            self.assertEqual(report.sha(report.ASSETS/name),credits[name]['sha256'])
        self.assertGreater(len(self.source.split()),4000)
        self.assertEqual(len(re.findall(r'\\Page\{',self.source)),25)


if __name__=='__main__': unittest.main()
