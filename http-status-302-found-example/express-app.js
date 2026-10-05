// The same invoice PDF redirect in an Express app. res.redirect() sends HTTP 302 by default.
const express = require("express");

const app = express();

app.get("/invoices/:id/pdf", (req, res) => {
  res.set("Cache-Control", "no-store");
  const storageUrl = "/storage/invoices/" + req.params.id + ".pdf?expires=1791200000&sig=3f9a1c";
  res.redirect(storageUrl);
});

app.listen(9183, "127.0.0.1", () => console.log("Express app on http://127.0.0.1:9183"));
