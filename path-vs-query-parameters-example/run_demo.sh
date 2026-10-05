#!/usr/bin/env bash
# Sends every request from the article. The app must run on port 8480
# and nginx on port 8481 (see README.md).
APP=http://localhost:8480
PROXY=http://localhost:8481

# Prints the command with shell quoting, so it can be copied as shown.
run() {
  local shown="\$"
  for arg in "$@"; do
    if [[ "$arg" == *'"'* ]]; then
      shown+=" '$arg'"
    elif [[ "$arg" =~ [\&\?\ \[] ]]; then
      shown+=" \"$arg\""
    else
      shown+=" $arg"
    fi
  done
  echo "$shown"
  "$@"
  echo
  echo
}

echo "### 1. Path identifies, query shapes"
run curl -s "$APP/orders/1001"
run curl -s "$APP/orders/1001?include_items=true"
run curl -s "$APP/customers/7/orders"
run curl -s "$APP/orders?status=paid&sort=total&limit=1"

echo "### 2. Missing and invalid values"
run curl -s -i "$APP/orders/9999"
run curl -s -i "$APP/customers/42/orders"
run curl -s "$APP/customers/9/orders"
run curl -s "$APP/customers//orders"
run curl -s "$APP/orders/abc"
run curl -s "$APP/orders"
run curl -s -i "$APP/orders?limit=500"
run curl -s "$APP/products/KB-101/price"
run curl -s "$APP/products/KB-101/price?currency=EUR"

echo "### 3. Arrays and repeated keys"
run curl -s "$APP/orders?status=paid&status=shipped"
run curl -s "$APP/orders?status=paid,shipped"
run curl -s -g "$APP/orders?status[]=paid&limit=2"

echo "### 4. Encoding"
run curl -s "$APP/products?q=C++"
run curl -s "$APP/products?q=C%2B%2B"
run curl -s "$APP/products?q=AT&T"
run curl -s "$APP/products?q=AT%26T"
run curl -s -G "$APP/products" --data-urlencode "q=AT&T"
run curl -s "$APP/products/KB-101"
run curl -s "$APP/products/ZZ-999"
run curl -s "$APP/products/AB%2F12"

echo "### 5. Cache key and parameter order (through nginx)"
for url in "$PROXY/products?category=books&q=rust" \
           "$PROXY/products?category=books&q=rust" \
           "$PROXY/products?q=rust&category=books"; do
  echo "\$ curl -s -o /dev/null -D - \"$url\""
  curl -s -o /dev/null -D - "$url" | grep -i -E "^HTTP|^cache-control|^x-cache-status"
  echo
done

echo "### 6. URL length limits"
for size in 8150 8170; do
  echo "\$ long_value=\$(head -c $size /dev/zero | tr '\\0' x)"
  long_value=$(head -c "$size" /dev/zero | tr '\0' x)
  echo "\$ curl -s -o /dev/null -w \"%{http_code}\\n\" \"$PROXY/orders?note=\$long_value\""
  curl -s -o /dev/null -w "%{http_code}\n" "$PROXY/orders?note=$long_value"
  echo
done
echo "\$ # the same 8170-character value sent to uvicorn without nginx"
echo "\$ curl -s -o /dev/null -w \"%{http_code}\\n\" \"$APP/orders?note=\$long_value\""
curl -s -o /dev/null -w "%{http_code}\n" "$APP/orders?note=$long_value"
echo
echo "\$ curl -s \"$PROXY/orders?note=\$long_value\" | head -4"
curl -s "$PROXY/orders?note=$long_value" | head -4
echo

echo "### 7. Secrets in the query string end up in logs"
run curl -s -o /dev/null "$PROXY/orders?api_key=demo-key-123&status=paid"
run curl -s -o /dev/null -H "Authorization: Bearer demo-key-123" "$PROXY/orders?status=paid"
echo "\$ tail -2 nginx/access.log"
tail -2 nginx/access.log
echo

echo "### 8. HTTP QUERY with a JSON body"
run curl -s -i -X QUERY "$APP/orders" -H "Content-Type: application/json" \
  -d '{"status": ["paid"], "customer_ids": [7, 8], "limit": 5}'

echo "\$ # the same QUERY request through nginx (status line and cache header only)"
curl -s -o /dev/null -D - -X QUERY "$PROXY/orders" -H "Content-Type: application/json" \
  -d '{"status": ["paid"]}' | grep -i -E "^HTTP|^x-cache-status"
echo "(no X-Cache-Status header: nginx caches GET and HEAD only by default)"
echo

echo "### 9. Building query strings in client code"
run python3 encoding_demo.py
run node encoding_demo.mjs

echo "### 10. URL length limit of a plain Node.js server"
run node node_url_limit.mjs
