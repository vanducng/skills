/**
 * Port finder utility - finds available port in range
 * Sibling of markdown-render's port-finder. Uses 3556-3600 range
 * to avoid colliding with markdown-render (3456-3500).
 */

const net = require('net');

const DEFAULT_PORT = 3556;
const PORT_RANGE_END = 3600;

function isPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', () => resolve(false));
    server.once('listening', () => {
      server.close();
      resolve(true);
    });
    server.listen(port);
  });
}

async function findAvailablePort(startPort = DEFAULT_PORT) {
  for (let port = startPort; port <= PORT_RANGE_END; port++) {
    if (await isPortAvailable(port)) {
      return port;
    }
  }
  throw new Error(`No available port in range ${startPort}-${PORT_RANGE_END}`);
}

module.exports = {
  isPortAvailable,
  findAvailablePort,
  DEFAULT_PORT,
  PORT_RANGE_END
};
