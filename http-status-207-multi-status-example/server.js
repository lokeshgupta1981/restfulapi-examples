import express from "express";

const MAX_ITEMS = 50;

// In-memory orders for the demo
export function createOrders() {
  return new Map([
    ["ord-1001", { id: "ord-1001", state: "pending" }],
    ["ord-1002", { id: "ord-1002", state: "shipped" }],
    ["ord-1003", { id: "ord-1003", state: "pending" }],
  ]);
}

function problem(status, title, detail) {
  return { type: "about:blank", title, status, detail };
}

function cancelOne(orders, orderId) {
  const order = orders.get(orderId);
  if (!order) {
    return { status: 404, error: problem(404, "Not Found", "Order " + orderId + " does not exist.") };
  }
  if (order.state === "shipped") {
    return { status: 409, error: problem(409, "Conflict", "Order " + orderId + " has already shipped.") };
  }
  order.state = "cancelled";
  return { status: 200, order: { ...order } };
}

export function createApp(orders = createOrders()) {
  const app = express();
  app.use(express.json());

  app.post("/orders/bulk-cancel", (req, res) => {
    const items = req.body?.items;
    if (!Array.isArray(items) || items.length === 0 || items.length > MAX_ITEMS) {
      return res
        .status(422)
        .type("application/problem+json")
        .json(problem(422, "Unprocessable Content", "Send \"items\" as an array of 1 to " + MAX_ITEMS + " orders."));
    }

    const results = items.map((item, index) => ({
      index,
      orderId: item.orderId,
      ...cancelOne(orders, item.orderId),
    }));
    const succeeded = results.filter((result) => result.status < 300).length;

    res.status(207).json({
      results,
      summary: { succeeded, failed: results.length - succeeded },
    });
  });

  // Malformed JSON: the request as a whole fails, so no 207
  app.use((err, req, res, next) => {
    if (err.type === "entity.parse.failed") {
      return res
        .status(400)
        .type("application/problem+json")
        .json(problem(400, "Bad Request", "The request body is not valid JSON."));
    }
    next(err);
  });

  return app;
}

if (import.meta.url === "file://" + process.argv[1]) {
  const port = Number(process.env.PORT || 9207);
  createApp().listen(port, "127.0.0.1", () => console.log("Orders API on http://127.0.0.1:" + port));
}
