import React, { createContext, useContext, useState, useEffect } from "react";

type AuthContextType = {
  token: string | null;
  login: (token: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const t = localStorage.getItem("VITE_CURRENT_USER_TOKEN");
    if (t) setToken(t);
  }, []);

  const login = (tok: string) => {
    localStorage.setItem("VITE_CURRENT_USER_TOKEN", tok);
    setToken(tok);
  };
  const logout = () => {
    localStorage.removeItem("VITE_CURRENT_USER_TOKEN");
    setToken(null);
  };

  return <AuthContext.Provider value={{ token, login, logout }}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
};
