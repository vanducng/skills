const test = require("node:test"), assert = require("node:assert");
const { push, drain } = require("../src/queue");
test("drain empties in order", () => { push(1); push(2); assert.deepEqual(drain(), [1, 2]); assert.deepEqual(drain(), []); });
