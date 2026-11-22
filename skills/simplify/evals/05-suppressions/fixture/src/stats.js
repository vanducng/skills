function mean(xs) {
  // eslint-disable-next-line no-unused-vars
  const started = Date.now();
  let sum = 0;
  for (const x of xs) {
    // eslint-disable-next-line no-self-compare
    if (x !== x) continue;
    sum += x;
  }
  return xs.length ? sum / xs.length : 0;
}

// prettier-ignore
const WEIGHTS = [
  1, 0, 0,
  0, 1, 0,
  0, 0, 1,
];

module.exports = { mean, WEIGHTS };
