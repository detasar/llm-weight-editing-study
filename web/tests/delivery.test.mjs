import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile, mkdtemp, rm, mkdir, writeFile, readdir} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {prepare, verifyPublication, deliveryFiles, version} from '../prepare.mjs';
const root = fileURLToPath(new URL('../../', import.meta.url));
const publication = path.join(root, 'publication', version);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const text = name => readFile(path.join(root, name), 'utf8');
const historicalBinaries = ['presentation/presentation.pdf', 'presentation/weight-editing-offline.zip', 'report/report.pdf'];
const forbidden = /SPEAKER_NOTES|PRIVATE_NARRATOR|narrator-chapter-input|private_runs|\/Users\/|\/private\/tmp\/|\/tmp\/slm-|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|sk-or-v1-[a-z0-9]{20}/i;

// Frozen baseline from acceptance, independent of the generated delivery manifest.
test('all six scientific inputs retain their accepted byte identity', async () => {
  const hashes = {
    'manifest.json':'e7fb895f7d06c5caaefbbf6ef8be62736ca398b81d64db983542c1f86a525952',
    'adult_graph.json':'870e2badefed3fbe615ce432bdce572b2a7ccb20bdb248d04825643d622ee0d8',
    'adult_predictions.json':'286877d6ac28d7ba8765018f1fa4b0d0c5f7f62475ee5d42b1034a960f08ca81',
    'lm_v1_predictions.json':'a821a10fbf199dadea80e361a822b08766d7d7abcad415bfa28a890353a4d1a7',
    'lm_v2_predictions.json':'a821a10fbf199dadea80e361a822b08766d7d7abcad415bfa28a890353a4d1a7',
    'lm_v2_frozen_patches.json':'94ea5d9f46c56a76fcd6be2d0960de4e98bd528e585ab6dd3fc3be897545de48'
  };
  for (const [name, expected] of Object.entries(hashes)) assert.equal(hash(await readFile(path.join(root, 'data', name))), expected, name);
});

test('actual publication files bind their sizes and hashes, including the single ZIP', async () => {
  const manifest = await verifyPublication();
  assert.equal(manifest.author, 'Davut Emre Taşar');
  assert.equal(manifest.event, 'BBVA AI Innovation');
  assert.equal(manifest.duration_seconds, 2700);
  assert.equal(manifest.report_pages, 26);
  assert.equal(manifest.chapters, 33);
  // A corrupt copy must fail closed rather than silently publish stale bytes.
  const temp = await mkdtemp(path.join(tmpdir(), 'delivery-binding-'));
  try {
    await writeFile(path.join(temp, 'artifact-manifest.json'), JSON.stringify(manifest));
    await writeFile(path.join(temp, 'START_PRESENTATION.html'), 'corrupt');
    await assert.rejects(verifyPublication(temp), /Delivery binding differs/);
  } finally { await rm(temp, {recursive: true, force: true}); }
});

test('landing explains targets before outcomes and uses current, base-relative destinations', async () => {
  const main = await text('web/src/main.ts');
  assert.ok(main.indexOf('UCI Adult census-income') < main.indexOf('What the measurements show'));
  assert.ok(main.indexOf('starts intact') < main.indexOf('What the measurements show'));
  assert.match(main, /double-click START_PRESENTATION\.html/);
  assert.match(main, /Davut Emre Taşar/);
  assert.match(main, /BBVA AI Innovation/);
  assert.doesNotMatch(main, /22.scene|3.minute|\?view=|launch\.py|SPEAKER_NOTES/);
  const m = JSON.parse(await text('data/manifest.json'));
  const percent = value => (100 * value).toFixed(2) + '%';
  for (const method of ['baseline', 'Sol', 'joint']) assert.ok(main.includes(percent(m.adult.methods[method].metrics.balanced_accuracy)));
  const html = await text('web/index.html');
  assert.match(html, /name="author" content="Davut Emre Taşar"/);
  for (const file of ['docs/SPEAKER_NOTES.md','presentation/index.html','report/index.html']) assert.equal(existsSync(path.join(root, file)), false, file);
  for (const file of historicalBinaries) {
    assert.ok(existsSync(path.join(root, file)), file);
    for (const current of ['web/src/main.ts', 'web/index.html', 'README.md', ...((await readdir(path.join(root, 'docs'))).filter(name => name.endsWith('.md')).map(name => `docs/${name}`))]) {
      assert.ok(!(await text(current)).includes(file), `${current} references ${file}`);
    }
  }
});

