#!/usr/bin/env node
/**
 * Smoke tests for file-browser. Boots the server on a random free port,
 * fires HTTP requests at every route, asserts status + key behaviors,
 * shuts down. No external runner — exits non-zero on first failure.
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const { createHttpServer } = require('../lib/http-server.cjs');
const { findAvailablePort } = require('../lib/port-finder.cjs');
const { classify, isMedia } = require('../lib/media-renderer.cjs');

let failures = 0;
function test(name, fn) {
  return Promise.resolve()
    .then(() => fn())
    .then(() => console.log(`✓ ${name}`))
    .catch((err) => {
      failures++;
      console.error(`✗ ${name}`);
      console.error(`  ${err.message}`);
    });
}

function get(port, urlPath, headers = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request(
      { host: '127.0.0.1', port, path: urlPath, method: 'GET', headers },
      (res) => {
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () =>
          resolve({
            status: res.statusCode,
            headers: res.headers,
            body: Buffer.concat(chunks)
          })
        );
      }
    );
    req.on('error', reject);
    req.end();
  });
}

async function main() {
  // Sandbox with a fake image, a markdown file, and a subdir
  const sandbox = fs.mkdtempSync(path.join(os.tmpdir(), 'file-browser-test-'));
  const imgPath = path.join(sandbox, 'sample.png');
  // 1x1 transparent PNG
  fs.writeFileSync(
    imgPath,
    Buffer.from(
      '89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c63000100000005000101a30a3aaa0000000049454e44ae426082',
      'hex'
    )
  );
  const mdPath = path.join(sandbox, 'note.md');
  fs.writeFileSync(mdPath, '# Hello\n\nA paragraph with *italic* and `code`.\n');
  const subDir = path.join(sandbox, 'sub');
  fs.mkdirSync(subDir);

  const assetsDir = path.join(__dirname, '..', '..', 'assets');
  const port = await findAvailablePort(3590);
  const server = createHttpServer({ assetsDir, allowedDirs: [sandbox, assetsDir] });

  await new Promise((r) => server.listen(port, '127.0.0.1', r));

  await test('classify image/video/audio', () => {
    if (classify('foo.png') !== 'image') throw new Error('png not image');
    if (classify('foo.mp4') !== 'video') throw new Error('mp4 not video');
    if (classify('foo.mp3') !== 'audio') throw new Error('mp3 not audio');
    if (classify('foo.txt') !== null) throw new Error('txt should be null');
    if (!isMedia('a.JPG')) throw new Error('JPG case-insensitive failed');
  });

  await test('GET / returns welcome', async () => {
    const r = await get(port, '/');
    if (r.status !== 200) throw new Error(`status ${r.status}`);
    if (!r.body.toString().includes('file-browser')) throw new Error('missing title');
  });

  await test('GET /browse renders gallery', async () => {
    const r = await get(port, `/browse?dir=${encodeURIComponent(sandbox)}`);
    if (r.status !== 200) throw new Error(`status ${r.status}`);
    const html = r.body.toString();
    if (!html.includes('sample.png')) throw new Error('missing sample.png');
    if (!html.includes('Folders')) throw new Error('missing Folders section');
  });

  await test('GET /view renders single image', async () => {
    const r = await get(port, `/view?file=${encodeURIComponent(imgPath)}`);
    if (r.status !== 200) throw new Error(`status ${r.status}`);
    if (!r.body.toString().includes('<img class="media"')) throw new Error('no img tag');
  });

  await test('GET /view dispatches markdown to novel-theme', async () => {
    const r = await get(port, `/view?file=${encodeURIComponent(mdPath)}`);
    if (r.status !== 200) throw new Error(`status ${r.status}`);
    const html = r.body.toString();
    if (!/<h1[^>]*>Hello/.test(html)) throw new Error('h1 Hello missing');
    if (!html.includes('<em>italic</em>')) throw new Error('italic missing');
  });

  await test('Gallery surfaces markdown in Documents section', async () => {
    const r = await get(port, `/browse?dir=${encodeURIComponent(sandbox)}`);
    const html = r.body.toString();
    if (!html.includes('Documents (1)')) throw new Error('docs section missing');
    if (!html.includes('note.md')) throw new Error('note.md not listed');
  });

  await test('GET /file streams with correct mime', async () => {
    const r = await get(port, '/file' + imgPath);
    if (r.status !== 200) throw new Error(`status ${r.status}`);
    if (r.headers['content-type'] !== 'image/png')
      throw new Error(`mime ${r.headers['content-type']}`);
    if (r.headers['accept-ranges'] !== 'bytes')
      throw new Error('accept-ranges header missing');
  });

  await test('Range request returns 206 + Content-Range', async () => {
    const r = await get(port, '/file' + imgPath, { Range: 'bytes=0-9' });
    if (r.status !== 206) throw new Error(`expected 206 got ${r.status}`);
    if (!/^bytes 0-9\/\d+$/.test(r.headers['content-range']))
      throw new Error(`bad content-range ${r.headers['content-range']}`);
    if (r.body.length !== 10) throw new Error(`expected 10 bytes got ${r.body.length}`);
  });

  await test('path traversal is blocked', async () => {
    const evil = '/etc/passwd';
    const r = await get(port, '/file' + evil);
    if (r.status !== 403) throw new Error(`expected 403 got ${r.status}`);
  });

  await test('missing query params return 400', async () => {
    const r = await get(port, '/view');
    if (r.status !== 400) throw new Error(`expected 400 got ${r.status}`);
  });

  await test('non-existent file returns 404', async () => {
    const ghost = path.join(sandbox, 'no-such-file.png');
    const r = await get(port, `/view?file=${encodeURIComponent(ghost)}`);
    if (r.status !== 404) throw new Error(`expected 404 got ${r.status}`);
  });

  server.close();
  fs.rmSync(sandbox, { recursive: true, force: true });

  if (failures > 0) {
    console.error(`\n${failures} test(s) failed`);
    process.exit(1);
  }
  console.log('\nAll tests passed');
}

main().catch((err) => {
  console.error('Test runner crashed:', err);
  process.exit(1);
});
