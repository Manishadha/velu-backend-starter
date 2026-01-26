import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

type JwtUser = {
  email: string;
  role: string;
  exp?: number;
};

type AuthState = {
  token: string | null;
  user: JwtUser | null;
  isAdmin: boolean;
  isReady: boolean;
  setToken: (token: string | null) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

function decodeJwt(token: string): JwtUser | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    const email = String(payload?.sub || "");
    const role = String(payload?.role || "");
    const exp = typeof payload?.exp === "number" ? payload.exp : undefined;
    if (!email) return null;
    return { email, role, exp };
  } catch {
    return null;
  }
}

function isExpired(exp?: number): boolean {
  if (!exp) return false;
  const now = Math.floor(Date.now() / 1000);
  return exp <= now;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setTokenState] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  const setToken = (t: string | null) => {
    setTokenState(t);
    if (typeof window !== "undefined") {
      if (t) localStorage.setItem("velu_token", t);
      else localStorage.removeItem("velu_token");
    }
  };

  const logout = () => setToken(null);

  useEffect(() => {
    try {
      const t = typeof window !== "undefined" ? localStorage.getItem("velu_token") : null;
      setTokenState(t || null);
    } finally {
      setIsReady(true);
    }
  }, []);

  const user = useMemo(() => (token ? decodeJwt(token) : null), [token]);

  useEffect(() => {
    if (!user) return;
    if (isExpired(user.exp)) logout();
  }, [user]);

  const value = useMemo<AuthState>(() => {
    const isAdmin = !!user && user.role === "admin";
    return { token, user, isAdmin, isReady, setToken, logout };
  }, [token, user, isReady]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider />");
  return ctx;
}
