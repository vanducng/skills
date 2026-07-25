async function(args) {
  const el = document.activeElement?.closest('[data-testid="tweet"]');
  if (!el) return { error: 'no active tweet found' };
  const labels = [...el.querySelectorAll('[data-testid="User-Name"] span')]
    .map((span) => span.innerText?.trim())
    .filter(Boolean);
  return {
    text: el.querySelector('[data-testid="tweetText"]')?.innerText?.trim() || '',
    author: labels.find((label) => !label.startsWith('@')) || '',
    handle: labels.find((label) => label.startsWith('@')) || '',
    timestamp: el.querySelector('time')?.getAttribute('datetime') || '',
  };
}
