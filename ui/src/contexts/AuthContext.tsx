/**
 * AuthContext — session state for OmniView.
 *
 * Architecture (portable, per ecosystem guidance):
 *   - AuthContext.tsx = React Provider + state wiring
 *   - hooks/useAuth.ts = consumer hook (pure, no JSX)
 *   - components/auth/LoginForm.tsx = UI only (no business logic)
 *
 * On mount: calls GET /api/auth/me to rehydrate session from cookie.
 * On 401 event (from api.ts interceptor): clears user and redirects to /login.
 */
import {
  createContext,
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import * as api from "../lib/api";
import type { User } from "../types";

export interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const navigateRef = useRef(navigate);
  navigateRef.current = navigate;

  // Rehydrate on mount
  useEffect(() => {
    api.getMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  // Listen for 401 events emitted by api.ts interceptor
  useEffect(() => {
    const handle = () => {
      setUser(null);
      navigateRef.current("/login", { replace: true });
    };
    window.addEventListener("omniview:unauthorized", handle);
    return () => window.removeEventListener("omniview:unauthorized", handle);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const u = await api.login(username, password);
    setUser(u);
  }, []);

  const logout = useCallback(async () => {
    await api.logout();
    setUser(null);
    navigateRef.current("/login", { replace: true });
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
