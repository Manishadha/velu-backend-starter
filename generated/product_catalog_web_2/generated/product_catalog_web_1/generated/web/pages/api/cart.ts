import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== "POST") {
    res.setHeader("Allow", ["POST"]);
    return res.status(405).json({ detail: "Method not allowed" });
  }

  try {
    const backendBase = process.env.BACKEND_URL || "http://127.0.0.1:9001";

    const resp = await fetch(`${backendBase}/cart`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // req.body can be object or string; ensure we send JSON string
      body: typeof req.body === "string" ? req.body : JSON.stringify(req.body),
    });

    const data = await resp.json();
    res.status(resp.status).json(data);
  } catch (err) {
    console.error("Error calling backend /cart:", err);
    res.status(500).json({ detail: "Failed to reach backend /cart" });
  }
}
