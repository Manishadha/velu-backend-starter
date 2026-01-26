import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { useAuth } from "../../lib/auth";
import { apiGet, apiPost, apiDelete } from "../../lib/api";

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

export default function AdminProductsPage() {
  const router = useRouter();
  const { token, user, isAdmin, isReady, logout } = useAuth();

  const [items, setItems] = useState<Product[]>([]);
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const [formSlug, setFormSlug] = useState("");
  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formPrice, setFormPrice] = useState("19.99");
  const [formCurrency, setFormCurrency] = useState("EUR");
  const [formInStock, setFormInStock] = useState(true);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  async function load() {
    setLoadingProducts(true);
    setError("");
    try {
      const data = await apiGet<Product[]>("/api/products/", token);
      setItems(data);
    } catch (e: any) {
      setError(String(e));
    } finally {
      setLoadingProducts(false);
    }
  }

  useEffect(() => {
    if (!isReady) return;
    if (!token) {
      router.replace("/login");
      return;
    }
    if (!isAdmin) return;
    load().catch(() => {});
  }, [isReady, token, isAdmin]);

  async function handleDelete(id: number) {
    if (!token) return;
    if (!confirm("Delete this product?")) return;
    try {
      await apiDelete<void>(`/api/products/${id}`, token);
      setItems((prev) => prev.filter((p) => p.id !== id));
    } catch (e: any) {
      alert(`Delete failed: ${String(e)}`);
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await load();
    } finally {
      setRefreshing(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;

    setCreateError("");

    const priceNum = parseFloat(formPrice);
    if (Number.isNaN(priceNum) || priceNum < 0) {
      return setCreateError("Price must be a non-negative number.");
    }
    if (!formSlug.trim() || !formName.trim()) {
      return setCreateError("Slug and name are required.");
    }

    setCreating(true);
    try {
      const payload = {
        slug: formSlug.trim(),
        name: formName.trim(),
        description: formDescription.trim() || null,
        price: priceNum,
        currency: formCurrency.trim() || "EUR",
        in_stock: formInStock,
      };

      const created = await apiPost<Product>("/api/products/", payload, token);

      setItems((prev) => [created, ...prev]);

      setFormSlug("");
      setFormName("");
      setFormDescription("");
      setFormPrice("19.99");
      setFormCurrency("EUR");
      setFormInStock(true);
    } catch (e: any) {
      setCreateError(String(e));
    } finally {
      setCreating(false);
    }
  }

  if (!isReady) return null;

  if (token && !isAdmin) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-slate-100 px-4">
        <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-6 max-w-md w-full text-center">
          <h1 className="text-xl font-semibold mb-2">403 — Admin only</h1>
          <p className="text-sm text-slate-600 mb-4">
            Signed in as <span className="font-mono">{user?.email}</span> ({user?.role}).
          </p>
          <div className="flex gap-2 justify-center">
            <button
              onClick={logout}
              className="rounded-lg bg-slate-900 text-white text-sm font-medium px-4 py-2"
            >
              Log out
            </button>
            <a
              href="/"
              className="rounded-lg border border-slate-200 text-sm font-medium px-4 py-2 bg-white"
            >
              Back to store
            </a>
          </div>
        </div>
      </main>
    );
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#f9fafb",
        color: "#0f172a",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
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
            maxWidth: 1120,
            margin: "0 auto",
            padding: "12px 16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <a
              href="/"
              style={{
                fontSize: 13,
                textDecoration: "none",
                padding: "4px 10px",
                borderRadius: 999,
                border: "1px solid #e5e7eb",
                background: "#f9fafb",
                color: "#111827",
              }}
            >
              ← Back to storefront
            </a>
            <span
              style={{
                fontSize: 13,
                padding: "4px 10px",
                borderRadius: 999,
                background: "#eff6ff",
                color: "#1d4ed8",
              }}
            >
              Admin · Products
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {token && (
              <button
                type="button"
                onClick={logout}
                style={{
                  fontSize: 12,
                  padding: "4px 10px",
                  borderRadius: 999,
                  border: "1px solid #e5e7eb",
                  background: "#f9fafb",
                  cursor: "pointer",
                }}
              >
                Log out
              </button>
            )}
            <div style={{ fontSize: 12, color: "#6b7280", textAlign: "right" }}>
              {user?.email ? (
                <>
                  <span className="font-mono">{user.email}</span> · {user.role}
                  <br />
                </>
              ) : null}
              FastAPI admin demo · product_v1
            </div>
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "24px 16px 40px" }}>
        <section
          style={{
            marginBottom: 16,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <div>
            <h1 style={{ margin: 0, fontSize: 22 }}>Products admin</h1>
            <p style={{ margin: "4px 0 0", fontSize: 13, color: "#6b7280" }}>
              Admin-only mutations (create/delete) are protected by JWT + role check.
            </p>
          </div>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={refreshing}
            style={{
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#111827",
              color: "#ffffff",
              padding: "6px 12px",
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
        </section>

        <section
          style={{
            marginBottom: 20,
            borderRadius: 12,
            border: "1px solid #e5e7eb",
            background: "#ffffff",
            padding: 16,
          }}
        >
          <h2 style={{ margin: "0 0 8px", fontSize: 16 }}>Add product</h2>

          {createError && (
            <div
              style={{
                marginBottom: 8,
                padding: "6px 10px",
                borderRadius: 8,
                border: "1px solid #fca5a5",
                background: "#fef2f2",
                color: "#991b1b",
                fontSize: 12,
              }}
            >
              {createError}
            </div>
          )}

          <form
            onSubmit={handleCreate}
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 10,
              alignItems: "flex-start",
            }}
          >
            <div>
              <label style={{ fontSize: 12, fontWeight: 500 }}>Slug</label>
              <input
                value={formSlug}
                onChange={(e) => setFormSlug(e.target.value)}
                style={{
                  width: "100%",
                  padding: "6px 8px",
                  borderRadius: 6,
                  border: "1px solid #e5e7eb",
                  fontSize: 13,
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: 12, fontWeight: 500 }}>Name</label>
              <input
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                style={{
                  width: "100%",
                  padding: "6px 8px",
                  borderRadius: 6,
                  border: "1px solid #e5e7eb",
                  fontSize: 13,
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: 12, fontWeight: 500 }}>Price</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={formPrice}
                onChange={(e) => setFormPrice(e.target.value)}
                style={{
                  width: "100%",
                  padding: "6px 8px",
                  borderRadius: 6,
                  border: "1px solid #e5e7eb",
                  fontSize: 13,
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: 12, fontWeight: 500 }}>Currency</label>
              <input
                value={formCurrency}
                onChange={(e) => setFormCurrency(e.target.value)}
                style={{
                  width: "100%",
                  padding: "6px 8px",
                  borderRadius: 6,
                  border: "1px solid #e5e7eb",
                  fontSize: 13,
                }}
              />
            </div>

            <div style={{ gridColumn: "1 / -1" }}>
              <label style={{ fontSize: 12, fontWeight: 500 }}>Description</label>
              <textarea
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                rows={2}
                style={{
                  width: "100%",
                  padding: "6px 8px",
                  borderRadius: 6,
                  border: "1px solid #e5e7eb",
                  fontSize: 13,
                  resize: "vertical",
                }}
              />
            </div>

            <div
              style={{
                gridColumn: "1 / -1",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 8,
                marginTop: 4,
              }}
            >
              <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
                <input
                  type="checkbox"
                  checked={formInStock}
                  onChange={(e) => setFormInStock(e.target.checked)}
                  style={{ width: "auto" }}
                />
                In stock
              </label>

              <button
                type="submit"
                disabled={creating}
                style={{
                  borderRadius: 999,
                  border: "1px solid #111827",
                  background: "#111827",
                  color: "#ffffff",
                  padding: "6px 12px",
                  fontSize: 13,
                  cursor: "pointer",
                  minWidth: 120,
                }}
              >
                {creating ? "Creating…" : "Create product"}
              </button>
            </div>
          </form>
        </section>

        {loadingProducts && <p>Loading products…</p>}

        {error && (
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
            Failed to load products: {error}
          </div>
        )}

        {!loadingProducts && items.length > 0 && (
          <div
            style={{
              borderRadius: 12,
              border: "1px solid #e5e7eb",
              background: "#ffffff",
              overflow: "hidden",
            }}
          >
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                <tr>
                  <th style={{ textAlign: "left", padding: "8px 10px", fontWeight: 600 }}>ID</th>
                  <th style={{ textAlign: "left", padding: "8px 10px", fontWeight: 600 }}>Name</th>
                  <th style={{ textAlign: "left", padding: "8px 10px", fontWeight: 600 }}>Price</th>
                  <th style={{ textAlign: "left", padding: "8px 10px", fontWeight: 600 }}>Stock</th>
                  <th style={{ textAlign: "left", padding: "8px 10px", fontWeight: 600 }}>Featured</th>
                  <th style={{ textAlign: "right", padding: "8px 10px", fontWeight: 600 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((p) => (
                  <tr key={p.id} style={{ borderTop: "1px solid #f3f4f6" }}>
                    <td style={{ padding: "6px 10px", fontVariantNumeric: "tabular-nums" }}>{p.id}</td>
                    <td style={{ padding: "6px 10px" }}>
                      <div style={{ fontWeight: 500 }}>{p.name}</div>
                      <div
                        style={{
                          fontSize: 11,
                          color: "#6b7280",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          maxWidth: 260,
                        }}
                      >
                        {p.description || "No description"}
                      </div>
                    </td>
                    <td style={{ padding: "6px 10px" }}>{formatMoney(p.price, p.currency)}</td>
                    <td style={{ padding: "6px 10px" }}>{p.in_stock ? "In stock" : "Out of stock"}</td>
                    <td style={{ padding: "6px 10px" }}>{p.is_featured ? "⭐" : "—"}</td>
                    <td style={{ padding: "6px 10px", textAlign: "right" }}>
                      <a
                        href={`/products/${p.id}`}
                        style={{ fontSize: 12, marginRight: 8, textDecoration: "none", color: "#1d4ed8" }}
                      >
                        View
                      </a>
                      <button
                        type="button"
                        onClick={() => handleDelete(p.id)}
                        style={{
                          fontSize: 12,
                          borderRadius: 999,
                          border: "1px solid #fee2e2",
                          background: "#fef2f2",
                          color: "#b91c1c",
                          padding: "4px 8px",
                          cursor: "pointer",
                        }}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
