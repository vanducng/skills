function boundedInteger(value, fallback, max) {
  const number = value === undefined ? fallback : Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.max(1, Math.min(max, Math.trunc(number)));
}

export async function searchAndExtract(ctx, args = {}) {
  const query = args?.query;
  if (!query) throw new Error("search query is required");
  const maxResults = boundedInteger(args?.maxResults, 10, 100);

  await ctx.browser.openOrReuseTab(
    `https://www.google.com/search?q=${encodeURIComponent(query)}`,
    { wait: true },
  );
  await ctx.page.waitForLoadState("load");

  const resultLocator = ctx.page.locator("div.g");
  const ready = await resultLocator
    .first()
    .waitFor({ state: "visible", timeout: 10000 });
  if (!ready) return [];

  const results = await resultLocator.evaluateAll((items, limit) => {
    return items
      .slice(0, limit)
      .map((el) => ({
        title: el.querySelector("h3")?.innerText?.trim() || "",
        url:
          el.querySelector("h3")?.closest("a")?.getAttribute("href") || "",
        snippet: el.querySelector("[data-sncf]")?.innerText?.trim() || "",
      }))
      .filter((r) => r.title);
  }, maxResults);

  return results;
}
