# Errors

Errors use Problem Details (RFC 9457) with the media type application/problem+json:

    {"type": "https://api.acme.example/errors/validation", "title": "Validation failed", "status": 422,
     "errors": [{"field": "items[0].quantity", "message": "must be at least 1"}]}

Retry HTTP 429 and HTTP 503 after the number of seconds in the Retry-After header. Do not retry HTTP 4xx errors other than 429.
