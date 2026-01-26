import express from "express";

const app = express();
app.use(express.json());

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

const port = process.env.PORT || 8000;
app.listen(port, () => {
  console.log(`API listening on ${port}`);
});
