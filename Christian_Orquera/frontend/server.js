// Static file server for the Next.js export in ./out
// Uses only Node built-ins so App Service can run it without an npm install.
const http = require('http')
const fs = require('fs')
const path = require('path')

const PORT = process.env.PORT || 8080
const OUT_DIR = path.join(__dirname, 'out')

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.mjs': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.txt': 'text/plain; charset=utf-8',
}

function send(res, status, body, headers = {}) {
  res.writeHead(status, headers)
  res.end(body)
}

function serveFile(res, filePath) {
  fs.readFile(filePath, (err, data) => {
    if (err) return notFound(res)

    const ext = path.extname(filePath).toLowerCase()
    // Hashed asset filenames make /_next/static safe to cache indefinitely.
    const cache = filePath.includes(`${path.sep}_next${path.sep}static${path.sep}`)
      ? 'public, max-age=31536000, immutable'
      : 'no-cache'

    send(res, 200, data, {
      'Content-Type': MIME[ext] || 'application/octet-stream',
      'Cache-Control': cache,
    })
  })
}

function notFound(res) {
  const custom = path.join(OUT_DIR, '404.html')
  fs.readFile(custom, (err, data) => {
    if (err) return send(res, 404, 'Not Found', { 'Content-Type': 'text/plain' })
    send(res, 404, data, { 'Content-Type': MIME['.html'] })
  })
}

const server = http.createServer((req, res) => {
  const urlPath = decodeURIComponent(new URL(req.url, `http://${req.headers.host}`).pathname)

  // Resolve inside OUT_DIR so encoded traversal can't escape the export.
  const resolved = path.normalize(path.join(OUT_DIR, urlPath))
  if (!resolved.startsWith(OUT_DIR)) return notFound(res)

  fs.stat(resolved, (err, stats) => {
    if (!err && stats.isFile()) return serveFile(res, resolved)
    if (!err && stats.isDirectory()) return serveFile(res, path.join(resolved, 'index.html'))

    // Export writes /about as about.html, so retry with the extension.
    const asHtml = `${resolved}.html`
    fs.stat(asHtml, (htmlErr, htmlStats) => {
      if (!htmlErr && htmlStats.isFile()) return serveFile(res, asHtml)
      notFound(res)
    })
  })
})

server.listen(PORT, () => {
  console.log(`Serving ${OUT_DIR} on port ${PORT}`)
})
