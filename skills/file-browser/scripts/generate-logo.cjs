#!/usr/bin/env node
// Generate logo via OpenRouter (openai/gpt-5.4-image-2).
// Usage: OPEN_ROUTER_KEY=... node scripts/generate-logo.cjs [out.png]
const fs = require('fs');
const path = require('path');

const apiKey = process.env.OPEN_ROUTER_KEY || process.env.OPENROUTER_API_KEY;
if (!apiKey) {
  console.error('Missing OPEN_ROUTER_KEY env var.');
  process.exit(1);
}

const outPath = path.resolve(process.argv[2] || path.join(__dirname, '..', 'assets', 'logo.png'));

const prompt = `A minimalist app icon logo for a local file browser called "file-browser".
Concept: an open book combined with a subtle markdown hash symbol (#) and a small play triangle,
warm cream background (#faf8f3) with saddle-brown (#8b4513) and warm-gold (#d4a574) accents,
flat vector style, soft rounded corners, no text, centered composition,
calm and book-like aesthetic, 1024x1024, transparent or warm-cream background, no gradients besides subtle.`;

async function main() {
  const res = await fetch('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      'HTTP-Referer': 'https://github.com/vanducng/skills',
      'X-Title': 'file-browser logo'
    },
    body: JSON.stringify({
      model: 'openai/gpt-5.4-image-2',
      modalities: ['image', 'text'],
      messages: [{ role: 'user', content: prompt }]
    })
  });

  if (!res.ok) {
    console.error('HTTP', res.status, await res.text());
    process.exit(1);
  }

  const data = await res.json();
  const msg = data.choices?.[0]?.message;
  const images = msg?.images || [];
  if (!images.length) {
    console.error('No image in response:', JSON.stringify(data, null, 2));
    process.exit(1);
  }

  const url = images[0].image_url?.url || images[0].url;
  if (!url) {
    console.error('No URL on image:', JSON.stringify(images[0], null, 2));
    process.exit(1);
  }

  let buf;
  if (url.startsWith('data:')) {
    const b64 = url.split(',')[1];
    buf = Buffer.from(b64, 'base64');
  } else {
    const r = await fetch(url);
    buf = Buffer.from(await r.arrayBuffer());
  }
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, buf);
  console.log('Wrote', outPath, '(' + buf.length + ' bytes)');
}

main().catch(e => { console.error(e); process.exit(1); });
