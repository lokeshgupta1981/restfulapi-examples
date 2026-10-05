import express from "express";

const app = express();

app.post("/v1/orders", (req, res) => {
  res.set("Cache-Control", "max-age=3600");
  res.redirect(308, "/v2/orders");
});

app.post("/maintenance/orders", (req, res) => {
  res.redirect("/v2/orders");
});

app.listen(9193);
