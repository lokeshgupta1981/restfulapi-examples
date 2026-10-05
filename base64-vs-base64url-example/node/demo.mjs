// Base64 vs Base64URL in Node.js. Run: node demo.mjs
const data = Buffer.from("<<???>>", "utf8");

console.log("1. Buffer");
console.log("   base64     :", data.toString("base64"));
console.log("   base64url  :", data.toString("base64url"));
console.log("   decode url :", Buffer.from("PDw_Pz8-Pg", "base64url").toString());
// The 'base64' decoder in Buffer also accepts the URL-safe characters
console.log("   'base64' decoder on url text:", Buffer.from("PDw_Pz8-Pg", "base64").toString());
// Buffer skips characters outside both alphabets without an error
console.log("   'base64url' decoder on 'PDw*Pz8-Pg':", Buffer.from("PDw*Pz8-Pg", "base64url"));

console.log("\n2. atob() and btoa() (browsers and Node.js)");
console.log("   atob('PDw/Pz8+Pg') :", atob("PDw/Pz8+Pg"));
console.log("   atob('PDw/Pz8+Pg==') with padding:", atob("PDw/Pz8+Pg=="));
try {
  atob("PDw_Pz8-Pg");
} catch (error) {
  console.log("   atob('PDw_Pz8-Pg') ->", error.name + ":", error.message);
}
try {
  btoa("Café €5");
} catch (error) {
  console.log("   btoa('Caf\\u00e9 \\u20ac5') ->", error.name + ":", error.message);
}

console.log("\n3. Uint8Array.toBase64() / fromBase64()");
if (typeof Uint8Array.fromBase64 === "function") {
  const bytes = new TextEncoder().encode("<<???>>");
  console.log("   toBase64()                    :", bytes.toBase64());
  console.log("   toBase64({alphabet:'base64url', omitPadding:true}):",
    bytes.toBase64({ alphabet: "base64url", omitPadding: true }));
  const decoded = Uint8Array.fromBase64("PDw_Pz8-Pg", { alphabet: "base64url" });
  console.log("   fromBase64('PDw_Pz8-Pg', {alphabet:'base64url'}):", new TextDecoder().decode(decoded));
  try {
    Uint8Array.fromBase64("PDw_Pz8-Pg");
  } catch (error) {
    console.log("   fromBase64('PDw_Pz8-Pg') ->", error.name + ":", error.message);
  }
} else {
  console.log("   not available in Node.js", process.version, "(needs Node.js 25 or later)");
}
