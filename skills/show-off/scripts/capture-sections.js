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

function printErrorPayload(error) {
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

let sharpPromise = null;
async function loadSharp() {
  if (!sharpPromise) {
    sharpPromise = import('sharp').then((mod) => mod.default).catch(() => null);
  }
  return sharpPromise;
}

function normalizeFormat(value = 'png') {
  const requested = String(value).toLowerCase();
  if (requested === 'png') return { type: 'png', extension: 'png' };
  if (requested === 'jpg') return { type: 'jpeg', extension: 'jpg' };
  if (requested === 'jpeg') return { type: 'jpeg', extension: 'jpeg' };
  throw new Error('Unsupported --format. Use png, jpg, or jpeg.');
}

function parseQuality(value = '90') {
  if (!/^\d+$/.test(String(value))) {
    throw new Error('Invalid --quality. Use an integer from 0 to 100.');
  }
  const quality = Number.parseInt(String(value), 10);
  if (!Number.isInteger(quality) || quality < 0 || quality > 100) {
    throw new Error('Invalid --quality. Use an integer from 0 to 100.');
  }
  return quality;
}

function parseMaxSize(value = '5') {
  if (!/^\d+(\.\d+)?$/.test(String(value))) {
    throw new Error('Invalid --max-size. Use a positive number of megabytes.');
  }
  const maxSize = Number.parseFloat(String(value));
  if (!Number.isFinite(maxSize) || maxSize <= 0) {
    throw new Error('Invalid --max-size. Use a positive number of megabytes.');
  }
  return maxSize;
}

// Viewport presets per ratio name
const VIEWPORTS = {
  horizontal: { width: 1920, height: 1080, label: 'horizontal' },  // 16:9
  vertical:   { width: 1080, height: 1920, label: 'vertical' },    // 9:16
  square:     { width: 1080, height: 1080, label: 'square' },      // 1:1
};

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
    const walker = document.createTreeWalker(
      document.body || document.documentElement,
      NodeFilter.SHOW_ELEMENT,
    );
    const bgCandidates = [];
    while (bgCandidates.length < 2000) {
      const node = walker.nextNode();
      if (!node) break;
      bgCandidates.push(node);
    }
    for (const el of bgCandidates) {
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
async function compressIfNeeded(filePath, maxSizeMB = 5, quality = 80) {
  const stats = await fs.stat(filePath);
  if (stats.size <= maxSizeMB * 1024 * 1024) return { compressed: false, size: stats.size };
  const sharp = await loadSharp();
  if (!sharp) return { compressed: false, size: stats.size, warning: 'sharp is not installed; compression skipped.' };

  try {
    const ext = path.extname(filePath).toLowerCase();
    const buf = await fs.readFile(filePath);
    let out;
    if (ext === '.png') {
      out = await sharp(buf).png({ compressionLevel: 9 }).toBuffer();
    } else if (ext === '.jpg' || ext === '.jpeg') {
      out = await sharp(buf).jpeg({ quality, progressive: true, mozjpeg: true }).toBuffer();
    } else {
      out = await sharp(buf).jpeg({ quality, progressive: true }).toBuffer();
    }
    await fs.writeFile(filePath, out);
    return { compressed: true, size: out.length };
  } catch (error) {
    return { compressed: false, size: stats.size, warning: `Compression failed: ${error.message}` };
  }
}

/**
 * Main: parse args, open page, capture all section+ratio combos in parallel.
 */
async function main() {
  const args = parseArgs(process.argv.slice(2));

  if (!args.url || !args['output-dir'] || !args.sections) {
    throw new Error('Required: --url, --output-dir, --sections');
  }

  const url = args.url;
  const outputDir = path.resolve(args['output-dir']);
  const sections = args.sections.split(',').map(s => s.trim());
  const ratios = (args.ratios || 'horizontal,vertical,square').split(',').map(s => s.trim());
  // `--delay` is the post-ready settle delay (kept for back-compat).
  // `--settle-delay` is a preferred alias. `--render-timeout` bounds each readiness check.
  const settleDelay = parseInt(args['settle-delay'] || args.delay || '1500', 10);
  const renderTimeout = parseInt(args['render-timeout'] || '15000', 10);
  const format = normalizeFormat(args.format || 'png');
  const quality = parseQuality(args.quality || '90');
  const maxSize = parseMaxSize(args['max-size'] || '5');

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
  const warnings = [];

  try {
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
            const fileName = `${vp.label}-${sectionName}.${format.extension}`;
            const filePath = path.join(outputDir, fileName);

            const opts = { path: filePath, type: format.type };
            if (format.type === 'jpeg') opts.quality = quality;

            await el.screenshot(opts);
            const comp = await compressIfNeeded(filePath, maxSize, quality);
            if (comp.warning) {
              warnings.push({
                section: selector,
                ratio,
                file: filePath,
                warning: comp.warning,
              });
            }

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
        if (ratioPage) {
          try {
            await ratioPage.close();
          } catch (err) {
            errors.push({ ratio, error: `Page close failed: ${err.message}` });
          }
        }
      }
    });

    // Run all ratios in parallel
    await Promise.all(ratioTasks);
  } finally {
    await browser.close();
  }

  outputJSON({
    success: errors.length === 0,
    total: results.length,
    captured: results,
    errors: errors.length > 0 ? errors : undefined,
    warnings: warnings.length > 0 ? warnings : undefined,
  });

  process.exit(errors.length > 0 ? 1 : 0);
}

main().catch(err => {
  printErrorPayload(err);
  process.exit(1);
});
