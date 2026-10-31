// Retry with capped exponential backoff, full jitter and Retry-After, using fetch (Node 18+).
const RETRYABLE_STATUS = new Set([408, 429, 500, 502, 503, 504]);
const IDEMPOTENT_METHODS = new Set(["GET", "HEAD", "OPTIONS", "PUT", "DELETE"]);
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function backoffDelay(attempt, baseMs = 500, capMs = 8000) {
  return Math.random() * Math.min(capMs, baseMs * 2 ** attempt);   // full jitter
}

function retryAfterMs(response) {
  const value = response.headers.get("Retry-After");
  if (value === null) return null;
  if (/^\d+$/.test(value.trim())) return Number(value) * 1000;
  const date = Date.parse(value);
  return Number.isNaN(date) ? null : Math.max(0, date - Date.now());
}

export async function fetchWithRetry(url, options = {}, { maxAttempts = 5, timeoutMs = 2000 } = {}) {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  const canRetry = IDEMPOTENT_METHODS.has(method) || headers.has("Idempotency-Key");
  const start = Date.now();

  for (let attempt = 0; ; attempt++) {
    let response = null, error = null;
    try {
      response = await fetch(url, { ...options, signal: AbortSignal.timeout(timeoutMs) });
      if (!RETRYABLE_STATUS.has(response.status)) return response;
    } catch (e) {
      error = e;                                   // network error or timeout
    }
    if (!canRetry || attempt === maxAttempts - 1) {
      if (response) return response;
      throw error;
    }
    const wait = (response && retryAfterMs(response)) ?? backoffDelay(attempt);
    const elapsed = ((Date.now() - start) / 1000).toFixed(2);
    console.log(elapsed + "s  attempt " + (attempt + 1) + ": " + (response?.status ?? error.name) +
                ", waiting " + (wait / 1000).toFixed(2) + "s");
    await pause(wait);
  }
}

if (import.meta.url === "file://" + process.argv[1]) {
  const response = await fetchWithRetry("http://127.0.0.1:8000/orders/1003?fail=2");
  console.log(response.status, await response.text());
}
