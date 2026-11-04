import './style.css';
const publication = 'publication/2026-11-04/';
const source = 'source/';
document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
<header class="hero">
  <div class="hero-copy"><p class="eyebrow">BBVA AI Innovation · 4 November 2026</p>
  <h1>Editing Neural Networks<br>with Language Models</h1>
  <p class="byline">Davut Emre Taşar</p>
  <p class="intro">Can a language model improve a decision rule by changing a few weights?</p>
  <a class="button" href="${publication}START_PRESENTATION.html">Start the 45-minute presentation <span aria-hidden="true">↗</span></a>
  <p class="detail">One continuous story · 33 chapters · written explanation</p></div>
  <figure><img src="story-assets/weight-space-hero.png" alt="Conceptual glass neural network with a highlighted intervention" width="1536" height="1024"><figcaption>Conceptual illustration; not measured network geometry.</figcaption></figure>
</header>
<main id="main">
<section aria-labelledby="question"><p class="eyebrow">The experiment</p><h2 id="question">Two targets. One editing question.</h2>
<p>The <strong>UCI Adult census-income dataset</strong> asks whether a person's annual income exceeds $50,000. Here a small classifier starts with a permanent weight lesion. <strong>SmolLM2-1.7B</strong> starts intact: we test bounded weight edits on ARC-Easy science questions and PIQA physical reasoning.</p>
<p><strong>Sol and Astra</strong> independently propose edits from the same origin. <strong>Joint</strong> starts from that origin with access to their development histories. Selection can retain the unchanged candidate zero. Adult's primary metric, <strong>balanced accuracy</strong>, gives each class equal weight; the language-model primary metric, <strong>acc_norm</strong>, normalizes answer likelihood by character length.</p></section>
<section aria-labelledby="results"><p class="eyebrow">What the measurements show</p><h2 id="results">A small tradeoff. An unchanged language model.</h2>
<div class="results"><article><h3>UCI Adult</h3><p class="number">+0.43 <small>percentage points</small></p><p>Sol's balanced-accuracy change: <strong>78.59% → 79.02%</strong>. Ordinary accuracy falls from 82.86% to 82.63%, and probability quality worsens. Joint reaches 78.97% balanced accuracy.</p></article>
<article><h3>SmolLM2 · completed v2</h3><p class="number">Candidate zero</p><p>Baseline, Sol, Astra and joint select the same unchanged weight state. ARC-Easy acc_norm is <strong>73.44%</strong> (512 examples); PIQA is <strong>78.52%</strong> (256 examples).</p></article></div>
<p class="detail">One exploratory seed-101 session. Paired intervals measure example uncertainty, not variation across editor sessions. Unequal candidate budgets and prior panel exposure limit comparisons; these results do not establish cooperative synergy.</p>
<p><a href="${source}data/manifest.json">Canonical results and exact values →</a></p></section>
<section aria-labelledby="read"><p class="eyebrow">Read, present, reproduce</p><h2 id="read">One publication, online or offline.</h2>
<div class="downloads"><a href="${publication}RESEARCH_REPORT.pdf"><strong>Research PDF</strong><span>26-page reader report</span></a><a href="${publication}RESEARCH_REPORT.html"><strong>Research HTML</strong><span>Self-contained browser edition</span></a><a href="${publication}PRESENTATION_BACKUP.pdf"><strong>Presentation PDF backup</strong><span>59 captured explanatory states</span></a><a href="${publication}BBVA_RESEARCH_OFFLINE.zip" download><strong>Download offline ZIP</strong><span>Presentation, reader report and PDF backup</span></a></div>
<p><strong>After unzipping, double-click START_PRESENTATION.html.</strong> Click Start presentation. Space pauses or resumes; Left/Right moves between explanatory cues. No server, installation, API key or internet connection is needed for playback.</p>
<p>The presentation uses synchronized written explanation. Reduced motion and a 2D view are available in its controls.</p>
<nav class="resources" aria-label="Research resources"><a href="${source}docs/REPRODUCE.md">Reproducibility</a><a href="${source}docs/METHODS.md">Methods</a><a href="${source}docs/SCORER.md">Scoring</a><a href="${source}docs/DELIVERY.md">Delivery guide</a><a href="https://github.com/detasar/llm-weight-editing-study">Sources on GitHub</a><a href="${publication}artifact-manifest.json">Artifact checksums</a></nav></section>
</main>
<footer><p>Davut Emre Taşar · BBVA AI Innovation · 2026</p><p>Inspired by Takehi, Teoh, Zhang and Khattab, <a href="https://rikiyat.github.io/blog/weight-space-programming/">Sparks of Weight-Space Programming</a>. Their title-page excerpt remains third-party copyright.</p><p>Code: <a href="${source}LICENSE">MIT</a> · Original report, artwork and derived numeric data: <a href="${source}CONTENT_LICENSE">CC BY 4.0</a> · <a href="${publication}THIRD_PARTY_NOTICES.txt">Third-party notices</a></p></footer>`;
