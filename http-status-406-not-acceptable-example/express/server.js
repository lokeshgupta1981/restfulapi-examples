const express = require("express");

const app = express();

const salesReport = {
  month: "2026-09",
  rows: [
    { region: "north", orders: 412, revenue: "18350.00" },
    { region: "south", orders: 287, revenue: "12990.50" },
  ],
};

// res.json() never looks at Accept: every client gets JSON with HTTP 200.
app.get("/plain-reports/:month", (req, res) => {
  res.json(salesReport);
});

function reportAsCsv(report) {
  const lines = ["region,orders,revenue"];
  for (const row of report.rows) {
    lines.push(row.region + "," + row.orders + "," + row.revenue);
  }
  return lines.join("\n") + "\n";
}

// res.format() picks a handler from Accept. Without a default handler,
// it passes a NotAcceptableError (status 406) to the error handler.
app.get("/bare-reports/:month", (req, res) => {
  res.format({
    "application/json": () => res.json(salesReport),
    "text/csv": () => res.send(reportAsCsv(salesReport)),
  });
});

// The default handler runs when no type matches, so we control the 406 body.
app.get("/reports/:month", (req, res) => {
  res.format({
    "application/json": () => res.json(salesReport),
    "text/csv": () => res.send(reportAsCsv(salesReport)),
    default: () => {
      res.status(406).type("application/problem+json").send({
        type: "https://example.com/problems/not-acceptable",
        title: "Not Acceptable",
        status: 406,
        detail: "No available format matches Accept: " + req.get("Accept"),
        available: [
          { type: "application/json", href: req.originalUrl },
          { type: "text/csv", href: req.originalUrl },
        ],
      });
    },
  });
});

const port = Number(process.env.PORT || 9407);
app.listen(port, "127.0.0.1", () => console.log("Express app on http://127.0.0.1:" + port));
