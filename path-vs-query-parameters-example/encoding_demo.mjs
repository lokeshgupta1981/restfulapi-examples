// How JavaScript builds query strings and path segments.
const searchParams = new URLSearchParams({ q: "C++ Primer" });
console.log("URLSearchParams:        ", searchParams.toString());
console.log("encodeURIComponent:     ", encodeURIComponent("C++ Primer"));
console.log("encodeURI (keeps & / ?):", encodeURI("AT&T Modem/AB?12"));

const statusParams = new URLSearchParams();
statusParams.append("status", "paid");
statusParams.append("status", "shipped");
console.log("Repeated keys:          ", statusParams.toString());
console.log("getAll('status'):       ", new URLSearchParams("status=paid&status=shipped").getAll("status"));
