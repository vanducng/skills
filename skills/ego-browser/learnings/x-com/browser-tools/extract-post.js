async function(args) {
  const el = document.activeElement?.closest('[data-testid="tweet"]');
  if (!el) return { error: 'no active tweet found' };
  return {
    text: el.querySelector('[data-testid="tweetText"]')?.innerText?.trim() || '',
    author: el.querySelector('[data-testid="User-Name"] a[role="link"] span')?.innerText?.trim() || '',
    timestamp: el.querySelector('time')?.getAttribute('datetime') || '',
  };
}
