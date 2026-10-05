import { Configuration, OrdersApi } from "./client";

const config = new Configuration({
  basePath: "http://127.0.0.1:4010",
  accessToken: "demo-token",
});
const ordersApi = new OrdersApi(config);

const page = await ordersApi.listOrders({ status: "pending", limit: 10 });
console.log("listOrders ->", page.items.length, "order(s), first id:", page.items[0]?.id);

const order = await ordersApi.createOrder({
  idempotencyKey: "5f2b7c1e-9a4d-4c55-8f0e-2d6b1a7e3c90",
  newOrder: { currency: "USD", items: [{ sku: "BOOK-REST-101", quantity: 2 }] },
});
console.log("createOrder ->", order.id, order.status, order.createdAt.toISOString());
