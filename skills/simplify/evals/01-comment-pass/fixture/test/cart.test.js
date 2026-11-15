const test = require("node:test"), assert = require("node:assert"), { total } = require("../src/cart");
test("total in dollars, 2 decimals", () => assert.equal(total([{ price: 1.333, qty: 3 }, { price: 2, qty: 1 }]), 6));
test("empty", () => assert.equal(total([]), 0));
