const test = require("node:test"), assert = require("node:assert"), { slug } = require("../src/slug");
test("slug", () => assert.equal(slug("  Hello, World! "), "hello-world"));
