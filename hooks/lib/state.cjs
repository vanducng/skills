'use strict';
/**
 * state.cjs - Per-session temp-file state manager.
 *
 * File: os.tmpdir()/vd-session-<sessionId>.json (NOT ~/.claude/session.json).
 * Write is atomic via O_EXCL lock + temp-file rename.
 * Superset-compatible: never drops keys written by session-state.cjs (statusline,
 * lastTranscriptPath, devRulesReminder).
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const VD_TIMEOUT_MS = 500;
const VD_RETRY_MS = 10;
const VD_STALE_MS = 5000;

function getSessionTempPath(sessionId) {
  return path.join(os.tmpdir(), `vd-session-${sessionId}.json`);
}

function getLockPath(sessionId) {
  return getSessionTempPath(sessionId) + '.lock';
}

function sleepSync(ms) {
  if (ms <= 0) return;
  if (typeof SharedArrayBuffer === 'function' && typeof Atomics === 'object') {
    const buf = new Int32Array(new SharedArrayBuffer(4));
    Atomics.wait(buf, 0, 0, ms);
    return;
  }
  const end = Date.now() + ms;
  while (Date.now() < end) { /* busy wait fallback */ }
}

function removeStale(lockPath) {
  try {
    const st = fs.statSync(lockPath);
    if (Date.now() - st.mtimeMs < VD_STALE_MS) return false;
    fs.unlinkSync(lockPath);
    return true;
  } catch {
    return false;
  }
}

function acquireLock(sessionId) {
  const lockPath = getLockPath(sessionId);
  const deadline = Date.now() + VD_TIMEOUT_MS;
  while (Date.now() <= deadline) {
    try {
      const fd = fs.openSync(lockPath, 'wx');
      fs.writeFileSync(fd, String(process.pid));
      return { fd, lockPath };
    } catch (e) {
      if (e?.code !== 'EEXIST') return null;
      removeStale(lockPath);
      sleepSync(VD_RETRY_MS);
    }
  }
  return null;
}

function releaseLock(lock) {
  if (!lock) return;
  try { fs.closeSync(lock.fd); } catch { /* ignore */ }
  try { fs.unlinkSync(lock.lockPath); } catch { /* ignore */ }
}

/** Read session state from temp file. Returns {} if missing/corrupt. */
function readSessionState(sessionId) {
  if (!sessionId) return null;
  const p = getSessionTempPath(sessionId);
  try {
    if (!fs.existsSync(p)) return null;
    return JSON.parse(fs.readFileSync(p, 'utf8'));
  } catch {
    return null;
  }
}

function atomicWrite(tempPath, data) {
  const tmp = `${tempPath}.${Math.random().toString(36).slice(2)}.json`;
  try {
    fs.writeFileSync(tmp, JSON.stringify(data, null, 2));
    fs.renameSync(tmp, tempPath);
    return true;
  } catch {
    try { fs.unlinkSync(tmp); } catch { /* ignore */ }
    return false;
  }
}

/**
 * Update session state atomically.
 * updater: partial object to merge, or transform function (prev) => next.
 * Preserves all existing keys (superset-compatible with session-state.cjs).
 */
function updateSessionState(sessionId, updater) {
  if (!sessionId) return false;
  const lock = acquireLock(sessionId);
  if (!lock) return false;
  try {
    const current = readSessionState(sessionId) || {};
    const next = typeof updater === 'function'
      ? updater({ ...current })
      : { ...current, ...(updater || {}) };
    if (!next || typeof next !== 'object') return false;
    return atomicWrite(getSessionTempPath(sessionId), next);
  } finally {
    releaseLock(lock);
  }
}

module.exports = {
  getSessionTempPath,
  readSessionState,
  updateSessionState
};
