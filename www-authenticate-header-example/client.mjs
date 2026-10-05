// A client that reads the WWW-Authenticate challenge and decides what to do next.
import { parseChallenges } from "./parse-challenges.mjs";

const API = "http://127.0.0.1:9420";

async function call(method, path, token) {
  const headers = token ? { Authorization: "Bearer " + token } : {};
  const response = await fetch(API + path, { method, headers });
  // fetch() joins repeated WWW-Authenticate lines with ", ".
  const challenges = parseChallenges(response.headers.get("www-authenticate"));
  const bearer = challenges.find((c) => c.scheme === "bearer");
  console.log(method, path, "->", response.status);
  return { response, challenges, bearer };
}

function nextStep(bearer) {
  if (!bearer) return "no Bearer challenge: stop and report the error";
  const error = bearer.params.error;
  if (!error) return "no token sent: get one from the authorization server";
  if (error === "invalid_token") return "refresh the token once, then retry";
  if (error === "insufficient_scope") return "ask for scope '" + bearer.params.scope + "', do not retry as is";
  if (error === "invalid_request") return "fix the Authorization header, do not retry as is";
  return "unknown error code: " + error;
}

// 1. No token: the challenge points to the resource metadata.
let result = await call("GET", "/shipments");
console.log("  next step:", nextStep(result.bearer));
const metadataUrl = result.bearer.params.resource_metadata;
const metadata = await (await fetch(metadataUrl)).json();
// RFC 9728 section 3.3: use the metadata only if "resource" is the URL we called.
if (metadata.resource !== API + "/shipments") throw new Error("Resource mismatch: " + metadata.resource);
console.log("  authorization server from metadata:", metadata.authorization_servers[0]);

// 2. Expired token.
result = await call("GET", "/shipments", "demo-token-expired");
console.log("  next step:", nextStep(result.bearer));

// 3. Valid token without the write scope.
result = await call("POST", "/shipments", "demo-token-read");
console.log("  next step:", nextStep(result.bearer));

// 4. Two challenges sent as two header lines.
result = await call("GET", "/v2/shipments");
console.log("  schemes offered:", result.challenges.map((c) => c.scheme).join(" and "));
console.log("  next step:", nextStep(result.bearer));
