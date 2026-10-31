#!/usr/bin/env bash
# Lints orders-api.yaml against each guide's ruleset, prints a summary,
# then lints both documents against our own house ruleset.
set -u
cd "$(dirname "$0")"
SPECTRAL="npx --no-install spectral"
mkdir -p results

for guide in microsoft google zalando agreed; do
  echo "== spectral lint orders-api.yaml -r rulesets/$guide.spectral.yaml"
  $SPECTRAL lint orders-api.yaml -r "rulesets/$guide.spectral.yaml" -f text --quiet | sed "s#$PWD/##"
  printf '\n\n'
  $SPECTRAL lint orders-api.yaml -r "rulesets/$guide.spectral.yaml" -f json --quiet \
    > "results/$guide.json" 2>/dev/null
done

echo "== summary for orders-api.yaml"
node summary.mjs results/microsoft.json results/google.json results/zalando.json results/agreed.json
echo

for doc in orders-api.yaml orders-api-house.yaml; do
  echo "== spectral lint $doc -r rulesets/house.spectral.yaml"
  $SPECTRAL lint "$doc" -r rulesets/house.spectral.yaml -f text | sed "s#$PWD/##"
  rc=${PIPESTATUS[0]}
  echo
  echo "exit code: $rc"
  echo
done
