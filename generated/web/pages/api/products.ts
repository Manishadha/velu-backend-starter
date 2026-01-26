import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  try {
    const backendBase = process.env.BACKEND_URL || "http://127.0.0.1:9001";

    const resp = await fetch(`${backendBase}/products`);
    const data = await resp.json();

    res.status(resp.status).json(data);
  } catch (err) {
    console.error("Error fetching products from backend:", err);
    res.status(500).json({ detail: "Failed to reach backend /products" });
  }
}
