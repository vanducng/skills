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
const { classify: classifyText, sniffBinary, isText } = require('../lib/text-renderer.cjs');

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
  // Code, plain text, JSON, binary fixtures
  const jsPath = path.join(sandbox, 'hello.js');
  fs.writeFileSync(jsPath, "const greet = (name) => `hi ${name}`;\nconsole.log(greet('world'));\n");
  const txtPath = path.join(sandbox, 'notes.txt');
  fs.writeFileSync(txtPath, 'plain text line\nanother line\n');
  const jsonPath = path.join(sandbox, 'data.json');
  fs.writeFileSync(jsonPath, '{"a":1,"b":[2,3]}');
  const binPath = path.join(sandbox, 'mystery.dat');
  fs.writeFileSync(binPath, Buffer.from([0x00, 0xff, 0x00, 0x42, 0x00, 0x99]));
  const pdfPath = path.join(sandbox, 'doc.pdf');
  fs.writeFileSync(pdfPath, '%PDF-1.4\n%fake pdf\n');

  const assetsDir = path.join(__dirname, '..', '..', 'assets');
  const port = await findAvailablePort(3590);
  const server = createHttpServer({ assetsDir, allowedDirs: [sandbox, assetsDir], treeRoot: sandbox });

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

  await test('GET /file with Sec-Fetch-Dest: document redirects to /view (sidebar wrapper)', async () => {
    const r = await get(port, '/file' + imgPath, {
      Accept: 'text/html,application/xhtml+xml',
      'Sec-Fetch-Dest': 'document'
    });
    if (r.status !== 302) throw new Error(`expected 302 got ${r.status}`);
    const loc = r.headers.location || '';
    if (!loc.startsWith('/view?file=')) throw new Error(`bad location ${loc}`);
    if (!loc.includes(encodeURIComponent(imgPath))) throw new Error(`location missing path: ${loc}`);
  });

  await test('GET /file from <iframe> streams raw (no recursive /view redirect)', async () => {
    // Regression: HTML viewer's <iframe src=/file/...> sends Accept: text/html
    // with Sec-Fetch-Dest: iframe. Redirecting on Accept alone caused the
    // iframe to reload the chrome → infinite nesting.
    const r = await get(port, '/file' + imgPath, {
      Accept: 'text/html,application/xhtml+xml',
      'Sec-Fetch-Dest': 'iframe'
    });
    if (r.status !== 200) throw new Error(`expected 200 got ${r.status}`);
    if (r.headers['content-type'] !== 'image/png')
      throw new Error(`expected raw stream, got ${r.headers['content-type']}`);
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

  await test('GET /api/tree lists directory entries as JSON', async () => {
    const r = await get(port, `/api/tree?dir=${encodeURIComponent(sandbox)}`);
    if (r.status !== 200) throw new Error(`status ${r.status}`);
    const data = JSON.parse(r.body.toString());
    if (data.path !== sandbox) throw new Error('path mismatch');
    const names = data.entries.map((e) => e.name);
    if (!names.includes('sample.png')) throw new Error('sample.png missing');
    if (!names.includes('note.md')) throw new Error('note.md missing');
    if (!names.includes('sub')) throw new Error('sub dir missing');
    const md = data.entries.find((e) => e.name === 'note.md');
    if (md.fileType !== 'markdown') throw new Error('markdown not classified');
    const sub = data.entries.find((e) => e.name === 'sub');
    if (sub.kind !== 'dir') throw new Error('sub not dir');
  });

  await test('classify text/code/data/pdf', () => {
    if (classifyText('foo.js') !== 'code') throw new Error('js not code');
    if (classifyText('foo.txt') !== 'text') throw new Error('txt not text');
    if (classifyText('foo.json') !== 'data') throw new Error('json not data');
    if (classifyText('foo.pdf') !== 'pdf') throw new Error('pdf not pdf');
    if (classifyText('foo.png') !== null) throw new Error('png leaked into text');
    if (!isText('a.PY')) throw new Error('PY case-insensitive failed');
  });

  await test('sniffBinary detects null byte', () => {
    if (!sniffBinary(Buffer.from([0x48, 0x00, 0x49]))) throw new Error('miss null');
    if (sniffBinary(Buffer.from('hello world'))) throw new Error('false positive');
  });

  await test('GET /view renders code with hljs', async () => {
    const r = await get(port, `/view?file=${encodeURIComponent(jsPath)}`);
    if (r.status !== 200) throw new Error(`status ${r.status}`);
    const html = r.body.toString();
    if (!html.includes('hljs')) throw new Error('no hljs class');
    if (!html.includes('language-javascript')) throw new Error('lang not javascript');
    if (!html.includes('class="ln"')) throw new Error('line numbers missing');
    if (!html.includes('id="copy-btn"')) throw new Error('copy button missing');
  });

  await test('GET /view renders plain text', async () => {
    const r = await get(port, `/view?file=${encodeURIComponent(txtPath)}`);
    if (r.status !== 200) throw new Error(`status ${r.status}`);
    const html = r.body.toString();
    if (!html.includes('plain text line')) throw new Error('content missing');
    if (!html.includes('class="ln"')) throw new Error('line numbers missing');
  });

  await test('GET /view pretty-prints JSON', async () => {
    const r = await get(port, `/view?file=${encodeURIComponent(jsonPath)}`);
    if (r.status !== 200) throw new Error(`status ${r.status}`);
    const html = r.body.toString();
    // hljs escapes quotes to &quot; — pretty-print indents to multi-line.
    if (!/&quot;a&quot;/.test(html)) throw new Error('json key missing');
    if (!/data-n="3"/.test(html)) throw new Error('json not pretty-printed (no line 3)');
  });

  await test('GET /view shows "binary" card for null-byte file', async () => {
    const r = await get(port, `/view?file=${encodeURIComponent(binPath)}`);
    if (r.status !== 200) throw new Error(`status ${r.status}`);
    const html = r.body.toString();
    if (!html.includes('looks binary')) throw new Error('binary notice missing');
    if (!html.includes('Open raw')) throw new Error('raw fallback link missing');
  });

  await test('classify html as html kind', () => {
    if (classifyText('foo.html') !== 'html') throw new Error('html not html');
    if (classifyText('foo.HTM') !== 'html') throw new Error('HTM not html');
  });

  await test('GET /view renders HTML via <iframe>', async () => {
    const htmlPath = path.join(sandbox, 'page.html');
    fs.writeFileSync(htmlPath, '<!doctype html><h1>Hi</h1>');
    const r = await get(port, `/view?file=${encodeURIComponent(htmlPath)}`);
    if (r.status !== 200) throw new Error(`status ${r.status}`);
    const html = r.body.toString();
    if (!/<iframe[^>]*class="html-frame"/.test(html)) throw new Error('iframe missing');
    if (!/sandbox=/.test(html)) throw new Error('sandbox attr missing');
    // raw=1 toggle returns source view
    const raw = await get(port, `/view?file=${encodeURIComponent(htmlPath)}&raw=1`);
    if (!/class="ln"/.test(raw.body.toString())) throw new Error('raw=1 should show source with line numbers');
  });

  await test('GET /view renders PDF via <embed>', async () => {
    const r = await get(port, `/view?file=${encodeURIComponent(pdfPath)}`);
    if (r.status !== 200) throw new Error(`status ${r.status}`);
    const html = r.body.toString();
    if (!/<embed[^>]*application\/pdf/.test(html)) throw new Error('embed missing');
  });

  await test('?root= override rebases sidebar treeRoot', async () => {
    // Default treeRoot is sandbox; override to subDir.
    const v = await get(port, `/view?file=${encodeURIComponent(imgPath)}&root=${encodeURIComponent(subDir)}`);
    if (v.status !== 200) throw new Error(`status ${v.status}`);
    if (!v.body.toString().includes(`data-tree-root="${subDir}"`)) {
      throw new Error('?root= override not reflected in sidebar');
    }
    // Invalid path falls back to default.
    const bad = await get(port, `/view?file=${encodeURIComponent(imgPath)}&root=${encodeURIComponent('/etc')}`);
    if (!bad.body.toString().includes(`data-tree-root="${sandbox}"`)) {
      throw new Error('disallowed ?root= should fall back to default');
    }
  });

  await test('?root= on /browse rebases sidebar', async () => {
    const r = await get(port, `/browse?dir=${encodeURIComponent(sandbox)}&root=${encodeURIComponent(subDir)}`);
    if (!r.body.toString().includes(`data-tree-root="${subDir}"`)) {
      throw new Error('?root= override not applied on /browse');
    }
  });

  await test('Sidebar exposes rebase-up button', async () => {
    const r = await get(port, `/browse?dir=${encodeURIComponent(sandbox)}`);
    if (!r.body.toString().includes('class="fb-sidebar-up"')) {
      throw new Error('rebase-up button missing');
    }
  });

  await test('Gallery + single-view + markdown inject sidebar', async () => {
    const g = await get(port, `/browse?dir=${encodeURIComponent(sandbox)}`);
    if (!g.body.toString().includes('class="fb-sidebar"')) throw new Error('gallery missing fb-sidebar');
    if (!g.body.toString().includes('/assets/sidebar.js')) throw new Error('gallery missing sidebar.js');
    const v = await get(port, `/view?file=${encodeURIComponent(imgPath)}`);
    if (!v.body.toString().includes('class="fb-sidebar"')) throw new Error('single-view missing fb-sidebar');
    const m = await get(port, `/view?file=${encodeURIComponent(mdPath)}`);
    if (!m.body.toString().includes('class="fb-sidebar"')) throw new Error('markdown missing fb-sidebar');
    if (!/has-fb-sidebar/.test(m.body.toString())) throw new Error('markdown body missing has-fb-sidebar class');
  });

  await test('sidebar.js reconciles tree-root in localStorage', async () => {
    const js = await get(port, '/assets/sidebar.js');
    if (js.status !== 200) throw new Error(`status ${js.status}`);
    const body = js.body.toString();
    if (!body.includes("'fb-tree-root'")) throw new Error('ROOT_KEY constant missing');
  });

  await test('pages with sidebar inject blocking <head> redirect script', async () => {
    // The script runs synchronously during head parse so URL→localStorage
    // restore happens before any body paint (no flash on click).
    for (const url of [
      `/browse?dir=${encodeURIComponent(sandbox)}`,
      `/view?file=${encodeURIComponent(imgPath)}`,
      `/view?file=${encodeURIComponent(mdPath)}`,
      `/view?file=${encodeURIComponent(jsPath)}`,
    ]) {
      const r = await get(port, url);
      const body = r.body.toString();
      if (!/fb-tree-root[^]*location\.replace/.test(body)) {
        throw new Error(`head-blocking redirect script missing in ${url}`);
      }
    }
  });

  await test('GET /api/search recursively matches by basename', async () => {
    // Create a nested file the basename-substring "needle" can find.
    const deep = path.join(subDir, 'deep');
    fs.mkdirSync(deep);
    const target = path.join(deep, 'find-needle-here.md');
    fs.writeFileSync(target, '# match');

    const r = await get(port, `/api/search?dir=${encodeURIComponent(sandbox)}&q=needle&limit=10`);
    if (r.status !== 200) throw new Error(`status ${r.status}`);
    const data = JSON.parse(r.body.toString());
    if (!Array.isArray(data.results) || data.results.length === 0) {
      throw new Error('expected at least one result');
    }
    if (!data.results.some((x) => x.path === target)) {
      throw new Error('did not find nested target');
    }
  });

  await test('GET /api/search rejects disallowed dir + missing params', async () => {
    const r1 = await get(port, `/api/search?dir=${encodeURIComponent('/etc')}&q=foo`);
    if (r1.status !== 403) throw new Error(`expected 403, got ${r1.status}`);
    const r2 = await get(port, `/api/search?dir=${encodeURIComponent(sandbox)}`);
    if (r2.status !== 400) throw new Error(`expected 400 for missing q, got ${r2.status}`);
  });

  await test('?root= propagates into rendered links', async () => {
    // Gallery folder cards include &root= so navigation never triggers redirect.
    // HTML-escapes the &, so check for &amp;root= in the served body.
    const g = await get(port, `/browse?dir=${encodeURIComponent(sandbox)}&root=${encodeURIComponent(sandbox)}`);
    const body = g.body.toString();
    if (!body.includes(`/browse?dir=${encodeURIComponent(subDir)}&amp;root=${encodeURIComponent(sandbox)}`)) {
      throw new Error('gallery folder link missing &root=');
    }
    if (!body.includes(`/view?file=${encodeURIComponent(mdPath)}&amp;root=${encodeURIComponent(sandbox)}`)) {
      throw new Error('gallery doc link missing &root=');
    }
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
