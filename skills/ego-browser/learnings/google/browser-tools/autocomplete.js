async function(args) {
  for (const selector of ['span.gsqphr', '.ssb-a']) {
    const elements = document.querySelectorAll(selector);
    if (elements.length) {
      return [...elements].map(el => el.innerText?.trim() || '').filter(Boolean);
    }
  }
  return [];
}
