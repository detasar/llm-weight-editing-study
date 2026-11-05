import {mkdir, cp, readFile, writeFile, rm} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root = fileURLToPath(new URL('../', import.meta.url));
export const version = '2026-11-04';
export const deliveryFiles = ['START_PRESENTATION.html', 'RESEARCH_REPORT.html', 'RESEARCH_REPORT.pdf', 'PRESENTATION_BACKUP.pdf', 'BBVA_RESEARCH_OFFLINE.zip', 'README.txt', 'THIRD_PARTY_NOTICES.txt', 'TURKCE_ANLATIM.html', 'TURKCE_ANLATIM.md', 'TURKCE_ANLATIM.pdf', 'MOTION_PREVIEW.mp4', 'DELIVERY_PREVIEW.jpg'];
const documents = ['DELIVERY.md', 'KNOWLEDGE_RIP.md', 'METHODS.md', 'REPRODUCE.md', 'SCORER.md', 'VERSIONS.md'];
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
export async function verifyPublication(directory = path.join(root, 'publication', version)) {
  const manifest = JSON.parse(await readFile(path.join(directory, 'artifact-manifest.json'), 'utf8'));
  for (const name of deliveryFiles) {
    const bytes = await readFile(path.join(directory, name));
    const expected = manifest.files[name];
    if (!expected || bytes.length !== expected.bytes || hash(bytes) !== expected.sha256) throw Error(`Delivery binding differs: ${name}`);
  }
  return manifest;
}
export async function prepare(destination) {
  await verifyPublication(); // Fail on absent or changed accepted artifacts; never publish placeholders.
  // Only approved public material is staged. A fresh staging tree removes stale deck/note copies.
  await rm(destination, {recursive: true, force: true});
  await mkdir(path.join(destination, 'source/docs'), {recursive: true});
  for (const dir of ['configs', 'prompts', 'data']) await cp(path.join(root, dir), path.join(destination, 'source', dir), {recursive: true});
  await cp(path.join(root, 'presentation/revised'), path.join(destination, 'source/presentation/revised'), {recursive: true});
  for (const name of documents) {
    const text = (await readFile(path.join(root, 'docs', name), 'utf8')).replaceAll('../publication/', '../../publication/');
    await writeFile(path.join(destination, 'source/docs', name), text);
  }
  for (const name of ['README.md', 'CITATION.cff', 'LICENSE', 'CONTENT_LICENSE']) {
    const text = (await readFile(path.join(root, name), 'utf8')).replaceAll('(publication/', '(../publication/');
    await writeFile(path.join(destination, 'source', name), text);
  }
  await cp(path.join(root, 'report/figures'), path.join(destination, 'source/report/figures'), {recursive: true});
  await cp(path.join(root, 'assets/art'), path.join(destination, 'source/assets/art'), {recursive: true});
  await mkdir(path.join(destination, 'publication', version), {recursive: true});
  for (const name of [...deliveryFiles, 'artifact-manifest.json']) await cp(path.join(root, 'publication', version, name), path.join(destination, 'publication', version, name));
  const m = JSON.parse(await readFile(path.join(root, 'data/manifest.json'), 'utf8'));
  await writeFile(path.join(destination, 'source/manifest-identity.txt'), m.manifest_sha256 + '\n');
}
// Keep accepted source assets untouched; Vite reads only this generated allowlisted tree.
export async function preparePublic() {
  const destination = path.join(root, 'web/delivery-public');
  await prepare(destination);
  for (const name of ['story-assets', 'licenses']) await cp(path.join(root, 'web/public', name), path.join(destination, name), {recursive: true});
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await preparePublic();
