import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "Method not allowed" });
  }

  try {
    const body = req.body || {};

    const company = body.company || { name: "Console App" };

    const rawLocales: string | string[] | undefined = body.locales;
    let locales: string[] | undefined;
    if (Array.isArray(rawLocales)) {
      locales = rawLocales.map((x) => String(x).trim()).filter(Boolean);
    } else if (typeof rawLocales === "string") {
      locales = rawLocales
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean);
    }

    const payload = {
      company,
      product: {
        type: "saas",
        goal: "internal_tool",
        ...(locales && locales.length > 0 ? { locales } : {}),
      },
      idea: body.idea || "",
      run_pipeline: Boolean(body.run_pipeline),
    };

    const r = await fetch("http://localhost:8000/v1/assistant/intake", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await r.json();
    return res.status(r.status).json(data);
  } catch (err) {
    return res.status(500).json({ error: "assistant intake proxy failed" });
  }
}
