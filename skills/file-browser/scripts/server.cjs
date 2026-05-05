#!/usr/bin/env node
/**
 * file-browser server entry point.
 *
 * Mirrors markdown-render's CLI shape so existing nvim/Hammerspoon glue works
 * with minimal change:
 *
 *   node server.cjs --file /path/to/img.png            # single view
 *   node server.cjs --dir  /path/to/folder             # gallery
 *   node server.cjs --stop                             # stop all file-browser servers
 *   node server.cjs --file foo.mp4 --port 3556 --host 0.0.0.0 --background
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn, execSync } = require('child_process');

const { findAvailablePort, DEFAULT_PORT } = require('./lib/port-finder.cjs');
const {
  writePidFile,
  stopAllServers,
  setupShutdownHandlers,
  findRunningInstances
} = require('./lib/process-mgr.cjs');
const { createHttpServer } = require('./lib/http-server.cjs');

function parseArgs(argv) {
  const args = {
    file: null,
    dir: null,
    port: DEFAULT_PORT,
    host: 'localhost',
    open: true,
    stop: false,
    background: false,
    foreground: false,
    isChild: false
  };

  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--file' && argv[i + 1]) args.file = argv[++i];
    else if (a === '--dir' && argv[i + 1]) args.dir = argv[++i];
    else if (a === '--port' && argv[i + 1]) args.port = parseInt(argv[++i], 10);
    else if (a === '--host' && argv[i + 1]) args.host = argv[++i];
    else if (a === '--open') args.open = true;
    else if (a === '--no-open') args.open = false;
    else if (a === '--stop') args.stop = true;
    else if (a === '--background') args.background = true;
    else if (a === '--foreground') args.foreground = true;
    else if (a === '--child') args.isChild = true;
    else if (!a.startsWith('--') && !args.file && !args.dir) args.file = a;
  }
  return args;
}

function resolveInput(input, cwd) {
  if (!input) return { type: null, path: null };
  const resolved = path.isAbsolute(input) ? input : path.resolve(cwd, input);
  if (!fs.existsSync(resolved)) return { type: null, path: null };
  const stats = fs.statSync(resolved);
  if (stats.isFile()) return { type: 'file', path: resolved };
  if (stats.isDirectory()) return { type: 'directory', path: resolved };
  return { type: null, path: null };
}

function openBrowser(targetUrl) {
  const platform = process.platform;
  const cmd =
    platform === 'darwin'
      ? `open "${targetUrl}"`
      : platform === 'win32'
        ? `start "" "${targetUrl}"`
        : `xdg-open "${targetUrl}"`;
  try {
    execSync(cmd, { stdio: 'ignore' });
  } catch {
    /* ignore */
  }
}

function getLocalIP() {
  const interfaces = os.networkInterfaces();
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) return iface.address;
    }
  }
  return null;
}

function buildUrl(host, port, type, fsPath) {
  const displayHost = host === '0.0.0.0' ? 'localhost' : host;
  const baseUrl = `http://${displayHost}:${port}`;
  let urlPath = '';
  if (type === 'file') urlPath = `/view?file=${encodeURIComponent(fsPath)}`;
  else if (type === 'directory') urlPath = `/browse?dir=${encodeURIComponent(fsPath)}`;
  const url = baseUrl + urlPath;

  let networkUrl = null;
  if (host === '0.0.0.0') {
    const ip = getLocalIP();
    if (ip) networkUrl = `http://${ip}:${port}${urlPath}`;
  }
  return { url, networkUrl };
}

