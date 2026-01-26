import { useEffect, useMemo, useState } from "react";

type Product = {
  id: number;
  name: string;
  price: number;
  currency: string;
  category: string;
  in_stock: boolean;
  image_url?: string | null;
  description?: string | null;
};

type CartItem = {
  product: Product;
  quantity: number;
};

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

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
      } catch (err: any) {
        console.error("Failed to load products", err);
        setError(
          "Could not load products. Is the FastAPI server running on :9001?",
        );
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  function addToCart(product: Product) {
    setCart((prev) => {
      const existing = prev.find((item) => item.product.id === product.id);
      if (existing) {
        return prev.map((item) =>
          item.product.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item,
        );
      }
      return [...prev, { product, quantity: 1 }];
    });
  }

  function updateQuantity(productId: number, delta: number) {
    setCart((prev) =>
      prev
        .map((item) =>
          item.product.id === productId
            ? { ...item, quantity: Math.max(1, item.quantity + delta) }
            : item,
        )
        .filter((item) => item.quantity > 0),
    );
  }

  function clearCart() {
    setCart([]);
  }

  const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
  const totalPrice = cart.reduce(
    (sum, item) => sum + item.quantity * item.product.price,
    0,
  );

  const categories = useMemo(
    () =>
      Array.from(new Set(products.map((p) => p.category))).sort(
        (a, b) => a.localeCompare(b),
      ),
    [products],
  );

  const filteredProducts = useMemo(() => {
    const q = search.trim().toLowerCase();
    return products.filter((p) => {
      if (selectedCategory !== "all" && p.category !== selectedCategory) {
        return false;
      }
      if (!q) return true;
      return (
        p.name.toLowerCase().includes(q) ||
        (p.description && p.description.toLowerCase().includes(q)) ||
        p.category.toLowerCase().includes(q)
      );
    });
  }, [products, search, selectedCategory]);

  return (
    <main
      style={{
        minHeight: "100vh",
        padding: "2rem 1.5rem",
        maxWidth: "1100px",
        margin: "0 auto",
        fontFamily:
          "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      <header
        style={{
          marginBottom: "2rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: "1.5rem",
          flexWrap: "wrap",
        }}
      >
        <div>
          <p
            style={{
              fontSize: "0.85rem",
              textTransform: "uppercase",
              letterSpacing: "0.15em",
              color: "#6b7280",
              marginBottom: "0.5rem",
            }}
          >
            Products
          </p>
          <h1
            style={{
              fontSize: "2rem",
              fontWeight: 700,
              marginBottom: "0.25rem",
            }}
          >
            Shop the collection
          </h1>
          <p style={{ color: "#4b5563", maxWidth: "36rem" }}>
            Browse products by category, use search to quickly filter items,
            and simulate a simple cart. Data comes from the FastAPI{" "}
            <code>/products</code> endpoint.
          </p>
        </div>

        <aside
          style={{
            minWidth: "260px",
            padding: "0.9rem 1rem",
            borderRadius: "0.9rem",
            border: "1px solid #e5e7eb",
            background: "#f9fafb",
            boxShadow: "0 4px 12px rgba(15,23,42,0.04)",
          }}
        >
          <p
            style={{
              fontSize: "0.8rem",
              textTransform: "uppercase",
              letterSpacing: "0.15em",
              color: "#6b7280",
              marginBottom: "0.5rem",
            }}
          >
            Filters
          </p>
          <div style={{ marginBottom: "0.75rem" }}>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name or category…"
              style={{
                width: "100%",
                padding: "0.45rem 0.7rem",
                borderRadius: "999px",
                border: "1px solid #d1d5db",
                fontSize: "0.9rem",
                outline: "none",
              }}
            />
          </div>

          {categories.length > 0 && (
            <div style={{ marginBottom: "0.75rem" }}>
              <p
                style={{
                  fontSize: "0.8rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.12em",
                  color: "#6b7280",
                  marginBottom: "0.25rem",
                }}
              >
                Category
              </p>
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "0.35rem",
                }}
              >
                <button
                  type="button"
                  onClick={() => setSelectedCategory("all")}
                  style={{
                    fontSize: "0.8rem",
                    padding: "0.25rem 0.7rem",
                    borderRadius: "999px",
                    border:
                      selectedCategory === "all"
                        ? "1px solid #111827"
                        : "1px solid #e5e7eb",
                    background:
                      selectedCategory === "all" ? "#111827" : "#f9fafb",
                    color:
                      selectedCategory === "all" ? "#ffffff" : "#111827",
                    cursor: "pointer",
                  }}
                >
                  All
                </button>
                {categories.map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setSelectedCategory(cat)}
                    style={{
                      fontSize: "0.8rem",
                      padding: "0.25rem 0.7rem",
                      borderRadius: "999px",
                      border:
                        selectedCategory === cat
                          ? "1px solid #111827"
                          : "1px solid #e5e7eb",
                      background:
                        selectedCategory === cat ? "#111827" : "#f9fafb",
                      color:
                        selectedCategory === cat ? "#ffffff" : "#111827",
                      cursor: "pointer",
                    }}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div
            style={{
              marginTop: "0.5rem",
              paddingTop: "0.5rem",
              borderTop: "1px solid #e5e7eb",
            }}
          >
            <p
              style={{
                fontSize: "0.8rem",
                textTransform: "uppercase",
                letterSpacing: "0.15em",
                color: "#6b7280",
                marginBottom: "0.25rem",
              }}
            >
              Cart summary
            </p>
            <p style={{ fontSize: "0.95rem", marginBottom: "0.25rem" }}>
              Items: <strong>{totalItems}</strong>
            </p>
            <p style={{ fontSize: "0.95rem", marginBottom: "0.5rem" }}>
              Total:{" "}
              <strong>
                {totalPrice.toFixed(2)} {products[0]?.currency ?? "EUR"}
              </strong>
            </p>
            <button
              type="button"
              onClick={clearCart}
              disabled={cart.length === 0}
              style={{
                fontSize: "0.85rem",
                padding: "0.35rem 0.75rem",
                borderRadius: "999px",
                border: "none",
                cursor: cart.length === 0 ? "not-allowed" : "pointer",
                background: cart.length === 0 ? "#e5e7eb" : "#111827",
                color: "#f9fafb",
              }}
            >
              Clear cart
            </button>
          </div>
        </aside>
      </header>

      {loading && <p>Loading products…</p>}
      {error && (
        <p style={{ color: "#b91c1c", marginTop: "1rem" }}>{error}</p>
      )}

      {!loading && !error && (
        <section
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "1.5rem",
            marginTop: "1rem",
          }}
        >
          {filteredProducts.map((p) => (
            <article
              key={p.id}
              style={{
                borderRadius: "1rem",
                border: "1px solid #e5e7eb",
                padding: "1rem",
                display: "flex",
                flexDirection: "column",
                gap: "0.75rem",
                background: "white",
                boxShadow: "0 4px 12px rgba(15,23,42,0.04)",
              }}
            >
              {p.image_url && (
                <div
                  style={{
                    borderRadius: "0.75rem",
                    overflow: "hidden",
                    aspectRatio: "1 / 1",
                    background: "#f3f4f6",
                  }}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={p.image_url}
                    alt={p.name}
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                    }}
                  />
                </div>
              )}

              <div>
                <p
                  style={{
                    fontSize: "0.8rem",
                    color: "#6b7280",
                    marginBottom: "0.15rem",
                  }}
                >
                  {p.category}
                </p>
                <h2
                  style={{
                    fontSize: "1.1rem",
                    fontWeight: 600,
                  }}
                >
                  {p.name}
                </h2>
                {p.description && (
                  <p
                    style={{
                      fontSize: "0.9rem",
                      color: "#4b5563",
                      marginTop: "0.25rem",
                    }}
                  >
                    {p.description}
                  </p>
                )}
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginTop: "auto",
                  gap: "0.5rem",
                }}
              >
                <span style={{ fontWeight: 600 }}>
                  {p.price.toFixed(2)} {p.currency}
                </span>
                <span
                  style={{
                    fontSize: "0.8rem",
                    padding: "0.25rem 0.5rem",
                    borderRadius: "999px",
                    background: p.in_stock ? "#ecfdf5" : "#fef2f2",
                    color: p.in_stock ? "#15803d" : "#b91c1c",
                  }}
                >
                  {p.in_stock ? "In stock" : "Out of stock"}
                </span>
              </div>

              <button
                type="button"
                onClick={() => addToCart(p)}
                disabled={!p.in_stock}
                style={{
                  marginTop: "0.75rem",
                  padding: "0.6rem 0.8rem",
                  borderRadius: "0.75rem",
                  border: "none",
                  cursor: p.in_stock ? "pointer" : "not-allowed",
                  background: p.in_stock ? "#111827" : "#9ca3af",
                  color: "#f9fafb",
                  fontSize: "0.9rem",
                  fontWeight: 500,
                }}
              >
                {p.in_stock ? "Add to cart" : "Out of stock"}
              </button>
            </article>
          ))}
        </section>
      )}

      {cart.length > 0 && (
        <section style={{ marginTop: "2.5rem" }}>
          <h2
            style={{
              fontSize: "1.3rem",
              fontWeight: 600,
              marginBottom: "0.75rem",
            }}
          >
            Cart details
          </h2>
          <div
            style={{
              borderRadius: "1rem",
              border: "1px solid #e5e7eb",
              padding: "1rem",
              background: "white",
              boxShadow: "0 4px 12px rgba(15,23,42,0.04)",
            }}
          >
            {cart.map((item) => (
              <div
                key={item.product.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "0.5rem 0",
                  borderBottom: "1px solid #f3f4f6",
                  gap: "0.75rem",
                }}
              >
                <div style={{ flex: 1 }}>
                  <p style={{ fontWeight: 500 }}>{item.product.name}</p>
                  <p
                    style={{
                      fontSize: "0.85rem",
                      color: "#6b7280",
                    }}
                  >
                    {item.product.price.toFixed(2)}{" "}
                    {item.product.currency} each
                  </p>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.4rem",
                    fontSize: "0.9rem",
                  }}
                >
                  <button
                    type="button"
                    onClick={() =>
                      updateQuantity(item.product.id, -1)
                    }
                    style={{
                      width: "1.8rem",
                      height: "1.8rem",
                      borderRadius: "999px",
                      border: "1px solid #e5e7eb",
                      background: "#f9fafb",
                      cursor: "pointer",
                    }}
                  >
                    -
                  </button>
                  <span>{item.quantity}</span>
                  <button
                    type="button"
                    onClick={() =>
                      updateQuantity(item.product.id, 1)
                    }
                    style={{
                      width: "1.8rem",
                      height: "1.8rem",
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
                    {(item.product.price * item.quantity).toFixed(2)}{" "}
                    {item.product.currency}
                  </p>
                </div>
              </div>
            ))}

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginTop: "0.75rem",
                paddingTop: "0.75rem",
                borderTop: "1px solid #e5e7eb",
                fontWeight: 600,
              }}
            >
              <span>Order total</span>
              <span>
                {totalPrice.toFixed(2)} {products[0]?.currency ?? "EUR"}
              </span>
            </div>
          </div>
        </section>
      )}
    </main>
  );
}
