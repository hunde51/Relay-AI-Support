import React, { createContext, useContext, useState, useEffect } from "react";

type AuthContextType = {
  token: string | null;
  userId: string | null;
  organizationId: string | null;
  role: string | null;
  login: (payload: { token: string; userId: string; organizationId: string; role: string }) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [token, setToken] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);

  useEffect(() => {
    const t = localStorage.getItem("VITE_CURRENT_USER_TOKEN");
    const u = localStorage.getItem("VITE_CURRENT_USER_ID");
    const o = localStorage.getItem("VITE_CURRENT_USER_ORG");
    const r = localStorage.getItem("VITE_CURRENT_USER_ROLE");
    if (t) setToken(t);
    if (u) setUserId(u);
    if (o) setOrganizationId(o);
    if (r) setRole(r);
  }, []);

  const login = (payload: { token: string; userId: string; organizationId: string; role: string }) => {
    localStorage.setItem("VITE_CURRENT_USER_TOKEN", payload.token);
    localStorage.setItem("VITE_CURRENT_USER_ID", payload.userId);
    localStorage.setItem("VITE_CURRENT_USER_ORG", payload.organizationId);
    localStorage.setItem("VITE_CURRENT_USER_ROLE", payload.role);
    setToken(payload.token);
    setUserId(payload.userId);
    setOrganizationId(payload.organizationId);
    setRole(payload.role);
  };
  const logout = () => {
    localStorage.removeItem("VITE_CURRENT_USER_TOKEN");
    localStorage.removeItem("VITE_CURRENT_USER_ID");
    localStorage.removeItem("VITE_CURRENT_USER_ORG");
    localStorage.removeItem("VITE_CURRENT_USER_ROLE");
    setToken(null);
    setUserId(null);
    setOrganizationId(null);
    setRole(null);
  };

  return <AuthContext.Provider value={{ token, userId, organizationId, role, login, logout }}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
};