async function main() {
  const args = parseArgs(process.argv);
  const cwd = process.cwd();
  const assetsDir = path.join(__dirname, '..', 'assets');

  if (args.stop) {
    const instances = findRunningInstances();
    if (instances.length === 0) {
      console.log('No file-browser server running');
      process.exit(0);
    }
    const stopped = stopAllServers();
    console.log(`Stopped ${stopped} file-browser server(s)`);
    process.exit(0);
  }

  const input = args.dir || args.file;
  if (!input) {
    console.error('Error: --file or --dir required');
    console.error('Usage:');
    console.error('  node server.cjs --file /path/to/image-or-video');
    console.error('  node server.cjs --dir  /path/to/folder');
    console.error('  node server.cjs --stop');
    process.exit(1);
  }

  let resolved = resolveInput(input, cwd);
  if (args.dir && resolved.type === null) {
    const dirPath = path.isAbsolute(args.dir) ? args.dir : path.resolve(cwd, args.dir);
    if (fs.existsSync(dirPath) && fs.statSync(dirPath).isDirectory()) {
      resolved = { type: 'directory', path: dirPath };
    }
  }
  if (resolved.type === null) {
    console.error(`Error: invalid path: ${input}`);
    process.exit(1);
  }

  // Detached background mode (legacy - matches markdown-render)
  if (args.background && !args.foreground && !args.isChild) {
    const childArgs = ['--port', String(args.port), '--host', args.host, '--child'];
    if (resolved.type === 'file') childArgs.unshift('--file', resolved.path);
    else childArgs.unshift('--dir', resolved.path);
    if (args.open) childArgs.push('--open');

    const child = spawn(process.execPath, [__filename, ...childArgs], {
      detached: true,
      stdio: 'ignore',
      cwd
    });
    child.unref();

    await new Promise((r) => setTimeout(r, 500));
    const instance = findRunningInstances().find((i) => i.port >= args.port);
    const port = instance ? instance.port : args.port;
    const { url, networkUrl } = buildUrl(args.host, port, resolved.type, resolved.path);

    const result = {
      success: true,
      url,
      path: resolved.path,
      port,
      host: args.host,
      mode: resolved.type
    };
    if (networkUrl) result.networkUrl = networkUrl;
    console.log(JSON.stringify(result));
    process.exit(0);
  }

  const port = await findAvailablePort(args.port);
  if (port !== args.port) console.error(`Port ${args.port} in use, using ${port}`);

  // Build allowed-dir allowlist for path-traversal guard
  const allowedDirs = [assetsDir, cwd];
  const targetDir = resolved.type === 'file' ? path.dirname(resolved.path) : resolved.path;
  if (!allowedDirs.includes(targetDir)) allowedDirs.push(targetDir);
  // Allow $HOME so /file/<absolute-path> works for anything under home
  // (matches markdown-render's behavior when launched from $HOME).
  const home = os.homedir();
  if (home && !allowedDirs.includes(home)) allowedDirs.push(home);

  const treeRoot = resolved.type === 'file' ? path.dirname(resolved.path) : resolved.path;
  const server = createHttpServer({ assetsDir, allowedDirs, treeRoot });

  server.listen(port, args.host, () => {
    const { url, networkUrl } = buildUrl(args.host, port, resolved.type, resolved.path);
    writePidFile(port, process.pid);
    setupShutdownHandlers(port, () => server.close());

    if (args.foreground || args.isChild || process.env.CLAUDE_COMMAND) {
      const result = {
        success: true,
        url,
        path: resolved.path,
        port,
        host: args.host,
        mode: resolved.type
      };
      if (networkUrl) result.networkUrl = networkUrl;
      console.log(JSON.stringify(result));
    } else {
      console.log(`\nfile-browser`);
      console.log(`${'─'.repeat(40)}`);
      console.log(`URL:  ${url}`);
      if (networkUrl) console.log(`Net:  ${networkUrl}`);
      console.log(`Path: ${resolved.path}`);
      console.log(`Port: ${port}`);
      console.log(`Host: ${args.host}`);
      console.log(`Mode: ${resolved.type === 'file' ? 'Single Viewer' : 'Gallery'}`);
      console.log(`\nPress Ctrl+C to stop\n`);
    }

    if (args.open) openBrowser(url);
  });

  server.on('error', (err) => {
    console.error(`Server error: ${err.message}`);
    process.exit(1);
  });
}

main().catch((err) => {
  console.error(`Error: ${err.message}`);
  process.exit(1);
});
