// SPDX-License-Identifier: MIT

const ZERO_DECIMAL = new Set(["JPY", "KRW", "VND"]);

/** `amount` is in major units (dollars, yen); an unknown currency is treated as two-decimal. */
function toMinorUnits(amount, currency) {
  // The payment API takes whole units for zero-decimal currencies: https://docs.stripe.com/currencies#zero-decimal
  return ZERO_DECIMAL.has(currency) ? Math.round(amount) : Math.round(amount * 100);
}

module.exports = { toMinorUnits };
