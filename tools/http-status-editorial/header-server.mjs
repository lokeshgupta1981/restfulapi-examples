import http from 'node:http';

http.createServer({ maxHeaderSize: 16 * 1024 }, (req, res) => {
  res.end('OK');
}).listen(3000, '127.0.0.1');