test('clean preparation excludes stale files and every landing link resolves under the Pages base', async () => {
  const temp = await mkdtemp(path.join(tmpdir(), 'delivery-stage-'));
  try {
    await mkdir(path.join(temp, 'source/docs'), {recursive: true});
    await writeFile(path.join(temp, 'source/docs/obsolete.md'), 'stale private copy');
    await prepare(temp);
    assert.equal(existsSync(path.join(temp, 'source/docs/obsolete.md')), false);
    const main = (await text('web/src/main.ts')).replaceAll('${publication}', `publication/${version}/`).replaceAll('${source}', 'source/');
    for (const [, href] of main.matchAll(/href="([^"]+)"/g)) {
      if (/^https:/.test(href)) continue;
      assert.ok(!href.startsWith('/'), href);
      const url = new URL(href, 'https://detasar.github.io/llm-weight-editing-study/');
      assert.ok(url.pathname.startsWith('/llm-weight-editing-study/'), href);
      assert.ok(existsSync(path.join(temp, href)), href);
    }
    async function scan(directory) {
      for (const entry of await readdir(directory, {withFileTypes: true})) {
        const filename = path.join(directory, entry.name);
        assert.doesNotMatch(entry.name, forbidden);
        assert.ok(!historicalBinaries.some(file => path.basename(file) === entry.name), `Historical binary staged: ${filename}`);
        if (entry.isDirectory()) await scan(filename);
        else if (/\.(?:html|md|txt|json|cff)$|LICENSE$/.test(filename)) assert.doesNotMatch(await readFile(filename, 'utf8'), forbidden, filename);
      }
    }
    await scan(temp);
    // Markdown delivery links remain readable in the staged source hierarchy too.
    const delivery = await readFile(path.join(temp, 'source/docs/DELIVERY.md'), 'utf8');
    for (const [, href] of delivery.matchAll(/\]\(([^)]+)\)/g)) if (!/^https:/.test(href)) assert.ok(existsSync(path.resolve(temp, 'source/docs', href)), href);
  } finally { await rm(temp, {recursive: true, force: true}); }
});

test('both HTML editions have no external runtime dependencies or private material', async () => {
  for (const name of ['START_PRESENTATION.html', 'RESEARCH_REPORT.html']) {
    const html = await readFile(path.join(publication, name), 'utf8');
    assert.doesNotMatch(html, forbidden, name);
    assert.doesNotMatch(html, /<script[^>]+\bsrc\s*=|<link[^>]+\bhref\s*=/i, name);
    const markup = html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '');
    for (const [, src] of markup.matchAll(/<(?:img|iframe|video|audio|source)\b[^>]*\bsrc=["']([^"']+)["']/gi)) assert.ok(src.startsWith('data:'), `${name}: ${src.slice(0,80)}`);
    for (const [, src] of markup.matchAll(/url\(["']?([^)'"\s]+)/gi)) assert.ok(src.startsWith('data:') || src.startsWith('#'), `${name}: ${src.slice(0,80)}`);
    assert.match(html, /Davut Emre Taşar/);
  }
});

test('offline ZIP contains only matching deliverables and a verified inner manifest', () => {
  // Python standard library reads compressed members without extracting or executing them.
  const result = spawnSync('python3', ['-c', String.raw`
import hashlib,json,sys,zipfile
from pathlib import Path
p=Path(sys.argv[1])
with zipfile.ZipFile(p/'BBVA_RESEARCH_OFFLINE.zip') as z:
    assert z.testzip() is None
    entries={Path(n).name:n for n in z.namelist()}
    expected=set(json.loads(sys.argv[2]))-{'BBVA_RESEARCH_OFFLINE.zip'}
    assert set(entries)==expected|{'artifact-manifest.json'},entries
    assert len(entries)==len(z.namelist())
    manifest=json.loads(z.read(entries['artifact-manifest.json']))
    for name in expected:
        b=z.read(entries[name])
        assert b==(p/name).read_bytes(),name
        assert len(b)==manifest['files'][name]['bytes'],name
        assert hashlib.sha256(b).hexdigest()==manifest['files'][name]['sha256'],name
    for n in z.namelist():
        assert '..' not in Path(n).parts and not n.startswith('/'),n
`, publication, JSON.stringify(deliveryFiles)], {encoding: 'utf8'});
  assert.equal(result.status, 0, result.stderr || result.stdout);
});
