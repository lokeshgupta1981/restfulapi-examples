// Prints the routes and responses that Mockoon created from openapi.yaml.
import { readFileSync } from 'node:fs';

const environment = JSON.parse(readFileSync(process.argv[2], 'utf8'));
for (const route of environment.routes) {
  console.log(route.method.toUpperCase() + ' /' + route.endpoint);
  for (const response of route.responses) {
    const marker = response.default ? ' (default)' : '';
    console.log('  HTTP ' + response.statusCode + '  ' + response.label + marker);
  }
}
