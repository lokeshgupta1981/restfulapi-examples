// Tickets API in Express 5 that accepts JSON, form-urlencoded and multipart bodies.
// Run: npm install && npm start   (listens on 127.0.0.1:9171)
import express from "express";
import multer from "multer";

const app = express();
const ACCEPTED = ["application/json", "application/x-www-form-urlencoded", "multipart/form-data"];

// Each parser runs only when the request Content-Type matches its type.
app.use(express.json({ limit: "100kb" }));
app.use(express.urlencoded({ extended: true, limit: "100kb" }));
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 5 * 1024 * 1024 } });

function requireBodyType(req, res, next) {
  if (!req.is(ACCEPTED)) {
    res.status(415).set("Accept", ACCEPTED.join(", ")).type("application/problem+json").send({
      type: "about:blank",
      title: "Unsupported Media Type",
      status: 415,
      detail: "Content-Type '" + (req.get("Content-Type") ?? "(none)") + "' is not supported",
    });
    return;
  }
  next();
}

// Multer errors carry no HTTP status, so we set one here; otherwise Express answers 500.
function parseMultipart(req, res, next) {
  upload.single("attachment")(req, res, (err) => {
    if (err) {
      err.status ??= err.code === "LIMIT_FILE_SIZE" ? 413 : 400;
    }
    next(err);
  });
}

function createTicket(req, res) {
  if (typeof req.body?.subject !== "string") {
    res.status(422).type("application/problem+json").send({
      type: "about:blank",
      title: "Unprocessable Content",
      status: 422,
      detail: "Field 'subject' is required",
      receivedFields: Object.keys(req.body ?? {}),
    });
    return;
  }
  const file = req.file
    ? { filename: req.file.originalname, contentType: req.file.mimetype, size: req.file.size }
    : null;
  res.status(201).json({ contentType: req.get("Content-Type"), body: req.body, attachment: file });
}

app.post("/tickets", requireBodyType, parseMultipart, createTicket);

// Nested JSON and a file in one multipart request: the "ticket" part holds JSON text.
// curl -F sends the JSON part as a text field; a browser Blob arrives as a file named "blob".
const ticketUpload = upload.fields([{ name: "ticket", maxCount: 1 }, { name: "attachment", maxCount: 1 }]);

app.post("/tickets/with-attachment", ticketUpload, (req, res) => {
  const ticketText = req.body.ticket ?? req.files.ticket[0].buffer.toString("utf8");
  const ticket = JSON.parse(ticketText);
  const attachment = req.files.attachment[0];
  res.status(201).json({ parsedAs: "multipart with a JSON part", ticket, attachmentSize: attachment.size });
});

// OAuth 2.0 token endpoint (RFC 6749 section 4.4): form-encoded request, JSON response.
// Demo credentials only: client "ticket-cli", secret "s3cret".
app.post("/oauth/token", (req, res) => {
  res.set("Cache-Control", "no-store");
  if (!req.is("application/x-www-form-urlencoded")) {
    res.status(400).json({
      error: "invalid_request",
      error_description: "Send the token request as application/x-www-form-urlencoded",
    });
    return;
  }
  const basic = Buffer.from("ticket-cli:s3cret").toString("base64");
  if (req.get("Authorization") !== "Basic " + basic) {
    res.status(401).set("WWW-Authenticate", 'Basic realm="tickets"').json({ error: "invalid_client" });
    return;
  }
  if (req.body.grant_type !== "client_credentials") {
    res.status(400).json({ error: "unsupported_grant_type" });
    return;
  }
  res.json({ access_token: "demo-token-7f3a", token_type: "Bearer", expires_in: 3600, scope: req.body.scope ?? "tickets" });
});

// Parser errors (bad JSON, missing boundary, file too large) end up here.
app.use((err, req, res, next) => {
  const status = err.status ?? err.statusCode ?? 500;
  res.status(status).type("application/problem+json").send({
    type: "about:blank",
    title: status === 413 ? "Content Too Large" : "Bad Request",
    status,
    detail: err.message,
  });
});

app.listen(9171, "127.0.0.1", () => console.log("Express tickets API on http://127.0.0.1:9171"));
