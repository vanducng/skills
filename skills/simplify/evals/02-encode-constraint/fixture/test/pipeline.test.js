const test = require("node:test"), assert = require("node:assert"), { run, saved } = require("../src/pipeline");
test("saves a valid order", () => { run({ id: 1 }); assert.deepEqual(saved.at(-1), { id: 1 }); });
