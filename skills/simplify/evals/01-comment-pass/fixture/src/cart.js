// Returns the cart total in cents.
function total(items) {
  let sum = 0;
  // loop over the items
  for (const item of items) {
    // add the price times the quantity
    sum += item.price * item.qty;
  }
  // The payment API rejects amounts with more than 2 decimals, so round here.
  return Math.round(sum * 100) / 100;
}
module.exports = { total };
