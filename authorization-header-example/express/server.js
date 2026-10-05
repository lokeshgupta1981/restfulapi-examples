import express from 'express';
import { readFileSync } from 'node:fs';
import { bearerToken, parseBasic, safeEqual, schemeForLog } from './auth.js';

// Demo values for local tests only.
const DEMO_USER = 'reports-app';
const DEMO_PASSWORD = 'demo-pass-123';
const DEMO_TOKEN = readFileSync(new URL('../demo-token.txt', import.meta.url), 'utf8').trim();

const app = express();

app.use((req, res, next) => {
  console.log(req.method + ' ' + req.path + ' auth-scheme=' + schemeForLog(req.get('Authorization')));
  next();
});

function challenge(res, header) {
  res.status(401).set('WWW-Authenticate', header)
    .json({ error: 'missing or invalid credentials' });
}

app.get('/basic/orders', (req, res) => {
  const credentials = parseBasic(req.get('Authorization') ?? '');
  if (!credentials || !safeEqual(credentials.name, DEMO_USER)
      || !safeEqual(credentials.pass, DEMO_PASSWORD)) {
    challenge(res, 'Basic realm="orders", charset="UTF-8"');
    return;
  }
  res.json({ user: credentials.name, orders: [1001, 1002] });
});

app.get('/bearer/orders', (req, res) => {
  const token = bearerToken(req.get('Authorization'));
  if (!token || !safeEqual(token, DEMO_TOKEN)) {
    challenge(res, 'Bearer realm="orders"');
    return;
  }
  res.json({ user: DEMO_USER, orders: [1001, 1002] });
});

app.listen(9761, '127.0.0.1', () => console.log('Express on http://127.0.0.1:9761'));
