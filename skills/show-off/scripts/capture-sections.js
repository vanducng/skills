#!/usr/bin/env node
/**
 * Parallel section screenshot capture for show-off skill.
 * Captures multiple sections at multiple viewport ratios concurrently.
 *
 * Usage:
 *   node capture-sections.js \
 *     --url "file:///path/to/page.html" \
 *     --output-dir "./images" \
 *     --sections "#hero,#about,#features" \
 *     --ratios "horizontal,vertical,square" \
 *     --delay 2000
 *
 * Uses Puppeteer directly so the skill works as a standalone capture helper.
 */
import path from 'path';
import fs from 'fs/promises';

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith('--')) {
      args[key] = true;
    } else {
      args[key] = next;
      i++;
    }
  }
  return args;
}

function outputJSON(payload) {
  console.log(JSON.stringify(payload, null, 2));
}

function outputError(error) {
  console.error(JSON.stringify({ success: false, error: error.message }, null, 2));
}

async function loadPuppeteer() {
  try {
    return (await import('puppeteer')).default;
  } catch (error) {
    throw new Error(
      'Puppeteer is not installed. Run `npm install` in skills/show-off/scripts first.',
    );
  }
}

// Viewport presets per ratio name
const VIEWPORTS = {
  horizontal: { width: 1920, height: 1080, label: 'horizontal' },  // 16:9
  vertical:   { width: 1080, height: 1920, label: 'vertical' },    // 9:16
  square:     { width: 1080, height: 1080, label: 'square' },      // 1:1
};

// Optional sharp for compression (mirrors chrome-devtools approach)
let sharp = null;
try { sharp = (await import('sharp')).default; } catch { /* noop */ }

/**
 * Wait until the page is visually ready:
 *  1. Fonts loaded (`document.fonts.ready`)
 *  2. Every <img> complete and non-zero natural size (or explicitly broken)
 *  3. Every CSS background-image resolved (best-effort via Image() preload)
 *  4. Two rAF paints to let layout + compositor settle
 *  5. Final `settleDelay` ms for animations / lazy-triggered work
 *
 * Timeout bounds each wait so a broken asset never hangs the capture.
 */
async function waitForRender(page, { settleDelay = 500, timeout = 15000 } = {}) {
  await page.evaluate(async (timeoutMs) => {
    const withTimeout = (promise, ms) =>
      Promise.race([promise, new Promise((r) => setTimeout(r, ms))]);

    if (document.fonts && document.fonts.ready) {
      await withTimeout(document.fonts.ready, timeoutMs);
    }

    const imgs = Array.from(document.images || []);
    await withTimeout(
      Promise.all(
        imgs.map((img) =>
          img.complete
            ? Promise.resolve()
            : new Promise((res) => {
                img.addEventListener('load', res, { once: true });
                img.addEventListener('error', res, { once: true });
              }),
        ),
      ),
      timeoutMs,
    );

    const bgUrls = new Set();
    for (const el of document.querySelectorAll('*')) {
      const bg = getComputedStyle(el).backgroundImage;
      if (!bg || bg === 'none') continue;
      for (const m of bg.matchAll(/url\(["']?([^"')]+)["']?\)/g)) bgUrls.add(m[1]);
    }
    await withTimeout(
      Promise.all(
        Array.from(bgUrls).map(
          (url) =>
            new Promise((res) => {
              const probe = new Image();
              probe.addEventListener('load', res, { once: true });
              probe.addEventListener('error', res, { once: true });
              probe.src = url;
            }),
        ),
      ),
      timeoutMs,
    );

    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  }, timeout);

  if (settleDelay > 0) await new Promise((r) => setTimeout(r, settleDelay));
}

/**
 * Compress image if it exceeds maxSizeMB.
 */
async function compressIfNeeded(filePath, maxSizeMB = 5) {
  const stats = await fs.stat(filePath);
  if (stats.size <= maxSizeMB * 1024 * 1024) return { compressed: false, size: stats.size };
  if (!sharp) return { compressed: false, size: stats.size };

  const ext = path.extname(filePath).toLowerCase();
  const buf = await fs.readFile(filePath);
  let out;
  if (ext === '.png') {
    out = await sharp(buf).png({ quality: 80, compressionLevel: 9 }).toBuffer();
  } else if (ext === '.jpg' || ext === '.jpeg') {
    out = await sharp(buf).jpeg({ quality: 80, progressive: true, mozjpeg: true }).toBuffer();
  } else if (ext === '.webp') {
    out = await sharp(buf).webp({ quality: 80 }).toBuffer();
  } else {
    out = await sharp(buf).jpeg({ quality: 80, progressive: true }).toBuffer();
  }
  await fs.writeFile(filePath, out);
  return { compressed: true, size: out.length };
}

