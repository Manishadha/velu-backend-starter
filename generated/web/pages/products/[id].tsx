import { useRouter } from "next/router";
import { useEffect, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

type Product = {
  id: number;
  slug: string;
  name: string;
  description?: string | null;
  price: number;
  currency: string;
  in_stock: boolean;
  category?: string | null;
  is_featured?: boolean;
};

function formatMoney(price: number, currency: string) {
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency || "EUR",
      maximumFractionDigits: 2,
    }).format(price);
  } catch {
    return `${price.toFixed(2)} ${currency}`;
  }
}

export default function ProductDetailPage() {
  const router = useRouter();
  const { id } = router.query;

  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await fetch(`${API_BASE}/api/products/${id}/`);
        if (!res.ok) {
          if (res.status === 404) {
            throw new Error("Product not found");
          }
          throw new Error(`HTTP ${res.status}`);
        }
        const data = (await res.json()) as Product;
        setProduct(data);
      } catch (e: any) {
        setError(String(e));
      } finally {
        setLoading(false);
      }
    }

    load().catch(() => {});
  }, [id]);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#f9fafb",
        color: "#0f172a",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      {/* Header */}
      <header
        style={{
          borderBottom: "1px solid #e5e7eb",
          background: "#ffffff",
          position: "sticky",
          top: 0,
          zIndex: 10,
        }}
      >
        <div
          style={{
            maxWidth: 960,
            margin: "0 auto",
            padding: "12px 16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
          }}
        >
          <button
            type="button"
            onClick={() => router.push("/")}
            style={{
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              padding: "6px 10px",
              background: "#f9fafb",
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            ← Back to products
          </button>
          <div style={{ textAlign: "right" }}>
            <div
              style={{
                fontWeight: 600,
                fontSize: 14,
              }}
            >
              product_v1 shop
            </div>
            <div style={{ fontSize: 11, color: "#6b7280" }}>
              Next.js + FastAPI + Postgres
            </div>
          </div>
        </div>
      </header>

      {/* Main */}
      <main
        style={{
          maxWidth: 960,
          margin: "0 auto",
          padding: "24px 16px 40px",
        }}
      >
        {loading && <p>Loading product…</p>}

        {error && !loading && (
          <div
            style={{
              marginBottom: 12,
              padding: "8px 10px",
              borderRadius: 8,
              border: "1px solid #fca5a5",
              background: "#fef2f2",
              color: "#991b1b",
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}

        {!loading && !error && !product && (
          <p style={{ color: "#6b7280" }}>No product found.</p>
        )}

        {product && (
          <section
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 2fr) minmax(0, 3fr)",
              gap: 24,
            }}
          >
            <div
              style={{
                borderRadius: 16,
                background:
                  "linear-gradient(135deg, #e0f2fe, #ddd6fe, #fee2e2)",
                minHeight: 260,
              }}
            />
            <div>
              <h1
                style={{
                  margin: "0 0 8px",
                  fontSize: 26,
                }}
              >
                {product.name}
              </h1>
              <p
                style={{
                  fontSize: 14,
                  color: "#4b5563",
                  margin: "0 0 12px",
                }}
              >
                {product.description || "No description yet."}
              </p>
              <div
                style={{
                  fontSize: 13,
                  color: "#6b7280",
                  marginBottom: 12,
                }}
              >
                <span
                  style={{
                    display: "inline-block",
                    marginRight: 8,
                  }}
                >
                  <strong>Slug:</strong> {product.slug}
                </span>
                {product.category && (
                  <span
                    style={{
                      display: "inline-block",
                      marginRight: 8,
                    }}
                  >
                    <strong>Category:</strong> {product.category}
                  </span>
                )}
                {product.is_featured && (
                  <span
                    style={{
                      display: "inline-block",
                      fontSize: 12,
                      padding: "2px 8px",
                      borderRadius: 999,
                      background: "#fef3c7",
                      color: "#92400e",
                    }}
                  >
                    Featured
                  </span>
                )}
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "baseline",
                  gap: 8,
                  marginBottom: 16,
                }}
              >
                <div
                  style={{
                    fontSize: 22,
                    fontWeight: 700,
                  }}
                >
                  {formatMoney(product.price, product.currency)}
                </div>
                <div
                  style={{
                    fontSize: 13,
                    color: product.in_stock ? "#16a34a" : "#b91c1c",
                  }}
                >
                  {product.in_stock ? "In stock" : "Out of stock"}
                </div>
              </div>

              <button
                type="button"
                disabled={!product.in_stock}
                style={{
                  borderRadius: 999,
                  border: "1px solid #111827",
                  background: product.in_stock ? "#111827" : "#9ca3af",
                  color: "#ffffff",
                  padding: "8px 14px",
                  fontSize: 14,
                  cursor: product.in_stock ? "pointer" : "not-allowed",
                }}
              >
                {product.in_stock ? "Add to cart (wire later)" : "Out of stock"}
              </button>

              <p
                style={{
                  marginTop: 10,
                  fontSize: 11,
                  color: "#6b7280",
                }}
              >
                In a real project, this button would call the cart API or your
                checkout flow. Here it’s just a safe demo.
              </p>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
