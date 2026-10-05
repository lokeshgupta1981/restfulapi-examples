// A tiny demo token issuer (authorization server) for the Orders API example.
// It supports only the OAuth 2.0 client credentials grant (RFC 6749, section 4.4)
// and signs JWT access tokens (RFC 9068) with an RSA key created at startup.
// Demo only: use a real authorization server in production.
import express from "express";
import { randomUUID } from "node:crypto";
import { generateKeyPair, exportJWK, SignJWT } from "jose";

const PORT = Number(process.env.ISSUER_PORT ?? 4000);
const ISSUER = "http://localhost:" + PORT;
const KEY_ID = "demo-key-1";

// Registered demo clients. Lifetimes are in seconds.
const clients = {
  "orders-app": {
    secret: "orders-app-secret",
    allowedScopes: ["orders:read", "orders:write"],
    tokenLifetime: 300,
  },
  "reports-app": {
    secret: "reports-app-secret",
    allowedScopes: ["reports:read"],
    tokenLifetime: 300,
  },
  "short-lived-app": {
    secret: "short-lived-app-secret",
    allowedScopes: ["orders:read"],
    tokenLifetime: 2,
  },
};

// APIs (resource servers) this issuer can issue tokens for.
const knownResources = ["http://localhost:3000/orders", "http://localhost:3000/billing"];

const { publicKey, privateKey } = await generateKeyPair("RS256");
const publicJwk = { ...(await exportJWK(publicKey)), kid: KEY_ID, alg: "RS256", use: "sig" };

const app = express();
app.disable("x-powered-by");
app.use(express.urlencoded({ extended: false }));

// The API downloads the public key from here to verify signatures.
app.get("/.well-known/jwks.json", (req, res) => {
  res.json({ keys: [publicJwk] });
});

function tokenError(res, status, error, description) {
  res.set("Cache-Control", "no-store");
  res.status(status).json({ error, error_description: description });
}

app.post("/token", async (req, res) => {
  // Client authentication with HTTP Basic (RFC 6749, section 2.3.1).
  const authHeader = req.get("authorization") ?? "";
  const [scheme, encoded] = authHeader.split(" ");
  if (scheme?.toLowerCase() !== "basic" || !encoded) {
    res.set("WWW-Authenticate", 'Basic realm="demo-issuer"');
    return tokenError(res, 401, "invalid_client", "Client authentication is required");
  }
  const decoded = Buffer.from(encoded, "base64").toString("utf8");
  const separator = decoded.indexOf(":");
  const clientId = decoded.slice(0, separator);
  const clientSecret = decoded.slice(separator + 1);
  const client = clients[clientId];
  if (!client || client.secret !== clientSecret) {
    res.set("WWW-Authenticate", 'Basic realm="demo-issuer"');
    return tokenError(res, 401, "invalid_client", "Unknown client or wrong secret");
  }

  if (req.body?.grant_type !== "client_credentials") {
    return tokenError(res, 400, "unsupported_grant_type", "Only client_credentials is supported");
  }

  // The resource parameter (RFC 8707) names the API the token is for.
  const resource = req.body.resource;
  if (!knownResources.includes(resource)) {
    return tokenError(res, 400, "invalid_target", "Unknown resource");
  }

  const requestedScopes = (req.body.scope ?? "").split(" ").filter(Boolean);
  const grantedScopes = requestedScopes.filter((scope) => client.allowedScopes.includes(scope));
  if (requestedScopes.length > 0 && grantedScopes.length === 0) {
    return tokenError(res, 400, "invalid_scope", "None of the requested scopes is allowed");
  }
  const scope = (grantedScopes.length > 0 ? grantedScopes : client.allowedScopes).join(" ");

  const accessToken = await new SignJWT({ scope, client_id: clientId })
    .setProtectedHeader({ alg: "RS256", typ: "at+jwt", kid: KEY_ID })
    .setIssuer(ISSUER)
    .setSubject(clientId)
    .setAudience(resource)
    .setIssuedAt()
    .setExpirationTime(client.tokenLifetime + "s")
    .setJti(randomUUID())
    .sign(privateKey);

  res.set("Cache-Control", "no-store");
  res.json({
    access_token: accessToken,
    token_type: "Bearer",
    expires_in: client.tokenLifetime,
    scope,
  });
});

app.listen(PORT, () => {
  console.log("Demo issuer listening on " + ISSUER);
});
