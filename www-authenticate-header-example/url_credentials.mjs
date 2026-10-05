// fetch() refuses a URL that contains a user name and password.
try {
  await fetch("http://ana:demo-pass-123@127.0.0.1:9420/legacy/reports");
} catch (error) {
  console.log(error.name + ": " + error.message);
}
