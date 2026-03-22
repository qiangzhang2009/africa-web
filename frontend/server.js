const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const DIST_DIR = path.join(__dirname, 'dist');
const INDEX = path.join(DIST_DIR, 'index.html');

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript',
  '.mjs': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.txt': 'text/plain',
};

function serve(req, res, filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const mime = MIME_TYPES[ext] || 'application/octet-stream';
  
  fs.readFile(filePath, (err, data) => {
    if (err) {
      if (err.code === 'ENOENT') {
        // Try index.html for SPA routes
        if (req.url.startsWith('/api')) {
          res.writeHead(502);
          res.end('API proxy not configured');
          return;
        }
        fs.readFile(INDEX, (err2, data2) => {
          if (err2) {
            res.writeHead(500);
            res.end('Server error');
          } else {
            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
            res.end(data2);
          }
        });
      } else {
        res.writeHead(500);
        res.end('Server error');
      }
    } else {
      res.writeHead(200, { 'Content-Type': mime });
      res.end(data);
    }
  });
}

const server = http.createServer((req, res) => {
  const url = req.url.split('?')[0];
  
  // Proxy API requests to backend
  if (url.startsWith('/api/')) {
    const backendUrl = 'https://africa-web-wuxs.onrender.com' + url;
    const lib = url.startsWith('/api/v1') ? require('https') : require('http');
    
    const proxyReq = lib.request(backendUrl, {
      method: req.method,
      headers: {
        ...req.headers,
        host: 'africa-web-wuxs.onrender.com',
      }
    }, (proxyRes) => {
      res.writeHead(proxyRes.statusCode, {
        ...proxyRes.headers,
        'access-control-allow-origin': '*',
      });
      proxyRes.pipe(res);
    });
    
    proxyReq.on('error', () => {
      res.writeHead(502);
      res.end('Backend unavailable');
    });
    
    req.pipe(proxyReq);
    return;
  }
  
  // Serve static files
  let filePath = path.join(DIST_DIR, url === '/' ? 'index.html' : url);
  
  // Security: prevent directory traversal
  if (!filePath.startsWith(DIST_DIR)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }
  
  // If it's a directory, try index.html
  fs.stat(filePath, (err, stats) => {
    if (!err && stats.isDirectory()) {
      filePath = path.join(filePath, 'index.html');
    }
    serve(req, res, filePath);
  });
});

server.listen(PORT, () => {
  console.log(`AfricaZero frontend running on port ${PORT}`);
});
