function total(items, coupons) {
  let sum = items.reduce((s, i) => s + i.price * i.qty, 0);
  for (const c of coupons) sum -= c.amount;
  return Math.max(sum, 0);
}
module.exports = { total };
