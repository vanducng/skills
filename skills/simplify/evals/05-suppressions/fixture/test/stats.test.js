const test = require("node:test"), assert = require("node:assert");
const { mean, WEIGHTS } = require("../src/stats");
test("mean", () => assert.equal(mean([1, 2, 3]), 2));
test("empty", () => assert.equal(mean([]), 0));
test("weights", () => assert.equal(WEIGHTS.length, 9));
