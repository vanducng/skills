function boundedInteger(value, fallback, max) {
  const number = value === undefined ? fallback : Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.max(1, Math.min(max, Math.trunc(number)));
}

export async function getTimelinePosts(ctx, args = {}) {
  const maxPosts = boundedInteger(args?.maxPosts, 50, 100);

  const posts = await ctx.page
    .locator('[data-testid="tweet"]')
    .evaluateAll((articles, limit) => {
      return articles.slice(0, limit).map((el) => {
        const labels = [...el.querySelectorAll('[data-testid="User-Name"] span')]
          .map((span) => span.innerText?.trim())
          .filter(Boolean);
        return {
          text:
            el.querySelector('[data-testid="tweetText"]')?.innerText?.trim() ||
            "",
          author: labels.find((label) => !label.startsWith("@")) || "",
          handle: labels.find((label) => label.startsWith("@")) || "",
          timestamp: el.querySelector("time")?.getAttribute("datetime") || "",
        };
      });
    }, maxPosts);

  return posts;
}
