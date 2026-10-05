// What JSON.parse() does with comments and trailing commas.
import { readFileSync } from 'node:fs';

for (const name of ['orders-service.jsonc', 'trailing-comma.jsonc']) {
  const text = readFileSync(new URL("../config/" + name, import.meta.url), 'utf8');
  try {
    JSON.parse(text);
  } catch (error) {
    console.log(name + ': ' + error.name + ': ' + error.message);
  }
}
