// Orders API that accepts JWT bearer tokens (RFC 6750, RFC 9068).
import express from "express";
import { createRemoteJWKSet, jwtVerify, errors } from "jose";

const PORT = Number(process.env.API_PORT ?? 3000);
const ISSUER = process.env.ISSUER_URL ?? "http://localhost:4000";
const AUDIENCE = "http://localhost:" + PORT + "/orders";
const REALM = "orders-api";

// jose downloads and caches the issuer's public keys.
const jwks = createRemoteJWKSet(new URL(ISSUER + "/.well-known/jwks.json"));

// b64token from RFC 6750, section 2.1. The scheme name is case-insensitive.
const BEARER_PATTERN = /^Bearer +([A-Za-z0-9\-._~+/]+=*)$/i;

const orders = [
  { id: "ord-1001", status: "shipped", total: "49.90", currency: "USD" },
  { id: "ord-1002", status: "pending", total: "15.00", currency: "USD" },
];

// A rejected request: status code, RFC 6750 error code and description.
class AuthError extends Error {
  constructor(status, error, description, scope) {
    super(description);
    this.status = status;
    this.error = error; // undefined when the request had no credentials
    this.scope = scope;
  }
}

// The API could not load the issuer's keys. The token may be fine.
class KeySetUnavailable extends Error {}

function challenge(authError) {
  const params = ['realm="' + REALM + '"'];
  if (authError.error) {
    params.push('error="' + authError.error + '"');
    params.push('error_description="' + authError.message + '"');
  }
  if (authError.scope) {
    params.push('scope="' + authError.scope + '"');
  }
  return "Bearer " + params.join(", ");
}

// This API reads the header and the query string only. GET requests have
// no body, so the form body method of RFC 6750 does not apply here.
function extractToken(req) {
  const header = req.get("authorization");
  const queryToken = req.query.access_token;

  if (header && queryToken) {
    throw new AuthError(400, "invalid_request", "Send the access token in one place only");
  }
  if (queryToken) {
    // RFC 6750 allows the query method, but this API does not accept it.
    throw new AuthError(400, "invalid_request", "Send the access token in the Authorization header");
  }
  if (!header) {
    throw new AuthError(401, undefined, "No credentials");
  }
  const scheme = header.split(" ")[0];
  if (scheme.toLowerCase() !== "bearer") {
    // A different scheme (for example Basic) counts as "no bearer credentials".
    throw new AuthError(401, undefined, "Unsupported authentication scheme");
  }
  const match = BEARER_PATTERN.exec(header);
  if (!match) {
    throw new AuthError(400, "invalid_request", "Use the format: Authorization: Bearer <token>");
  }
  return match[1];
}

// Network errors, timeouts and bad responses from the JWKS endpoint.
function isKeySetFailure(err) {
  return (
    !(err instanceof errors.JOSEError) ||
    err instanceof errors.JWKSTimeout ||
    err instanceof errors.JWKSInvalid ||
    err.code === "ERR_JOSE_GENERIC"
  );
}

async function validateToken(token) {
  try {
    const { payload } = await jwtVerify(token, jwks, {
      algorithms: ["RS256"],
      issuer: ISSUER,
      audience: AUDIENCE,
      typ: "at+jwt",
      requiredClaims: ["exp", "sub"],
      clockTolerance: 5, // seconds of allowed clock skew
    });
    return payload;
  } catch (err) {
    if (isKeySetFailure(err)) {
      throw new KeySetUnavailable("Cannot load the issuer's signing keys", { cause: err });
    }
    if (err instanceof errors.JWTExpired) {
      throw new AuthError(401, "invalid_token", "The access token expired");
    }
    if (err instanceof errors.JWTClaimValidationFailed && err.claim === "aud") {
      throw new AuthError(401, "invalid_token", "The access token is not meant for this API");
    }
    if (err instanceof errors.JWTClaimValidationFailed && err.claim === "typ") {
      throw new AuthError(401, "invalid_token", "The typ header is not at+jwt");
    }
    if (err instanceof errors.JWTClaimValidationFailed) {
      throw new AuthError(401, "invalid_token", "The " + err.claim + " claim is not valid");
    }
    if (err instanceof errors.JWSSignatureVerificationFailed) {
      throw new AuthError(401, "invalid_token", "The signature is not valid");
    }
    // Includes JWKSNoMatchingKey: jose reloads the key set once before it
    // reports that no key matches, so the token was not signed by this issuer.
    throw new AuthError(401, "invalid_token", "The access token is malformed");
  }
}

// Middleware factory: requireScope("orders:read") protects one route.
function requireScope(requiredScope) {
  return async (req, res, next) => {
    try {
      const token = extractToken(req);
      const claims = await validateToken(token);
      const grantedScopes = String(claims.scope ?? "").split(" ");
      if (!grantedScopes.includes(requiredScope)) {
        throw new AuthError(403, "insufficient_scope", "The access token lacks the required scope", requiredScope);
      }
      req.auth = claims;
      next();
    } catch (err) {
      if (err instanceof KeySetUnavailable) {
        // Not the client's fault: no WWW-Authenticate, so clients do not refresh in a loop.
        console.error(err.message + ": " + err.cause?.message);
        res.set("Retry-After", "30");
        return res.status(503).type("application/problem+json").json({
          type: "about:blank",
          title: "Service Unavailable",
          status: 503,
          detail: "Token validation is not available, try again later",
        });
      }
      if (!(err instanceof AuthError)) {
        return next(err);
      }
      res.set("WWW-Authenticate", challenge(err));
      res.status(err.status).type("application/problem+json").json({
        type: "about:blank",
        title: err.status === 403 ? "Forbidden" : err.status === 400 ? "Bad Request" : "Unauthorized",
        status: err.status,
        detail: err.message,
      });
    }
  };
}

const app = express();
app.disable("x-powered-by");
app.set("etag", false);

// Access log without the Authorization header and without the query string.
app.use((req, res, next) => {
  res.on("finish", () => {
    const caller = req.auth?.sub ?? "-";
    console.log(req.method + " " + req.path + " " + res.statusCode + " sub=" + caller);
  });
  next();
});

app.get("/orders", requireScope("orders:read"), (req, res) => {
  res.json({ caller: req.auth.sub, orders });
});

app.listen(PORT, () => {
  console.log("Orders API listening on http://localhost:" + PORT);
});
