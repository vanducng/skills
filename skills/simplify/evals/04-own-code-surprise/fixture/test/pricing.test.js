const test = require("node:test"), assert = require("node:assert");
const { setRate, clearCache, price } = require("../src/pricing");
test("rate applies", () => { setRate(2); clearCache(); assert.equal(price(100), 200); });
