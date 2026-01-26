import { useEffect, useState, FormEvent } from "react";

type Product = {
  id: number;
  name: string;
  price: number;
  currency: string;
  in_stock: boolean;
};

type Line = {
  product: Product;
  quantity: number;
};

export default function CheckoutPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [lines, setLines] = useState<Line[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [address, setAddress] = useState("");
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const res = await fetch("http://127.0.0.1:9001/products");
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data: Product[] = await res.json();
        setProducts(data);
        const initialLines = data
          .filter((p) => p.in_stock)
          .map((p) => ({ product: p, quantity: 1 }));
        setLines(initialLines);
      } catch (err: any) {
        setError("Could not load products for checkout. Is the API on :9001?");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  function updateQuantity(id: number, qty: number) {
    setLines((prev) =>
      prev
        .map((l) =>
          l.product.id === id ? { ...l, quantity: Math.max(0, qty) } : l,
        )
        .filter((l) => l.quantity > 0),
    );
  }

  const total = lines.reduce(
    (sum, l) => sum + l.quantity * l.product.price,
    0,
  );
  const currency = lines[0]?.product.currency || "EUR";

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitted(true);
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        padding: "2rem 1.5rem",
        maxWidth: "1100px",
        margin: "0 auto",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      <header style={{ marginBottom: "1.75rem" }}>
        <p
          style={{
            fontSize: "0.8rem",
            textTransform: "uppercase",
            letterSpacing: "0.18em",
            color: "#6b7280",
            marginBottom: "0.4rem",
          }}
        >
          Checkout
        </p>
        <h1 style={{ fontSize: "2rem", fontWeight: 700, marginBottom: "0.4rem" }}>
          Complete your order
        </h1>
        <p style={{ color: "#4b5563", maxWidth: "38rem" }}>
          This checkout page is wired to the FastAPI <code>/products</code>{" "}
          endpoint on port <strong>9001</strong>. It demonstrates how Velu can
          connect your frontend to your ecommerce backend.
        </p>
      </header>

      {loading && <p>Loading order summary…</p>}
      {error && <p style={{ color: "#b91c1c" }}>{error}</p>}

      {!loading && !error && (
        <section
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 2fr) minmax(0, 1.4fr)",
            gap: "1.75rem",
            alignItems: "flex-start",
          }}
        >
          <div
            style={{
              borderRadius: "1rem",
              border: "1px solid #e5e7eb",
              padding: "1.25rem 1.5rem",
              background: "#fff",
              boxShadow: "0 6px 18px rgba(15,23,42,0.05)",
            }}
          >
            <h2
              style={{
                fontSize: "1.25rem",
                fontWeight: 600,
                marginBottom: "0.75rem",
              }}
            >
              Order summary
            </h2>

            {lines.length === 0 && (
              <p style={{ fontSize: "0.95rem", color: "#6b7280" }}>
                No in-stock products found. Add items on the Products page first.
              </p>
            )}

            {lines.map((line) => (
              <div
                key={line.product.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "0.6rem 0",
                  borderBottom: "1px solid #f3f4f6",
                  gap: "0.75rem",
                }}
              >
                <div style={{ flex: 1 }}>
                  <p style={{ fontWeight: 500 }}>{line.product.name}</p>
                  <p
                    style={{
                      fontSize: "0.85rem",
                      color: "#6b7280",
                      marginTop: "0.15rem",
                    }}
                  >
                    {line.product.price.toFixed(2)} {line.product.currency} each
                  </p>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.45rem",
                    fontSize: "0.9rem",
                  }}
                >
                  <button
                    type="button"
                    onClick={() =>
                      updateQuantity(line.product.id, line.quantity - 1)
                    }
                    style={{
                      width: "1.9rem",
                      height: "1.9rem",
                      borderRadius: "999px",
                      border: "1px solid #e5e7eb",
                      background: "#f9fafb",
                      cursor: "pointer",
                    }}
                  >
                    -
                  </button>
                  <span>{line.quantity}</span>
                  <button
                    type="button"
                    onClick={() =>
                      updateQuantity(line.product.id, line.quantity + 1)
                    }
                    style={{
                      width: "1.9rem",
                      height: "1.9rem",
                      borderRadius: "999px",
                      border: "1px solid #e5e7eb",
                      background: "#f9fafb",
                      cursor: "pointer",
                    }}
                  >
                    +
                  </button>
                </div>
                <div style={{ minWidth: "5.5rem", textAlign: "right" }}>
                  <p style={{ fontWeight: 600 }}>
                    {(line.product.price * line.quantity).toFixed(2)}{" "}
                    {line.product.currency}
                  </p>
                </div>
              </div>
            ))}

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginTop: "0.9rem",
                paddingTop: "0.9rem",
                borderTop: "1px solid #e5e7eb",
                fontWeight: 600,
              }}
            >
              <span>Order total</span>
              <span>
                {total.toFixed(2)} {currency}
              </span>
            </div>
          </div>

          <form
            onSubmit={handleSubmit}
            style={{
              borderRadius: "1rem",
              border: "1px solid #e5e7eb",
              padding: "1.25rem 1.5rem",
              background: "#fff",
              boxShadow: "0 6px 18px rgba(15,23,42,0.05)",
              display: "grid",
              gap: "0.85rem",
            }}
          >
            <h2
              style={{
                fontSize: "1.25rem",
                fontWeight: 600,
                marginBottom: "0.5rem",
              }}
            >
              Shipping details
            </h2>

            <label style={{ fontSize: "0.9rem" }}>
              Full name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                style={{
                  width: "100%",
                  marginTop: "0.25rem",
                  padding: "0.5rem 0.65rem",
                  borderRadius: "0.6rem",
                  border: "1px solid #e5e7eb",
                }}
              />
            </label>

            <label style={{ fontSize: "0.9rem" }}>
              Email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={{
                  width: "100%",
                  marginTop: "0.25rem",
                  padding: "0.5rem 0.65rem",
                  borderRadius: "0.6rem",
                  border: "1px solid #e5e7eb",
                }}
              />
            </label>

            <label style={{ fontSize: "0.9rem" }}>
              Shipping address
              <textarea
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                required
                rows={3}
                style={{
                  width: "100%",
                  marginTop: "0.25rem",
                  padding: "0.5rem 0.65rem",
                  borderRadius: "0.6rem",
                  border: "1px solid #e5e7eb",
                  resize: "vertical",
                }}
              />
            </label>

            <button
              type="submit"
              disabled={lines.length === 0 || total === 0}
              style={{
                marginTop: "0.75rem",
                padding: "0.7rem 1rem",
                borderRadius: "0.8rem",
                border: "none",
                background:
                  lines.length === 0 || total === 0 ? "#9ca3af" : "#111827",
                color: "#f9fafb",
                fontWeight: 600,
                cursor:
                  lines.length === 0 || total === 0
                    ? "not-allowed"
                    : "pointer",
              }}
            >
              Place order
            </button>

            {submitted && (
              <p
                style={{
                  marginTop: "0.5rem",
                  fontSize: "0.9rem",
                  color: "#15803d",
                }}
              >
                Order submitted in demo mode. Connect this form to a real
                backend endpoint to process payments or store orders.
              </p>
            )}
          </form>
        </section>
      )}
    </main>
  );
}
