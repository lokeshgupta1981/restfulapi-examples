// Prints how many problems each ruleset found, grouped by rule.
// Usage: node summary.mjs results/microsoft.json results/google.json ...
import { readFileSync } from 'node:fs';
import { basename } from 'node:path';

const severity = ['error', 'warning', 'info', 'hint'];

for (const file of process.argv.slice(2)) {
  const problems = JSON.parse(readFileSync(file, 'utf8'));
  const byRule = new Map();
  for (const p of problems) byRule.set(p.code, (byRule.get(p.code) ?? 0) + 1);

  const errors = problems.filter((p) => p.severity === 0).length;
  const warnings = problems.filter((p) => p.severity === 1).length;
  console.log(`${basename(file, '.json').padEnd(10)} ${errors} errors, ${warnings} warnings`);
  for (const [rule, count] of [...byRule].sort()) {
    const sev = severity[problems.find((p) => p.code === rule).severity];
    console.log(`  ${String(count).padStart(2)} x ${rule} (${sev})`);
  }
}
