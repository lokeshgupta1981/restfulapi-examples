// How JavaScript (Node.js 22 or a browser) encodes the same values.
const values = ["C++ & Java/Go", "café", "50% off", "~user*(1)!"];
const base = "http://127.0.0.1:9160";

for (const [name, fn] of [
  ["encodeURIComponent(v)", encodeURIComponent],
  ["encodeURI(v)", encodeURI],
  ["URLSearchParams({ q: v })", (v) => new URLSearchParams({ q: v }).toString()],
]) {
  console.log(`${name}:`);
  for (const v of values) {
    console.log(`  ${JSON.stringify(v).padEnd(18)} -> ${fn(v)}`);
  }
}

console.log();
console.log("URL object, searchParams.set():");
const searchUrl = new URL("/v2/docs/report", base);
searchUrl.searchParams.set("tag", "C++ & Java/Go");
console.log("  href:", searchUrl.href);
let response = await fetch(searchUrl);
console.log("  received:", JSON.stringify((await response.json()).query));

console.log("URL object, pathname with a slash in the value:");
const pathUrl = new URL(base);
pathUrl.pathname = "/v2/docs/AB/12 café";
console.log("  href:", pathUrl.href);
response = await fetch(pathUrl);
console.log("  status:", response.status);

console.log("Path segment from encodeURIComponent():");
const docName = "AB/12 café";
const docUrl = base + "/v2/docs/" + encodeURIComponent(docName);
console.log("  url:", docUrl);
response = await fetch(docUrl);
console.log("  received:", (await response.json()).name);

console.log();
try {
  decodeURIComponent("50%zz");
} catch (err) {
  console.log("decodeURIComponent('50%zz') throws", err.name + ":", err.message);
}