/**
 * Main: parse args, open page, capture all section+ratio combos in parallel.
 */
async function main() {
  const args = parseArgs(process.argv.slice(2));

  if (!args.url || !args['output-dir'] || !args.sections) {
    outputError(new Error('Required: --url, --output-dir, --sections'));
    process.exit(1);
  }

  const url = args.url;
  const outputDir = path.resolve(args['output-dir']);
  const sections = args.sections.split(',').map(s => s.trim());
  const ratios = (args.ratios || 'horizontal,vertical,square').split(',').map(s => s.trim());
  // `--delay` is the post-ready settle delay (kept for back-compat).
  // `--settle-delay` is a preferred alias. `--render-timeout` bounds each readiness check.
  const settleDelay = parseInt(args['settle-delay'] || args.delay || '1500', 10);
  const renderTimeout = parseInt(args['render-timeout'] || '15000', 10);
  const format = args.format || 'png';
  const quality = parseInt(args.quality || '90', 10);
  const maxSize = parseFloat(args['max-size'] || '5');

  await fs.mkdir(outputDir, { recursive: true });

  const puppeteer = await loadPuppeteer();
  const browser = await puppeteer.launch({
    headless: args.headless === 'false' ? false : true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  // Build capture tasks: one per (section, ratio) pair
  // Group by ratio to minimise viewport switches — captures within same ratio run sequentially,
  // but different ratios run in parallel (each gets its own page context via browser.newPage).
  const results = [];
  const errors = [];

  const ratioTasks = ratios.map(async (ratio) => {
    let ratioPage;
    try {
      // Each ratio gets a fresh page so viewport changes don't conflict
      ratioPage = await browser.newPage();
      const vp = VIEWPORTS[ratio];
      if (!vp) throw new Error(`Unknown ratio: ${ratio}. Use: ${Object.keys(VIEWPORTS).join(', ')}`);

      await ratioPage.setViewport({ width: vp.width, height: vp.height, deviceScaleFactor: 2 });
      await ratioPage.goto(url, { waitUntil: 'networkidle0', timeout: renderTimeout + 15000 });
      await waitForRender(ratioPage, { settleDelay, timeout: renderTimeout });

      for (const selector of sections) {
        try {
          const el = await ratioPage.$(selector);
          if (!el) {
            errors.push({ section: selector, ratio, error: `Element not found: ${selector}` });
            continue;
          }
          await el.scrollIntoView();
          // Let scroll-linked animations / IntersectionObserver reveals trigger, then repaint.
          await waitForRender(ratioPage, { settleDelay: Math.min(settleDelay, 400), timeout: renderTimeout });

          const sectionName = selector.replace(/^[#.]/, '').replace(/[^a-zA-Z0-9-_]/g, '_');
          const fileName = `${vp.label}-${sectionName}.${format}`;
          const filePath = path.join(outputDir, fileName);

          const opts = { path: filePath, type: format };
          if (format !== 'png' && quality) opts.quality = quality;

          await el.screenshot(opts);
          const comp = await compressIfNeeded(filePath, maxSize);

          results.push({
            section: selector,
            ratio,
            file: filePath,
            size: comp.size,
            compressed: comp.compressed,
          });
        } catch (err) {
          errors.push({ section: selector, ratio, error: err.message });
        }
      }
    } catch (err) {
      errors.push({ ratio, error: err.message });
    } finally {
      if (ratioPage) await ratioPage.close();
    }
  });

  // Run all ratios in parallel
  await Promise.all(ratioTasks);

  await browser.close();

  outputJSON({
    success: errors.length === 0,
    total: results.length,
    captured: results,
    errors: errors.length > 0 ? errors : undefined,
  });

  process.exit(errors.length > 0 ? 1 : 0);
}

main().catch(err => {
  outputError(err);
  process.exit(1);
});
