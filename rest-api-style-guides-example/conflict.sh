#!/usr/bin/env bash
# Shows that one field name cannot satisfy all three guides:
# lints customerId and customer_id against each guide and prints only
# the problems that mention the field.
set -u
cd "$(dirname "$0")"
SPECTRAL="npx --no-install spectral"
tmp=$(mktemp -d)
cp orders-api.yaml "$tmp/camel.yaml"
sed 's/customerId/customer_id/' orders-api.yaml > "$tmp/snake.yaml"

for variant in camel snake; do
  for guide in microsoft google zalando; do
    out=$($SPECTRAL lint "$tmp/$variant.yaml" -r "rulesets/$guide.spectral.yaml" -f text --quiet | grep -E 'customer(Id|_id)')
    printf '%-6s %-10s %s\n' "$variant" "$guide" "${out:-ok}" | sed "s#$tmp/##"
  done
done
rm -r "$tmp"
