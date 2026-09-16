// Zero-dependency static file server for Azure App Service
// Uses only Node.js built-in modules — no npm install needed
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8080;
const OUT_DIR = path.join(__dirname, 'out');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'application/javascript',
  '.css':  'text/css',
  '.json': 'application/json',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.svg':  'image/svg+xml',
  '.ico':  'image/x-icon',
  '.woff': 'font/woff',
  '.woff2':'font/woff2',
  '.ttf':  'font/ttf',
  '.txt':  'text/plain',
  '.webmanifest': 'application/manifest+json',
};

http.createServer((req, res) => {
  // Strip query string
  let urlPath = req.url.split('?')[0];

  let filePath = path.join(OUT_DIR, urlPath);

  // Resolve to index.html for root
  if (urlPath === '/' || urlPath === '') {
    filePath = path.join(OUT_DIR, 'index.html');
  }

  // If no extension, try .html (Next.js static export uses trailingSlash or .html files)
  if (!path.extname(filePath)) {
    const withHtml = filePath + '.html';
    if (fs.existsSync(withHtml)) {
      filePath = withHtml;
    } else {
      // SPA fallback
      filePath = path.join(OUT_DIR, 'index.html');
    }
  }

  if (!fs.existsSync(filePath)) {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not found');
    return;
  }

  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME[ext] || 'application/octet-stream';

  // Cache static assets aggressively, HTML never
  const cacheControl = ext === '.html'
    ? 'no-cache'
    : 'public, max-age=31536000, immutable';

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end('Internal error');
      return;
    }
    res.writeHead(200, {
      'Content-Type': contentType,
      'Cache-Control': cacheControl,
    });
    res.end(data);
  });
}).listen(PORT, '0.0.0.0', () => {
  console.log(`AI Project Co-Pilot frontend running on port ${PORT}`);
  console.log(`Serving static files from: ${OUT_DIR}`);
});
