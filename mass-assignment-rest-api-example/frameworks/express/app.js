// Express version of the bug and the fix. Run: node app.js (PORT=3000 by default)
import express from 'express';

const app = express();
app.use(express.json());

const users = new Map([[2, { id: 2, email: 'alice@example.com', name: 'Alice', role: 'customer', storeCredit: 0 }]]);

// Vulnerable: copies every key of the body onto the stored user
app.patch('/vulnerable/users/:id', (req, res) => {
  const user = users.get(Number(req.params.id));
  Object.assign(user, req.body);
  res.json(user);
});

// Fixed: an allow-list of the fields this endpoint may change
const UPDATABLE = ['email', 'name'];

app.patch('/users/:id', (req, res) => {
  const unknown = Object.keys(req.body).filter((key) => !UPDATABLE.includes(key));
  if (unknown.length > 0) {
    return res.status(422).json({ error: 'Fields not allowed: ' + unknown.join(', ') });
  }
  const user = users.get(Number(req.params.id));
  for (const key of UPDATABLE) {
    if (key in req.body) user[key] = req.body[key];
  }
  res.json(user);
});

const port = Number(process.env.PORT ?? 3000);
app.listen(port, () => console.log(`Express demo on port ${port}`));
