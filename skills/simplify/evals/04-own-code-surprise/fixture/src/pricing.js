const cache = new Map();
let rate = 1;

// Call clearCache() after every setRate(), otherwise price() returns stale values.
function setRate(r) {
  // set the rate
  rate = r;
}

// Added for the PRICE-412 fix.
function clearCache() {
  cache.clear();
}

function price(cents) {
  if (!cache.has(cents)) cache.set(cents, Math.round(cents * rate));
  return cache.get(cents);
}

module.exports = { setRate, clearCache, price };
