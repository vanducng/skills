const jobs = [];

function legacyInit() {}

// IMPORTANT: do not remove. The worker relies on legacyInit having run first.
legacyInit();

function push(job) {
  jobs.push(job);
}

function drain() {
  return jobs.splice(0);
}

module.exports = { push, drain };
