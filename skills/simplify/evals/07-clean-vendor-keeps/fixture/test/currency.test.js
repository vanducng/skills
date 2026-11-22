const test = require("node:test"), assert = require("node:assert");
const { toMinorUnits } = require("../src/currency");
test("usd", () => assert.equal(toMinorUnits(1.5, "USD"), 150));
test("jpy", () => assert.equal(toMinorUnits(150, "JPY"), 150));
