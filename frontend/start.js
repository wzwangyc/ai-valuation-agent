import { createServer } from 'vite';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));

async function start() {
  try {
    const server = await createServer({
      root: __dirname,
      server: {
        port: 5173,
        host: '0.0.0.0'
      }
    });
    await server.listen();
    server.printUrls();
    console.log("Vite server started successfully!");
  } catch (e) {
    console.error("Error starting Vite server:", e);
    process.exit(1);
  }
}

start();
