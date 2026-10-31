// PKCE in the browser (or Node.js 20+) with the Web Crypto API.
// Run: node pkce.mjs

function base64url(bytes) {
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function createVerifier() {
  return base64url(crypto.getRandomValues(new Uint8Array(32)));
}

export async function createChallenge(verifier) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return base64url(new Uint8Array(digest));
}

// RFC 7636, Appendix B test vector
const rfc = await createChallenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk");
console.log("RFC 7636 challenge:", rfc, rfc === "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM");

const verifier = createVerifier();
console.log("code_verifier :", verifier);
console.log("code_challenge:", await createChallenge(verifier));
