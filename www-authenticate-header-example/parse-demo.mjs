// Parses the RFC 9110 example value and prints the result.
import { parseChallenges } from "./parse-challenges.mjs";

const value = 'Basic realm="simple", Newauth realm="apps", type=1, title="Login to \\"apps\\""';
const challenges = parseChallenges(value);
console.log(JSON.stringify(challenges, null, 2));
