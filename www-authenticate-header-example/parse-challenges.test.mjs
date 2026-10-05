// Run with: node --test
import { test } from "node:test";
import assert from "node:assert/strict";
import { parseChallenges } from "./parse-challenges.mjs";

test("RFC 9110 example: two challenges on one line", () => {
  const value = 'Basic realm="simple", Newauth realm="apps", type=1, title="Login to \\"apps\\""';
  assert.deepEqual(parseChallenges(value), [
    { scheme: "basic", params: { realm: "simple" }, token68: null },
    { scheme: "newauth", params: { realm: "apps", type: "1", title: 'Login to "apps"' }, token68: null },
  ]);
});

test("comma inside a quoted-string does not split the challenge", () => {
  const value = 'Bearer realm="shipments-api", error="invalid_token", error_description="Expired, get a new one"';
  assert.equal(parseChallenges(value)[0].params.error_description, "Expired, get a new one");
  assert.equal(parseChallenges(value).length, 1);
});

test("two header lines joined by fetch() with a comma", () => {
  const value = 'Bearer realm="shipments-api", DPoP algs="ES256 PS256"';
  const schemes = parseChallenges(value).map((c) => c.scheme);
  assert.deepEqual(schemes, ["bearer", "dpop"]);
});

test("scheme without parameters, followed by another challenge", () => {
  const value = 'Bearer, DPoP algs="ES256 PS256"';
  assert.deepEqual(parseChallenges(value), [
    { scheme: "bearer", params: {}, token68: null },
    { scheme: "dpop", params: { algs: "ES256 PS256" }, token68: null },
  ]);
});

test("token68 challenge", () => {
  const value = "Negotiate YIIBhgYGKwYBBQUCoIIBejCCAXag==";
  assert.deepEqual(parseChallenges(value), [
    { scheme: "negotiate", params: {}, token68: "YIIBhgYGKwYBBQUCoIIBejCCAXag==" },
  ]);
});

test("case-insensitive scheme and parameter names, token values", () => {
  const value = "BASIC Realm=legacy, CHARSET=UTF-8";
  assert.deepEqual(parseChallenges(value), [
    { scheme: "basic", params: { realm: "legacy", charset: "UTF-8" }, token68: null },
  ]);
});
