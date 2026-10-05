// Parses a WWW-Authenticate (or Proxy-Authenticate) value into challenges.
// Grammar: RFC 9110 section 11.3, challenge = auth-scheme [ 1*SP ( token68 / #auth-param ) ]
// Works in Node.js and in the browser.

const TOKEN = /^[!#$%&'*+\-.^_`|~0-9A-Za-z]+/;
const TOKEN68 = /^[A-Za-z0-9\-._~+\/]+=*/;

export function parseChallenges(value) {
  const challenges = [];
  let rest = value || "";
  let current = null;

  const skip = (re) => { rest = rest.replace(re, ""); };

  while (true) {
    skip(/^[\s,]+/);
    if (!rest) break;

    const name = rest.match(TOKEN);
    if (!name) throw new SyntaxError("Unexpected text: " + rest);
    const afterName = rest.slice(name[0].length);

    // "name =" means a parameter of the current challenge. Anything else starts a new challenge.
    if (current && /^\s*=/.test(afterName) && !current.token68) {
      rest = afterName.replace(/^\s*=\s*/, "");
      let paramValue;
      if (rest.startsWith('"')) {
        const quoted = rest.match(/^"((?:[^"\\]|\\.)*)"/);
        if (!quoted) throw new SyntaxError("Unclosed quoted-string");
        paramValue = quoted[1].replace(/\\(.)/g, "$1");
        rest = rest.slice(quoted[0].length);
      } else {
        const token = rest.match(TOKEN);
        if (!token) throw new SyntaxError("Missing value for " + name[0]);
        paramValue = token[0];
        rest = rest.slice(token[0].length);
      }
      // Parameter names are case-insensitive (RFC 9110 section 11.2).
      current.params[name[0].toLowerCase()] = paramValue;
      continue;
    }

    // A new challenge: the scheme name is case-insensitive too.
    current = { scheme: name[0].toLowerCase(), params: {}, token68: null };
    challenges.push(current);
    rest = afterName;

    // A token68 follows the scheme after a space and is not followed by "=" plus a value.
    const space = rest.match(/^ +/);
    if (space) {
      const candidate = rest.slice(space[0].length);
      const t68 = candidate.match(TOKEN68);
      if (t68) {
        const after = candidate.slice(t68[0].length);
        if (/^\s*(,|$)/.test(after) && !/^[A-Za-z0-9\-._~+\/]+\s*=\s*[^=\s,]/.test(candidate)) {
          current.token68 = t68[0];
          rest = after;
        }
      }
    }
  }
  return challenges;
}
