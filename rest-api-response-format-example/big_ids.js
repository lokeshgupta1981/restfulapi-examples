// Why IDs go over the wire as strings: JavaScript numbers are IEEE 754 doubles.
const body = '{"orderId": 9007199254740993, "orderIdText": "9007199254740993"}';
const order = JSON.parse(body);

console.log("Number.MAX_SAFE_INTEGER:", Number.MAX_SAFE_INTEGER);
console.log("orderId as number:      ", order.orderId);
console.log("orderId as string:      ", order.orderIdText);
console.log("Same order?             ", String(order.orderId) === order.orderIdText);

// Money has the same problem with floating point.
console.log("0.1 + 0.2 =", 0.1 + 0.2);
