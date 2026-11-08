// Formats an amount in cents for display, such as formatPrice(129900, "USD") -> "$1,299.00".
const SYMBOLS = { USD: "$", EUR: "€", GBP: "£" };

export function formatPrice(cents, currency = "USD") {
  if (!Number.isInteger(cents)) throw new TypeError("cents must be an integer");
  const sign = cents < 0 ? "-" : "";
  const whole = Math.floor(Math.abs(cents) / 100).toLocaleString("en-US");
  const part = String(Math.abs(cents) % 100).padStart(2, "0");
  const symbol = SYMBOLS[currency] ?? `${currency} `;
  return `${sign}${symbol}${whole}.${part}`;
}
