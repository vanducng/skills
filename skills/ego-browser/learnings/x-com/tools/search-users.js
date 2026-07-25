export async function searchUsers(ctx, args = {}) {
  const query = args?.query;
  if (!query) throw new Error("search query is required");

  await ctx.browser.openOrReuseTab(
    `https://x.com/search?f=user&q=${encodeURIComponent(query)}`,
    { wait: true },
  );
  await ctx.page.waitForLoadState("load");

  const cards = ctx.page.locator(
    '[data-testid="cellInnerDiv"]:has([data-testid="User-Name"])',
  );
  const ready = await cards.first().waitFor({ state: "visible" });
  if (!ready) return [];

  const users = await cards.evaluateAll((results) => {
    return results
      .map((el) => {
        const labels = [...el.querySelectorAll('[data-testid="User-Name"] span')]
          .map((span) => span.innerText?.trim())
          .filter(Boolean);
        return {
          name: labels.find((label) => !label.startsWith("@")) || "",
          handle: labels.find((label) => label.startsWith("@")) || "",
        };
      })
      .filter((u) => u.name || u.handle);
  });

  return users;
}
